"""ArcGIS Pro: build RF_Test_Probability table exactly as in the tool history
(AddField ProbFlood -> CalculateField !PROB_02! -> AddField ResultCode -> JoinField FloodStat/SampleID
 -> CalculateField ResultCode -> ExportTable), then write the CSV used for the paper's metrics."""
import os, arcpy
GDB = r"C:\MELAKA_FLASHFLOOD_APACE\Melaka_FlashFlood.gdb"
TABLE = os.path.join(GDB, "RF_Test_Probability_V3_REPRO")        # output of a0
TEST_PTS = os.path.join(GDB, "RF_Testing_Points_V2")
CSV_DIR, CSV_NAME = r"C:\MELAKA_FLASHFLOOD_APACE", "RF_Test_Probability_V3_REPRO.csv"

arcpy.management.AddField(TABLE, "ProbFlood", "DOUBLE")
arcpy.management.CalculateField(TABLE, "ProbFlood", "!PROB_02!", "PYTHON3")   # PROB_02 = probability of class 1 (flood)
arcpy.management.AddField(TABLE, "ResultCode", "TEXT", field_length=50)
arcpy.management.JoinField(TABLE, "SOURCE_ID", TEST_PTS, "OBJECTID", ["FloodStat", "SampleID"])
arcpy.management.CalculateField(TABLE, "ResultCode", "outcome(!FloodStat!,!PREDICTED!)", "PYTHON3", """def outcome(observed, predicted):
    if observed == 0 and predicted == 0: return "TN"
    elif observed == 0 and predicted == 1: return "FP"
    elif observed == 1 and predicted == 0: return "FN"
    elif observed == 1 and predicted == 1: return "TP"
    else: return "Check\"""")
arcpy.conversion.ExportTable(TABLE, os.path.join(CSV_DIR, CSV_NAME))
print("exported", CSV_NAME)
