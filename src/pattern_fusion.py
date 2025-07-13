#!/usr/bin/env python3
"""
Umbra Băncii – Pattern Fusion v1.5  (toate 28 perechi, rulare orară, fără Yahoo)
--------------------------------------------------------------------------------
Momentum se calculează ca:  Close(ultim)  vs  EMA‑10  pe seria M15 din ingest.
EMA‑10 pe H1 ≈ EMA‑40 pe M15  (α identic).  Folosim ultimele 48 valori M15.
Scor = momentum – event_risk + news_score
Salvăm PATTERN_FUSION_<PAIR>_<timestamp>.yaml  pentru fiecare pair.
"""

import glob, os, datetime as dt, hashlib, yaml
from pathlib import Path

import pandas as pd

# ------------------------------------------------------------------
# 0) Config – pairs list
# ------------------------------------------------------------------
PAIRS = yaml.safe_load(Path("configs/pairs.yaml").read_text())["pairs"]

UTCNOW   = dt.datetime.utcnow().replace(microsecond=0)
TS_ISO   = UTCNOW.isoformat() + "Z"
SAFE_TS  = UTCNOW.strftime("%Y-%m-%dT%H-%M-%SZ")
OUT_DIR  = Path("output"); OUT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------------
# 1) Load latest Calendar & News (recursive)
# ------------------------------------------------------------------
def latest(pattern: str):
    files = glob.glob(pattern, recursive=True)
    return max(files, key=os.path.getmtime) if files else None

CAL_FILE  = latest("output/**/CALENDAR_*.yaml")
NEWS_FILE = latest("output/**/NEWS_*.yaml")

cal  = yaml.safe_load(Path(CAL_FILE).read_text())  if CAL_FILE  else {}
news = yaml.safe_load(Path(NEWS_FILE).read_text()) if NEWS_FILE else {}

# Calendar risk (<4 h)
event_risk = 0
for ev in cal.get("events", []):
    ts = pd.to_datetime(ev["timestamp_utc"])
    if 0 < (ts - pd.Timestamp.utcnow()).total_seconds() < 4 * 3600:
        event_risk = 1
        break

news_score = news.get("average_score", 0)

# ------------------------------------------------------------------
# 2) Loop peste perechi
# ------------------------------------------------------------------
for pair in PAIRS:
    # a) ingest FX YAML
    fx_files = glob.glob(f"output/**/{pair}_*.yaml", recursive=True)
    if not fx_files:
        print(f"[warn] Missing ingest for {pair}")
        continue
    fx_path = max(fx_files, key=os.path.getmtime)
    fx = yaml.safe_load(Path(fx_path).read_text())
    rows = fx["rows"]

    # b) DataFrame Close
    df = pd.DataFrame(rows)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    closes = df["close"].tail(48)          # ultimile 12 h = 48×M15
    if closes.isna().all():
        print(f"[warn] No close data for {pair}")
        continue

    ema40 = closes.ewm(span=40, adjust=False).mean().iloc[-1]
    last_close = closes.iloc[-1]
    momentum = 1 if last_close > ema40 else -1

    # c) Scor & verdict
    score = momentum - event_risk + news_score
    verdict = "BUY" if score >= 1 else "SELL" if score <= -1 else "STANDBY"

    fusion = {
        "timestamp_utc": TS_ISO,
        "pair": pair,
        "fx_close": round(float(last_close), 5),
        "ema40_m15": round(float(ema40), 5),
        "fx_momentum": momentum,
        "event_risk": event_risk,
        "news_score": news_score,
        "fusion_score": round(float(score), 3),
        "verdict": verdict,
        "source_files": [
            os.path.basename(fx_path),
            os.path.basename(CAL_FILE)  if CAL_FILE  else "",
            os.path.basename(NEWS_FILE) if NEWS_FILE else "",
        ],
    }

    raw = yaml.safe_dump(fusion, sort_keys=False, allow_unicode=True)
    out = OUT_DIR / f"PATTERN_FUSION_{pair}_{SAFE_TS}.yaml"
    out.write_text(raw, encoding="utf-8")

    print("Generated:", out)
    print("SHA256:", hashlib.sha256(raw.encode()).hexdigest())
