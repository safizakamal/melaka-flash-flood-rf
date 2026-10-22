"""STEP 2: confirm (or create) the train/test split and log the counts."""
import pandas as pd
from sklearn.model_selection import train_test_split
import config as C
from audit import log, require

df = pd.read_csv(C.SAMPLES_CSV)
if C.SPLIT not in df.columns or df[C.SPLIT].isna().any():
    print("No split column: creating a seeded random split (48 test records).")
    tr, te = train_test_split(df.index, test_size=C.EXPECTED["n_test"], random_state=C.SEED)
    df[C.SPLIT] = "train"
    df.loc[te, C.SPLIT] = "test"
    df.to_csv(C.SAMPLES_CSV, index=False)

tr, te = df[df[C.SPLIT] == "train"], df[df[C.SPLIT] == "test"]
log("2_split", files=[C.SAMPLES_CSV], n_train=len(tr), n_test=len(te),
    n_test_flood=int(te[C.LABEL].sum()), n_test_background=int((te[C.LABEL] == 0).sum()))
E = C.EXPECTED
require(len(tr) == E["n_train"] and len(te) == E["n_test"], "train/test sizes differ from the paper")
require(int(te[C.LABEL].sum()) == E["n_test_flood"], "test flood count differs from the paper")
