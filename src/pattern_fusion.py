#!/usr/bin/env python3
"""
Umbra Băncii – Pattern Fusion v1.5 (toate 28 perechi, rulare orară)
------------------------------------------------------------------
Flux:
1.  Citește lista perechilor din configs/pairs.yaml
2.  Pentru fiecare pair:
      • găsește cel mai nou ingest <PAIR>_*.yaml
      • calculează momentum: close vs EMA‑10 (H1) din Yahoo
3.  Calendar & News:
      • calendar risk (High/Medium în <4h)
      • news sentiment (average_score)
4.  Integrează scor = momentum – event_risk + news_score
5.  Scrie câte un  PATTERN_FUSION_<PAIR>_<timestamp>.yaml  în output/
"""

import glob
import os
import datetime as dt
import hashlib
import yaml
import pandas as pd
import yfinance as yf
from pathlib import Path

# ------------------------------------------------------------------
# 0) Config – pairs list
# ------------------------------------------------------------------
try:
    PAIRS = yaml.safe_load(Path("configs/pairs.yaml").read_text())["pairs"]
except Exception as e:
    raise RuntimeError(f"Cannot load pairs.yaml: {e}")

UTCNOW = dt.datetime.utcnow().replace(microsecond=0)
TIMESTAMP_ISO = UTCNOW.isoformat() + "Z"
SAFE_TS = UTCNOW.strftime("%Y-%m-%dT%H-%M-%SZ")

# ------------------------------------------------------------------
# 1) Load latest Calendar & News
# ------------------------------------------------------------------
def latest(glob_pat: str):
    files = glob.glob(glob_pat)
    return max(files, key=os.path.getmtime) if files else None

CAL_FILE = latest("output/CALENDAR_*.yaml")
NEWS_FILE = latest("output/NEWS_*.yaml")

cal = yaml.safe_load(Path(CAL_FILE).read_text()) if CAL_FILE else {}
news = yaml.safe_load(Path(NEWS_FILE).read_text()) if NEWS_FILE else {}

# Calendar event risk (<4h)
event_risk = 0
for ev in cal.get("events", []):
    ts = pd.to_datetime(ev["timestamp_utc"])
    delta = (ts - pd.Timestamp.utcnow()).total_seconds()
    if 0 < delta < 4 * 3600:
        event_risk = 1
        break

# News score
news_score = news.get("average_score", 0)

# ------------------------------------------------------------------
# 2) Loop over pairs
# ------------------------------------------------------------------
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

for pair in PAIRS:
    # a) găsește ingest FX
    fx_files = glob.glob(f"output/{pair}_*.yaml")
    if not fx_files:
        print(f"[warn] No ingest file for {pair} – skip.")
        continue
    fx_file = max(fx_files, key=os.path.getmtime)
    fx_data = yaml.safe_load(Path(fx_file).read_text())
    rows = fx_data["rows"]
    last_close = float(rows[-1]["close"])

    # b) momentum EMA‑10 (H1)
    symbol = f"{pair}=X"
    try:
        hist = yf.Ticker(symbol).history(period="15d", interval="1h").close
        ema10 = hist.ewm(span=10).mean().iloc[-1]
    except Exception as e:
        print(f"[warn] Yahoo fail {symbol}: {e} – skip pair.")
        continue
    ema_cond = 1 if last_close > ema10 else -1

    # c) Fusion score & verdict
    score = ema_cond - event_risk + news_score
    if score >= 1:
        verdict = "BUY"
    elif score <= -1:
        verdict = "SELL"
    else:
        verdict = "STANDBY"

    fusion = {
        "timestamp_utc": TIMESTAMP_ISO,
        "pair": pair,
        "fx_close": round(last_close, 5),
        "ema10_h1": round(float(ema10), 5),
        "fx_momentum": ema_cond,
        "event_risk": event_risk,
        "news_score": news_score,
        "fusion_score": round(float(score), 3),
        "verdict": verdict,
        "source_files": [
            os.path.basename(fx_file),
            os.path.basename(CAL_FILE) if CAL_FILE else "",
            os.path.basename(NEWS_FILE) if NEWS_FILE else "",
        ],
    }

    raw_yaml = yaml.safe_dump(fusion, sort_keys=False, allow_unicode=True)
    out_name = OUTPUT_DIR / f"PATTERN_FUSION_{pair}_{SAFE_TS}.yaml"
    out_name.write_text(raw_yaml, encoding="utf-8")

    print("Generated:", out_name)
    print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
