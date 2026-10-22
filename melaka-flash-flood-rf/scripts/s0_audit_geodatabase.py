"""Audit the project geodatabase WITHOUT ArcGIS (needs: pip install pandas pyogrio geopandas).
usage: python s0_audit_geodatabase.py path/to/Melaka_FlashFlood.gdb
Prints the audit trail from raw points to the 129/48 split and checks the paper's counts."""
import sys, pandas as pd, pyogrio, warnings
warnings.filterwarnings("ignore")
G = sys.argv[1]
rd = lambda n: pyogrio.read_dataframe(G, layer=n, fid_as_index=True)
ok = True
def check(label, got, want):
    global ok
    good = got == want; ok &= good
    print(f"{'OK    ' if good else 'DIFFERS'} {label}: {got}" + ("" if good else f"  (expected {want})"))

fl, bg, allp, clean = rd("Flood_Sites_RSO"), rd("Background_Points_90"), rd("RF_Sample_Points"), rd("RF_Model_Samples_Clean")
tr, te = rd("RF_Training_Points_V2"), rd("RF_Testing_Points_V2")
print("== audit trail")
check("flood sites", len(fl), 90); check("background points", len(bg), 90)
check("combined sample points", len(allp), 180)
removed = allp[~allp.SampleID.isin(clean.SampleID)]
check("clean records", len(clean), 177)
print("   removed (null predictors):", removed.SampleID.tolist(), "|", removed.SiteName.fillna("-").tolist())
print("   clean flood / background:", int(clean.FloodStat.sum()), "/", int((clean.FloodStat == 0).sum()))
print("== split used by the model (V2 layers)")
check("training records", len(tr), 129); check("testing records", len(te), 48)
check("train flood/background", (int(tr.FloodStat.sum()), int((tr.FloodStat == 0).sum())), (61, 68))
check("test flood/background", (int(te.FloodStat.sum()), int((te.FloodStat == 0).sum())), (27, 21))
check("train and test share no record", len(set(tr.SampleID) & set(te.SampleID)), 0)
check("train + test = clean set", set(tr.SampleID) | set(te.SampleID) == set(clean.SampleID), True)
v1tr, v1te = rd("RF_Training_Points"), rd("RF_Testing_Points")
print("   moved from V1 test to V2 train:", sorted(set(v1te.SampleID) & set(tr.SampleID)) or "none")
print("   moved from V1 train to V2 test:", sorted(set(te.SampleID) - set(v1te.SampleID)))
print("== land-cover support in the 177 records (class: flood / background)")
x = pd.crosstab(clean["LandCover_2025_30m_Aligned"], clean.FloodStat)
print(x.rename(columns={0: "background", 1: "flood"}).to_string())
print("== variable importance (V3 model run)")
imp = rd("RF_Importance_Probability_V3"); print(imp[["VARIABLES", "PERCENTAGE"]].to_string(index=False))
print("\nRESULT:", "ALL AUDIT CHECKS PASS" if ok else "SOME CHECKS DIFFER")
