#!/usr/bin/env python3
"""
Ingest FX prices M15  ➜  YAML artefact Umbra Băncii
--------------------------------------------------
1. încearcă TwelveData  – gratuit 8 calls/min
2. la eroare 429 sau network‑fail ➜ fallback Yahoo
3. salvează YAML în  artefacte GitHub Actions
"""

import argparse, os, sys, datetime as dt
import hashlib, json, requests, yfinance as yf
import yaml

TD_API = os.getenv("TWELVE_API_KEY")
TD_URL  = "https://api.twelvedata.com/time_series"

def fetch_twelve(pair):
    params = {
        "symbol": pair,
        "interval": "15min",
        "outputsize": 96,          # ultimele 24 h
        "apikey": TD_API,
        "format": "JSON"
    }
    r = requests.get(TD_URL, params=params, timeout=10)
    if r.status_code == 200 and "values" in r.json():
        return r.json()["values"]
    raise RuntimeError(f"TwelveData fail {r.status_code}")

def fetch_yahoo(pair):
    # Yahoo foloseşte format EURUSD=X
    ticker = f"{pair}=X"
    data = yf.download(ticker, period="1d", interval="15m", progress=False)
    if data.empty:
        raise RuntimeError("Yahoo feed empty")
    return (
        data.reset_index()
            .rename(columns={"Datetime": "datetime"})
            .to_dict(orient="records")
    )

def save_yaml(pair, rows):
    now = dt.datetime.utcnow()
    name = f"{pair}_{now:%Y%m%d_%H%M}.yaml"
    payload = {
        "timestamp_utc": now.isoformat(timespec="seconds") + "Z",
        "pair": pair,
        "rows": rows
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps(rows, sort_keys=True).encode()
    ).hexdigest()
    with open(name, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True)
    print(f">>> wrote {name}")
    return name

def main(pair):
    try:
        rows = fetch_twelve(pair)
    except Exception as e:
        print(f"[warn] TwelveData fallback → Yahoo: {e}")
        rows = fetch_yahoo(pair)
    save_yaml(pair, rows)

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--pair", required=True)
    main(argp.parse_args().pair.upper())
