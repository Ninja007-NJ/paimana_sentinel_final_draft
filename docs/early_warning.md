# Early warning

The engine emits CRITICAL_RISK, RAPIDLY_RISING_RISK, NEW_HIGH_RISK, LOW_CONFIDENCE_HIGH_RISK, STAGNATING_PROJECT and REPEATED_TARGET_REVISION. Rules use the current snapshot and historical observations up to that month only.

RAPIDLY_RISING_RISK requires a rise of at least 20 percentage points from the oldest to newest of the latest three observed snapshots. NEW_HIGH_RISK requires a transition from LOW/MEDIUM to HIGH/CRITICAL. Low-confidence high risk uses source reliability below 65, stagnation uses a streak of at least three months, and repeated target revision uses at least two revisions in the recent three-month feature window. CRITICAL_RISK uses the frozen backend risk band.

Priority combines severity, current risk, recent increase, reported project cost, and reliability. Higher-reliability signals receive a small trust bonus so low-quality predictions are not treated as equally trustworthy. Every alert returns supporting evidence. The queue is deterministic, filterable by severity, alert type, sector and ministry, and remains a triage aid rather than a causal conclusion.
