import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import config as C

def make_rf(seed=C.SEED):
    """RF on the five predictors; land cover one-hot encoded (categorical)."""
    num = [p for p in C.PREDICTORS if p not in C.CATEGORICAL]
    pre = ColumnTransformer([("cat", OneHotEncoder(categories=[C.LC_KEEP], handle_unknown="ignore"),
                              C.CATEGORICAL)], remainder="passthrough")
    # remainder keeps numeric columns; column order handled by name via DataFrame input
    return Pipeline([("pre", pre),
                     ("rf", RandomForestClassifier(n_estimators=C.N_TREES, random_state=C.SEED if seed is None else seed,
                                                   n_jobs=-1))])

def metrics(y, prob, thr=C.THRESHOLD):
    from sklearn.metrics import cohen_kappa_score, roc_auc_score
    pred = (prob >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    P = tp / (tp + fp) if tp + fp else float("nan"); S = tp / (tp + fn)
    return dict(TP=tp, TN=tn, FP=fp, FN=fn,
                accuracy=(tp + tn) / len(y), precision=P, sensitivity=S,
                specificity=tn / (tn + fp), f1=2 * P * S / (P + S),
                kappa=float(cohen_kappa_score(y, pred)), auc=float(roc_auc_score(y, prob)))

def bootstrap_auc(y, prob, n=C.N_BOOT, seed=C.SEED):
    """Stratified bootstrap keeping the 27:21 class counts."""
    from sklearn.metrics import roc_auc_score
    rng = np.random.RandomState(seed)   # legacy generator: this is the one that reproduces the paper's interval
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    aucs = np.empty(n)
    for i in range(n):
        idx = np.r_[rng.choice(neg, len(neg)), rng.choice(pos, len(pos))]   # background first, then flood
        aucs[i] = roc_auc_score(y[idx], prob[idx])
    return [float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))]
