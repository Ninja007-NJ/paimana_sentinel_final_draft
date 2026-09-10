#!/usr/bin/env python3
"""
PAIMANA / OCMS longitudinal dataset builder for SIH PS 26103.

Goal
----
Build a leakage-safe project-month panel from official MoSPI/PAIMANA monthly
Flash Reports and derive 3/6-month early-warning labels for target-date
revision and cost escalation.

Outputs
-------
- raw_snapshots.csv          Canonical project-month observations
- project_master.csv         Crosswalk / one row per canonical project
- quality_flags.csv          Data-quality anomalies per project-month
- training_rows.csv          Leakage-safe engineered features + labels
- collection_log.csv         Source/download/parser audit log

Important scientific constraints
--------------------------------
1. A completion-date revision is treated as an administrative target-date
   deterioration signal; it is NOT assumed to be pure execution failure.
2. Counterfactual/what-if scenarios built from these features are predictive
   model responses, NOT causal guarantees.
3. Newer PAIMANA and legacy OCMS report schemas differ. Raw revised and
   anticipated fields are kept separate before a canonical current target is
   selected.
4. Never mix synthetic rows into the real test set.

The collector is designed to be auditable. Every row keeps source URL,
report month and raw source cell text.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

import requests
import pdfplumber
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36 "
    "PAIMANA-SIH-research/1.0"
)

MISSING = {"", "-", "--", "na", "n.a", "n.a.", "nil", "none", "null", "not available"}

# Direct URLs are official MoSPI / IPM / PAIMANA sources that were located and
# checked during the feasibility audit. May-Jul 2026 are deliberately resolved
# from the official portal at run time because the portal's generated file URLs
# can change.
REPORTS = [
    ("2025-01", "OCMS legacy", "legacy_table7", [
        "https://ipm.mospi.gov.in/Content/PDF/FlashReportJanuary.pdf",
    ]),
    ("2025-02", "OCMS legacy", "legacy_table7", [
        "https://ipm.mospi.gov.in/Content/PDF/FRFebruary2025.pdf",
    ]),
    ("2025-03", "OCMS legacy", "legacy_table7", [
        "https://ipm.mospi.gov.in/Content/pdf/FRMarch2025.pdf",
    ]),
    ("2025-04", "OCMS legacy", "legacy_table7", [
        "https://www.mospi.gov.in/sites/default/files/publication_reports/FRApril2025_0.pdf",
    ]),
    ("2025-05", "OCMS legacy", "legacy_table7", [
        "https://www.mospi.gov.in/sites/default/files/publication_reports/FR_May2025_0.pdf",
    ]),
    ("2025-06", "OCMS legacy", "legacy_table7", [
        "https://www.mospi.gov.in/sites/default/files/publication_reports/FR_JUNE_2025.pdf",
    ]),
    ("2025-07", "PAIMANA transition", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Content/ArchiveReport/flash/2025-26/FlashReport_July_2025.pdf",
    ]),
    ("2025-08", "PAIMANA transition", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Content/ArchiveReport/flash/2025-26/FlashReport_August_2025.pdf",
    ]),
    ("2025-09", "PAIMANA", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Content/ArchiveReport/flash/2025-26/FlashReport_September_2025.pdf",
        "https://www.mospi.gov.in/sites/default/files/publication_reports/FlashReport_September_2025.pdf",
    ]),
    ("2025-10", "PAIMANA", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Content/ArchiveReport/flash/2025-26/FlashReport_October_2025.pdf",
    ]),
    ("2025-11", "PAIMANA", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Home/ViewPdf/24?path=FlashReport_November_2025.pdf",
    ]),
    ("2025-12", "PAIMANA", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Content/PDF/FlashReport_December_2025.pdf",
    ]),
    ("2026-01", "PAIMANA", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Home/ViewPdf/28?path=FlashReport_January_2026.pdf",
    ]),
    ("2026-02", "PAIMANA", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Content/PDF/FlashReport_February_2026.pdf",
        "https://mospi.gov.in/uploads/publications_reports/publications_reports1774428614731_6be2b404-0d16-4d8b-9082-adb3e22c3194_FlashReport_February_2026.pdf",
    ]),
    ("2026-03", "PAIMANA", "new_all_ongoing", [
        "https://ipm.mospi.gov.in/Content/PDF/FlashReport_March_2026.pdf",
        "https://ipm.mospi.gov.in/Home/ViewPdf/31?path=FlashReport_March_2026.pdf",
    ]),
    ("2026-04", "PAIMANA", "new_all_ongoing", [
        "https://mospi.gov.in/uploads/publications_reports/publications_reports1779688125413_332125c5-1fb9-4d23-87ca-dd89fc14cd15_Flash_Report_April_2026.pdf",
    ]),
    ("2026-05", "PAIMANA", "new_all_ongoing", [
        "https://paimana-proj.mospi.gov.in/",
        "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2277758&lang=1",
    ]),
    ("2026-06", "PAIMANA", "new_all_ongoing", [
        "https://paimana-proj.mospi.gov.in/",
        "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2290413&lang=1",
    ]),
    ("2026-07", "PAIMANA-PROJ / CRIP", "new_all_ongoing", [
        "https://paimana-proj.mospi.gov.in/",
        "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2303115&lang=1",
    ]),
]

SECTOR_HINTS = {
    "roads & highways", "railways", "coal", "oil & gas", "steel",
    "metals & mining", "electricity generation", "transmission & distribution",
    "energy storage", "urban public transport", "aviation & aviation infrastructure",
    "ports", "shipping", "inland waterways", "telecommunication", "real estate",
    "education", "healthcare", "waste & water", "tourism", "logistics infrastructure",
    "water & sanitation", "communication", "social & commercial", "transport & logistics",
}

RAW_FIELDS = [
    "snapshot_month", "source_report", "source_url", "source_page", "format_family",
    "parser_mode", "canonical_project_id", "paimana_project_code", "legacy_ocms_code",
    "pmgid", "project_name", "agency", "ministry_department", "sector", "state",
    "approval_date_raw", "approval_date", "start_date_raw", "start_date",
    "original_doc_raw", "original_doc", "revised_doc_raw", "revised_doc",
    "anticipated_doc_raw", "anticipated_doc", "original_cost_cr", "revised_cost_cr",
    "anticipated_cost_cr", "cumulative_expenditure_cr", "physical_progress_pct",
    "current_target_doc", "current_forecast_cost_cr", "identity_confidence",
    "data_quality_score", "quality_flags", "raw_project_cell", "raw_row_text",
]

TRAIN_FIELDS = [
    "canonical_project_id", "snapshot_month", "sector", "state", "ministry_department",
    "project_age_months", "months_to_target", "current_time_slip_months",
    "current_cost_overrun_pct", "spend_ratio_pct", "physical_progress_pct",
    "financial_physical_gap_pct", "progress_delta_1m", "progress_delta_3m",
    "progress_delta_6m", "spend_delta_1m_cr", "spend_delta_3m_cr",
    "spend_delta_6m_cr", "progress_velocity_3m", "schedule_pressure",
    "stagnation_streak_months", "target_revision_count_to_date",
    "cost_revision_count_to_date", "data_quality_score", "missing_core_fields_count",
    "delay_event_next_3m", "delay_event_next_6m", "cost_escalation_next_3m",
    "cost_escalation_next_6m", "future_coverage_3m", "future_coverage_6m",
]


def clean_text(x) -> str:
    if x is None:
        return ""
    s = str(x).replace("\u00a0", " ").replace("\r", "\n")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def norm_key(x) -> str:
    s = clean_text(x).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_missing(x) -> bool:
    return norm_key(x) in MISSING


def to_float(x) -> Optional[float]:
    if x is None:
        return None
    s = clean_text(x)
    if not s or norm_key(s) in MISSING:
        return None
    s = s.replace(",", "").replace("₹", "")
    # Preserve leading minus only when actually numeric.
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def numeric_tokens(x) -> List[float]:
    s = clean_text(x).replace(",", "")
    out = []
    for tok in re.findall(r"[-+]?\d+(?:\.\d+)?", s):
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out


def month_date(value) -> Optional[date]:
    """Parse common report date forms and return first day of month."""
    if value is None:
        return None
    s = clean_text(value)
    if not s or norm_key(s) in MISSING:
        return None
    # Prefer explicit DD/MM/YYYY or DD-MM-YYYY.
    for pat, fmt in [
        (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "%d/%m/%Y"),
        (r"\b\d{1,2}-\d{1,2}-\d{4}\b", "%d-%m-%Y"),
        (r"\b\d{1,2}/\d{4}\b", "%m/%Y"),
        (r"\b\d{1,2}-\d{4}\b", "%m-%Y"),
    ]:
        m = re.search(pat, s)
        if m:
            try:
                dt = datetime.strptime(m.group(), fmt).date()
                return date(dt.year, dt.month, 1)
            except ValueError:
                pass
    return None


def date_tokens(value) -> List[Tuple[str, date]]:
    s = clean_text(value)
    toks = []
    patterns = [
        (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "%d/%m/%Y"),
        (r"\b\d{1,2}-\d{1,2}-\d{4}\b", "%d-%m-%Y"),
        (r"\b\d{1,2}/\d{4}\b", "%m/%Y"),
        (r"\b\d{1,2}-\d{4}\b", "%m-%Y"),
    ]
    spans = []
    for pat, fmt in patterns:
        for m in re.finditer(pat, s):
            if any(a <= m.start() < b for a, b in spans):
                continue
            try:
                d = datetime.strptime(m.group(), fmt).date()
                toks.append((m.group(), date(d.year, d.month, 1)))
                spans.append(m.span())
            except ValueError:
                pass
    toks.sort(key=lambda x: s.find(x[0]))
    return toks


def iso(d: Optional[date]) -> str:
    return d.isoformat() if d else ""


def months_between(a: Optional[date], b: Optional[date]) -> Optional[int]:
    """b - a in whole calendar months."""
    if not a or not b:
        return None
    return (b.year - a.year) * 12 + (b.month - a.month)


def snapshot_date(snapshot: str) -> date:
    return datetime.strptime(snapshot, "%Y-%m").date().replace(day=1)


def slug(s: str) -> str:
    s = norm_key(s)
    return re.sub(r"\s+", "-", s)[:100]


def hash_id(*parts: str) -> str:
    h = hashlib.sha1("|".join(norm_key(p) for p in parts).encode("utf-8")).hexdigest()[:12]
    return f"NAME-{h}"


def parenthetical_tokens(project_cell: str) -> List[str]:
    return [clean_text(x) for x in re.findall(r"\(([^()]*)\)", clean_text(project_cell))]


def parse_project_cell(cell: str) -> Dict[str, str]:
    text = clean_text(cell)
    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    joined = "\n".join(lines)

    paimana = ""
    legacy = ""
    pmgid = ""
    # Numeric project code usually 6 digits; PMG can also be numeric, so order
    # of parenthetical IDs is considered after the N-prefixed legacy code.
    nums = []
    for token in parenthetical_tokens(joined):
        if re.fullmatch(r"N\d{6,12}", token, re.I):
            legacy = token.upper()
        elif re.fullmatch(r"\d{5,8}", token):
            nums.append(token)
    if nums:
        paimana = nums[0]
        if len(nums) > 1:
            pmgid = nums[1]

    # Agency tends to be the first non-ID parenthetical token after project name.
    agency = ""
    for token in parenthetical_tokens(joined):
        if re.fullmatch(r"N\d+|\d+|-", token, re.I):
            continue
        if len(token) > 2:
            agency = token
            break

    # Project name: remove parenthetical chunks and code-only suffixes.
    name = re.sub(r"\([^()]*\)", " ", joined)
    name = re.sub(r"\s+", " ", name).strip(" -")
    return {
        "project_name": name,
        "agency": agency,
        "paimana_project_code": paimana,
        "legacy_ocms_code": legacy,
        "pmgid": pmgid,
        "raw_project_cell": text,
    }


def split_two_dates(cell: str) -> Tuple[str, Optional[date], str, Optional[date]]:
    toks = date_tokens(cell)
    if not toks:
        return "", None, "", None
    first = toks[0]
    second = toks[1] if len(toks) > 1 else ("", None)
    return first[0], first[1], second[0], second[1]


def split_three_dates(cell: str) -> Tuple[List[str], List[Optional[date]]]:
    toks = date_tokens(cell)[:3]
    raws = [t[0] for t in toks] + [""] * (3 - len(toks))
    vals = [t[1] for t in toks] + [None] * (3 - len(toks))
    return raws[:3], vals[:3]


def split_costs(cell: str, n=3) -> List[Optional[float]]:
    vals = numeric_tokens(cell)
    return (vals + [None] * n)[:n]


@dataclass
class ReportSpec:
    snapshot_month: str
    format_family: str
    parser_mode: str
    urls: List[str]


def report_specs(start: str, end: str) -> List[ReportSpec]:
    sd, ed = snapshot_date(start), snapshot_date(end)
    out = []
    for m, family, mode, urls in REPORTS:
        d = snapshot_date(m)
        if sd <= d <= ed:
            out.append(ReportSpec(m, family, mode, list(urls)))
    return out


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return s


def is_pdf_bytes(content: bytes, ctype: str = "") -> bool:
    return content[:4] == b"%PDF" or "application/pdf" in (ctype or "").lower()


def discover_pdf_links(sess: requests.Session, page_url: str, snapshot_month: str) -> List[str]:
    """Discover likely Flash Report PDF links from an official landing page."""
    year, month = snapshot_month.split("-")
    month_name = datetime.strptime(month, "%m").strftime("%B")
    try:
        r = sess.get(page_url, timeout=35)
        r.raise_for_status()
    except Exception:
        return []
    if is_pdf_bytes(r.content, r.headers.get("Content-Type", "")):
        return [r.url]
    soup = BeautifulSoup(r.text, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        href = urljoin(r.url, a["href"])
        label = clean_text(a.get_text(" ", strip=True))
        score_text = f"{label} {href}".lower()
        score = 0
        if "flash" in score_text:
            score += 3
        if month_name.lower() in score_text or f"_{month}_" in score_text or f"-{month}-" in score_text:
            score += 3
        if year in score_text:
            score += 2
        if ".pdf" in score_text or "viewpdf" in score_text:
            score += 3
        if score >= 5:
            candidates.append((score, href))
    return [u for _, u in sorted(set(candidates), reverse=True)]


def download_report(sess: requests.Session, spec: ReportSpec, pdf_dir: Path, retries=3) -> Tuple[Optional[Path], str, str]:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    local = pdf_dir / f"{spec.snapshot_month}.pdf"
    if local.exists() and local.stat().st_size > 10_000:
        return local, "LOCAL_CACHE", ""

    # First try direct URLs, then discover PDFs from HTML landing pages.
    todo = list(spec.urls)
    discovered = []
    for u in list(todo):
        if not u.lower().endswith(".pdf") and "viewpdf" not in u.lower():
            discovered.extend(discover_pdf_links(sess, u, spec.snapshot_month))
    todo = discovered + todo

    seen = set()
    for url in todo:
        if url in seen:
            continue
        seen.add(url)
        for attempt in range(1, retries + 1):
            try:
                r = sess.get(url, timeout=60, allow_redirects=True)
                if r.status_code == 200 and is_pdf_bytes(r.content, r.headers.get("Content-Type", "")):
                    local.write_bytes(r.content)
                    return local, r.url, ""
                err = f"HTTP {r.status_code}; content-type={r.headers.get('Content-Type','')}"
            except Exception as e:
                err = repr(e)
            time.sleep(min(2 ** attempt, 8))
    return None, "", err if 'err' in locals() else "No PDF URL resolved"


def table_settings_candidates():
    return [
        {"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 4, "join_tolerance": 4},
        {"vertical_strategy": "text", "horizontal_strategy": "text", "intersection_tolerance": 8, "text_tolerance": 3},
    ]


def table_header_score(row: Sequence[str]) -> int:
    s = " | ".join(norm_key(c) for c in row)
    terms = ["project name", "state", "approval", "cost", "expenditure", "physical progress", "doc", "commission"]
    return sum(t in s for t in terms)


def find_col(headers: List[str], *needles: str) -> Optional[int]:
    for i, h in enumerate(headers):
        hk = norm_key(h)
        if all(n in hk for n in needles):
            return i
    return None


def nonempty_cells(row: Sequence[str]) -> List[str]:
    return [clean_text(c) for c in row if clean_text(c)]


def parse_heading_row(row: Sequence[str], current_ministry: str, current_sector: str) -> Tuple[str, str]:
    vals = nonempty_cells(row)
    if len(vals) != 1:
        return current_ministry, current_sector
    v = vals[0]
    vk = norm_key(v)
    if vk.startswith("ministry ") or vk.startswith("department ") or "ministry of" in vk:
        return v, current_sector
    if vk in SECTOR_HINTS or any(h in vk for h in SECTOR_HINTS):
        return current_ministry, v
    return current_ministry, current_sector


def canonical_row_base(spec: ReportSpec, pdf_url: str, page_no: int) -> Dict[str, object]:
    return {
        "snapshot_month": spec.snapshot_month,
        "source_report": f"Flash Report {spec.snapshot_month}",
        "source_url": pdf_url,
        "source_page": page_no,
        "format_family": spec.format_family,
        "parser_mode": spec.parser_mode,
    }


def parse_new_table(table: List[List[str]], spec: ReportSpec, pdf_url: str, page_no: int,
                    current_ministry: str, current_sector: str) -> Tuple[List[Dict], str, str]:
    rows = []
    if not table:
        return rows, current_ministry, current_sector

    # Identify the best header row; often the header spans two or more PDF rows.
    best_i, best_score = 0, -1
    for i, r in enumerate(table[:8]):
        sc = table_header_score(r)
        if sc > best_score:
            best_i, best_score = i, sc

    headers = [clean_text(c) for c in table[best_i]]
    # Some extractors split header over adjacent rows. Combine by column.
    if best_i + 1 < len(table) and table_header_score(table[best_i + 1]) >= 2:
        nxt = table[best_i + 1]
        headers = [clean_text(headers[i] if i < len(headers) else "") + " " + clean_text(nxt[i] if i < len(nxt) else "") for i in range(max(len(headers), len(nxt)))]
        data_start = best_i + 2
    else:
        data_start = best_i + 1

    # Flexible column mapping.
    idx_sl = find_col(headers, "sl")
    idx_project = find_col(headers, "project", "name")
    idx_state = find_col(headers, "state")
    idx_approval = find_col(headers, "approval")
    idx_doc = find_col(headers, "doc")
    if idx_doc is None:
        idx_doc = find_col(headers, "completion")
    idx_cost = find_col(headers, "cost")
    idx_exp = find_col(headers, "expenditure")
    idx_prog = find_col(headers, "physical")

    # If mapping fails, use expected PAIMANA Table 6 order.
    if idx_project is None and len(headers) >= 7:
        idx_sl, idx_project, idx_state, idx_approval, idx_doc, idx_cost = 0, 1, 2, 3, 4, 5
        idx_exp = 6 if len(headers) > 6 else None
        idx_prog = 7 if len(headers) > 7 else None

    for r in table[data_start:]:
        r = [clean_text(c) for c in r]
        current_ministry, current_sector = parse_heading_row(r, current_ministry, current_sector)
        if idx_sl is None or idx_sl >= len(r):
            continue
        sl = clean_text(r[idx_sl])
        if not re.fullmatch(r"\d{1,5}", sl):
            continue
        if idx_project is None or idx_project >= len(r):
            continue
        project_cell = r[idx_project]
        p = parse_project_cell(project_cell)
        if not p["project_name"]:
            continue

        out = canonical_row_base(spec, pdf_url, page_no)
        out.update(p)
        out["ministry_department"] = current_ministry
        out["sector"] = current_sector
        out["state"] = r[idx_state] if idx_state is not None and idx_state < len(r) else ""

        approval_cell = r[idx_approval] if idx_approval is not None and idx_approval < len(r) else ""
        a_raw, a_dt, s_raw, s_dt = split_two_dates(approval_cell)
        out.update({"approval_date_raw": a_raw, "approval_date": iso(a_dt), "start_date_raw": s_raw, "start_date": iso(s_dt)})

        doc_cell = r[idx_doc] if idx_doc is not None and idx_doc < len(r) else ""
        o_raw, o_dt, rev_raw, rev_dt = split_two_dates(doc_cell)
        out.update({
            "original_doc_raw": o_raw, "original_doc": iso(o_dt),
            "revised_doc_raw": rev_raw, "revised_doc": iso(rev_dt),
            "anticipated_doc_raw": "", "anticipated_doc": "",
        })

        cost_cell = r[idx_cost] if idx_cost is not None and idx_cost < len(r) else ""
        c = split_costs(cost_cell, 2)
        out.update({"original_cost_cr": c[0], "revised_cost_cr": c[1], "anticipated_cost_cr": None})
        out["cumulative_expenditure_cr"] = to_float(r[idx_exp]) if idx_exp is not None and idx_exp < len(r) else None
        out["physical_progress_pct"] = to_float(r[idx_prog]) if idx_prog is not None and idx_prog < len(r) else None
        out["raw_row_text"] = " | ".join(r)
        rows.append(out)
    return rows, current_ministry, current_sector


def parse_legacy_table(table: List[List[str]], spec: ReportSpec, pdf_url: str, page_no: int,
                       current_ministry: str, current_sector: str) -> Tuple[List[Dict], str, str]:
    rows = []
    if not table:
        return rows, current_ministry, current_sector
    best_i, best_score = 0, -1
    for i, r in enumerate(table[:10]):
        sc = table_header_score(r)
        if sc > best_score:
            best_i, best_score = i, sc
    headers = [clean_text(c) for c in table[best_i]]

    idx_sl = find_col(headers, "sl")
    idx_project = find_col(headers, "project", "name")
    idx_state = find_col(headers, "state")
    idx_sector = find_col(headers, "sector")
    idx_approval = find_col(headers, "approval")
    idx_doc = find_col(headers, "commission")
    if idx_doc is None:
        idx_doc = find_col(headers, "completion")
    idx_cost = find_col(headers, "cost")
    idx_exp = find_col(headers, "expenditure")
    idx_prog = find_col(headers, "physical")

    # Legacy Table 7 commonly has State, Sector, Sl No, Project, Approval,
    # Commissioning dates, Cost, Expenditure, Physical progress.
    if idx_project is None and len(headers) >= 8:
        idx_state, idx_sector, idx_sl, idx_project, idx_approval, idx_doc, idx_cost = 0, 1, 2, 3, 4, 5, 6
        idx_exp = 7 if len(headers) > 7 else None
        idx_prog = 8 if len(headers) > 8 else None

    for r in table[best_i + 1:]:
        r = [clean_text(c) for c in r]
        current_ministry, current_sector = parse_heading_row(r, current_ministry, current_sector)
        if idx_sl is None or idx_sl >= len(r) or not re.fullmatch(r"\d{1,5}", clean_text(r[idx_sl])):
            continue
        project_cell = r[idx_project] if idx_project is not None and idx_project < len(r) else ""
        p = parse_project_cell(project_cell)
        if not p["project_name"]:
            continue
        out = canonical_row_base(spec, pdf_url, page_no)
        out.update(p)
        out["state"] = r[idx_state] if idx_state is not None and idx_state < len(r) else ""
        out["sector"] = r[idx_sector] if idx_sector is not None and idx_sector < len(r) else current_sector
        out["ministry_department"] = current_ministry

        approval_cell = r[idx_approval] if idx_approval is not None and idx_approval < len(r) else ""
        a_raw, a_dt, s_raw, s_dt = split_two_dates(approval_cell)
        out.update({"approval_date_raw": a_raw, "approval_date": iso(a_dt), "start_date_raw": s_raw, "start_date": iso(s_dt)})

        docs = r[idx_doc] if idx_doc is not None and idx_doc < len(r) else ""
        dr, dv = split_three_dates(docs)
        out.update({
            "original_doc_raw": dr[0], "original_doc": iso(dv[0]),
            "revised_doc_raw": dr[1], "revised_doc": iso(dv[1]),
            "anticipated_doc_raw": dr[2], "anticipated_doc": iso(dv[2]),
        })
        cost_cell = r[idx_cost] if idx_cost is not None and idx_cost < len(r) else ""
        c = split_costs(cost_cell, 3)
        out.update({"original_cost_cr": c[0], "revised_cost_cr": c[1], "anticipated_cost_cr": c[2]})
        out["cumulative_expenditure_cr"] = to_float(r[idx_exp]) if idx_exp is not None and idx_exp < len(r) else None
        out["physical_progress_pct"] = to_float(r[idx_prog]) if idx_prog is not None and idx_prog < len(r) else None
        out["raw_row_text"] = " | ".join(r)
        rows.append(out)
    return rows, current_ministry, current_sector


def page_is_relevant(text: str, spec: ReportSpec) -> bool:
    t = norm_key(text)
    if spec.parser_mode == "new_all_ongoing":
        return "all ongoing projects" in t
    return ("all ongoing" in t or "ongoing projects" in t) and ("project name" in t or "physical progress" in t)


def parse_pdf(pdf_path: Path, spec: ReportSpec, source_url: str) -> Tuple[List[Dict], Dict[str, int]]:
    all_rows = []
    stats = {"pages_total": 0, "pages_relevant": 0, "tables_seen": 0, "rows_parsed": 0}
    current_ministry, current_sector = "", ""
    seen_keys = set()

    with pdfplumber.open(str(pdf_path)) as pdf:
        stats["pages_total"] = len(pdf.pages)
        for pno, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            if not page_is_relevant(text, spec):
                continue
            stats["pages_relevant"] += 1
            page_rows = []
            for settings in table_settings_candidates():
                try:
                    tables = page.extract_tables(table_settings=settings) or []
                except Exception:
                    tables = []
                stats["tables_seen"] += len(tables)
                for table in tables:
                    if spec.parser_mode == "legacy_table7":
                        parsed, current_ministry, current_sector = parse_legacy_table(
                            table, spec, source_url, pno, current_ministry, current_sector
                        )
                    else:
                        parsed, current_ministry, current_sector = parse_new_table(
                            table, spec, source_url, pno, current_ministry, current_sector
                        )
                    page_rows.extend(parsed)
                if page_rows:
                    break

            for r in page_rows:
                key = (
                    r.get("snapshot_month"), r.get("paimana_project_code"),
                    r.get("legacy_ocms_code"), norm_key(r.get("project_name", "")),
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                all_rows.append(r)

    stats["rows_parsed"] = len(all_rows)
    return all_rows, stats


def choose_current_fields(row: Dict):
    # Legacy: anticipated value is a forecast and is usually the best current
    # target/cost; otherwise revised; otherwise original. New PAIMANA: revised
    # is latest reported revision, otherwise original.
    ad = month_date(row.get("anticipated_doc"))
    rd = month_date(row.get("revised_doc"))
    od = month_date(row.get("original_doc"))
    row["current_target_doc"] = iso(ad or rd or od)

    ac = row.get("anticipated_cost_cr")
    rc = row.get("revised_cost_cr")
    oc = row.get("original_cost_cr")
    row["current_forecast_cost_cr"] = ac if ac is not None else (rc if rc is not None else oc)


def quality_for_row(row: Dict, prev: Optional[Dict]) -> Tuple[int, List[str]]:
    flags, penalty = [], 0
    p = row.get("physical_progress_pct")
    exp = row.get("cumulative_expenditure_cr")
    oc = row.get("original_cost_cr")
    fc = row.get("current_forecast_cost_cr")
    target = month_date(row.get("current_target_doc"))
    snap = snapshot_date(row["snapshot_month"])

    def add(flag, pts):
        nonlocal penalty
        flags.append(flag); penalty += pts

    if p is None: add("MISSING_PROGRESS", 12)
    elif p < 0 or p > 100: add("PROGRESS_OUT_OF_RANGE", 25)
    if exp is None: add("MISSING_EXPENDITURE", 10)
    if oc is None: add("MISSING_ORIGINAL_COST", 8)
    if target is None: add("MISSING_TARGET_DATE", 12)
    if fc is not None and fc <= 0: add("NONPOSITIVE_FORECAST_COST", 15)
    if exp is not None and fc not in (None, 0) and exp > fc * 1.5: add("EXPENDITURE_GT_150PCT_COST", 8)
    if target and (target.year < 1990 or target.year > snap.year + 25): add("EXTREME_TARGET_DATE", 7)
    if prev:
        pp = prev.get("physical_progress_pct")
        pe = prev.get("cumulative_expenditure_cr")
        if p is not None and pp is not None:
            if p < pp - 1.0: add("PROGRESS_DECREASE", 12)
            if p > pp + 40: add("PROGRESS_JUMP_GT40", 8)
        if exp is not None and pe is not None and exp < pe - 0.01: add("CUM_EXPENDITURE_DECREASE", 12)
        if p is not None and pp is not None and abs(p-pp) < 0.01 and exp is not None and pe is not None and abs(exp-pe) < 0.01:
            add("POSSIBLE_STALE_UPDATE", 4)
    if not row.get("paimana_project_code") and not row.get("legacy_ocms_code"):
        add("NO_STABLE_PROJECT_CODE", 8)
    return max(0, 100 - penalty), flags


def assign_canonical_ids(rows: List[Dict]) -> Dict[str, str]:
    legacy_to_new = {}
    for r in rows:
        if r.get("legacy_ocms_code") and r.get("paimana_project_code"):
            legacy_to_new[r["legacy_ocms_code"]] = r["paimana_project_code"]

    for r in rows:
        pid = r.get("paimana_project_code") or ""
        legacy = r.get("legacy_ocms_code") or ""
        if pid:
            cid = f"P-{pid}"
            conf = 1.00
        elif legacy and legacy in legacy_to_new:
            cid = f"P-{legacy_to_new[legacy]}"
            conf = 0.98
        elif legacy:
            cid = f"L-{legacy}"
            conf = 0.95
        else:
            cid = hash_id(r.get("project_name", ""), r.get("agency", ""))
            conf = 0.60
        r["canonical_project_id"] = cid
        r["identity_confidence"] = conf
    return legacy_to_new


def finalize_rows(rows: List[Dict]):
    for r in rows:
        choose_current_fields(r)
    assign_canonical_ids(rows)
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["canonical_project_id"]].append(r)
    for proj_rows in grouped.values():
        proj_rows.sort(key=lambda x: x["snapshot_month"])
        prev = None
        for r in proj_rows:
            score, flags = quality_for_row(r, prev)
            r["data_quality_score"] = score
            r["quality_flags"] = ";".join(flags)
            prev = r


def nearest_prior(rows: List[Dict], idx: int, months: int) -> Optional[Dict]:
    target = snapshot_date(rows[idx]["snapshot_month"]) - relativedelta(months=months)
    for j in range(idx - 1, -1, -1):
        d = snapshot_date(rows[j]["snapshot_month"])
        if d == target:
            return rows[j]
        if d < target:
            break
    return None


def safe_sub(a, b):
    return None if a is None or b is None else a - b


def safe_pct(num, den):
    if num is None or den in (None, 0):
        return None
    return 100.0 * num / den


def changed_later_date(base: Optional[date], future: Optional[date]) -> bool:
    return bool(base and future and future > base)


def future_label(rows: List[Dict], idx: int, horizon: int, kind: str, cost_threshold=0.01) -> Tuple[Optional[int], int]:
    t = snapshot_date(rows[idx]["snapshot_month"])
    end = t + relativedelta(months=horizon)
    future = [r for r in rows[idx+1:] if snapshot_date(r["snapshot_month"]) <= end]
    max_seen = max([snapshot_date(r["snapshot_month"]) for r in rows[idx+1:]], default=None)
    coverage = int(bool(max_seen and max_seen >= end))
    if not coverage:
        return None, 0
    base = rows[idx]
    if kind == "delay":
        b = month_date(base.get("current_target_doc"))
        if b is None:
            return None, coverage
        event = any(changed_later_date(b, month_date(r.get("current_target_doc"))) for r in future)
    else:
        b = base.get("current_forecast_cost_cr")
        if b is None or b <= 0:
            return None, coverage
        event = any((r.get("current_forecast_cost_cr") is not None and r["current_forecast_cost_cr"] > b * (1 + cost_threshold)) for r in future)
    return int(event), coverage


def build_training_rows(rows: List[Dict]) -> List[Dict]:
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["canonical_project_id"]].append(r)
    out = []
    for cid, seq in grouped.items():
        seq.sort(key=lambda x: x["snapshot_month"])
        target_revisions = 0
        cost_revisions = 0
        prev_target = None
        prev_cost = None
        stagnation = 0
        for i, r in enumerate(seq):
            snap = snapshot_date(r["snapshot_month"])
            approval = month_date(r.get("approval_date")) or month_date(r.get("start_date"))
            target = month_date(r.get("current_target_doc"))
            original_doc = month_date(r.get("original_doc"))
            fc = r.get("current_forecast_cost_cr")
            oc = r.get("original_cost_cr")
            exp = r.get("cumulative_expenditure_cr")
            prog = r.get("physical_progress_pct")

            if prev_target and target and target != prev_target:
                target_revisions += 1
            if prev_cost is not None and fc is not None and abs(fc-prev_cost) > max(1.0, 0.001*abs(prev_cost)):
                cost_revisions += 1

            p1, p3, p6 = nearest_prior(seq, i, 1), nearest_prior(seq, i, 3), nearest_prior(seq, i, 6)
            pd1 = safe_sub(prog, p1.get("physical_progress_pct") if p1 else None)
            pd3 = safe_sub(prog, p3.get("physical_progress_pct") if p3 else None)
            pd6 = safe_sub(prog, p6.get("physical_progress_pct") if p6 else None)
            sd1 = safe_sub(exp, p1.get("cumulative_expenditure_cr") if p1 else None)
            sd3 = safe_sub(exp, p3.get("cumulative_expenditure_cr") if p3 else None)
            sd6 = safe_sub(exp, p6.get("cumulative_expenditure_cr") if p6 else None)

            if pd1 is not None and abs(pd1) < 0.5:
                stagnation += 1
            elif pd1 is not None:
                stagnation = 0

            spend_ratio = safe_pct(exp, fc)
            current_cost_overrun = None if oc in (None, 0) or fc is None else 100.0*(fc-oc)/oc
            months_to_target = months_between(snap, target)
            time_slip = months_between(original_doc, target)
            schedule_pressure = None
            if prog is not None and months_to_target is not None:
                schedule_pressure = (100.0 - prog) / max(months_to_target, 1)

            d3, c3 = future_label(seq, i, 3, "delay")
            d6, c6 = future_label(seq, i, 6, "delay")
            k3, _ = future_label(seq, i, 3, "cost")
            k6, _ = future_label(seq, i, 6, "cost")
            missing_core = sum(x is None or x == "" for x in [fc, exp, prog, r.get("current_target_doc")])

            tr = {
                "canonical_project_id": cid,
                "snapshot_month": r["snapshot_month"],
                "sector": r.get("sector", ""),
                "state": r.get("state", ""),
                "ministry_department": r.get("ministry_department", ""),
                "project_age_months": months_between(approval, snap),
                "months_to_target": months_to_target,
                "current_time_slip_months": time_slip,
                "current_cost_overrun_pct": current_cost_overrun,
                "spend_ratio_pct": spend_ratio,
                "physical_progress_pct": prog,
                "financial_physical_gap_pct": None if spend_ratio is None or prog is None else spend_ratio - prog,
                "progress_delta_1m": pd1,
                "progress_delta_3m": pd3,
                "progress_delta_6m": pd6,
                "spend_delta_1m_cr": sd1,
                "spend_delta_3m_cr": sd3,
                "spend_delta_6m_cr": sd6,
                "progress_velocity_3m": None if pd3 is None else pd3 / 3.0,
                "schedule_pressure": schedule_pressure,
                "stagnation_streak_months": stagnation,
                "target_revision_count_to_date": target_revisions,
                "cost_revision_count_to_date": cost_revisions,
                "data_quality_score": r.get("data_quality_score"),
                "missing_core_fields_count": missing_core,
                "delay_event_next_3m": d3,
                "delay_event_next_6m": d6,
                "cost_escalation_next_3m": k3,
                "cost_escalation_next_6m": k6,
                "future_coverage_3m": c3,
                "future_coverage_6m": c6,
            }
            out.append(tr)
            prev_target, prev_cost = target, fc
    return out


def write_csv(path: Path, rows: List[Dict], fields: Sequence[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def write_project_master(path: Path, rows: List[Dict]):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["canonical_project_id"]].append(r)
    fields = [
        "canonical_project_id", "paimana_project_code", "legacy_ocms_code", "pmgid",
        "project_name", "agency", "ministry_department", "sector", "state",
        "first_snapshot", "last_snapshot", "snapshot_count", "max_identity_confidence",
    ]
    out = []
    for cid, seq in grouped.items():
        seq.sort(key=lambda x: x["snapshot_month"])
        last = seq[-1]
        def first_nonempty(k):
            for r in reversed(seq):
                if r.get(k): return r.get(k)
            return ""
        out.append({
            "canonical_project_id": cid,
            "paimana_project_code": first_nonempty("paimana_project_code"),
            "legacy_ocms_code": first_nonempty("legacy_ocms_code"),
            "pmgid": first_nonempty("pmgid"),
            "project_name": first_nonempty("project_name"),
            "agency": first_nonempty("agency"),
            "ministry_department": first_nonempty("ministry_department"),
            "sector": first_nonempty("sector"),
            "state": first_nonempty("state"),
            "first_snapshot": seq[0]["snapshot_month"],
            "last_snapshot": seq[-1]["snapshot_month"],
            "snapshot_count": len(seq),
            "max_identity_confidence": max(float(r.get("identity_confidence") or 0) for r in seq),
        })
    write_csv(path, out, fields)


def write_quality(path: Path, rows: List[Dict]):
    fields = ["canonical_project_id", "snapshot_month", "data_quality_score", "quality_flags", "source_url", "source_page"]
    write_csv(path, [r for r in rows if r.get("quality_flags")], fields)


def load_manual_csv(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="paimana_dataset", help="Output directory")
    ap.add_argument("--pdf-dir", default="raw_pdfs", help="PDF cache directory")
    ap.add_argument("--start", default="2025-01")
    ap.add_argument("--end", default="2026-07")
    ap.add_argument("--local-only", action="store_true", help="Do not download; read YYYY-MM.pdf files from --pdf-dir")
    ap.add_argument("--min-rows", type=int, default=50, help="Warn when parser returns fewer rows than this")
    args = ap.parse_args()

    out_dir = Path(args.out)
    pdf_dir = Path(args.pdf_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    specs = report_specs(args.start, args.end)
    sess = session()
    all_rows: List[Dict] = []
    log_rows = []

    print(f"Collecting {len(specs)} report months: {args.start}..{args.end}")
    for spec in specs:
        print(f"\n[{spec.snapshot_month}] {spec.format_family}")
        if args.local_only:
            path = pdf_dir / f"{spec.snapshot_month}.pdf"
            url = "LOCAL_ONLY"
            err = "" if path.exists() else "Local PDF missing"
            if not path.exists(): path = None
        else:
            path, url, err = download_report(sess, spec, pdf_dir)

        if not path:
            print(f"  SKIP: {err}")
            log_rows.append({
                "snapshot_month": spec.snapshot_month, "status": "DOWNLOAD_FAILED",
                "pdf_path": "", "resolved_url": url, "rows_parsed": 0,
                "pages_total": 0, "pages_relevant": 0, "error": err,
            })
            continue

        try:
            rows, stats = parse_pdf(path, spec, url)
            status = "OK" if len(rows) >= args.min_rows else "REVIEW_LOW_ROW_COUNT"
            print(f"  {status}: {len(rows)} rows from {stats['pages_relevant']}/{stats['pages_total']} relevant pages")
            all_rows.extend(rows)
            log_rows.append({
                "snapshot_month": spec.snapshot_month, "status": status,
                "pdf_path": str(path), "resolved_url": url,
                "rows_parsed": len(rows), "pages_total": stats["pages_total"],
                "pages_relevant": stats["pages_relevant"], "error": "",
            })
        except Exception as e:
            print(f"  PARSE FAILED: {e!r}")
            log_rows.append({
                "snapshot_month": spec.snapshot_month, "status": "PARSE_FAILED",
                "pdf_path": str(path), "resolved_url": url, "rows_parsed": 0,
                "pages_total": 0, "pages_relevant": 0, "error": repr(e),
            })

    if not all_rows:
        print("\nNo rows were parsed. If official sites blocked automated downloads, manually place PDFs as raw_pdfs/YYYY-MM.pdf and rerun with --local-only.")
        write_csv(out_dir / "collection_log.csv", log_rows,
                  ["snapshot_month", "status", "pdf_path", "resolved_url", "rows_parsed", "pages_total", "pages_relevant", "error"])
        sys.exit(2)

    finalize_rows(all_rows)
    all_rows.sort(key=lambda r: (r.get("canonical_project_id", ""), r["snapshot_month"]))
    training = build_training_rows(all_rows)

    write_csv(out_dir / "raw_snapshots.csv", all_rows, RAW_FIELDS)
    write_project_master(out_dir / "project_master.csv", all_rows)
    write_quality(out_dir / "quality_flags.csv", all_rows)
    write_csv(out_dir / "training_rows.csv", training, TRAIN_FIELDS)
    write_csv(out_dir / "collection_log.csv", log_rows,
              ["snapshot_month", "status", "pdf_path", "resolved_url", "rows_parsed", "pages_total", "pages_relevant", "error"])

    # Summary for reproducibility / sanity checks.
    project_count = len({r["canonical_project_id"] for r in all_rows})
    months = sorted({r["snapshot_month"] for r in all_rows})
    dq = [r.get("data_quality_score") for r in all_rows if r.get("data_quality_score") is not None]
    summary = [
        ["metric", "value"],
        ["raw_project_month_rows", len(all_rows)],
        ["canonical_projects", project_count],
        ["months_parsed", len(months)],
        ["first_month", months[0] if months else ""],
        ["last_month", months[-1] if months else ""],
        ["training_rows", len(training)],
        ["mean_data_quality_score", round(sum(dq)/len(dq), 2) if dq else ""],
    ]
    with (out_dir / "dataset_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(summary)

    print("\nDONE")
    print(f"  raw snapshots : {len(all_rows):,}")
    print(f"  projects      : {project_count:,}")
    print(f"  training rows : {len(training):,}")
    print(f"  output        : {out_dir.resolve()}")
    print("\nBefore training: inspect collection_log.csv for REVIEW_LOW_ROW_COUNT / failed months and quality_flags.csv for anomalies.")


if __name__ == "__main__":
    main()
