"""STEP 6: check this run against the numbers printed in the paper, and (optionally)
against a previous run to prove reproducibility.  usage: python s6_verify.py [other_outputs_dir]"""
import json, sys
import pandas as pd
import config as C

paper = dict(TP=22, TN=18, FP=3, FN=5, accuracy=0.8333, precision=0.88, sensitivity=0.8148,
             specificity=0.8571, f1=0.8462, kappa=0.665, auc=0.837)
m = json.loads((C.OUT / "metrics.json").read_text())
ok = True
for k, v in paper.items():
    good = abs(m[k] - v) < (0.5 if k in "TP TN FP FN" else 0.0006)
    ok &= good
    print(f"{k:12s} paper={v:<8} run={m[k]:<10.4f} {'OK' if good else 'DIFFERS'}")
a = pd.read_csv(C.OUT / "class_areas.csv").iloc[-1]
print("valid cells", int(a.cells), "(paper 1,799,525)", "area", a.area_km2, "(paper 1619.573)")
if len(sys.argv) > 1:
    other = json.loads((pd.io.common.Path(sys.argv[1]) / "metrics.json").read_text())
    same = other == m
    print("Identical to previous run:", same); ok &= same
print("\nRESULT:", "REPRODUCES THE PAPER" if ok else "DOES NOT MATCH THE PAPER: report the difference, do not hide it")
