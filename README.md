# Melaka flash-flood susceptibility: Random Forest workflow (APACE2026)

Code and data tables for the paper *A Reproducible GeoAI Workflow for Flash-Flood Susceptibility in Melaka, Malaysia* (APACE2026).
Preliminary, reproducible 30 m workflow. Software: ArcGIS Pro 3.7.2 (Forest-based classification, 500 trees), Python 3 (NumPy, pandas, scikit-learn, geopandas).

## Contents
| Folder | What it holds |
|---|---|
| `data/inventory/` | The flood inventory: `flood_sites.csv` (90 geocoded sites, WGS84 lat/lon, precision Site/Locality/District), `flood_occurrences.csv` (120 occurrence records), `flood_events.csv` (28 dated events, Oct 2024 to Jul 2026) |
| `data/samples/samples.csv` | The 177 modelling records (88 flood, 89 background): coordinates (EPSG:3375, GDM2000 MRSO), five predictor values, label, train/test split |
| `results/` | `holdout_predictions_arcgis.csv` (48 hold-out records, ArcGIS probabilities), supplementary checks (`robustness_block*km.json`, `permutation_importance.csv`) |
| `model/` | The saved ArcGIS model (`.ssm`) behind the paper |
| `scripts/` | ArcGIS Pro scripts (`a*.py`) and Python scripts (`s*.py`) |

## Rebuilding the inputs (all rasters are 30 m, EPSG:3375, one common snap grid)
1. **Elevation, slope**: NASA/USGS SRTM 1 Arc-Second Global v3 void-filled DEM, tile SRTM1N02E102V3, from USGS EarthExplorer (acquired Feb 2000). Project Raster to GDM2000 MRSO, BILINEAR, 30 m (`GDM2000_to_WGS_1984_1`) -> `DEM_Melaka_RSO` -> `Elevation_30m`. Slope: Slope tool on `Elevation_30m`.
2. **TWI**: from `DEM_Filled_30m` = Fill(`Elevation_30m`, no Z limit); Flow Direction (D8) -> Flow Accumulation -> slope -> TWI.
3. **Distance to drainage**: `Stream_Raster_1000` = `Con("Flow_Accumulation_30m" >= 1000, 1)` (about 0.9 km2 of upstream area); then Distance Accumulation (planar, 30 m, mask = Melaka boundary). This is a DEM-derived network, not a surveyed river layer.
4. **Land cover**: Esri/Impact Observatory Sentinel-2 10 m Land Use/Land Cover, 2025 (ArcGIS Living Atlas), Resample NEAREST to 30 m, categorical. Classes kept for modelling: 2, 5, 7, 8, 11.
5. **Boundary**: Melaka local-authority boundary in GDM2000 MRSO.
6. **Points**: 90 flood sites (`data/inventory`) plus 90 background points drawn at random outside 500 m buffers around all flood sites; predictors extracted at all 180; 3 removed for missing raster values (FLD_S020, FLD_S029, BG_065) -> 177 -> 129 train / 48 test.
Original rasters are not redistributed (third-party licences); obtain them from the sources above.

## Reproducing the numbers
**Path A: Python only (no ArcGIS needed; about 5 minutes).** Install `pip install -r requirements.txt`, then from the `scripts/` folder:
```
python s7_verify_from_arcgis_csv.py ../results/holdout_predictions_arcgis.csv
```
Recomputes every hold-out number in the paper (confusion matrix, accuracy, kappa, AUC and its bootstrap interval) from the saved ArcGIS predictions; the last line must read `ALL PAPER NUMBERS REPRODUCED FROM THE ARCGIS TABLE`.
```
set BLOCK_M=5000  && python s5_robustness.py     (Windows; use BLOCK_M=5000 python s5_robustness.py on Linux/macOS)
set BLOCK_M=10000 && python s5_robustness.py
set BLOCK_M=15000 && python s5_robustness.py
```
Writes `results/robustness_block{5,10,15}km.json`. Expected spatial-block AUC of the scikit-learn Random Forest: 0.868 (5 km), 0.866 (10 km), 0.817 (15 km). Both scripts were run from a clean copy of this folder with Python 3.13, NumPy 2.5, pandas 3.0 and scikit-learn 1.9; scikit-learn output may differ slightly across versions.

**Path B: ArcGIS Pro 3.7.2 (needs a licence and the rebuilt rasters).**
1. Rebuild the five rasters as described above and edit the paths at the top of each `a*.py` script and in `scripts/config.py`.
2. `python scripts/s0_audit_geodatabase.py <gdb>` re-derives the audit trail 180 -> 177 -> 129/48.
3. ArcGIS: `a0_forest_train_predict_test.py`, then `a1_test_table_export.py`; compare with `results/holdout_predictions_arcgis.csv`.
4. `a1_arcgis_prediction.py` predicts the surface in 37 row blocks and builds the five classes; `a2_landcover_counts_and_dem_voids.py` gives the land-cover counts and the excluded area.
Edit paths and settings in `scripts/config.py` only.

Expected hold-out values: TP 22, TN 18, FP 3, FN 5; accuracy 83.33%; AUC 0.837 (95% CI 0.695-0.958; RandomState(42), 10,000 stratified resamples). Map: 1,799,525 valid cells = 1,619.573 km2. Excluded inside the boundary: 40.814 km2 (2.46%).
Two ArcGIS re-runs on one machine gave identical hold-out CSVs. Identical results on other machines or versions have not been tested (the Forest tool exposes no random seed).

## Data notes and limits
- Flood records were compiled from news feeds, agency information, and news reports: a flood-location list (104 occurrences, 82 sites) and named news reports (16 occurrences, 8 sites). No formal independent-corroboration rule is documented. 81 of the 88 modelled flood records lie on built-up land.
- Background points mark locations with no documented flood, not proof of none.
- `samples.csv` columns: SampleID (FLD_ = flood, BG_ = background), x, y, elevation, slope, twi, dist_drain (m), landcover (code), flood (1/0), split (train/test).

## Licence
Code: MIT. Inventory and sample tables: CC BY 4.0 (cite the paper). Third-party layers keep their own licences (Esri/Impact Observatory land cover: CC BY 4.0).
