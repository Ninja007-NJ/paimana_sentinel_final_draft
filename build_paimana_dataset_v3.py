#!/usr/bin/env python3
"""PAIMANA dataset builder v3.

This module intentionally builds on ``build_paimana_dataset_fixed.py`` without
modifying it.  It replaces only the audited transition/PAIMANA table parser and
the downstream cleaning, quality and target-building stages.
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pdfplumber
from dateutil.relativedelta import relativedelta

import build_paimana_dataset_fixed as base


AUDIT_MONTHS = {"2025-07", "2025-08", "2025-09", "2025-10", "2025-11"}
STABLE_METADATA = ("project_name", "sector", "state", "ministry_department", "agency")
COST_ESCALATION_THRESHOLD = 0.01

RAW_FIELDS = list(base.RAW_FIELDS)
for field in ("reporting_regime", "current_target_source", "current_cost_source"):
    if field not in RAW_FIELDS:
        RAW_FIELDS.append(field)
TRAIN_FIELDS = list(base.TRAIN_FIELDS)
for field in (
    "valid_delay_target_3m", "valid_delay_target_6m",
    "valid_cost_target_3m", "valid_cost_target_6m",
):
    if field not in TRAIN_FIELDS:
        TRAIN_FIELDS.append(field)


def flat_text(value) -> str:
    """Normalize user-facing categorical text to one whitespace-clean line."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", base.clean_text(value)).strip()


def month_date(value) -> Optional[date]:
    """Parse supported dates and return their first calendar day of month."""
    if isinstance(value, datetime):
        return date(value.year, value.month, 1)
    if isinstance(value, date):
        return date(value.year, value.month, 1)
    if value is None:
        return None
    s = base.clean_text(value)
    if not s or base.norm_key(s) in base.MISSING:
        return None
    patterns = (
        (r"\b\d{4}-\d{1,2}-\d{1,2}\b", "%Y-%m-%d"),
        (r"\b\d{1,2}-\d{1,2}-\d{4}\b", "%d-%m-%Y"),
        (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "%d/%m/%Y"),
        (r"\b\d{1,2}/\d{4}\b", "%m/%Y"),
        (r"\b\d{1,2}-\d{4}\b", "%m-%Y"),
    )
    for pattern, fmt in patterns:
        match = re.search(pattern, s)
        if not match:
            continue
        try:
            parsed = datetime.strptime(match.group(), fmt).date()
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue
    return None


def date_tokens(value) -> List[Tuple[str, date]]:
    """Extract supported dates in source order without overlapping matches."""
    s = base.clean_text(value)
    patterns = (
        (r"\b\d{4}-\d{1,2}-\d{1,2}\b", "%Y-%m-%d"),
        (r"\b\d{1,2}-\d{1,2}-\d{4}\b", "%d-%m-%Y"),
        (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "%d/%m/%Y"),
        (r"\b\d{1,2}/\d{4}\b", "%m/%Y"),
        (r"\b\d{1,2}-\d{4}\b", "%m-%Y"),
    )
    found = []
    spans = []
    for pattern, fmt in patterns:
        for match in re.finditer(pattern, s):
            if any(a < match.end() and match.start() < b for a, b in spans):
                continue
            try:
                parsed = datetime.strptime(match.group(), fmt).date()
            except ValueError:
                continue
            found.append((match.start(), match.group(), date(parsed.year, parsed.month, 1)))
            spans.append(match.span())
    return [(raw, parsed) for _, raw, parsed in sorted(found)]


# The inherited split helpers resolve these functions through base's globals.
base.month_date = month_date
base.date_tokens = date_tokens


def reporting_regime(snapshot_month: str) -> str:
    if snapshot_month <= "2025-06":
        return "OCMS_LEGACY"
    if snapshot_month <= "2025-08":
        return "PAIMANA_TRANSITION"
    return "PAIMANA"


def choose_current_fields_v3(row: Dict):
    """Select current target/cost and retain the exact source-field provenance."""
    target_candidates = (
        ("ANTICIPATED", month_date(row.get("anticipated_doc"))),
        ("REVISED", month_date(row.get("revised_doc"))),
        ("ORIGINAL", month_date(row.get("original_doc"))),
    )
    target_source, target = next(
        ((source, value) for source, value in target_candidates if value is not None),
        ("MISSING", None),
    )
    cost_candidates = (
        ("ANTICIPATED", row.get("anticipated_cost_cr")),
        ("REVISED", row.get("revised_cost_cr")),
        ("ORIGINAL", row.get("original_cost_cr")),
    )
    cost_source, cost = next(
        ((source, value) for source, value in cost_candidates if value is not None),
        ("MISSING", None),
    )
    row["current_target_doc"] = base.iso(target)
    row["current_target_source"] = target_source
    row["current_forecast_cost_cr"] = cost
    row["current_cost_source"] = cost_source
    row["reporting_regime"] = reporting_regime(row["snapshot_month"])


base.choose_current_fields = choose_current_fields_v3


def _best_header(table: List[List[str]]) -> Tuple[int, List[str], int]:
    """Prefer the populated header row when a page-wide title ties its score."""
    candidates = []
    for i, row in enumerate(table[:10]):
        score = base.table_header_score(row)
        populated = sum(bool(base.clean_text(cell)) for cell in row)
        candidates.append((score, populated, i))
    _, _, best_i = max(candidates, default=(0, 0, 0))
    headers = [base.clean_text(cell) for cell in table[best_i]]
    data_start = best_i + 1
    if data_start < len(table) and base.table_header_score(table[data_start]) >= 2:
        next_row = table[data_start]
        width = max(len(headers), len(next_row))
        headers = [
            flat_text(
                f"{headers[i] if i < len(headers) else ''} "
                f"{next_row[i] if i < len(next_row) else ''}"
            )
            for i in range(width)
        ]
        data_start += 1
    return best_i, headers, data_start


def _find_header_col(headers: List[str], *needles: str) -> Optional[int]:
    """Choose the narrowest matching header cell, avoiding page-spanning cells."""
    matches = []
    for index, header in enumerate(headers):
        key = base.norm_key(header)
        if all(needle in key for needle in needles):
            matches.append((len(key.split()), len(key), index))
    return min(matches)[2] if matches else None


def parse_new_table_v3(
    table: List[List[str]], spec: base.ReportSpec, pdf_url: str, page_no: int,
    current_ministry: str, current_sector: str,
) -> Tuple[List[Dict], str, str]:
    """Parse the complete PAIMANA All Ongoing Projects table."""
    rows = []
    if not table:
        return rows, current_ministry, current_sector
    _, headers, data_start = _best_header(table)

    idx_sl = _find_header_col(headers, "sl")
    idx_project = _find_header_col(headers, "project", "name")
    idx_state = _find_header_col(headers, "state")
    idx_approval = _find_header_col(headers, "approval")
    idx_doc = _find_header_col(headers, "doc")
    if idx_doc is None:
        idx_doc = _find_header_col(headers, "completion")
    idx_cost = _find_header_col(headers, "cost")
    idx_exp = _find_header_col(headers, "expenditure")
    idx_prog = _find_header_col(headers, "physical")

    # Border-only columns occur on some transition pages.  Infer positions from
    # the actual populated header, rather than assuming column zero is Sl.No.
    if idx_project is None:
        populated = [i for i, value in enumerate(headers) if base.clean_text(value)]
        if len(populated) >= 7:
            idx_sl, idx_project, idx_state, idx_approval, idx_doc, idx_cost = populated[:6]
            idx_exp = populated[6]
            idx_prog = populated[7] if len(populated) > 7 else None

    for source_row in table[data_start:]:
        row = [base.clean_text(cell) for cell in source_row]
        current_ministry, current_sector = base.parse_heading_row(
            row, current_ministry, current_sector
        )
        if idx_sl is None or idx_sl >= len(row):
            continue
        serial = base.clean_text(row[idx_sl])
        if not re.fullmatch(r"\d{1,5}", serial):
            continue
        if idx_project is None or idx_project >= len(row):
            continue
        project = base.parse_project_cell(row[idx_project])
        if not project["project_name"]:
            continue

        out = base.canonical_row_base(spec, pdf_url, page_no)
        out.update(project)
        out["_source_serial_no"] = int(serial)
        out["ministry_department"] = current_ministry
        out["sector"] = current_sector
        out["state"] = row[idx_state] if idx_state is not None and idx_state < len(row) else ""

        approval_cell = row[idx_approval] if idx_approval is not None and idx_approval < len(row) else ""
        a_raw, a_dt, s_raw, s_dt = base.split_two_dates(approval_cell)
        out.update({
            "approval_date_raw": a_raw, "approval_date": base.iso(a_dt),
            "start_date_raw": s_raw, "start_date": base.iso(s_dt),
        })
        doc_cell = row[idx_doc] if idx_doc is not None and idx_doc < len(row) else ""
        o_raw, o_dt, r_raw, r_dt = base.split_two_dates(doc_cell)
        out.update({
            "original_doc_raw": o_raw, "original_doc": base.iso(o_dt),
            "revised_doc_raw": r_raw, "revised_doc": base.iso(r_dt),
            "anticipated_doc_raw": "", "anticipated_doc": "",
        })
        cost_cell = row[idx_cost] if idx_cost is not None and idx_cost < len(row) else ""
        costs = base.split_costs(cost_cell, 2)
        out.update({
            "original_cost_cr": costs[0], "revised_cost_cr": costs[1],
            "anticipated_cost_cr": None,
            "cumulative_expenditure_cr": base.to_float(row[idx_exp]) if idx_exp is not None and idx_exp < len(row) else None,
            "physical_progress_pct": base.to_float(row[idx_prog]) if idx_prog is not None and idx_prog < len(row) else None,
            "raw_row_text": " | ".join(row),
        })
        rows.append(out)
    return rows, current_ministry, current_sector


def _project_page(text: str, spec: base.ReportSpec) -> bool:
    if spec.parser_mode != "new_all_ongoing":
        return base.page_is_relevant(text, spec)
    key = base.norm_key(text)
    return (
        "all ongoing projects" in key
        and "project name" in key
        and "physical progress" in key
        and ("sl no" in key or "slno" in key)
    )


def _row_key(row: Dict) -> Tuple:
    if row.get("_source_serial_no"):
        return row.get("snapshot_month"), int(row["_source_serial_no"])
    stable_id = row.get("paimana_project_code") or row.get("legacy_ocms_code")
    if stable_id:
        return row.get("snapshot_month"), stable_id
    return (
        row.get("snapshot_month"), base.norm_key(row.get("project_name", "")),
        base.norm_key(row.get("state", "")), row.get("_source_serial_no", ""),
    )


def parse_pdf_v3(pdf_path: Path, spec: base.ReportSpec, source_url: str):
    """Parse once, while auditing old/new transition-parser counts in-place."""
    new_rows, old_rows, new_candidates = [], [], []
    new_seen, old_seen = set(), set()
    stats = {
        "pages_total": 0, "pages_relevant": 0, "tables_seen": 0,
        "rows_parsed": 0, "before_rows": 0, "declared_project_count": 0,
    }
    new_ministry = new_sector = old_ministry = old_sector = ""
    with pdfplumber.open(str(pdf_path)) as pdf:
        stats["pages_total"] = len(pdf.pages)
        for page_no, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            old_relevant = base.page_is_relevant(text, spec)
            new_relevant = _project_page(text, spec)
            if not old_relevant and not new_relevant:
                continue
            if new_relevant:
                stats["pages_relevant"] += 1
            for settings in base.table_settings_candidates():
                try:
                    tables = page.extract_tables(table_settings=settings) or []
                except Exception:
                    tables = []
                stats["tables_seen"] += len(tables)
                page_new, page_old = [], []
                for table in tables:
                    if spec.parser_mode == "legacy_table7":
                        parsed, new_ministry, new_sector = base.parse_legacy_table(
                            table, spec, source_url, page_no, new_ministry, new_sector
                        )
                        page_new.extend(parsed)
                    else:
                        if new_relevant:
                            parsed, new_ministry, new_sector = parse_new_table_v3(
                                table, spec, source_url, page_no, new_ministry, new_sector
                            )
                            page_new.extend(parsed)
                        if spec.snapshot_month in AUDIT_MONTHS and old_relevant:
                            parsed_old, old_ministry, old_sector = base.parse_new_table(
                                table, spec, source_url, page_no, old_ministry, old_sector
                            )
                            page_old.extend(parsed_old)
                for row in page_new:
                    new_candidates.append(row)
                    key = _row_key(row)
                    if key not in new_seen:
                        new_seen.add(key)
                        new_rows.append(row)
                for row in page_old:
                    key = (
                        row.get("snapshot_month"), row.get("paimana_project_code"),
                        row.get("legacy_ocms_code"), base.norm_key(row.get("project_name", "")),
                    )
                    if key not in old_seen:
                        old_seen.add(key)
                        old_rows.append(row)
                if page_new or page_old:
                    break
    serials = [int(r["_source_serial_no"]) for r in new_rows if r.get("_source_serial_no")]
    stats["declared_project_count"] = max(serials, default=0)
    stats["rows_parsed"] = len(new_rows)
    stats["before_rows"] = len(old_rows)
    stats["candidate_rows"] = len(new_candidates)
    stats["rows_dropped_by_deduplication"] = len(new_candidates) - len(new_rows)
    counts = Counter(serials)
    stats["unique_serials"] = len(counts)
    stats["duplicate_serials"] = sorted(serial for serial, count in counts.items() if count > 1)
    stats["missing_serials"] = sorted(set(range(1, max(serials, default=0) + 1)) - set(serials))
    return new_rows, stats


def _best_metadata_value(rows: List[Dict], field: str) -> str:
    values = [flat_text(r.get(field)) for r in rows if flat_text(r.get(field))]
    if not values:
        return ""
    frequency = Counter(base.norm_key(v) for v in values)
    # Mode first; completeness only breaks frequency ties; lexical ordering
    # makes the result reproducible when both are equal.
    return sorted(
        values,
        key=lambda v: (
            -frequency[base.norm_key(v)], -len(base.norm_key(v).split()),
            -len(v), v.casefold(), v,
        ),
    )[0]


def _append_flag(row: Dict, flag: str):
    flags = set(filter(None, str(row.get("quality_flags", "")).split(";")))
    flags.add(flag)
    row["quality_flags"] = ";".join(sorted(flags))


def disambiguate_code_collisions(rows: List[Dict]) -> int:
    """Retain distinct source rows that collide on an uncertain parsed code."""
    by_month_code = defaultdict(list)
    for row in rows:
        code = row.get("paimana_project_code") or row.get("legacy_ocms_code")
        if code:
            by_month_code[(row["snapshot_month"], code)].append(row)
    collision_rows = set()
    for values in by_month_code.values():
        identities = {
            (r.get("_source_serial_no"), base.norm_key(r.get("project_name")), base.norm_key(r.get("raw_project_cell")))
            for r in values
        }
        if len(identities) <= 1:
            continue
        for row in values:
            collision_rows.add(id(row))
            row["_identity_collision"] = True
            code = row.get("paimana_project_code") or row.get("legacy_ocms_code")
            suffix = base.hash_id(row.get("project_name", ""), row.get("raw_project_cell", "")).replace("NAME-", "")
            row["canonical_project_id"] = f"P-{code}-COLL-{suffix}"
            row["identity_confidence"] = min(float(row.get("identity_confidence") or 0.6), 0.70)
    return len(collision_rows)


def _quality(row: Dict, previous: Optional[Dict], metadata_inconsistent: bool) -> Tuple[int, List[str]]:
    score, inherited = base.quality_for_row(row, previous)
    flags = set(inherited)
    progress = row.get("physical_progress_pct")
    costs = [row.get(k) for k in ("original_cost_cr", "revised_cost_cr", "anticipated_cost_cr")]
    if progress is not None and progress > 100:
        flags.add("PHYSICAL_PROGRESS_GT_100")
    if any(value is not None and value < 0 for value in costs):
        flags.add("NEGATIVE_COST")
    if metadata_inconsistent:
        flags.add("METADATA_INCONSISTENCY")
    if row.get("_identity_collision"):
        flags.add("POSSIBLE_CODE_COLLISION")
    flags.update(row.get("_provenance_flags", set()))
    if previous:
        prior_progress = previous.get("physical_progress_pct")
        prior_cost = previous.get("current_forecast_cost_cr")
        cost = row.get("current_forecast_cost_cr")
        if (
            progress is not None and prior_progress is not None
            and prior_progress >= 20 and progress <= max(5, prior_progress * 0.25)
        ):
            flags.add("SUSPICIOUS_PROGRESS_RESET")
        if (
            cost is not None and prior_cost is not None and prior_cost > 0
            and cost >= 0 and cost < prior_cost * 0.25
        ):
            flags.add("SUSPICIOUS_COST_RESET")
    # Apply a small, transparent penalty for requested supplemental flags.
    supplemental = flags - set(inherited)
    score = max(0, score - 8 * len(supplemental))
    return score, sorted(flags)


def _same_number(left, right) -> bool:
    if left is None or right is None:
        return left is right
    return abs(float(left) - float(right)) <= max(0.01, 0.000001 * abs(float(left)))


def annotate_source_transitions(project_rows: List[Dict]):
    project_rows.sort(key=lambda r: r["snapshot_month"])
    previous = None
    for row in project_rows:
        row["_provenance_flags"] = set()
        row["_target_semantic_comparable"] = True
        row["_cost_semantic_comparable"] = True
        if previous is not None:
            regime_change = row["reporting_regime"] != previous["reporting_regime"]
            target_source_change = row["current_target_source"] != previous["current_target_source"]
            cost_source_change = row["current_cost_source"] != previous["current_cost_source"]
            if regime_change:
                row["_provenance_flags"].add("REPORTING_REGIME_CHANGE")
            if target_source_change:
                row["_provenance_flags"].add("TARGET_SOURCE_TRANSITION")
            if cost_source_change:
                row["_provenance_flags"].add("COST_SOURCE_TRANSITION")

            previous_target = month_date(previous.get("current_target_doc"))
            current_target = month_date(row.get("current_target_doc"))
            # A source/regime switch with an unchanged date is comparable.  A
            # changed date is semantically ambiguous and is excluded, rather
            # than guessed to be a new project delay.
            if (regime_change or target_source_change) and previous_target != current_target:
                row["_target_semantic_comparable"] = False
            if (regime_change or cost_source_change) and not _same_number(
                previous.get("current_forecast_cost_cr"), row.get("current_forecast_cost_cr")
            ):
                row["_cost_semantic_comparable"] = False
        previous = row


def finalize_rows_v3(rows: List[Dict], partial_months: set, scope_change_months: set):
    for row in rows:
        for field in STABLE_METADATA:
            row[field] = flat_text(row.get(field))
        base.choose_current_fields(row)
    base.assign_canonical_ids(rows)
    disambiguate_code_collisions(rows)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["canonical_project_id"]].append(row)

    for project_rows in grouped.values():
        inconsistent = False
        best = {}
        for field in STABLE_METADATA:
            observed = {base.norm_key(r.get(field)) for r in project_rows if flat_text(r.get(field))}
            inconsistent = inconsistent or len(observed) > 1
            best[field] = _best_metadata_value(project_rows, field)
        for row in project_rows:
            for field, value in best.items():
                if value:
                    row[field] = value

        annotate_source_transitions(project_rows)
        previous = None
        for row in project_rows:
            score, flags = _quality(row, previous, inconsistent)
            if row["snapshot_month"] in partial_months:
                flags.append("POSSIBLE_PARTIAL_EXTRACTION")
                score = max(0, score - 8)
            if row["snapshot_month"] in scope_change_months:
                flags.append("POSSIBLE_SCOPE_CHANGE")
                score = max(0, score - 2)
            row["quality_flags"] = ";".join(sorted(set(flags)))
            row["data_quality_score"] = score
            previous = row


def evaluate_future(rows: List[Dict], idx: int, horizon: int, kind: str):
    """Return label, continuous coverage, and an auditable exclusion reason."""
    start = base.snapshot_date(rows[idx]["snapshot_month"])
    by_month = {base.snapshot_date(r["snapshot_month"]): r for r in rows[idx + 1:]}
    required_dates = [start + relativedelta(months=offset) for offset in range(1, horizon + 1)]
    coverage = int(all(month in by_month for month in required_dates))
    if not coverage:
        return None, 0, "NO_FUTURE_COVERAGE"
    future = [by_month[month] for month in required_dates]
    current = rows[idx]
    if kind == "delay":
        baseline = month_date(current.get("current_target_doc"))
        values = [month_date(r.get("current_target_doc")) for r in future]
        if baseline is None or any(value is None for value in values):
            return None, 1, "MISSING_TARGET"
        semantic_rows = [current] + future
        if not current.get("_target_semantic_comparable", True) or any(
            not row.get("_target_semantic_comparable", True) for row in future
        ):
            if any("REPORTING_REGIME_CHANGE" in row.get("_provenance_flags", set()) for row in semantic_rows):
                return None, 1, "REPORTING_TRANSITION"
            return None, 1, "TARGET_SEMANTICS"
        return int(any(value > baseline for value in values)), 1, ""
    baseline = current.get("current_forecast_cost_cr")
    values = [r.get("current_forecast_cost_cr") for r in future]
    if baseline is None or any(value is None for value in values):
        return None, 1, "MISSING_TARGET"
    if baseline <= 0 or any(value <= 0 for value in values):
        return None, 1, "DATA_QUALITY"
    semantic_rows = [current] + future
    if not current.get("_cost_semantic_comparable", True) or any(
        not row.get("_cost_semantic_comparable", True) for row in future
    ):
        if any("REPORTING_REGIME_CHANGE" in row.get("_provenance_flags", set()) for row in semantic_rows):
            return None, 1, "REPORTING_TRANSITION"
        return None, 1, "TARGET_SEMANTICS"
    return int(any(value > baseline * (1 + COST_ESCALATION_THRESHOLD) for value in values)), 1, ""


def future_label_v3(rows: List[Dict], idx: int, horizon: int, kind: str, cost_threshold=0.01):
    label, coverage, _ = evaluate_future(rows, idx, horizon, kind)
    return label, coverage


base.future_label = future_label_v3


def build_training_rows_v3(rows: List[Dict]) -> List[Dict]:
    training = base.build_training_rows(rows)
    grouped_raw, grouped_training = defaultdict(list), defaultdict(list)
    for row in rows:
        grouped_raw[row["canonical_project_id"]].append(row)
    for row in training:
        grouped_training[row["canonical_project_id"]].append(row)
    for project_id, sequence in grouped_raw.items():
        sequence.sort(key=lambda r: r["snapshot_month"])
        target_rows = sorted(grouped_training[project_id], key=lambda r: r["snapshot_month"])
        for index, row in enumerate(target_rows):
            for kind, prefix in (("delay", "delay_event"), ("cost", "cost_escalation")):
                for horizon in (3, 6):
                    label, coverage, reason = evaluate_future(sequence, index, horizon, kind)
                    row[f"{prefix}_next_{horizon}m"] = label
                    row[f"future_coverage_{horizon}m"] = coverage
                    row[f"valid_{kind}_target_{horizon}m"] = int(label is not None)
                    row[f"_{kind}_exclusion_{horizon}m"] = reason
    return training


def write_csv(path: Path, rows: List[Dict], fields: Sequence[str]):
    base.write_csv(path, rows, fields)


def month_completeness(rows: List[Dict], parse_stats: Dict[str, Dict]) -> Tuple[List[Dict], set, set]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["snapshot_month"]].append(row)
    counts = {month: len(values) for month, values in grouped.items()}
    historical_reference = statistics.median(counts.values()) if counts else 0
    output, partial, scope_change = [], set(), set()
    for month in sorted(grouped):
        stats = parse_stats.get(month, {})
        declared = int(stats.get("declared_project_count") or 0)
        extracted = counts[month]
        serial_complete = (extracted / declared) if declared else None
        scope_ratio = extracted / historical_reference if historical_reference else None
        possible = bool(serial_complete is not None and serial_complete < 0.98)
        if possible:
            partial.add(month)
        scope = bool(scope_ratio is not None and scope_ratio < 0.65 and not possible)
        if scope:
            scope_change.add(month)
        unique_projects = len({r["canonical_project_id"] for r in grouped[month]})
        output.append({
            "snapshot_month": month,
            "project_month_rows": extracted,
            "unique_projects": unique_projects,
            "declared_project_count": declared or "",
            "serial_extraction_completeness_pct": round(100 * serial_complete, 2) if serial_complete is not None else "",
            "relative_scope_ratio": round(scope_ratio, 4) if scope_ratio is not None else "",
            "duplicate_project_months": extracted - unique_projects,
            "possible_partial_extraction": int(possible),
            "possible_scope_change": int(scope),
        })
    return output, partial, scope_change


def project_continuity(rows: List[Dict]) -> List[Dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["canonical_project_id"]].append(row)
    output = []
    for project_id, values in grouped.items():
        months = sorted({base.snapshot_date(r["snapshot_month"]) for r in values})
        span = (base.months_between(months[0], months[-1]) or 0) + 1
        missing = []
        cursor = months[0]
        observed = set(months)
        while cursor <= months[-1]:
            if cursor not in observed:
                missing.append(cursor.strftime("%Y-%m"))
            cursor += relativedelta(months=1)
        output.append({
            "canonical_project_id": project_id,
            "first_snapshot": months[0].strftime("%Y-%m"),
            "last_snapshot": months[-1].strftime("%Y-%m"),
            "observed_months": len(months),
            "calendar_span_months": span,
            "coverage_pct": round(100 * len(months) / span, 2),
            "missing_month_count": len(missing),
            "missing_months": ";".join(missing),
        })
    return sorted(output, key=lambda r: r["canonical_project_id"])


def build_extraction_audit(rows: List[Dict], parse_stats: Dict[str, Dict]):
    by_month = defaultdict(list)
    for row in rows:
        by_month[row["snapshot_month"]].append(row)
    audit, reconciliation = [], []
    for month in sorted(AUDIT_MONTHS):
        values = by_month.get(month, [])
        stats = parse_stats.get(month, {})
        declared = int(stats.get("declared_project_count") or 0)
        serial_counts = Counter(int(r["_source_serial_no"]) for r in values if r.get("_source_serial_no"))
        missing = sorted(set(range(1, declared + 1)) - set(serial_counts)) if declared else []
        duplicate_serials = {serial for serial, count in serial_counts.items() if count > 1}
        code_groups, canonical_groups = defaultdict(list), defaultdict(list)
        for row in values:
            code = row.get("paimana_project_code") or row.get("legacy_ocms_code")
            if code:
                code_groups[code].append(row)
            canonical_groups[row["canonical_project_id"]].append(row)
        duplicate_code_rows = {
            id(row) for group in code_groups.values() if len(group) > 1
            for row in group
        }
        duplicate_canonical_rows = {
            id(row) for group in canonical_groups.values() if len(group) > 1
            for row in group
        }
        issue_rows = []
        for row in values:
            issues = []
            if row.get("_source_serial_no") in duplicate_serials:
                issues.append("DUPLICATE_SERIAL")
            if id(row) in duplicate_code_rows:
                issues.append("DUPLICATE_PROJECT_CODE")
            if id(row) in duplicate_canonical_rows:
                issues.append("DUPLICATE_CANONICAL_ID")
            if row.get("_identity_collision"):
                issues.append("POSSIBLE_CODE_COLLISION")
            if issues:
                issue_rows.append(row)
                reconciliation.append({
                    "snapshot_month": month,
                    "issue_type": ";".join(sorted(set(issues))),
                    "source_serial_no": row.get("_source_serial_no", ""),
                    "paimana_project_code": row.get("paimana_project_code", ""),
                    "canonical_project_id": row.get("canonical_project_id", ""),
                    "source_page": row.get("source_page", ""),
                    "raw_project_cell": row.get("raw_project_cell", ""),
                    "raw_row_text": row.get("raw_row_text", ""),
                })
        for serial in missing:
            reconciliation.append({
                "snapshot_month": month, "issue_type": "MISSING_SERIAL",
                "source_serial_no": serial, "paimana_project_code": "",
                "canonical_project_id": "", "source_page": "",
                "raw_project_cell": "", "raw_row_text": "",
            })
        parsed, unique = len(values), len(serial_counts)
        dropped = int(stats.get("rows_dropped_by_deduplication") or 0)
        if declared and unique == declared and not duplicate_serials and not issue_rows and not dropped:
            status = "COMPLETE"
        elif declared and unique == declared and (duplicate_serials or issue_rows):
            status = "COMPLETE_WITH_SOURCE_DUPLICATES"
        elif missing:
            status = "PARTIAL_PARSER_ISSUE"
        elif declared:
            status = "PARTIAL_SOURCE_ISSUE"
        else:
            status = "REVIEW"
        unresolved = len(missing) + len(issue_rows) + dropped
        audit.append({
            "snapshot_month": month,
            "reporting_regime": reporting_regime(month),
            "declared_projects": declared,
            "parsed_rows": parsed,
            "unique_serials": unique,
            "duplicate_serial_count": sum(count - 1 for count in serial_counts.values() if count > 1),
            "missing_serial_count": len(missing),
            "extraction_completeness_pct": round(100 * unique / declared, 2) if declared else "",
            "unresolved_rows": unresolved,
            "audit_status": status,
            "missing_serial_numbers": ";".join(map(str, missing)),
            "duplicate_serial_numbers": ";".join(map(str, sorted(duplicate_serials))),
            "duplicate_project_code_count": sum(len(group) - 1 for group in code_groups.values() if len(group) > 1),
            "duplicate_canonical_id_count": sum(len(group) - 1 for group in canonical_groups.values() if len(group) > 1),
            "rows_dropped_by_deduplication": dropped,
        })
    return audit, reconciliation


def build_target_semantics_audit(rows: List[Dict]) -> List[Dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["canonical_project_id"]].append(row)
    output = []
    for project_id, values in grouped.items():
        values.sort(key=lambda r: r["snapshot_month"])
        for previous, current in zip(values, values[1:]):
            previous_target = month_date(previous.get("current_target_doc"))
            current_target = month_date(current.get("current_target_doc"))
            transition_window = previous["snapshot_month"] in {"2025-06", "2025-07"} or current["snapshot_month"] in {"2025-07", "2025-08"}
            changed = (
                previous_target != current_target
                or previous.get("current_target_source") != current.get("current_target_source")
                or previous.get("reporting_regime") != current.get("reporting_regime")
            )
            if not transition_window and not changed:
                continue
            comparable = bool(current.get("_target_semantic_comparable", True))
            reason = ""
            if not comparable:
                if previous.get("reporting_regime") != current.get("reporting_regime"):
                    reason = "REPORTING_REGIME_CHANGE"
                elif previous.get("current_target_source") != current.get("current_target_source"):
                    reason = "TARGET_SOURCE_TRANSITION"
                else:
                    reason = "TARGET_SEMANTICS_UNCERTAIN"
            if previous_target is None or current_target is None:
                comparable = False
                reason = "MISSING_TARGET"
            output.append({
                "project_id": project_id,
                "snapshot_month": current["snapshot_month"],
                "previous_target": base.iso(previous_target),
                "previous_target_source": previous.get("current_target_source", "MISSING"),
                "current_target": base.iso(current_target),
                "current_target_source": current.get("current_target_source", "MISSING"),
                "reporting_regime": current.get("reporting_regime", ""),
                "interpreted_change_months": base.months_between(previous_target, current_target),
                "semantic_comparable": int(comparable),
                "exclusion_reason": reason,
            })
    return output


def build_identity_audit(rows: List[Dict]) -> List[Dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["canonical_project_id"]].append(row)
    output = []
    for canonical_id, values in grouped.items():
        paimana = next((r.get("paimana_project_code") for r in values if r.get("paimana_project_code")), "")
        legacy = next((r.get("legacy_ocms_code") for r in values if r.get("legacy_ocms_code")), "")
        collision = any(r.get("_identity_collision") for r in values)
        if collision:
            source = "AMBIGUOUS_COLLISION"
        elif paimana:
            source = "PAIMANA_ID"
        elif legacy:
            source = "LEGACY_OCMS_ID"
        else:
            source = "FALLBACK_GENERATED"
        output.append({
            "canonical_project_id": canonical_id,
            "paimana_project_code": paimana,
            "legacy_ocms_code": legacy,
            "identity_source": source,
            "identity_confidence": min(float(r.get("identity_confidence") or 0) for r in values),
            "collision_flag": int(collision),
        })
    return sorted(output, key=lambda r: r["canonical_project_id"])


def severity_for_flags(flags: str) -> str:
    values = set(filter(None, str(flags).split(";")))
    critical = {"PHYSICAL_PROGRESS_GT_100", "NEGATIVE_COST", "PROGRESS_OUT_OF_RANGE"}
    warning = {
        "CUM_EXPENDITURE_DECREASE", "PROGRESS_DECREASE", "SUSPICIOUS_PROGRESS_RESET",
        "SUSPICIOUS_COST_RESET", "MISSING_TARGET_DATE", "METADATA_INCONSISTENCY",
        "POSSIBLE_PARTIAL_EXTRACTION", "POSSIBLE_CODE_COLLISION",
    }
    if values & critical:
        return "CRITICAL"
    if values & warning:
        return "WARNING"
    return "INFO"


def build_quality_output(rows: List[Dict]) -> List[Dict]:
    return [
        {
            "canonical_project_id": row["canonical_project_id"],
            "snapshot_month": row["snapshot_month"],
            "severity": severity_for_flags(row.get("quality_flags", "")),
            "data_quality_score": row.get("data_quality_score"),
            "quality_flags": row.get("quality_flags", ""),
            "source_url": row.get("source_url", ""),
            "source_page": row.get("source_page", ""),
        }
        for row in rows if row.get("quality_flags")
    ]


def build_label_audit(training: List[Dict]) -> List[Dict]:
    output = []
    for target_name, kind, horizon, field in (
        ("delay 3m", "delay", 3, "delay_event_next_3m"),
        ("delay 6m", "delay", 6, "delay_event_next_6m"),
        ("cost 3m", "cost", 3, "cost_escalation_next_3m"),
        ("cost 6m", "cost", 6, "cost_escalation_next_6m"),
    ):
        usable = [row for row in training if row.get(field) is not None]
        positives = sum(int(row[field]) == 1 for row in usable)
        reasons = Counter(row.get(f"_{kind}_exclusion_{horizon}m", "") for row in training if row.get(field) is None)
        output.append({
            "target_name": target_name,
            "usable_rows": len(usable),
            "positive_rows": positives,
            "negative_rows": len(usable) - positives,
            "positive_rate_pct": round(100 * positives / len(usable), 4) if usable else 0,
            "rows_excluded_no_future_coverage": reasons["NO_FUTURE_COVERAGE"],
            "rows_excluded_missing_target": reasons["MISSING_TARGET"],
            "rows_excluded_target_semantics": reasons["TARGET_SEMANTICS"],
            "rows_excluded_data_quality": reasons["DATA_QUALITY"],
            "rows_excluded_reporting_transition": reasons["REPORTING_TRANSITION"],
        })
    return output


def write_leakage_audit(path: Path):
    text = """# Leakage audit — PAIMANA dataset V3

No future observation is used in an engineered feature. Future rows are read only by the four label builders after the feature row at month `t` has been completed.

| Feature family | Data available at month t | Why leakage-safe |
|---|---|---|
| Identity and metadata | Current and repaired stable categorical observations | Repair uses only stable descriptive fields, never outcomes or time-varying numbers. |
| Project age / months to target | Approval/start and target reported at t | No later report is consulted. |
| Current slip / cost overrun / spend ratio | Original and current values reported at t | These are contemporaneous state variables. |
| Progress and spend deltas | Exact observations at t-1, t-3, or t-6 | `nearest_prior` requires the intended prior calendar month and never substitutes a future row. |
| Velocity / schedule pressure / stagnation | Current and prior observations only | Computed before future labels are evaluated. |
| Revision counts to date | Chronological observations through t | Counters are updated while walking forward and contain no later revisions. |
| Data-quality and provenance flags | Source rows through t | Transition flags compare t only with t-1. |
| Delay and cost labels | Strictly t+1..t+h | These columns are outcomes, not features; gaps or semantic ambiguity produce NaN. |

The model-specific CSVs retain only rows whose corresponding outcome is genuinely known. They must not feed label columns, validity flags, future-coverage fields, or future-derived audit fields into model features.

Do **not** use a random row-level train/test split. Use a temporal split for future evaluation, with optional group-aware checks by `canonical_project_id` to measure project memorization. No ML model was trained by this builder.
"""
    path.write_text(text, encoding="utf-8")


def _known(rows: List[Dict], field: str) -> List[Dict]:
    return [row for row in rows if row.get(field) is not None]


def _label_counts(rows: List[Dict], field: str) -> Tuple[int, int, int]:
    usable = _known(rows, field)
    positives = sum(int(row[field]) == 1 for row in usable)
    return len(usable), positives, len(usable) - positives


def make_summary(rows: List[Dict], training: List[Dict]) -> List[Dict]:
    grouped = defaultdict(set)
    for row in rows:
        grouped[row["canonical_project_id"]].add(row["snapshot_month"])
    target_known = sum(bool(month_date(row.get("current_target_doc"))) for row in rows)
    duplicate_count = len(rows) - len({(r["canonical_project_id"], r["snapshot_month"]) for r in rows})
    scores = [float(r["data_quality_score"]) for r in rows if r.get("data_quality_score") is not None]
    metrics = [
        ("total_cleaned_project_month_rows", len(rows)),
        ("unique_projects", len(grouped)),
        ("projects_with_ge_3_months_history", sum(len(v) >= 3 for v in grouped.values())),
        ("projects_with_ge_6_months_history", sum(len(v) >= 6 for v in grouped.values())),
        ("projects_with_ge_12_months_history", sum(len(v) >= 12 for v in grouped.values())),
        ("target_date_coverage_pct", round(100 * target_known / len(rows), 2) if rows else 0),
        ("duplicate_project_month_count", duplicate_count),
        ("average_data_quality_score", round(statistics.mean(scores), 2) if scores else ""),
    ]
    for label, field in (
        ("delay_3m", "delay_event_next_3m"), ("delay_6m", "delay_event_next_6m"),
        ("cost_3m", "cost_escalation_next_3m"), ("cost_6m", "cost_escalation_next_6m"),
    ):
        usable, positives, negatives = _label_counts(training, field)
        metrics.extend(((f"usable_{label}_rows", usable), (f"{label}_positives", positives), (f"{label}_negatives", negatives)))
    return [{"metric": metric, "value": value} for metric, value in metrics]


def _print_summary(rows: List[Dict], training: List[Dict], summary: List[Dict]):
    values = {item["metric"]: item["value"] for item in summary}
    print("\nFINAL VALIDATION SUMMARY")
    print(f"  Total cleaned project-month rows: {values['total_cleaned_project_month_rows']:,}")
    print(f"  Unique projects: {values['unique_projects']:,}")
    print("  Rows per month:")
    for month, count in sorted(Counter(r["snapshot_month"] for r in rows).items()):
        print(f"    {month}: {count:,}")
    print(f"  Projects with >=3 months history: {values['projects_with_ge_3_months_history']:,}")
    print(f"  Projects with >=6 months history: {values['projects_with_ge_6_months_history']:,}")
    print(f"  Projects with >=12 months history: {values['projects_with_ge_12_months_history']:,}")
    print(f"  Target date coverage: {values['target_date_coverage_pct']:.2f}%")
    for label in ("delay_3m", "delay_6m", "cost_3m", "cost_6m"):
        print(
            f"  Usable {label.replace('_', ' ')} rows: {values[f'usable_{label}_rows']:,} "
            f"(positives {values[f'{label}_positives']:,} / negatives {values[f'{label}_negatives']:,})"
        )
    print(f"  Duplicate project-month count: {values['duplicate_project_month_count']:,}")
    print(f"  Average data quality score: {values['average_data_quality_score']:.2f}")


def _flag_count(rows: List[Dict], flag: str) -> int:
    return sum(flag in set(filter(None, str(row.get("quality_flags", "")).split(";"))) for row in rows)


def print_full_summary(
    rows: List[Dict], summary: List[Dict], extraction: List[Dict],
    label_audit: List[Dict], semantics: List[Dict], identities: List[Dict],
    status: str, status_reasons: List[str],
):
    values = {item["metric"]: item["value"] for item in summary}
    labels = {item["target_name"]: item for item in label_audit}
    print("\nFINAL VALIDATION SUMMARY")
    print("\nExtraction")
    print(f"  Months parsed: {len(set(r['snapshot_month'] for r in rows))}")
    for month, count in sorted(Counter(r["snapshot_month"] for r in rows).items()):
        print(f"  {month}: {count:,} rows")
    for item in extraction:
        print(
            f"  {item['snapshot_month']} declared {item['declared_projects']:,}; "
            f"parsed {item['parsed_rows']:,}; completeness {item['extraction_completeness_pct']}%; "
            f"{item['audit_status']}"
        )
    print("\nDataset")
    print(f"  Total cleaned rows: {values['total_cleaned_project_month_rows']:,}")
    print(f"  Unique projects: {values['unique_projects']:,}")
    print(f"  Duplicate project-month count: {values['duplicate_project_month_count']:,}")
    print(f"  Target date coverage: {values['target_date_coverage_pct']:.2f}%")
    print(f"  Average data quality score: {values['average_data_quality_score']:.2f}")
    print("\nHistory")
    print(f"  Projects >=3 months: {values['projects_with_ge_3_months_history']:,}")
    print(f"  Projects >=6 months: {values['projects_with_ge_6_months_history']:,}")
    print(f"  Projects >=12 months: {values['projects_with_ge_12_months_history']:,}")
    for heading, names in (("Delay targets", ("delay 3m", "delay 6m")), ("Cost targets", ("cost 3m", "cost 6m"))):
        print(f"\n{heading}")
        for name in names:
            item = labels[name]
            print(
                f"  {name}: usable {item['usable_rows']:,}; positives {item['positive_rows']:,}; "
                f"negatives {item['negative_rows']:,}; positive rate {item['positive_rate_pct']:.2f}%"
            )
    target_transitions = sum("TARGET_SOURCE_TRANSITION" in r.get("quality_flags", "") for r in rows)
    semantic_exclusions = sum(
        labels[name]["rows_excluded_target_semantics"] + labels[name]["rows_excluded_reporting_transition"]
        for name in ("delay 3m", "delay 6m")
    )
    print("\nTarget semantics")
    print(f"  Target-source transitions: {target_transitions:,}")
    print(f"  Delay rows excluded for semantic ambiguity: {semantic_exclusions:,}")
    ambiguous = sum(i["identity_source"] in {"FALLBACK_GENERATED", "AMBIGUOUS_COLLISION"} for i in identities)
    collisions = sum(int(i["collision_flag"]) for i in identities)
    print("\nIdentity")
    print(f"  Ambiguous project IDs: {ambiguous:,}")
    print(f"  Collision count: {collisions:,}")
    print("\nQuality")
    print(f"  Physical progress >100: {_flag_count(rows, 'PHYSICAL_PROGRESS_GT_100'):,}")
    print(f"  Progress decreases: {_flag_count(rows, 'PROGRESS_DECREASE'):,}")
    print(f"  Expenditure decreases: {_flag_count(rows, 'CUM_EXPENDITURE_DECREASE'):,}")
    print(f"  Suspicious resets: {_flag_count(rows, 'SUSPICIOUS_PROGRESS_RESET') + _flag_count(rows, 'SUSPICIOUS_COST_RESET'):,}")
    print(f"  Partial extraction flags: {_flag_count(rows, 'POSSIBLE_PARTIAL_EXTRACTION'):,}")
    print(f"\nDATASET_STATUS={status}")
    for reason in status_reasons:
        print(f"  - {reason}")


def main():
    global COST_ESCALATION_THRESHOLD
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="paimana_dataset_v3")
    parser.add_argument("--pdf-dir", default="raw_pdfs")
    parser.add_argument("--start", default="2025-01")
    parser.add_argument("--end", default="2026-04")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--min-rows", type=int, default=50)
    parser.add_argument(
        "--cost-escalation-threshold-pct", type=float, default=1.0,
        help="Increase over the baseline current cost that defines escalation (default: 1%%)",
    )
    args = parser.parse_args()
    COST_ESCALATION_THRESHOLD = args.cost_escalation_threshold_pct / 100.0

    out_dir, pdf_dir = Path(args.out), Path(args.pdf_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = base.report_specs(args.start, args.end)
    session = base.session()
    all_rows, parse_stats = [], {}
    previous_counts = Counter()
    previous_path = Path("paimana_dataset") / "raw_snapshots.csv"
    if previous_path.exists():
        with previous_path.open("r", encoding="utf-8-sig", newline="") as handle:
            previous_counts.update(row.get("snapshot_month", "") for row in csv.DictReader(handle))
    print(f"Collecting {len(specs)} cached report months: {args.start}..{args.end}")
    for spec in specs:
        if args.local_only:
            path = pdf_dir / f"{spec.snapshot_month}.pdf"
            url = "LOCAL_CACHE"
            error = "" if path.exists() else "Local PDF missing"
            if not path.exists():
                path = None
        else:
            path, url, error = base.download_report(session, spec, pdf_dir)
        if not path:
            print(f"[{spec.snapshot_month}] SKIP: {error}")
            continue
        rows, stats = parse_pdf_v3(path, spec, url)
        parse_stats[spec.snapshot_month] = stats
        all_rows.extend(rows)
        print(
            f"[{spec.snapshot_month}] {len(rows):,} rows; "
            f"{stats['pages_relevant']}/{stats['pages_total']} project pages"
        )
        if spec.snapshot_month in AUDIT_MONTHS:
            before = previous_counts.get(spec.snapshot_month, stats["before_rows"])
            print(
                f"  PAIMANA parser before/after: {before:,} -> {len(rows):,}; "
                f"declared serial count: {stats['declared_project_count']:,}"
            )

    if not all_rows:
        print("No rows parsed from the cached PDFs.")
        sys.exit(2)

    # IDs are needed to assess month completeness; finalize again after partial
    # months are known so their requested flag contributes to the quality score.
    for row in all_rows:
        for field in STABLE_METADATA:
            row[field] = flat_text(row.get(field))
        base.choose_current_fields(row)
    base.assign_canonical_ids(all_rows)
    completeness, partial_months, scope_change_months = month_completeness(all_rows, parse_stats)
    finalize_rows_v3(all_rows, partial_months, scope_change_months)
    all_rows.sort(key=lambda r: (r["canonical_project_id"], r["snapshot_month"]))
    training = build_training_rows_v3(all_rows)

    delay3 = [r for r in training if r.get("valid_delay_target_3m") == 1]
    delay6 = [r for r in training if r.get("valid_delay_target_6m") == 1]
    cost3 = [r for r in training if r.get("valid_cost_target_3m") == 1]
    cost6 = [r for r in training if r.get("valid_cost_target_6m") == 1]
    continuity = project_continuity(all_rows)
    summary = make_summary(all_rows, training)
    extraction_audit, reconciliation = build_extraction_audit(all_rows, parse_stats)
    semantics_audit = build_target_semantics_audit(all_rows)
    identity_audit = build_identity_audit(all_rows)
    quality_output = build_quality_output(all_rows)
    label_audit = build_label_audit(training)

    identity_by_project = {row["canonical_project_id"]: row["identity_source"] for row in identity_audit}
    row_identity_counts = Counter(identity_by_project[r["canonical_project_id"]] for r in all_rows)
    ambiguous_projects = sum(
        row["identity_source"] in {"FALLBACK_GENERATED", "AMBIGUOUS_COLLISION"}
        for row in identity_audit
    )
    collision_count = sum(int(row["collision_flag"]) for row in identity_audit)
    semantic_exclusions = sum(
        item["rows_excluded_target_semantics"] + item["rows_excluded_reporting_transition"]
        for item in label_audit if item["target_name"].startswith("delay")
    )
    extra_metrics = [
        ("cost_escalation_threshold_pct", args.cost_escalation_threshold_pct),
        ("target_source_transition_rows", _flag_count(all_rows, "TARGET_SOURCE_TRANSITION")),
        ("semantic_ambiguity_delay_exclusions", semantic_exclusions),
        ("identity_rows_paimana_pct", round(100 * row_identity_counts["PAIMANA_ID"] / len(all_rows), 2)),
        ("identity_rows_legacy_ocms_pct", round(100 * row_identity_counts["LEGACY_OCMS_ID"] / len(all_rows), 2)),
        ("identity_rows_fallback_pct", round(100 * row_identity_counts["FALLBACK_GENERATED"] / len(all_rows), 2)),
        ("ambiguous_identity_count", ambiguous_projects),
        ("identity_collision_count", collision_count),
        ("physical_progress_gt_100_count", _flag_count(all_rows, "PHYSICAL_PROGRESS_GT_100")),
        ("progress_decrease_count", _flag_count(all_rows, "PROGRESS_DECREASE")),
        ("expenditure_decrease_count", _flag_count(all_rows, "CUM_EXPENDITURE_DECREASE")),
        ("suspicious_reset_count", _flag_count(all_rows, "SUSPICIOUS_PROGRESS_RESET") + _flag_count(all_rows, "SUSPICIOUS_COST_RESET")),
        ("partial_extraction_flag_count", _flag_count(all_rows, "POSSIBLE_PARTIAL_EXTRACTION")),
        ("possible_scope_change_flag_count", _flag_count(all_rows, "POSSIBLE_SCOPE_CHANGE")),
    ]
    summary.extend({"metric": metric, "value": value} for metric, value in extra_metrics)

    extraction_ok = all(
        item["audit_status"] in {"COMPLETE", "COMPLETE_WITH_SOURCE_DUPLICATES"}
        for item in extraction_audit
    )
    delay3_usable = next(item["usable_rows"] for item in label_audit if item["target_name"] == "delay 3m")
    ambiguous_row_pct = 100 * (
        row_identity_counts["FALLBACK_GENERATED"] + row_identity_counts["AMBIGUOUS_COLLISION"]
    ) / len(all_rows)
    if not extraction_ok or delay3_usable < 500 or ambiguous_row_pct > 30:
        status = "RED"
        status_reasons = []
        if not extraction_ok:
            status_reasons.append("One or more transition-month extraction audits remain incomplete.")
        if delay3_usable < 500:
            status_reasons.append("Trustworthy 3-month delay labels are too sparse for modeling.")
        if ambiguous_row_pct > 30:
            status_reasons.append("More than 30% of rows use ambiguous/generated identities.")
    elif semantic_exclusions or ambiguous_projects or collision_count or scope_change_months:
        status = "YELLOW"
        status_reasons = ["The audited dataset is usable, but documented source-regime caveats remain."]
        if semantic_exclusions:
            status_reasons.append(f"{semantic_exclusions:,} delay-horizon rows were conservatively excluded for semantic transitions.")
        if ambiguous_projects:
            status_reasons.append(f"{ambiguous_projects:,} project identities are generated or ambiguous and require group-aware review.")
        if scope_change_months:
            status_reasons.append("The July-November reporting population is a verified scope change, preserved as provenance.")
    else:
        status = "GREEN"
        status_reasons = ["Extraction, labels, target semantics, identity continuity, and leakage audits passed without material caveats."]
    summary.append({"metric": "dataset_status", "value": status})

    write_csv(out_dir / "raw_snapshots_clean.csv", all_rows, RAW_FIELDS)
    write_csv(out_dir / "training_master.csv", training, TRAIN_FIELDS)
    write_csv(out_dir / "training_delay_3m.csv", delay3, TRAIN_FIELDS)
    write_csv(out_dir / "training_delay_6m.csv", delay6, TRAIN_FIELDS)
    write_csv(out_dir / "training_cost_3m.csv", cost3, TRAIN_FIELDS)
    write_csv(out_dir / "training_cost_6m.csv", cost6, TRAIN_FIELDS)
    write_csv(out_dir / "month_completeness.csv", completeness, list(completeness[0]))
    write_csv(out_dir / "project_continuity.csv", continuity, list(continuity[0]))
    write_csv(out_dir / "extraction_audit.csv", extraction_audit, list(extraction_audit[0]))
    write_csv(
        out_dir / "extraction_reconciliation.csv", reconciliation,
        ("snapshot_month", "issue_type", "source_serial_no", "paimana_project_code", "canonical_project_id", "source_page", "raw_project_cell", "raw_row_text"),
    )
    write_csv(out_dir / "target_semantics_audit.csv", semantics_audit, list(semantics_audit[0]))
    write_csv(out_dir / "identity_audit.csv", identity_audit, list(identity_audit[0]))
    write_csv(out_dir / "quality_flags.csv", quality_output, list(quality_output[0]))
    write_csv(out_dir / "label_audit.csv", label_audit, list(label_audit[0]))
    write_csv(out_dir / "dataset_summary_v3.csv", summary, ("metric", "value"))
    write_leakage_audit(out_dir / "leakage_audit.md")

    date_fields = ("original_doc", "revised_doc", "anticipated_doc", "current_target_doc")
    print("\nDATE FIELD VALIDATION")
    for field in date_fields:
        count = sum(month_date(row.get(field)) is not None for row in all_rows)
        print(f"  {field}: {count:,}/{len(all_rows):,}")
    bad_target = sum(
        row.get("current_target_doc")
        != base.iso(month_date(row.get("anticipated_doc")) or month_date(row.get("revised_doc")) or month_date(row.get("original_doc")))
        for row in all_rows
    )
    print(f"  current_target_doc precedence violations: {bad_target:,}")
    print_full_summary(
        all_rows, summary, extraction_audit, label_audit, semantics_audit,
        identity_audit, status, status_reasons,
    )
    print(f"\nOutputs written to: {out_dir.resolve()}")
    print("No ML model was trained.")


if __name__ == "__main__":
    main()
