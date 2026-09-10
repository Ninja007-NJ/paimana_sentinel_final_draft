# SIH judge demo — 3–5 minutes

Use real project `P-618861`, “BAKHTIYARPUR RAJAULI PKG-II FROM KM 54.405 TO KM 101.630 NH20”. Values below were verified from the frozen local backend; read the live screen if they differ after a deliberate artifact update.

Verified April 2026 story: 88.9% CRITICAL risk, 92/100 data reliability, an 85.1 percentage-point rise across the latest three observed snapshots, and CRITICAL_RISK, RAPIDLY_RISING_RISK, and REPEATED_TARGET_REVISION warnings. Its deterministic cohort has 118 peers; progress is 97.85% versus a 97.48% peer median, delay risk is at the 98.31st peer percentile, and peer median risk is 75.0%. The suggested expenditure-velocity scenario changes the model estimate from 88.9% to 85.6% (-3.25 percentage points) within the validated bounds.

1. Open the Executive Dashboard. Say: “This is the national project-risk overview.” Show monitored projects, the risk distribution, and HIGH/CRITICAL counts. Explain that risk is a three-month target-revision warning, not a delay verdict.
2. Open the Early Warning Centre. Say: “Instead of manually reviewing every project, Sentinel prioritizes projects showing emerging risk.” Locate `P-618861` in the live queue.
3. Open that project. Show its three-month risk and data reliability separately. Say: “Risk and data reliability are separate.”
4. Trace the risk trajectory. Say: “Sentinel identifies deterioration before the final delay materializes.”
5. Inspect the top SHAP associations and explain the plain-language drivers without implying causality.
6. Show Peer Comparison: project progress and expenditure versus the peer medians, current risk versus peer risk, percentile, cohort definition, and sample size.
7. Show its warning evidence and explain that the rule uses only observations available through the displayed month.
8. Load a Suggested Scenario into the What-If Simulator, or move one control within its displayed bounds. Run it and read current risk, scenario risk, and the percentage-point difference. Say: “This is a model scenario, not a guaranteed intervention effect.”
9. Show the remaining one-to-three Suggested Scenarios and their feasibility scores.
10. Open Portfolio Analytics. Briefly show distribution, trend, sufficiently large ministry/sector/state groups, deteriorating ministries, and reporting reliability.

Close: “PAIMANA Sentinel transforms monthly infrastructure reporting into predictive, explainable and actionable decision support.”
