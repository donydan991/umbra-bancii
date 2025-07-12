import os, requests, datetime, yaml, hashlib, sys

API_KEY = os.environ["TWELVE_API_KEY"]
PAIR     = "EUR/USD"                     # păstrăm slash‑ul
ENDPOINT = "https://api.twelvedata.com/time_series"

params = {
    "symbol": PAIR,                      # fără .replace("/", "")
    "interval": "1min",
    "outputsize": 1,
    "apikey": API_KEY,
    "format": "JSON"
}

resp = requests.get(ENDPOINT, params=params, timeout=15)
resp.raise_for_status()
data_json = resp.json()

# --- verificăm dacă a venit cheie 'values' -----------------
if "values" not in data_json:
    print("TwelveData error:", data_json, file=sys.stderr)
    raise SystemExit(1)

payload = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "instrument": PAIR,
    "last_close": float(data_json["values"][0]["close"]),
    "source": "TwelveData"
}

raw_yaml = yaml.dump(payload, sort_keys=False)
safe_ts = payload["timestamp"].replace(":", "-")
fname   = f"output/{PAIR.replace('/','')}_{safe_ts}.yaml"

os.makedirs("output", exist_ok=True)
with open(fname, "w") as f:
    f.write(raw_yaml)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
