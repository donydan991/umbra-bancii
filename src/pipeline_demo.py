- Conținut:
```python name=src/pipeline_demo.py
import yaml, os, pandas as pd, datetime, hashlib, json
os.makedirs("output", exist_ok=True)

data = {
  "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
  "instrument": "EURUSD",
  "demo_score": 1.23
}
raw = yaml.dump(data)
fn = f"output/EURUSD_{data['timestamp']}.yaml"
with open(fn, "w") as f:
  f.write(raw)

print("Generated", fn)
print("SHA256:", hashlib.sha256(raw.encode()).hexdigest())
