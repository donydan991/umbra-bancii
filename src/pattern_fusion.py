import glob, yaml, os, datetime, hashlib
import pandas as pd
import yfinance as yf

# ── 1. Citeşte ultimele fişiere din folderul output/ ────────────────────────────
files = sorted(glob.glob("output/*.yaml"), key=os.path.getmtime)[-5:]  # safety
fx, cal, news = {}, {}, {}

for f in files:
    with open(f) as fh:
        data = yaml.safe_load(fh)
    if data.get("instrument") == "EUR/USD":
        fx = data
    elif f"CALENDAR" in f:
        cal = data
    elif f"NEWS" in f:
        news = data

# ── 2. Calculează momentum simplu pe preţ (close vs EMA‑10) ────────────────────
close_price = fx.get("last_close")
ema_cond    = 0
if close_price:
    hist = yf.Ticker("EURUSD=X").history(period="15d", interval="1h").close
    ema  = hist.ewm(span=10).mean().iloc[-1]
    ema_cond = 1 if close_price > ema else -1

# ── 3. Calendar risk: eveniment High în < 4 h? ──────────────────────────────────
event_risk = 0
for ev in cal.get("events", []):
    ts = pd.to_datetime(ev["timestamp"])
    if ts > pd.Timestamp.utcnow() and (ts - pd.Timestamp.utcnow()).total_seconds() < 14400:
        event_risk = 1
        break

# ── 4. News sentiment (deja în YAML) ────────────────────────────────────────────
news_score = news.get("average_score", 0)

# ── 5. Scor integrat & verdict ─────────────────────────────────────────────────
score = ema_cond - event_risk + news_score   # simplu: +1/‑1 momentum, ‑1 risc, ±sentiment
if score >= 1:
    verdict = "BUY"
elif score <= -1:
    verdict = "SELL"
else:
    verdict = "STANDBY"

fusion = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "fx_momentum": ema_cond,
    "event_risk": event_risk,
    "news_score": news_score,
    "fusion_score": score,
    "verdict": verdict,
    "source_files": [os.path.basename(f) for f in files]
}

raw = yaml.dump(fusion, sort_keys=False)
safe_ts = fusion["timestamp"].replace(":", "-")
fname = f"output/PATTERN_FUSION_{safe_ts}.yaml"
with open(fname, "w") as f:
    f.write(raw)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw.encode()).hexdigest())
