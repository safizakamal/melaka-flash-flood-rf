"""Audit trail: every stage appends its counts and file hashes to outputs/audit.json."""
import hashlib, json, time
from config import OUT

AUDIT = OUT / "audit.json"

def sha256(path, n=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(n):
            h.update(chunk)
    return h.hexdigest()[:16]

def log(stage, files=(), **counts):
    data = json.loads(AUDIT.read_text()) if AUDIT.exists() else {}
    data[stage] = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), **counts,
                   "files": {str(p.name): sha256(p) for p in files}}
    AUDIT.write_text(json.dumps(data, indent=2))
    print(f"[audit] {stage}: {counts}")

def require(cond, msg):
    if not cond:
        raise SystemExit(f"AUDIT FAILED: {msg}")
