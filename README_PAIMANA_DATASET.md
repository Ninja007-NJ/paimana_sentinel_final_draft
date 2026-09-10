# PAIMANA / OCMS Full Dataset Builder — SIH PS 26103

This package is for the **AI-powered Predictive Analytics and Early Warning System** requested in SIH Problem Statement **26103**.

## What is included

- `PAIMANA_ProjectReady_Dataset_Package.xlsx` — verified seed data, full schemas, source manifest, data-quality rules, leakage-safe model design and documented limitations.
- `verified_seed.csv` — 27 **real, source-verified** project-month snapshots used to validate the longitudinal design.
- `source_manifest.csv` — official report/source inventory.
- `build_paimana_dataset.py` — collector + parser + project crosswalk + quality engine + feature/label builder.
- `requirements_paimana.txt` — Python dependencies.

## What the builder creates

After successful collection/parsing:

1. `raw_snapshots.csv` — one row per project per report month.
2. `project_master.csv` — PAIMANA/legacy crosswalk and project identity table.
3. `training_rows.csv` — leakage-safe 3/6 month model features and labels.
4. `quality_flags.csv` — expenditure/progress/date/missingness anomalies.
5. `collection_log.csv` — exact URL, local PDF, parsed row count and failures for each month.
6. `dataset_summary.csv` — basic row/project/month coverage summary.

## Recommended run

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements_paimana.txt
python build_paimana_dataset.py --start 2025-01 --end 2026-07
```

If a government endpoint blocks automation, manually download the relevant official Flash Report PDFs, name them `YYYY-MM.pdf`, place them in `raw_pdfs/`, then run:

```bash
python build_paimana_dataset.py --start 2025-01 --end 2026-07 --local-only
```

## Why the dataset is longitudinal

The model is not trained to answer **"is this project already delayed?"**. For each project-month snapshot at time `t`, features use only information available at or before `t`. Labels look forward:

- `delay_event_next_3m`: does the reported current target completion date move later during the next 3 months?
- `delay_event_next_6m`: same over 6 months.
- `cost_escalation_next_3m`: does the current forecast/revised cost increase materially within 3 months?
- `cost_escalation_next_6m`: same over 6 months.

Rows without sufficient future coverage are left unlabeled rather than forced to zero.

## Core raw fields

The canonical schema preserves, where available:

- report month and source URL/page
- PAIMANA project code
- legacy OCMS code
- PMG ID
- project name, agency, ministry/department, sector and state
- approval and start dates
- original, revised and anticipated completion dates
- original, revised and anticipated costs
- cumulative expenditure
- physical progress
- canonical current target/current forecast cost
- identity confidence
- data-quality score and flags
- raw source cell/row text for auditability

## Important limitations — do not hide these in SIH judging

1. **The public Flash Reports are not the complete internal CUF database.** Milestone-level land, tender, clearance, planned-vs-actual and funding fields are not consistently public.
2. **OCMS → PAIMANA migration changed schema and identifiers.** Keep both legacy and new IDs and audit the crosswalk.
3. **Revised vs anticipated fields are not identical concepts.** They are preserved separately before deriving a canonical current target.
4. **Physical progress is self-reported and sector-dependent.** Do not assume a 50% railway project is measured identically to a 50% highway project.
5. **Cumulative expenditure can be corrected downward.** The pipeline flags this instead of silently forcing monotonicity.
6. **Unchanged progress may be real stagnation or stale reporting.** Staleness must influence prediction confidence.
7. **Ongoing-project tables create survivor/censoring bias.** Completed/frozen/exited projects leave the panel.
8. **A target-date extension is an administrative deterioration signal, not proof of execution failure.** Scope changes/rescheduling can also produce revisions.
9. **Cost escalation has mixed causes.** Inflation/scope additions can increase cost without managerial failure.
10. **Do not random-split project-month rows.** That leaks the same project's identity across train/test. Use chronological backtesting and preferably project hold-outs.
11. **Never use future revised dates/costs as features for an earlier snapshot.** The builder labels future events only after `t`.
12. **Class imbalance is expected.** Judge the model with PR-AUC, calibrated probability, recall at an alert budget and false-alert rate, not raw accuracy alone.
13. **External causal drivers are missing.** Weather, litigation, contractor health, commodity prices and court/land events require separate legal/reliable sources if added.
14. **Counterfactual 'what-if' output is not causal proof.** Present it as a constrained model-response simulator requiring human review.
15. **Government endpoints can move or block bulk automated access.** Keep local PDF cache and a collection log; never invent missing rows.
16. **Latest PAIMANA-PROJ/CRIP onboarding changes coverage.** Mid-2026 project count changes can reflect repository/API migration as well as real project completion/addition.

The workbook's `Limitations` and `Quality_Rules` sheets contain the expanded audit list.

## Data integrity rule for this project

**Never fabricate a missing real project-month.** If a report cannot be obtained or parsed, mark the month missing and repair the source/parser. Synthetic data, if ever used for stress tests, must have `synthetic_flag=1` and must never enter the final real-data test set.

## Suggested ML workflow

1. Run collector and audit `collection_log.csv`.
2. Inspect low-row months and `quality_flags.csv`.
3. Freeze a clean canonical snapshot dataset.
4. Build time-based train/validation/test splits.
5. Baseline: logistic regression.
6. Main model: CatBoost / LightGBM / XGBoost.
7. Calibrate probabilities.
8. Explain with SHAP.
9. Build constrained **what-if** simulations using only actionable variables and state clearly that they are predictive, not causal.

