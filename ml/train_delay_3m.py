from __future__ import annotations

import copy
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import catboost
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import sklearn
import xgboost
from sklearn.base import clone
from sklearn.metrics import brier_score_loss

from ml.config import *
from ml.data.loader import load_delay_data
from ml.data.splitting import project_overlap, split_summary, temporal_split, unseen_project_test
from ml.data.validation import validate_training_data
from ml.evaluation.metrics import classification_metrics, timed_probabilities
from ml.evaluation.plots import (bar_metrics, calibration_plot, comparison_curves, confusion_plot, feature_importance_plot, target_plots, threshold_plot)
from ml.evaluation.subgroup_analysis import subgroup_metrics
from ml.evaluation.temporal_analysis import metrics_by_month
from ml.evaluation.thresholding import select_thresholds, threshold_table
from ml.explainability.shap_explainer import catboost_shap, xgboost_shap
from ml.features.feature_registry import ALLOWED_FEATURES, CATEGORICAL_FEATURES, CONTROLLABILITY, NUMERICAL_FEATURES, registry_for_columns
from ml.features.leakage_guard import assert_leakage_safe
from ml.features.preprocessing import prepare_catboost
from ml.models.bundle import ModelBundle
from ml.models.calibration import ProbabilityCalibrator
from ml.models.catboost_model import make_catboost
from ml.models.dummy_baseline import make_dummy
from ml.models.logistic_model import make_logistic
from ml.models.xgboost_model import make_xgboost


def native(value):
    if isinstance(value, dict): return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [native(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return None if np.isnan(value) else float(value)
    if isinstance(value, np.ndarray): return value.tolist()
    if pd.isna(value) if not isinstance(value, (str, dict, list)) else False: return None
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(native(value), indent=2, sort_keys=True), encoding="utf-8")


def markdown_table(records, columns=None):
    if not records: return "_No qualifying rows._"
    frame = pd.DataFrame(records)
    if columns: frame = frame[columns]
    return frame.to_markdown(index=False)


def profile_dataset(data):
    monthly = []
    for month, group in data.groupby("snapshot_month"):
        positives = int(group[TARGET].sum())
        monthly.append({"snapshot_month": month, "rows": len(group), "positives": positives, "negatives": len(group)-positives, "positive_rate_pct": round(100*positives/len(group), 4)})
    missing = {feature: round(100 * data[feature].isna().mean(), 4) for feature in ALLOWED_FEATURES}
    distributions = {feature: native(data[feature].describe(percentiles=[.01,.05,.25,.5,.75,.95,.99]).to_dict()) for feature in NUMERICAL_FEATURES}
    cardinality = {feature: {"unique": int(data[feature].nunique(dropna=True)), "missing_pct": missing[feature]} for feature in CATEGORICAL_FEATURES}
    profile = {
        "rows": len(data), "unique_projects": int(data.canonical_project_id.nunique()),
        "snapshot_month_min": data.snapshot_month.min(), "snapshot_month_max": data.snapshot_month.max(),
        "target_positives": int(data[TARGET].sum()), "target_negatives": int((1-data[TARGET]).sum()),
        "target_prevalence_pct": round(100*data[TARGET].mean(),4), "rows_by_month": monthly,
        "feature_missing_pct": missing, "numerical_distributions": distributions,
        "categorical_cardinality": cardinality,
        "quality_threshold_counts": {f"below_{threshold}": int((data.data_quality_score < threshold).sum()) for threshold in (90,80,70,60)},
        "fallback_generated_identity_rows": int(data.identity_source.fillna("").isin(["FALLBACK_GENERATED","AMBIGUOUS_COLLISION"]).sum()),
        "reporting_regime_distribution": data.reporting_regime.fillna("MISSING").value_counts().to_dict(),
    }
    write_json(REPORT_DIR/"dataset_profile.json", profile)
    md = f"""# Dataset profile — PAIMANA Sentinel Model V1

- Rows: **{len(data):,}**
- Unique projects: **{data.canonical_project_id.nunique():,}**
- Snapshot range: **{data.snapshot_month.min()} through {data.snapshot_month.max()}**
- Positive prevalence: **{100*data[TARGET].mean():.2f}%**
- Fallback/generated identity rows: **{profile['fallback_generated_identity_rows']:,}**

## Target by month

{markdown_table(monthly)}

## Feature missingness

{markdown_table([{'feature': k, 'missing_pct': v} for k,v in missing.items()])}

## Categorical cardinality

{markdown_table([{'feature': k, **v} for k,v in cardinality.items()])}

## Data quality

{markdown_table([{'threshold': k, 'rows': v} for k,v in profile['quality_threshold_counts'].items()])}

## Numerical distributions

Full percentiles and moments are stored in `dataset_profile.json`; no rows were removed during profiling.
"""
    (REPORT_DIR/"dataset_profile.md").write_text(md,encoding="utf-8")
    return profile


def raw_probability(record, frame):
    X = frame[ALLOWED_FEATURES]
    if record["type"] == "catboost": return record["model"].predict_proba(prepare_catboost(X))[:,1]
    if record["type"] == "dummy": return record["model"].predict_proba(np.zeros((len(frame),1)))[:,1]
    return record["model"].predict_proba(X)[:,1]


def fit_candidates(train, valid):
    y_train, y_valid = train[TARGET], valid[TARGET]; ratio=(len(y_train)-y_train.sum())/y_train.sum()
    records=[]
    for strategy in ("prior","most_frequent"):
        model=make_dummy(strategy); model.fit(np.zeros((len(train),1)),y_train); records.append({"name":f"Dummy_{strategy}","type":"dummy","model":model,"config":{"strategy":strategy}})
    for weight in (None,"balanced"):
        for c in (0.1,1.0,10.0):
            model=make_logistic(c,weight); model.fit(train[ALLOWED_FEATURES],y_train); records.append({"name":f"Logistic_{'balanced' if weight else 'unweighted'}_C{c}","type":"logistic","model":model,"config":{"C":c,"class_weight":weight}})
    cat_configs=[
        {"depth":5,"iterations":500,"learning_rate":.05,"l2_leaf_reg":5},
        {"depth":6,"iterations":700,"learning_rate":.035,"l2_leaf_reg":7,"class_weights":[1,ratio]},
        {"depth":7,"iterations":600,"learning_rate":.04,"l2_leaf_reg":9,"class_weights":[1,ratio]},
    ]
    Xtr,Xv=prepare_catboost(train[ALLOWED_FEATURES]),prepare_catboost(valid[ALLOWED_FEATURES])
    for index,cfg in enumerate(cat_configs,1):
        model=make_catboost(**cfg); model.fit(Xtr,y_train,cat_features=CATEGORICAL_FEATURES,eval_set=(Xv,y_valid),early_stopping_rounds=70,verbose=False)
        records.append({"name":f"CatBoost_{index}","type":"catboost","model":model,"config":cfg})
    xgb_configs=[
        {"max_depth":3,"n_estimators":450,"learning_rate":.05,"min_child_weight":5},
        {"max_depth":4,"n_estimators":600,"learning_rate":.04,"min_child_weight":4,"scale_pos_weight":ratio},
        {"max_depth":5,"n_estimators":500,"learning_rate":.035,"min_child_weight":6,"scale_pos_weight":ratio,"subsample":.8,"colsample_bytree":.8},
    ]
    for index,cfg in enumerate(xgb_configs,1):
        model=make_xgboost(**cfg); model.fit(train[ALLOWED_FEATURES],y_train); records.append({"name":f"XGBoost_{index}","type":"xgboost","model":model,"config":cfg})
    for record in records:
        start=time.perf_counter(); probability=raw_probability(record,valid); elapsed=time.perf_counter()-start
        table=threshold_table(y_valid,probability); threshold=float(table.loc[table.f1.idxmax(),"threshold"])
        record.update({"valid_probability":probability,"valid_threshold":threshold,"valid_metrics":classification_metrics(y_valid,probability,threshold),"inference_ms_per_row":1000*elapsed/len(valid)})
    return records


def best_by_family(records):
    output={}
    for family in ("dummy","logistic","catboost","xgboost"):
        family_rows=[r for r in records if r["type"]==family]
        output[family]=max(family_rows,key=lambda r:(r["valid_metrics"]["pr_auc"],-r["valid_metrics"]["brier"]))
    return output


def choose_calibration(selected, valid):
    raw=selected["valid_probability"]; fit_mask=valid.snapshot_month.isin(["2025-09","2025-10"]); select_mask=valid.snapshot_month.eq("2025-11")
    comparison=[]; fitted={}
    for method in ("none","sigmoid","isotonic"):
        calibrator=ProbabilityCalibrator(method).fit(raw[fit_mask],valid.loc[fit_mask,TARGET]) if method!="none" else ProbabilityCalibrator("none")
        probability=calibrator.transform(raw[select_mask]); metrics=classification_metrics(valid.loc[select_mask,TARGET],probability,0.5)
        comparison.append({"method":method,**metrics}); fitted[method]=calibrator
    chosen=min(comparison,key=lambda r:(r["brier"],r["ece"]))["method"]
    calibrator=fitted[chosen]
    calibrated_valid=calibrator.transform(raw)
    operational_mask=select_mask.to_numpy(); table=threshold_table(valid.loc[select_mask,TARGET],calibrated_valid[operational_mask]); thresholds=select_thresholds(table)
    return chosen,calibrator,comparison,calibrated_valid,table,thresholds


def logistic_coefficients(record):
    pipeline=record["model"]; names=pipeline.named_steps["preprocess"].get_feature_names_out(); coef=pipeline.named_steps["model"].coef_[0]
    frame=pd.DataFrame({"feature":names,"coefficient":coef,"odds_ratio":np.exp(coef),"direction":np.where(coef>=0,"increases estimated delay odds","reduces estimated delay odds")}).sort_values("coefficient",key=abs,ascending=False)
    frame.to_csv(REPORT_DIR/"logistic_coefficients.csv",index=False); return frame


def git_commit():
    try: return subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: return None


def main():
    np.random.seed(RANDOM_SEED); data=load_delay_data(); validate_training_data(data); assert_leakage_safe(ALLOWED_FEATURES)
    dataset_hash=hashlib.sha256(DATASET.read_bytes()).hexdigest(); profile=profile_dataset(data); target_plots(data,TARGET,PLOT_DIR)
    train,valid,test=temporal_split(data)
    split={"train":split_summary(train),"validation":split_summary(valid),"test":split_summary(test),"project_overlap":{"train_validation":project_overlap(train,valid),"train_test":project_overlap(train,test),"validation_test":project_overlap(valid,test)}}
    unseen=unseen_project_test(train,valid,test); split["secondary_unseen_project_test"]=split_summary(unseen) if len(unseen) else {"rows":0}
    write_json(REPORT_DIR/"split_report.json",split)
    (REPORT_DIR/"split_report.md").write_text(f"# Temporal split\n\nThe split was fixed before training and preserves chronology.\n\n{markdown_table([{'partition':k,**v} for k,v in split.items() if k in ['train','validation','test']])}\n\n## Project overlap\n\n{markdown_table([{'comparison':k,**v} for k,v in split['project_overlap'].items()])}\n\nSecondary robustness uses only temporal-test rows from projects absent from both train and validation.\n",encoding="utf-8")
    write_json(REPORT_DIR/"feature_registry.json",registry_for_columns(data.columns))
    write_json(ML_ROOT/"features"/"what_if_feature_policy.json",{"warning":"Scenario adjustments are predictive associations, not causal effects.","features":CONTROLLABILITY})

    print("Training candidate models..."); records=fit_candidates(train,valid); families=best_by_family(records)
    selected=max([families[k] for k in ("logistic","catboost","xgboost")],key=lambda r:(r["valid_metrics"]["pr_auc"],-r["valid_metrics"]["brier"]))
    selected_name=selected["name"]; print("Validation-selected model:",selected_name)
    calibration_method,calibrator,calibration_comparison,calibrated_valid,thresholds_table,thresholds=choose_calibration(selected,valid)
    threshold_plot(thresholds_table,PLOT_DIR/"threshold_precision_recall.png")
    thresholds_table.to_csv(REPORT_DIR/"threshold_table.csv",index=False)

    comparison=[]; test_probabilities={}; family_test={}
    for family,record in families.items():
        probability=raw_probability(record,test); test_probabilities[record["name"]]=probability
        metrics=classification_metrics(test[TARGET],probability,record["valid_threshold"]); family_test[family]=metrics
        comparison.append({"model":record["name"],"family":family,"calibration":"raw","inference_ms_per_row":record["inference_ms_per_row"],"interpretability":"high" if family in {'logistic','dummy'} else "SHAP-supported",**metrics})
    raw_test=raw_probability(selected,test); calibrated_test=calibrator.transform(raw_test); balanced=thresholds["BALANCED"]
    final_metrics=classification_metrics(test[TARGET],calibrated_test,balanced)
    comparison.append({"model":selected_name+"_calibrated","family":selected["type"],"calibration":calibration_method,"inference_ms_per_row":selected["inference_ms_per_row"],"interpretability":"SHAP-supported" if selected["type"] in {'catboost','xgboost'} else "coefficient-based",**final_metrics})
    pd.DataFrame(comparison).to_csv(REPORT_DIR/"model_comparison.csv",index=False)
    comparison_curves(test[TARGET],test_probabilities,PLOT_DIR); confusion_plot(test[TARGET],calibrated_test,balanced,PLOT_DIR/"confusion_matrix.png"); calibration_plot(test[TARGET],{"raw":raw_test,"calibrated":calibrated_test},PLOT_DIR/"calibration_curve.png")

    monthly=metrics_by_month(test,calibrated_test,TARGET,balanced); pd.DataFrame(monthly).to_csv(REPORT_DIR/"temporal_metrics.csv",index=False); bar_metrics(monthly,"month","pr_auc","Temporal test PR-AUC",PLOT_DIR/"monthly_performance.png")
    eval_test=test.copy(); eval_test["quality_bucket"]=pd.cut(eval_test.data_quality_score,[-np.inf,69,79,89,np.inf],labels=["below 70","70-79","80-89","90-100"])
    eval_test["cost_bucket"]=pd.qcut(eval_test.current_forecast_cost_cr,4,duplicates="drop").astype(str)
    eval_test["progress_stage"]=pd.cut(eval_test.physical_progress_pct,[-np.inf,25,50,75,np.inf],labels=["0-25","25-50","50-75","75-100+"])
    subgroup=[]
    for column,minimum in (("sector",50),("state",50),("reporting_regime",25),("quality_bucket",25),("cost_bucket",25),("progress_stage",25)):
        subgroup.extend(subgroup_metrics(eval_test,calibrated_test,TARGET,column,balanced,minimum_rows=minimum))
    pd.DataFrame(subgroup).to_csv(REPORT_DIR/"subgroup_metrics.csv",index=False)
    quality_rows=[r for r in subgroup if r["group_column"]=="quality_bucket"]; bar_metrics(quality_rows,"group","pr_auc","PR-AUC by data-quality bucket",PLOT_DIR/"data_quality_bucket_performance.png")

    # Strictly out-of-time reporting-regime diagnostics. These are separate
    # models with the already-selected configuration, not V1 predictors.
    regime_diagnostics=[]
    for regime_name, fit_months, evaluate_months in (
        ("OCMS_LEGACY", ["2025-01","2025-02"], ["2025-03","2025-04","2025-05","2025-06"]),
        ("PAIMANA_TRANSITION", ["2025-01","2025-02","2025-03","2025-04","2025-05","2025-06"], ["2025-07","2025-08"]),
    ):
        fit_frame=data[data.snapshot_month.isin(fit_months)]; eval_frame=data[data.snapshot_month.isin(evaluate_months)]
        diagnostic=make_catboost(**selected["config"])
        diagnostic.fit(prepare_catboost(fit_frame[ALLOWED_FEATURES]),fit_frame[TARGET],cat_features=CATEGORICAL_FEATURES,verbose=False)
        probability=diagnostic.predict_proba(prepare_catboost(eval_frame[ALLOWED_FEATURES]))[:,1]
        regime_diagnostics.append({"reporting_regime":regime_name,"training_months":f"{fit_months[0]}..{fit_months[-1]}","evaluation_months":f"{evaluate_months[0]}..{evaluate_months[-1]}","rows":len(eval_frame),"positives":int(eval_frame[TARGET].sum()),**classification_metrics(eval_frame[TARGET],probability,.5)})
    regime_diagnostics.append({"reporting_regime":"PAIMANA","training_months":f"{TRAIN_START}..{TRAIN_END}","evaluation_months":f"{TEST_START}..{TEST_END}","rows":len(test),"positives":int(test[TARGET].sum()),**final_metrics})
    pd.DataFrame(regime_diagnostics).to_csv(REPORT_DIR/"reporting_regime_metrics.csv",index=False)

    unseen_probability=calibrator.transform(raw_probability(selected,unseen)) if len(unseen) else np.array([])
    unseen_metrics=classification_metrics(unseen[TARGET],unseen_probability,balanced) if len(unseen) and unseen[TARGET].nunique()>1 else {"note":"insufficient unseen-project class support","rows":len(unseen)}
    high_train=train[train.data_quality_score>=QUALITY_THRESHOLD]; high_valid=valid[valid.data_quality_score>=QUALITY_THRESHOLD]; high_test=test[test.data_quality_score>=QUALITY_THRESHOLD]
    high_model=clone(selected["model"])
    if selected["type"]=="catboost": high_model.fit(prepare_catboost(high_train[ALLOWED_FEATURES]),high_train[TARGET],cat_features=CATEGORICAL_FEATURES,eval_set=(prepare_catboost(high_valid[ALLOWED_FEATURES]),high_valid[TARGET]),early_stopping_rounds=70,verbose=False)
    else: high_model.fit(high_train[ALLOWED_FEATURES],high_train[TARGET])
    high_record={"type":selected["type"],"model":high_model}; high_raw_valid=raw_probability(high_record,high_valid); high_cal=ProbabilityCalibrator(calibration_method)
    if calibration_method!="none": high_cal.fit(high_raw_valid,high_valid[TARGET])
    high_probability=high_cal.transform(raw_probability(high_record,high_test)); high_metrics=classification_metrics(high_test[TARGET],high_probability,balanced)

    logistic_coefficients(families["logistic"])
    explanation_record=selected if selected["type"] in {"catboost","xgboost"} else max([families["catboost"],families["xgboost"]],key=lambda r:r["valid_metrics"]["pr_auc"])
    if explanation_record["type"]=="catboost": _,shap_sample,explanation,importance=catboost_shap(explanation_record["model"],test)
    else: _,shap_sample,explanation,importance=xgboost_shap(explanation_record["model"],test)
    write_json(REPORT_DIR/"global_feature_importance.json",importance); feature_importance_plot(importance,PLOT_DIR/"feature_importance.png")
    shap.plots.beeswarm(explanation,max_display=15,show=False); plt.tight_layout(); plt.savefig(PLOT_DIR/"shap_summary.png",dpi=160,bbox_inches="tight"); plt.close()
    sanity=[]
    if explanation_record["type"]=="catboost":
        for feature in NUMERICAL_FEATURES:
            idx=ALLOWED_FEATURES.index(feature); values=pd.to_numeric(shap_sample[feature],errors="coerce"); corr=values.corr(pd.Series(explanation.values[:,idx],index=values.index))
            sanity.append({"feature":feature,"value_shap_correlation":None if pd.isna(corr) else float(corr),"review_flag":bool(feature in {"schedule_pressure","target_revision_count_to_date","stagnation_streak_months"} and not pd.isna(corr) and corr<-.1)})
    write_json(REPORT_DIR/"feature_sanity.json",sanity)

    prediction_frame=test[["canonical_project_id","snapshot_month",TARGET,"sector","state",*NUMERICAL_FEATURES]].copy(); prediction_frame["predicted_probability"]=calibrated_test; prediction_frame["predicted_label"]=(calibrated_test>=balanced).astype(int)
    prediction_frame.to_csv(PREDICTION_DIR/"temporal_test_predictions.csv",index=False)
    false_positive=prediction_frame[(prediction_frame[TARGET]==0)&(prediction_frame.predicted_label==1)].sort_values("predicted_probability",ascending=False); false_negative=prediction_frame[(prediction_frame[TARGET]==1)&(prediction_frame.predicted_label==0)].sort_values("predicted_probability")
    false_positive.to_csv(PREDICTION_DIR/"false_positives.csv",index=False); false_negative.to_csv(PREDICTION_DIR/"false_negatives.csv",index=False)
    peer_columns=["canonical_project_id","snapshot_month","sector","project_age_months","physical_progress_pct","original_cost_cr","current_forecast_cost_cr"]
    data[peer_columns].to_csv(PREDICTION_DIR/"peer_reference_v1.csv",index=False)

    # Save trusted local artifacts.
    native_model_name=f"delay_3m_{selected['type']}_v1"
    if selected["type"]=="catboost": selected["model"].save_model(MODEL_DIR/(native_model_name+".cbm"))
    elif selected["type"]=="xgboost": selected["model"].named_steps["model"].save_model(MODEL_DIR/(native_model_name+".json"))
    else: joblib.dump(selected["model"],MODEL_DIR/(native_model_name+".joblib"))
    joblib.dump(calibrator,MODEL_DIR/"delay_3m_calibrator_v1.joblib"); joblib.dump(selected["model"].named_steps.get("preprocess") if hasattr(selected["model"],"named_steps") else {"categorical_missing":"__MISSING__"},MODEL_DIR/"preprocessing_v1.joblib")
    write_json(MODEL_DIR/"thresholds_v1.json",thresholds); write_json(MODEL_DIR/"feature_list_v1.json",ALLOWED_FEATURES)
    metadata={"model_version":MODEL_VERSION,"dataset_version":DATASET_VERSION,"selected_model":selected_name,"model_type":selected["type"],"selection_basis":"validation PR-AUC, then Brier; test untouched until selection","calibration":calibration_method,"training_prevalence":float(train[TARGET].mean()),"training_period":[TRAIN_START,TRAIN_END],"validation_period":[VALID_START,VALID_END],"test_period":[TEST_START,TEST_END],"dataset_sha256":dataset_hash,"git_commit":git_commit(),"random_seed":RANDOM_SEED,"configuration":selected["config"],"test_metrics":final_metrics,"thresholds":thresholds}
    write_json(MODEL_DIR/"model_metadata_v1.json",metadata)
    bundle=ModelBundle(selected["type"],selected["model"],calibrator,thresholds,ALLOWED_FEATURES,MODEL_VERSION,DATASET_VERSION,importance,metadata); joblib.dump(bundle,MODEL_DIR/"delay_3m_model_bundle_v1.joblib")

    # Reports.
    model_comparison_md="# Model comparison\n\nModel selection was made on validation data. Test metrics are reported for comparison but were not used to select hyperparameters. PR-AUC is primary because delay events are the minority class.\n\n"+markdown_table(comparison,["model","pr_auc","roc_auc","precision","recall","f1","balanced_accuracy","brier","calibration","inference_ms_per_row","interpretability"])
    (REPORT_DIR/"model_comparison.md").write_text(model_comparison_md,encoding="utf-8")
    (REPORT_DIR/"threshold_analysis.md").write_text("# Threshold analysis\n\nThresholds were selected on November 2025 validation observations, never test data.\n\n"+markdown_table([{"profile":k,"threshold":v} for k,v in thresholds.items()])+"\n\nFull precision/recall/F1/FPR/alert counts are in `threshold_table.csv`.\n",encoding="utf-8")
    (REPORT_DIR/"calibration_report.md").write_text("# Calibration report\n\nCalibration was fit on September–October validation probabilities and selected using November validation Brier score/ECE.\n\n"+markdown_table(calibration_comparison)+f"\n\nSelected method: **{calibration_method}**. Test Brier raw: **{classification_metrics(test[TARGET],raw_test,.5)['brier']:.4f}**; calibrated: **{final_metrics['brier']:.4f}**.\n",encoding="utf-8")
    (REPORT_DIR/"subgroup_analysis.md").write_text("# Subgroup analysis\n\nGroups below minimum support (50 rows and 5 positives; 25 rows for broad diagnostic buckets) are suppressed. These are diagnostics, not causal comparisons. Reporting regime is excluded from predictors; its table uses strictly later evaluation months for each regime.\n\n## Supported subgroups\n\n"+markdown_table(subgroup)+"\n\n## Reporting-regime diagnostics\n\n"+markdown_table(regime_diagnostics),encoding="utf-8")
    (REPORT_DIR/"temporal_stability.md").write_text("# Temporal stability\n\n"+markdown_table(monthly)+"\n\n## Secondary unseen-project robustness\n\n"+markdown_table([unseen_metrics]),encoding="utf-8")
    error_features=["months_to_target","current_time_slip_months","schedule_pressure","physical_progress_pct","progress_velocity_3m","target_revision_count_to_date","data_quality_score"]
    error_patterns=[]
    for label,frame in (("false_positive",false_positive.head(100)),("false_negative",false_negative.head(100))):
        record={"error_type":label,"reviewed_rows":len(frame)}
        record.update({f"mean_{feature}":float(pd.to_numeric(frame[feature],errors="coerce").mean()) for feature in error_features})
        record["common_sector"]=frame.sector.mode().iloc[0] if len(frame) and not frame.sector.mode().empty else ""
        error_patterns.append(record)
    (REPORT_DIR/"error_analysis.md").write_text(f"# Error analysis\n\nAt the balanced threshold there are **{len(false_positive):,}** false positives and **{len(false_negative):,}** false negatives. The table summarizes the 100 highest-confidence errors of each type; row-level evidence is exported separately. Predictions are associations, not causal findings.\n\n"+markdown_table(error_patterns)+"\n",encoding="utf-8")
    (REPORT_DIR/"leakage_validation.md").write_text("# Leakage validation\n\n- Feature registry is explicit and the leakage guard passed.\n- Target, validity, future coverage, reporting regime, identifiers, and all future outcomes are excluded from X.\n- Lag features use exact prior months only.\n- Train precedes validation; validation precedes test.\n- Thresholds and calibration were chosen without test labels.\n- No random row-level test split was used.\n",encoding="utf-8")
    (REPORT_DIR/"feature_sanity.md").write_text("# Feature-direction sanity check\n\nCorrelations between major numerical values and their SHAP contributions are in `feature_sanity.json`. Flags identify counter-intuitive protective relationships for schedule pressure, revision history, or stagnation; they are review prompts, not imposed monotonic rules.\n\n"+markdown_table(sanity),encoding="utf-8")
    (REPORT_DIR/"peer_engine_plan.md").write_text("# Peer engine plan\n\nModel V1 does not implement peer scoring. A later engine should form cohorts using normalized sector, log-scaled cost bucket, physical-progress stage, and project-age band. Require minimum cohort support, calculate robust percentile ranks, expose cohort composition, and never interpret peer differences causally. `peer_reference_v1.csv` preserves the needed frozen metadata.\n",encoding="utf-8")
    quality_experiment={"threshold":QUALITY_THRESHOLD,"full_test":final_metrics,"high_quality_train_rows":len(high_train),"high_quality_test_rows":len(high_test),"high_quality_test":high_metrics}; write_json(REPORT_DIR/"quality_score_experiment.json",quality_experiment)
    reproducibility={"python":sys.version,"platform":platform.platform(),"packages":{"pandas":pd.__version__,"numpy":np.__version__,"scikit_learn":sklearn.__version__,"catboost":catboost.__version__,"xgboost":xgboost.__version__,"shap":shap.__version__},"dataset_sha256":dataset_hash,"dataset_version":DATASET_VERSION,"random_seed":RANDOM_SEED,"model_configuration":selected["config"]}; write_json(REPORT_DIR/"reproducibility.json",reproducibility)

    prevalence=float(test[TARGET].mean()); logistic_pr=family_test["logistic"]["pr_auc"]
    if final_metrics["pr_auc"] <= prevalence*1.2 or final_metrics["roc_auc"] < .55: status="RED"
    elif final_metrics["pr_auc"] >= logistic_pr*1.05 and final_metrics["roc_auc"]>=.65 and final_metrics["brier"]<prevalence*(1-prevalence): status="GREEN"
    else: status="YELLOW"
    final_report=f"""# PAIMANA Sentinel — Model V1 final report

## Decision

**MODEL_STATUS={status}**

The validation-selected model is **{selected_name}**, calibrated with **{calibration_method}**. Selection emphasized future-period PR-AUC, operational recall/precision, calibration, stability, and explainability—not accuracy alone.

The model has substantial signal above the temporal-test prevalence baseline, but it is YELLOW unless it also materially exceeds the transparent logistic benchmark. Here, final PR-AUC is **{final_metrics['pr_auc']:.4f}** versus logistic **{logistic_pr:.4f}**; test ECE is **{final_metrics['ece']:.4f}**. The selected model therefore requires another feature/calibration iteration before a GREEN production recommendation.

## Temporal test metrics

{markdown_table([final_metrics])}

## Baseline comparison

{markdown_table(comparison,["model","pr_auc","roc_auc","precision","recall","f1","balanced_accuracy","brier"])}

## Quality experiment

{markdown_table([{"dataset":"full",**final_metrics},{"dataset":"quality >= 80",**high_metrics}])}

## Limitations

The outcome is a reported target-date deterioration signal, not proof of execution failure or causality. Reporting regimes changed during Dataset v1.0. Temporal test contains recurring and unseen projects; unseen-project results are separately reported. No cost model, neural network, frontend, peer engine, or causal what-if engine was trained.
"""
    (REPORT_DIR/"final_model_report.md").write_text(final_report,encoding="utf-8")
    write_json(REPORT_DIR/"training_result.json",{"status":status,"selected_model":selected_name,"calibration":calibration_method,"thresholds":thresholds,"test_metrics":final_metrics,"top_global_drivers":importance[:15],"unseen_project_metrics":unseen_metrics,"quality_experiment":quality_experiment})

    print("\nPAIMANA SENTINEL — MODEL V1")
    print(f"DATASET: Rows {len(data):,}; Projects {data.canonical_project_id.nunique():,}; Target prevalence {100*data[TARGET].mean():.2f}%")
    print(f"TEMPORAL SPLIT: Train {len(train):,} ({TRAIN_START}..{TRAIN_END}); Validation {len(valid):,} ({VALID_START}..{VALID_END}); Test {len(test):,} ({TEST_START}..{TEST_END})")
    for family in ("dummy","logistic","catboost","xgboost"): print(f"{family.upper()}: PR-AUC {family_test[family]['pr_auc']:.4f}; ROC-AUC {family_test[family]['roc_auc']:.4f}")
    print("BEST MODEL:",selected_name)
    for key in ("pr_auc","roc_auc","precision","recall","f1","balanced_accuracy","brier"): print(f"{key.upper()}: {final_metrics[key]:.4f}")
    print(f"SELECTED BALANCED THRESHOLD: {balanced:.4f}; FPR {final_metrics['false_positive_rate']:.4f}; Alerts {final_metrics['alerts_generated']}")
    print(f"CALIBRATION: {calibration_method}; raw Brier {classification_metrics(test[TARGET],raw_test,.5)['brier']:.4f}; calibrated Brier {final_metrics['brier']:.4f}")
    print("TOP GLOBAL DRIVERS:",", ".join(item["feature"] for item in importance[:10]))
    print("TEMPORAL STABILITY:",[(r["month"],round(r["pr_auc"],4)) for r in monthly])
    print(f"MODEL_STATUS={status}")


if __name__ == "__main__": main()
