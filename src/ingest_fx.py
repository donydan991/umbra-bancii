#!/usr/bin/env python3
"""
Umbra Băncii – Ingest FX prices (M15)
------------------------------------
1. Încearcă TwelveData   – 8 calls/min gratuite.
2. La eroare (429, 400 etc.) sau lipsă 'values' → fallback Yahoo.
3. Salvează artefact YAML:  <PAIR>_YYYYMMDD_HHMM.yaml
   Conține:
       - timestamp_utc   (ISO 8601)
       - pair            (ex. EURUSD)
       - rows            (listă OHLCV)
       - sha256          (hash al datelor pentru Blockchain Logic)
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from typing import List, Dict

import requests
import yaml
import yfinance as yf

TD_API = os.getenv("TWELVE_API_KEY")
TD_URL = "https://api.twelvedata.com/time_series"


# ----------------------------------------------------------------------
# Helper: TwelveData
# ----------------------------------------------------------------------
def fetch_twelve(pair: str) -> List[Dict]:
    """Returnează listă de dict‑uri OHLCV (M15, ultimele 24 h)."""
    params = {
        "symbol": pair,
        "interval": "15min",
        "outputsize": 96,  # ~24 h
        "apikey": TD_API,
        "format": "JSON",
    }
    r = requests.get(TD_URL, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if "values" in data:
            return data["values"]
    raise RuntimeError(f"TwelveData fail ({r.status_code})")


# ----------------------------------------------------------------------
# Helper: Yahoo Finance fallback
# ----------------------------------------------------------------------
def fetch_yahoo(pair: str) -> List[Dict]:
    """
    Yahoo Finance folosește simbolul <PAIR>=X, ex. EURUSD=X.
    yfinance returnează un DataFrame cu MultiIndex pe coloane -> îl aplatizăm.
    """
    ticker = f"{pair}=X"
    df = yf.download(ticker, period="1d", interval="15m", progress=False)

    if df.empty:
        raise RuntimeError("Yahoo feed empty")

    # 1️⃣  Aplatizăm MultiIndex‑ul   ('Open', '') -> 'open'
    df.columns = [
        c[0].lower() if isinstance(c, tuple) else str(c).lower()
        for c in df.columns
    ]

    # 2️⃣  Mutăm indexul în coloană ISO 8601
    df = df.reset_index().rename(columns={"Datetime": "datetime"})
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 3️⃣  Convertim la tipuri JSON‑safe (float & str)
    df = df.apply(
        lambda col: col.astype(float) if col.name != "datetime" else col
    )

    return df.to_dict(orient="records")


# ----------------------------------------------------------------------
# Helper: salvare YAML
# ----------------------------------------------------------------------
def save_yaml(pair: str, rows: List[Dict]) -> str:
    now = dt.datetime.utcnow()
    fname = f"{pair}_{now:%Y%m%d_%H%M}.yaml"

    payload = {
        "timestamp_utc": now.isoformat(timespec="seconds") + "Z",
        "pair": pair,
        "rows": rows,
        "sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
    }

    with open(fname, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True)

    print(f"[+] wrote {fname}")
    return fname


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main(pair: str) -> None:
    try:
        rows = fetch_twelve(pair)
    except Exception as e:
        print(f"[warn] TwelveData fallback → Yahoo  ({e})", file=sys.stderr)
        rows = fetch_yahoo(pair)

    save_yaml(pair, rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest FX prices M15")
    parser.add_argument("--pair", required=True, help="ex. EURUSD, GBPJPY …")
    args = parser.parse_args()

    main(args.pair.upper())
