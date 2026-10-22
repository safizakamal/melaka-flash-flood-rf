"""Recompute every hold-out number in the paper from ArcGIS' own test table (no re-training needed).
usage: python s7_verify_from_arcgis_csv.py RF_Test_Probability_V3.csv"""
import sys, json, numpy as np, pandas as pd
from model_utils import metrics, bootstrap_auc

d = pd.read_csv(sys.argv[1], encoding="utf-8-sig")
need = {"FloodStat", "PREDICTED", "ProbFlood", "ResultCode"}
assert need <= set(d.columns), f"missing columns: {need - set(d.columns)}"
y, prob = d["FloodStat"].to_numpy().astype(int), d["ProbFlood"].to_numpy().astype(float)
print("records:", len(d), "| flood:", int(y.sum()), "| background:", int((y == 0).sum()))
print("exact-0.5 ties:", int((prob == 0.5).sum()),
      "| PREDICTED equals (prob>0.5):", bool(((prob > 0.5).astype(int) == d["PREDICTED"]).all()))
print("ResultCode counts:", d["ResultCode"].value_counts().to_dict())

m = metrics(y, prob); m["auc_ci95"] = bootstrap_auc(y, prob)
paper = dict(TP=22, TN=18, FP=3, FN=5, accuracy=.8333, precision=.88, sensitivity=.8148,
             specificity=.8571, f1=.8462, kappa=.665, auc=.837)
ok = True
for k, v in paper.items():
    good = abs(m[k] - v) < (0.5 if k in ("TP", "TN", "FP", "FN") else 0.0006); ok &= good
    print(f"{k:12s} paper={v:<8} csv={m[k]:<10.4f} {'OK' if good else 'DIFFERS'}")
lo, hi = m["auc_ci95"]; print(f"AUC 95% CI  paper=0.695-0.958  csv={lo:.3f}-{hi:.3f}")
ok &= abs(lo - .695) < .0015 and abs(hi - .958) < .0015
print("\nRESULT:", "ALL PAPER NUMBERS REPRODUCED FROM THE ARCGIS TABLE" if ok else "SOME NUMBERS DIFFER: report the difference")
