"""ArcGIS Pro: train the Random Forest on the 129 training points and score the 48 hold-out points.
Reconstructed from the tool history stored in RF_Test_Probability_V3.csv.xml (run of 2026-10-02):

Forest PREDICT_FEATURES RF_Training_Points_V2 FloodStat CATEGORICAL # #
 "Elevation_30m #;Slope_Degree_30m #;TWI_30m #;Distance_Drainage_30m #;LandCover_2025_30m_Aligned true"
 RF_Testing_Points_V2 ...\\RF_Test_Probability_V3 # # #
 "Elevation_30m Elevation_30m;Slope_Degree_30m Slope_Degree_30m;TWI_30m TWI_30m;Distance_Drainage_30m Distance_Drainage_30m;LandCover_2025_30m_Aligned LandCover_2025_30m_Aligned"
 ...\\RF_Training_Probability_V3 ...\\RF_Importance_Probability_V3 # 500 1 # 100 # 0 # # FALSE 1 FALSE
 ...\\RF_FlashFlood_Probability_V3.ssm FOREST-BASED # # # # FALSE # # # # # ALL_PROBABILITIES

Meaning of the values (mapped to the tool's parameter order; please compare with Geoprocessing > History >
right-click the run > Copy Python Command, which is the authoritative version):
  trees 500 | minimum leaf size 1 | maximum depth default | sample size 100% | random variables default
  percentage for training 0 (ArcGIS' own validation split OFF: all 129 points fit the model)
  compensate sparse categories OFF | validation runs 1 | uncertainty OFF | model type FOREST-BASED
  output: ALL_PROBABILITIES
NOTE: the call exposes no random seed, so retraining may give slightly different numbers.
      The saved .ssm file is therefore the exact model behind the paper; archive it with the paper."""
import os, arcpy
GDB = r"C:\MELAKA_FLASHFLOOD_APACE\Melaka_FlashFlood.gdb"
OUT_MODEL = r"C:\MELAKA_FLASHFLOOD_APACE\RF_FlashFlood_Probability_V3_REPRO.ssm"   # does not overwrite the original
p = lambda n: os.path.join(GDB, n)
TRAIN, TEST = p("RF_Training_Points_V2"), p("RF_Testing_Points_V2")

n_tr, n_te = int(arcpy.management.GetCount(TRAIN)[0]), int(arcpy.management.GetCount(TEST)[0])
print("training points:", n_tr, " testing points:", n_te)
if (n_tr, n_te) != (129, 48):
    raise SystemExit("Expected 129 training and 48 testing points; do not continue.")

names = ["Elevation_30m", "Slope_Degree_30m", "TWI_30m", "Distance_Drainage_30m", "LandCover_2025_30m_Aligned"]
arcpy.stats.Forest(
    prediction_type="PREDICT_FEATURES",
    in_features=TRAIN,
    variable_predict="FloodStat",
    treat_variable_as_categorical="CATEGORICAL",
    explanatory_rasters=[[p(n), "true" if n.startswith("LandCover") else "false"] for n in names],
    features_to_predict=TEST,
    output_features=p("RF_Test_Probability_V3_REPRO"),
    explanatory_rasters_matching=[[n, n] for n in names],
    output_trained_features=p("RF_Training_Probability_V3_REPRO"),
    output_importance_table=p("RF_Importance_Probability_V3_REPRO"),
    number_of_trees=500,
    minimum_leaf_size=1,
    sample_size=100,
    percentage_for_training=0,
    number_validation_runs=1,
    output_trained_model=OUT_MODEL,
    # parameter names below are from the tool's newer signature; verify against Copy Python Command
    model_type="FOREST-BASED",
    include_probabilities="ALL_PROBABILITIES",
)
print(arcpy.GetMessages())
