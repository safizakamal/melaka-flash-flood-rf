"""Run the whole workflow.   python run_all.py            (steps 2-6; step 1 needs ArcGIS Pro)
                            python run_all.py --with-arcpy  (also runs step 1 with Pro's python)"""
import subprocess, sys
steps = ["s2_split_check.py", "s3_train_evaluate.py", "s4_predict_blocks.py",
         "s5_robustness.py", "s6_verify.py"]
if "--with-arcpy" in sys.argv:
    steps.insert(0, "s1_prepare_arcpy.py")
for s in steps:
    print(f"\n=== {s} ===")
    subprocess.run([sys.executable, s], check=True)
