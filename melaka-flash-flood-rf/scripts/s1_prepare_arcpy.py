"""STEP 1 (ArcGIS Pro 3.6, run in the Pro Python environment or as a notebook).
Align the five predictors to one grid, extract values at the points, write samples.csv.
NOTE: arcpy calls follow the documented tools; confirm parameter names against your
Pro 3.6 version (Geoprocessing > History > right-click > Copy Python Command)."""
import arcpy, pandas as pd, numpy as np
from arcpy.sa import ExtractMultiValuesToPoints
import config as C
from audit import log, require

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True
C.RASTER_DIR.mkdir(parents=True, exist_ok=True)

# Reference grid: elevation raster defines cell size / origin / snap
ref = str(C.RAW_RASTERS["elevation"])
arcpy.env.snapRaster = ref
arcpy.env.cellSize = C.CELL_M
arcpy.env.mask = str(C.BOUNDARY_FC)
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("GDM 2000 MRSO Peninsular Malaysia")
arcpy.env.extent = arcpy.Describe(str(C.BOUNDARY_FC)).extent

for name, src in C.RAW_RASTERS.items():
    out = str(C.RASTERS[name])
    method = "NEAREST" if name in C.CATEGORICAL else "BILINEAR"
    arcpy.management.ProjectRaster(str(src), out, arcpy.env.outputCoordinateSystem,
                                   method, C.CELL_M)
    r = arcpy.Describe(out)
    print(name, r.meanCellWidth, r.extent)

# Extract raster values at flood + background points
pts = "in_memory/pts"
arcpy.management.CopyFeatures(str(C.POINTS_FC), pts)
ExtractMultiValuesToPoints(pts, [[str(C.RASTERS[p]), p] for p in C.PREDICTORS])

fields = ["OID@", "SHAPE@X", "SHAPE@Y", C.LABEL, C.SPLIT] + C.PREDICTORS
arr = arcpy.da.FeatureClassToNumPyArray(pts, fields, null_value=np.nan)
df = pd.DataFrame(arr).rename(columns={"SHAPE@X": "x", "SHAPE@Y": "y", "OID@": "oid"})
n_raw = len(df)

df = df.dropna(subset=C.PREDICTORS)                  # incomplete records
df = df[df["landcover"].isin(C.LC_KEEP)]             # classes retained for prediction
df.to_csv(C.SAMPLES_CSV, index=False)

log("1_samples", files=[C.SAMPLES_CSV], n_raw_points=n_raw, n_records=len(df),
    n_flood=int(df[C.LABEL].sum()), n_background=int((df[C.LABEL] == 0).sum()))
require(len(df) == C.EXPECTED["n_records"],
        f"expected {C.EXPECTED['n_records']} records, got {len(df)}")
