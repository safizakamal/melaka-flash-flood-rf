"""Single source of truth for every setting used in the paper.
Edit paths here only; no other script contains a hard-coded number."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # repository root
DATA = ROOT / "data"          # input rasters + flood/background points
OUT = ROOT / "results"        # everything the workflow writes
OUT.mkdir(exist_ok=True)

# ---- model settings (as reported in the paper) ----
SEED = 42
N_TREES = 500
THRESHOLD = 0.5
N_BLOCKS = 37                 # row blocks for full-surface prediction
CELL_M = 30
CLASS_EDGES = [0.2, 0.4, 0.6, 0.8]            # equal-interval, right-inclusive
CLASS_NAMES = ["Very low", "Low", "Moderate", "High", "Very high"]
N_BOOT = 10_000
BLOCK_M = int(os.environ.get("BLOCK_M", 10_000))   # spatial-CV block size (m)

# ---- variables ----
PREDICTORS = ["elevation", "slope", "twi", "dist_drain", "landcover"]
CATEGORICAL = ["landcover"]
LC_KEEP = [2, 5, 7, 8, 11]    # trees, crops, built area, bare ground, rangeland
LABEL = "flood"               # 1 = flood record, 0 = background
SPLIT = "split"               # 'train' / 'test'

# ---- inputs ----
RASTER_DIR = DATA / "aligned"                 # written by step 1
RASTERS = {p: RASTER_DIR / f"{p}.tif" for p in PREDICTORS}
RAW_RASTERS = {p: DATA / "raw" / f"{p}.tif" for p in PREDICTORS}
POINTS_FC = DATA / "melaka.gdb" / "flood_background_points"   # step 1 (ArcGIS)
BOUNDARY_FC = DATA / "melaka.gdb" / "melaka_boundary"

# ---- outputs ----
SAMPLES_CSV = DATA / "samples" / "samples.csv"
MODEL_FILE = OUT / "rf_model.joblib"
SCORE_TIF = OUT / "susceptibility_score.tif"

# ---- numbers the paper reports; step 7 checks the run against them ----
EXPECTED = {
    "n_flood_sites": 90, "n_records": 177, "n_train": 129, "n_test": 48,
    "n_test_flood": 27, "n_test_background": 21,
    "cells_valid": 1_799_525, "area_km2": 1619.573,
}
