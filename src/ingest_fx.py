import os, requests, datetime, yaml, hashlib

# ----- Config -----
API_KEY = os.environ["TWELVE_API_KEY"]      # este injectat din Secrets
PAIR = "EUR/USD"
ENDPOINT = "https://api.twelvedata.com/time_series"

# ----- API call -----
params = {
    "symbol": PAIR.replace("/", ""),
    "interval": "1min",
    "outputsize": 1,
    "apikey": API_KEY,
    "format": "JSON"
}
r = requests.get(ENDPOINT, params=params, timeout=15)
r.raise_for_status()
data_json = r.json()

# ----- Build payload -----
payload = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "instrument": PAIR,
    "last_close": float(data_json["values"][0]["close"]),
    "source": "TwelveData"
}
raw_yaml = yaml.dump(payload, sort_keys=False)

# ----- Write YAML to output/ -----
safe_ts = payload["timestamp"].replace(":", "-")
fname = f"output/{PAIR.replace('/', '')}_{safe_ts}.yaml"
os.makedirs("output", exist_ok=True)
with open(fname, "w") as f:
    f.write(raw_yaml)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
