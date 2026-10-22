"""ArcGIS Pro 3.6 version of the surface-prediction steps, rebuilt from the notebook
Create_RF_Probability_Raster_V3 so it runs top-to-bottom WITHOUT the open map.
Logic, names, block size (40 rows -> 37 blocks), class edges and the SSM file are unchanged.

Run in the ArcGIS Pro Python environment (e.g.  propy a1_arcgis_prediction.py)
or paste each stage into a notebook cell.  Edit only the SETTINGS block."""
import math, os, time
import numpy as np
import arcpy
from arcpy.sa import Raster, SetNull, Con, IsNull

# ============================== SETTINGS ==============================
GDB = r"C:\MELAKA_FLASHFLOOD_APACE\MelakaFlood.gdb"            # <- your default geodatabase
MODEL_FILE = r"C:\MELAKA_FLASHFLOOD_APACE\RF_FlashFlood_AllProbabilities_V3.ssm"
OUT_DIR = r"C:\MELAKA_FLASHFLOOD_APACE\outputs"                 # GeoTIFF / CSV exports go here

# Predictors as stored in the geodatabase (same names as in the notebook)
R = {
    "ELEVATION_30M":                 os.path.join(GDB, "ELEVATION_30M"),
    "SLOPE_DEGREE_30M":              os.path.join(GDB, "SLOPE_DEGREE_30M"),
    "TWI_30M":                       os.path.join(GDB, "TWI_30M"),
    "DISTANCE_DRAINAGE_30M":         os.path.join(GDB, "DISTANCE_DRAINAGE_30M"),
    "LANDCOVER_2025_30M_ALIGNED":    os.path.join(GDB, "LANDCOVER_2025_30M_ALIGNED"),  # original land cover
}
SAMPLES_FC = os.path.join(GDB, "RF_Model_Samples_Clean")   # the 177 clean records
LC_FIELD, FLOOD_FIELD, ID_FIELD = "LANDCOVER_2025_30M_ALIGNED", "FLOODSTAT", "SAMPLEID"

LC_EXCLUDE = [0, 1, 4, 10]      # NoData, water, flooded vegetation (absent from samples), clouds
BLOCK_ROWS = 40                 # 1,474 rows / 40 = 37 blocks
CLASS_EDGES = [0.20, 0.40, 0.60, 0.80]
CLASS_NAMES = {1: "Very Low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very High"}
PROB_FIELD_ALIAS = "probability: 1"
# ======================================================================

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True
os.makedirs(OUT_DIR, exist_ok=True)

REF = R["ELEVATION_30M"]
ref = arcpy.Raster(REF)
ref_sr = arcpy.Describe(REF).spatialReference
CELL, NCOL, NROW = ref.meanCellWidth, ref.width, ref.height
XMIN, YMIN, XMAX = ref.extent.XMin, ref.extent.YMin, ref.extent.XMax

LC_EXACT = os.path.join(GDB, "LANDCOVER_2025_30M_RF_EXACT")
LC_FINAL = os.path.join(GDB, "LANDCOVER_2025_30M_RF_FINAL")
PROB = os.path.join(GDB, "RF_Flood_Probability_30m")
SUSC = os.path.join(GDB, "RF_Flood_Susceptibility_5Class")
LOG = os.path.join(OUT_DIR, "arcgis_audit.txt")


def log(msg):
    print(msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")


def env():
    return arcpy.EnvManager(snapRaster=REF, cellSize=REF, extent=REF, mask=REF,
                            outputCoordinateSystem=ref_sr)


# ---------------- Stage 0: environment + alignment check ----------------
def stage0_check():
    log(f"ArcGIS Pro {arcpy.GetInstallInfo()['Version']}; model exists: {os.path.exists(MODEL_FILE)}")
    log(f"Reference grid: {NCOL} x {NROW}, cell {CELL}, CRS {ref_sr.name} ({ref_sr.factoryCode})")
    ok = True
    for name, path in R.items():
        r, sr = arcpy.Raster(path), arcpy.Describe(path).spatialReference
        same = (abs(r.meanCellWidth - CELL) < 1e-3 and r.width == NCOL and r.height == NROW
                and abs(r.extent.XMin - XMIN) < 0.01 and abs(r.extent.YMax - ref.extent.YMax) < 0.01
                and sr.factoryCode == ref_sr.factoryCode)
        log(f"  {name}: {'PASS' if same else 'FAIL'}")
        ok &= same
    if not ok:
        raise RuntimeError("Alignment problem: do not continue.")


# ---------------- Stage 1: land cover ready for prediction ----------------
def stage1_landcover():
    with env():
        exact = Con(~IsNull(Raster(REF)), Raster(R["LANDCOVER_2025_30M_ALIGNED"]))
        exact.save(LC_EXACT)
        cond = None
        lc = Raster(LC_EXACT)
        for code in LC_EXCLUDE:
            cond = (lc == code) if cond is None else (cond | (lc == code))
        SetNull(cond, lc).save(LC_FINAL)
    arr = arcpy.RasterToNumPyArray(LC_FINAL, nodata_to_value=-999999)
    cats = sorted(int(v) for v in np.unique(arr) if v != -999999)

    # categories present in the 177 clean samples
    counts = {}
    with arcpy.da.SearchCursor(SAMPLES_FC, [LC_FIELD, FLOOD_FIELD]) as cur:
        for lcv, _ in cur:
            if lcv is not None:
                counts[int(lcv)] = counts.get(int(lcv), 0) + 1
    unsupported = sorted(set(cats) - set(counts))
    log(f"Land-cover categories kept for prediction: {cats}")
    log(f"Land-cover counts in the clean samples: {dict(sorted(counts.items()))}")
    log(f"Prediction categories absent from the samples: {unsupported}")
    if unsupported:
        raise RuntimeError(f"Categories {unsupported} were never seen in training.")


MATCH = lambda: [
    [R["ELEVATION_30M"], "ELEVATION_30M", False],
    [R["SLOPE_DEGREE_30M"], "SLOPE_DEGREE_30M", False],
    [R["TWI_30M"], "TWI_30M", False],
    [R["DISTANCE_DRAINAGE_30M"], "DISTANCE_DRAINAGE_30M", False],
    [LC_FINAL, "LANDCOVER_2025_30M_ALIGNED", True],      # model's variable name <- final raster
]


# ---------------- Stage 2: block-wise prediction + mosaic ----------------
def stage2_predict():
    paths = [R["ELEVATION_30M"], R["SLOPE_DEGREE_30M"], R["TWI_30M"],
             R["DISTANCE_DRAINAGE_30M"], LC_FINAL]
    nblocks = math.ceil(NROW / BLOCK_ROWS)
    log(f"Predicting {NROW} rows in {nblocks} blocks of {BLOCK_ROWS} rows")
    tiles, total_valid, t0 = [], 0, time.time()
    pts, preds = os.path.join(GDB, "TEMP_RF_Tile_Points"), os.path.join(GDB, "TEMP_RF_Tile_Predictions")

    for b, start in enumerate(range(0, NROW, BLOCK_ROWS), start=1):
        nrows = min(BLOCK_ROWS, NROW - start)
        ymin_t = YMIN + start * CELL
        ymax_t = ymin_t + nrows * CELL
        tile = os.path.join(GDB, f"RF_Prob_Tile_{b:03d}")
        if arcpy.Exists(tile):                       # resume after an interruption
            tiles.append(tile)
            continue
        valid = np.ones((nrows, NCOL), bool)
        for p in paths:
            a = arcpy.RasterToNumPyArray(p, arcpy.Point(XMIN, ymin_t), NCOL, nrows, nodata_to_value=-999999.0)
            valid &= np.isfinite(a) & (a != -999999.0)
        rr, cc = np.where(valid)
        total_valid += len(rr)
        log(f"Block {b}/{nblocks}: rows {start}-{start + nrows - 1}, valid cells {len(rr)}")
        if len(rr) == 0:
            continue
        arr = np.empty(len(rr), dtype=[("CELL_ID", "i8"), ("X_COORD", "f8"), ("Y_COORD", "f8")])
        arr["CELL_ID"] = (start + rr).astype(np.int64) * NCOL + cc
        arr["X_COORD"] = XMIN + (cc + 0.5) * CELL
        arr["Y_COORD"] = ymax_t - (rr + 0.5) * CELL
        for d in (pts, preds):
            if arcpy.Exists(d):
                arcpy.management.Delete(d)
        arcpy.da.NumPyArrayToFeatureClass(arr, pts, ["X_COORD", "Y_COORD"], ref_sr)
        arcpy.stats.PredictUsingSSMFile(MODEL_FILE, "PREDICT_FEATURES", pts, preds, None, None, None, MATCH())
        field = next((f.name for f in arcpy.ListFields(preds)
                      if f.aliasName.strip().lower() == PROB_FIELD_ALIAS), None)
        if field is None:
            raise RuntimeError("'Probability: 1' field not found in the prediction output.")
        with arcpy.EnvManager(snapRaster=REF, cellSize=REF,
                              extent=arcpy.Extent(XMIN, ymin_t, XMAX, ymax_t),
                              outputCoordinateSystem=ref_sr):
            arcpy.conversion.PointToRaster(preds, field, tile, "MEAN", None, CELL)
        tiles.append(tile)
        for d in (pts, preds):
            arcpy.management.Delete(d)
        log(f"  tile done; elapsed {(time.time() - t0) / 60:.1f} min")

    if arcpy.Exists(PROB):
        arcpy.management.Delete(PROB)
    arcpy.management.MosaicToNewRaster(tiles, GDB, os.path.basename(PROB), ref_sr,
                                       "32_BIT_FLOAT", CELL, 1, "FIRST", "FIRST")
    mn = float(arcpy.management.GetRasterProperties(PROB, "MINIMUM").getOutput(0))
    mx = float(arcpy.management.GetRasterProperties(PROB, "MAXIMUM").getOutput(0))
    log(f"Probability raster {arcpy.Raster(PROB).width} x {arcpy.Raster(PROB).height}; min {mn:.4f}, max {mx:.4f}")


# ---------------- Stage 3: five classes, area table, exports ----------------
def stage3_classify_and_export():
    p = Raster(PROB)
    with arcpy.EnvManager(snapRaster=REF, cellSize=REF, extent=REF, mask=PROB, outputCoordinateSystem=ref_sr):
        e = CLASS_EDGES
        Con(p <= e[0], 1, Con(p <= e[1], 2, Con(p <= e[2], 3, Con(p <= e[3], 4, 5)))).save(SUSC)
    arcpy.management.BuildRasterAttributeTable(SUSC, "Overwrite")

    rows = [(int(v), int(c)) for v, c in arcpy.da.SearchCursor(SUSC, ["VALUE", "COUNT"])]
    total = sum(c for _, c in rows)
    lines = ["class,cells,area_km2,area_pct"]
    for v, c in rows:
        lines.append(f"{CLASS_NAMES[v]},{c},{c * CELL * CELL / 1e6:.3f},{100 * c / total:.2f}")
    lines.append(f"Total,{total},{total * CELL * CELL / 1e6:.3f},100.00")
    open(os.path.join(OUT_DIR, "class_areas_arcgis.csv"), "w").write("\n".join(lines))
    log("Class table:\n" + "\n".join(lines))

    # exports for the Python verification scripts (s2-s6)
    arcpy.management.CopyRaster(PROB, os.path.join(OUT_DIR, "susceptibility_score.tif"),
                                pixel_type="32_BIT_FLOAT")
    arcpy.conversion.ExportTable(SAMPLES_FC, os.path.join(OUT_DIR, "samples_arcgis.csv"))
    log("Exported susceptibility_score.tif and samples_arcgis.csv")


if __name__ == "__main__":
    stage0_check()
    stage1_landcover()
    stage2_predict()
    stage3_classify_and_export()
