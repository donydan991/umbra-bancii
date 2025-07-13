#!/usr/bin/env python3
"""
Umbra Băncii – Pattern Fusion v1.5  (toate 28 perechi, rulare orară)
-------------------------------------------------------------------
Caută fișiere YAML în output/** (recursiv), deci funcționează indiferent
dacă download‑artifact le pune în subfoldere sau la rădăcină.

Scor =  fx_momentum (EMA10‑H1)  -  event_risk  +  news_score
Verdict: BUY / SELL / STANDBY
Pentru fiecare pair salvează:  PATTERN_FUSION_<PAIR>_<timestamp>.yaml
"""

import glob, os, datetime as dt, hashlib, yaml
from pathlib import Path

import pandas as pd
import yfinance as yf

# ── 0. Config – pairs list ─────────────────────────────────────────────────────
PAIRS = yaml.safe_load(Path("configs/pairs.yaml").read_text())["pairs"]

UTCNOW = dt.datetime.utcnow().replace(microsecond=0)
TIMESTAMP_ISO = UTCNOW.isoformat() + "Z"
SAFE_TS = UTCNOW.strftime("%Y-%m-%dT%H-%M-%SZ")

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 1. Load latest Calendar & News (recursive) ─────────────────────────────────
def latest(pattern: str):
    files = glob.glob(pattern, recursive=True)
    return max(files, key=os.path.getmtime) if files else None

CAL_FILE  = latest("output/**/CALENDAR_*.yaml")
NEWS_FILE = latest("output/**/NEWS_*.yaml")

cal  = yaml.safe_load(Path(CAL_FILE).read_text())  if CAL_FILE  else {}
news = yaml.safe_load(Path(NEWS_FILE).read_text()) if NEWS_FILE else {}

# Calendar risk: High/Medium în <4 h
event_risk = 0
for ev in cal.get("events", []):
    ts = pd.to_datetime(ev["timestamp_utc"])
    delta = (ts - pd.Timestamp.utcnow()).total_seconds()
    if 0 < delta < 4 * 3600:
        event_risk = 1
        break

# News sentiment
news_score = news.get("average_score", 0)

# ── 2. Parcurge perechile FX ───────────────────────────────────────────────────
for pair in PAIRS:
    # a) găseşte ingest FX (recursive)
    fx_files = glob.glob(f"output/**/{pair}_*.yaml", recursive=True)
    if not fx_files:
        print(f"[warn] No ingest file for {pair} – skip.")
        continue
    fx_file = max(fx_files, key=os.path.getmtime)
    fx_data = yaml.safe_load(Path(fx_file).read_text())
    rows = fx_data["rows"]
    last_close = float(rows[-1]["close"])

    # b) Momentum EMA‑10 pe 1h
    symbol = f"{pair}=X"
    try:
        hist = yf.Ticker(symbol).history(period="15d", interval="1h").close
        ema10 = hist.ewm(span=10).mean().iloc[-1]
    except Exception as e:
        print(f"[warn] Yahoo fail {symbol}: {e} – skip pair.")
        continue
    ema_cond = 1 if last_close > ema10 else -1

    # c) Scor integrat
    score = ema_cond - event_risk + news_score
    verdict = "BUY" if score >= 1 else "SELL" if score <= -1 else "STANDBY"

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
            os.path.basename(CAL_FILE)  if CAL_FILE  else "",
            os.path.basename(NEWS_FILE) if NEWS_FILE else "",
        ],
    }

    raw = yaml.safe_dump(fusion, sort_keys=False, allow_unicode=True)
    out_path = OUTPUT_DIR / f"PATTERN_FUSION_{pair}_{SAFE_TS}.yaml"
    out_path.write_text(raw, encoding="utf-8")

    print("Generated:", out_path)
    print("SHA256:", hashlib.sha256(raw.encode()).hexdigest())
