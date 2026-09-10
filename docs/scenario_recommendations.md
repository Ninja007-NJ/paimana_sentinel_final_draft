# Model-based scenario recommendations

The recommendation engine evaluates a small, deterministic set of single-feature scenarios using the same frozen CatBoost V1.1 model and the same 1st–99th percentile bounds as the what-if simulator. It never changes identity, sector, state, ministry, age, costs, dates, or historical observations.

At most three risk-lowering scenarios are returned. Ranking balances the model-estimated probability difference with distance from the current value, so modest in-range changes are preferred over extreme changes. Results are reproducible and do not modify stored project data.

Every recommendation uses predictive wording: under the modified model inputs, the estimated risk changes from one probability to another. It is not a causal prescription and does not promise an operational outcome.
