"""
STEP A2 (ArcGIS Pro): land-cover cell counts, excluded area, and DEM void check.
Run in the ArcGIS Pro Python window or a notebook. NOT yet run on ArcGIS: check the
edited names below first. Writes outputs/a2_report.txt next to this script.

Answers reviewer points: excluded area, spatial coverage, missing raster values, DEM voids.
"""
import os
import arcpy
from arcpy.sa import ExtractByMask, Con, IsNull, Raster

# ---------------- EDIT THESE ----------------
GDB       = r"C:\path\to\Melaka_FlashFlood.gdb"
LC_EXACT  = "LANDCOVER_2025_30M_RF_EXACT"      # pre-exclusion land cover (NOT *_FINAL)
PRED      = "RF_Flood_Probability_30m"          # final 32-bit probability raster (valid-cell mask)
BOUNDARY  = "MELAKA_LA_BOUNDARY_RSO"            # Melaka boundary polygon in EPSG:3375
DEM_PROC  = "Elevation_30m"                     # processed elevation used for the model
DEM_ORIG  = r"C:\path\to\DEM.tif"               # original SRTM tile (projected copy)
SUPPORTED = {2, 5, 7, 8, 11}
CELL_KM2  = 0.0009                              # 30 m x 30 m = 900 m2
# --------------------------------------------

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

# Temporary rasters go to a separate scratch geodatabase, so the project geodatabase
# (which ArcGIS keeps locked while it is open) is only read, never written.
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
SCRATCH = os.path.join(HERE, "a2_scratch.gdb")
if not arcpy.Exists(SCRATCH):
    arcpy.management.CreateFileGDB(HERE, "a2_scratch.gdb")

def tmp(name):
    path = os.path.join(SCRATCH, name)
    if arcpy.Exists(path):
        arcpy.management.Delete(path)
    return path

LC_EXACT = os.path.join(GDB, LC_EXACT)
PRED = os.path.join(GDB, PRED)
DEM_PROC = os.path.join(GDB, DEM_PROC)
arcpy.env.snapRaster = LC_EXACT
arcpy.env.cellSize = LC_EXACT
bnd = os.path.join(GDB, BOUNDARY)
lines = []

def say(s=""):
    print(s)
    lines.append(s)

def vat_counts(ras):
    """Return {value: count} from the raster attribute table of an integer raster."""
    arcpy.management.BuildRasterAttributeTable(ras, "OVERWRITE")
    out = {}
    with arcpy.da.SearchCursor(ras, ["Value", "Count"]) as cur:
        for v, c in cur:
            out[int(v)] = int(c)
    return out

# 1. cells inside the boundary (all cells, whatever their value)
BND_RAS = tmp("bnd_ras")
arcpy.conversion.PolygonToRaster(bnd, arcpy.Describe(bnd).OIDFieldName, BND_RAS,
                                 "CELL_CENTER", "NONE", 30)
n_bnd = sum(vat_counts(BND_RAS).values())

# 2. land-cover counts by code inside the boundary
LC_IN = tmp("lc_in_bnd")
ExtractByMask(LC_EXACT, bnd).save(LC_IN)
lc = vat_counts(LC_IN)
n_lc_valued = sum(lc.values())
n_lc_null = n_bnd - n_lc_valued      # cells inside the boundary that are true NoData

say("Land-cover codes inside the Melaka boundary (30 m cells)")
say("code, cells, km2, supported_by_model")
for k in sorted(lc):
    say(f"{k}, {lc[k]}, {lc[k]*CELL_KM2:.3f}, {'yes' if k in SUPPORTED else 'no'}")
say(f"true NoData inside boundary, {n_lc_null}, {n_lc_null*CELL_KM2:.3f}")
say(f"all cells inside boundary, {n_bnd}, {n_bnd*CELL_KM2:.3f}")

# 3. valid prediction cells inside the boundary
valid = ExtractByMask(Con(IsNull(Raster(PRED)), 0, 1), bnd)
VALID = tmp("valid_in_bnd")
valid.save(VALID)
vc = vat_counts(VALID)
n_valid = vc.get(1, 0)
say("")
say(f"valid prediction cells, {n_valid}, {n_valid*CELL_KM2:.4f} km2 (paper: 1,799,525 = 1,619.573 km2)")
excl = n_bnd - n_valid
unsupported = sum(c for k, c in lc.items() if k not in SUPPORTED)
other = excl - unsupported - n_lc_null
say(f"excluded cells, {excl}, {excl*CELL_KM2:.3f} km2, {100*excl/n_bnd:.2f}% of boundary")
say(f"  of which unsupported land-cover codes, {unsupported}, {unsupported*CELL_KM2:.3f} km2")
say(f"  of which land cover NoData, {n_lc_null}, {n_lc_null*CELL_KM2:.3f} km2")
say(f"  of which other predictor NoData (remainder), {other}, {other*CELL_KM2:.3f} km2")
say("(a negative remainder means the sets overlap; report only the first two lines then)")

# 4. DEM voids inside the boundary: SRTM voids are stored as values near -32768, not NoData
for label, path in [("original DEM", DEM_ORIG), ("processed DEM", DEM_PROC)]:
    r = Raster(path)
    void = ExtractByMask(Con(r <= -32000, 1, 0), bnd)
    VOID = tmp("void_tmp")
    void.save(VOID)
    vcnt = vat_counts(VOID)
    nul = ExtractByMask(Con(IsNull(r), 1, 0), bnd)
    NUL = tmp("null_tmp")
    nul.save(NUL)
    ncnt = vat_counts(NUL)
    say(f"{label}: void-valued cells {vcnt.get(1, 0)}, NoData cells {ncnt.get(1, 0)} (inside boundary)")

os.makedirs(os.path.join(HERE, "outputs"), exist_ok=True)
with open(os.path.join(HERE, "outputs", "a2_report.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
say("Saved outputs/a2_report.txt next to this script.")
