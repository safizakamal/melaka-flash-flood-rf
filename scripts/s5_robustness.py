"""STEP 5 (answers likely reviewer comments): baseline, spatial-block CV, variable importance."""
import json, numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import config as C
from audit import log
from model_utils import make_rf, metrics

df = pd.read_csv(C.SAMPLES_CSV)
tr, te = df[df[C.SPLIT] == "train"], df[df[C.SPLIT] == "test"]
num = [p for p in C.PREDICTORS if p not in C.CATEGORICAL]
res = {}

# (a) logistic-regression baseline on the same 129/48 split
def make_lr():
    return Pipeline([("pre", ColumnTransformer([
        ("n", StandardScaler(), num),
        ("c", OneHotEncoder(categories=[C.LC_KEEP], handle_unknown="ignore"), C.CATEGORICAL)])),
        ("lr", LogisticRegression(max_iter=2000))])
lr = make_lr().fit(tr[C.PREDICTORS], tr[C.LABEL])
res["baseline_logistic_holdout"] = metrics(te[C.LABEL].to_numpy(), lr.predict_proba(te[C.PREDICTORS])[:, 1])

# (b) repeated stratified CV (all 177 records) and spatial-block CV (C.BLOCK_M blocks)
def cv_auc(splits, model_fn):
    a = []
    for i, j in splits:
        m = model_fn().fit(df.iloc[i][C.PREDICTORS], df.iloc[i][C.LABEL])
        yj = df.iloc[j][C.LABEL]
        if yj.nunique() == 2:
            a.append(roc_auc_score(yj, m.predict_proba(df.iloc[j][C.PREDICTORS])[:, 1]))
    return dict(mean=float(np.mean(a)), sd=float(np.std(a)), folds=len(a))

rs = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=C.SEED)
res["rf_repeated_cv_auc"] = cv_auc(rs.split(df, df[C.LABEL]), make_rf)
blocks = (df.x // C.BLOCK_M).astype(int).astype(str) + "_" + (df.y // C.BLOCK_M).astype(int).astype(str)
res["n_spatial_blocks"] = int(blocks.nunique())
k = min(5, blocks.nunique())
assert k >= 2, 'Too few spatial blocks: reduce BLOCK_M in config.py'
res["rf_spatial_block_cv_auc"] = cv_auc(GroupKFold(n_splits=k).split(df, df[C.LABEL], blocks), make_rf)
res["logistic_spatial_block_cv_auc"] = cv_auc(GroupKFold(n_splits=k).split(df, df[C.LABEL], blocks), make_lr)

# (c) permutation importance on the hold-out records (AUC drop)
rf = make_rf().fit(tr[C.PREDICTORS], tr[C.LABEL])
pi = permutation_importance(rf, te[C.PREDICTORS], te[C.LABEL], scoring="roc_auc",
                            n_repeats=50, random_state=C.SEED)
imp = pd.DataFrame({"predictor": C.PREDICTORS, "auc_drop": pi.importances_mean,
                    "sd": pi.importances_std}).sort_values("auc_drop", ascending=False)
imp.to_csv(C.OUT / "permutation_importance.csv", index=False)
res["importance"] = imp.round(4).to_dict("records")

(C.OUT / f"robustness_block{C.BLOCK_M // 1000}km.json").write_text(json.dumps(res, indent=2))
log("5_robustness", files=[C.OUT / f"robustness_block{C.BLOCK_M // 1000}km.json", C.OUT / "permutation_importance.csv"],
    rf_block_auc=round(res["rf_spatial_block_cv_auc"]["mean"], 3),
    baseline_auc=round(res["baseline_logistic_holdout"]["auc"], 3))
print(json.dumps(res, indent=2))
