# PAIMANA Sentinel architecture

PAIMANA Sentinel is a read-only decision-support application. Frozen Dataset v1.0 feeds a frozen CatBoost V1.1 three-month delay model. FastAPI loads the model once, computes project risk, confidence, trajectories, peers, alerts and constrained scenarios, and exposes JSON endpoints. React renders executive, project, warning and portfolio views. The browser never reproduces model logic.

Flow: PAIMANA / historical OCMS reports → cleaned longitudinal Dataset v1.0 → frozen CatBoost V1.1 → FastAPI → risk scoring → SHAP explanations → data reliability → trajectory → peer benchmarking → early warning → constrained what-if → scenario recommendations → portfolio analytics → React dashboard.

Peer, alert and scenario services are deterministic layers around the unchanged prediction. No component writes back to the frozen source files.
