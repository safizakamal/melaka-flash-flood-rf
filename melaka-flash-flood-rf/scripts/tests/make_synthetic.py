"""Creates SYNTHETIC rasters + samples so the pipeline can be tested without the real data.
Numbers from a synthetic run mean nothing scientifically; they only prove the code runs."""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd, rasterio
from rasterio.transform import from_origin
import config as C
rng = np.random.default_rng(1)
H, W = 148, 221
tf = from_origin(100000, 200000, 30, 30)
C.RASTER_DIR.mkdir(parents=True, exist_ok=True)
yy, xx = np.mgrid[0:H, 0:W]
elev = 80 - 0.3 * xx + rng.normal(0, 3, (H, W)); slope = np.abs(rng.normal(3, 2, (H, W)))
twi = 8 - 0.2 * slope + rng.normal(0, 1, (H, W)); dist = np.abs(rng.normal(300, 200, (H, W)))
lc = rng.choice(C.LC_KEEP, (H, W), p=[.3, .2, .3, .1, .1]).astype("float32"); lc[:5, :5] = 0
layers = dict(elevation=elev, slope=slope, twi=twi, dist_drain=dist, landcover=lc)
for k, a in layers.items():
    with rasterio.open(C.RASTERS[k], "w", driver="GTiff", height=H, width=W, count=1,
                       dtype="float32", transform=tf, nodata=0 if k == "landcover" else -9999) as d:
        d.write(a.astype("float32"), 1)
def pts(n, flood):
    r, c = rng.integers(0, H, n), rng.integers(0, W, n)
    if flood:  # floods favour low elevation, near drains, built-up
        for i in range(n):
            for _ in range(50):
                if elev[r[i], c[i]] < 70 and dist[r[i], c[i]] < 300: break
                r[i], c[i] = rng.integers(0, H), rng.integers(0, W)
    d = {k: a[r, c] for k, a in layers.items()}
    d.update(x=100000 + c * 30 + 15, y=200000 - r * 30 - 15, flood=int(flood))
    return pd.DataFrame(d)
df = pd.concat([pts(100, True), pts(100, False)], ignore_index=True)
df = df[df.landcover.isin(C.LC_KEEP)]
df = pd.concat([df[df.flood == 1].head(90), df[df.flood == 0].head(87)], ignore_index=True)
# force exact 129/48 with 27 flood + 21 background in test
f, b = df[df.flood == 1].index.to_numpy().copy(), df[df.flood == 0].index.to_numpy().copy()
rng.shuffle(f); rng.shuffle(b)
df["split"] = "train"; df.loc[np.r_[f[:27], b[:21]], "split"] = "test"
df.to_csv(C.SAMPLES_CSV, index=False); print(len(df), df.split.value_counts().to_dict())
