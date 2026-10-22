"""STEP 3: train on 129 records, evaluate once on the 48 hold-out records."""
import json, joblib, numpy as np, pandas as pd
import config as C
from audit import log
from model_utils import make_rf, metrics, bootstrap_auc

df = pd.read_csv(C.SAMPLES_CSV)
tr, te = df[df[C.SPLIT] == "train"], df[df[C.SPLIT] == "test"]
X = lambda d: d[C.PREDICTORS]

model = make_rf().fit(X(tr), tr[C.LABEL])
prob = model.predict_proba(X(te))[:, 1]
y = te[C.LABEL].to_numpy()

m = metrics(y, prob)
m["auc_ci95"] = bootstrap_auc(y, prob)
(C.OUT / "metrics.json").write_text(json.dumps(m, indent=2))
te.assign(prob=prob, pred=(prob >= C.THRESHOLD).astype(int)).to_csv(C.OUT / "test_predictions.csv", index=False)
joblib.dump(model, C.MODEL_FILE)
log("3_model", files=[C.MODEL_FILE, C.OUT / "test_predictions.csv"],
    n_trees=C.N_TREES, seed=C.SEED, **{k: (round(v, 4) if isinstance(v, float) else v)
    for k, v in m.items() if k != "auc_ci95"}, auc_ci95=[round(v, 3) for v in m["auc_ci95"]])
print(json.dumps(m, indent=2))
