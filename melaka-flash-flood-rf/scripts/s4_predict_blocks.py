"""STEP 4: predict the whole surface in 37 row blocks, classify, and tabulate area."""
import joblib, numpy as np, pandas as pd, rasterio
import config as C
from audit import log, require

model = joblib.load(C.MODEL_FILE)
srcs = {p: rasterio.open(C.RASTERS[p]) for p in C.PREDICTORS}
ref = srcs[C.PREDICTORS[0]]
H, W = ref.height, ref.width
profile = ref.profile | dict(dtype="float32", count=1, nodata=-9999.0, compress="lzw")
counts = np.zeros(len(C.CLASS_NAMES), dtype=np.int64)

with rasterio.open(C.SCORE_TIF, "w", **profile) as dst:
    for rows in np.array_split(np.arange(H), C.N_BLOCKS):
        win = rasterio.windows.Window(0, int(rows[0]), W, len(rows))
        cube = {p: srcs[p].read(1, window=win).astype("float64") for p in C.PREDICTORS}
        valid = np.ones((len(rows), W), bool)
        for p, a in cube.items():
            nd = srcs[p].nodata
            valid &= ~np.isnan(a) & (a != nd if nd is not None else True)
        valid &= np.isin(cube["landcover"], C.LC_KEEP)
        out = np.full((len(rows), W), -9999.0, dtype="float32")
        if valid.any():
            Xb = pd.DataFrame({p: cube[p][valid] for p in C.PREDICTORS})
            score = model.predict_proba(Xb)[:, 1]
            out[valid] = score
            cls = np.digitize(score, C.CLASS_EDGES, right=True)   # (0.2,0.4] etc.
            counts += np.bincount(cls, minlength=len(C.CLASS_NAMES))
        dst.write(out, 1, window=win)

total = int(counts.sum())
area = counts * C.CELL_M ** 2 / 1e6
tab = pd.DataFrame({"class": C.CLASS_NAMES, "cells": counts, "area_km2": area.round(3),
                    "area_pct": (100 * counts / total).round(2)})
tab.loc[len(tab)] = ["Total", total, round(area.sum(), 3), 100.0]
tab.to_csv(C.OUT / "class_areas.csv", index=False)
print(tab)
log("4_prediction", files=[C.SCORE_TIF, C.OUT / "class_areas.csv"], n_blocks=C.N_BLOCKS,
    cells_valid=total, area_km2=round(float(area.sum()), 3),
    high_plus_very_high_pct=round(float(100 * counts[3:].sum() / total), 2))
