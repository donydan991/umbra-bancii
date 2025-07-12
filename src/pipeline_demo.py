import yaml, datetime, os, hashlib
os.makedirs("output", exist_ok=True)

data = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "instrument": "EURUSD",
    "demo_score": 1.23
}

raw_yaml = yaml.dump(data, sort_keys=False)

safe_ts = data['timestamp'].replace(":", "-")       # ← sanitisează
fname = f"output/EURUSD_{safe_ts}.yaml"
with open(fname, "w") as f:
    f.write(raw_yaml)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
