import json
from pathlib import Path

data = Path("data")
for p in data.rglob("*.json"):
    try:
        txt = p.read_text(encoding="utf-8")
        if "Farewell" in txt or "GTA 6" in txt or "clip" in p.name:
            print(p)
    except Exception:
        pass
