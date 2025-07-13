#!/usr/bin/env python3
"""
Umbra Băncii – Ingest News Sentiment (rulare orară)
---------------------------------------------------
• Sursă: NewsAPI.org  (plan free 100 requests/zi)
• Căutăm "EUR OR USD", limba EN, max 20 articole → păstrăm primele 10.
• Mini‑sentiment: +1 dacă titlul conţine cuv. bullish, –1 bearish, 0 neutră.
• Output YAML:  NEWS_<timestamp>.yaml  în folderul output/.
"""

import os
import sys
import requests
import datetime as dt
import hashlib
import yaml

API_KEY = os.environ["NEWS_API_KEY"]
ENDPOINT = "https://newsapi.org/v2/top-headlines"
HEADERS = {"User-Agent": "UmbraBancii/1.0"}

params = {
    "q": "EUR OR USD",
    "language": "en",
    "pageSize": 20,
    "apiKey": API_KEY,
}

# ----------------------------------------------------------------------
# 1) Fetch News
# ----------------------------------------------------------------------
try:
    r = requests.get(ENDPOINT, params=params, headers=HEADERS, timeout=15)
    if r.status_code == 429:
        print("[warn] NewsAPI quota reached (429) – skipping this run", file=sys.stderr)
        articles = []
    else:
        r.raise_for_status()
        articles = r.json().get("articles", [])
except requests.RequestException as e:
    print(f"[warn] NewsAPI error: {e}", file=sys.stderr)
    articles = []

# ----------------------------------------------------------------------
# 2) Sentiment scoring
# ----------------------------------------------------------------------
bullish_kw = ("rises", "higher", "beats", "surges", "gains")
bearish_kw = ("falls", "lower", "misses", "drops", "losses")

def title_score(title: str) -> int:
    t = title.lower()
    if any(k in t for k in bullish_kw):
        return 1
    if any(k in t for k in bearish_kw):
        return -1
    return 0

headlines = [
    {
        "title": a["title"],
        "publishedAt": a["publishedAt"],
        "score": title_score(a["title"]),
    }
    for a in articles[:10]
]

# ----------------------------------------------------------------------
# 3) Build payload
# ----------------------------------------------------------------------
now_utc = dt.datetime.utcnow().replace(microsecond=0)
payload = {
    "timestamp_utc": now_utc.isoformat() + "Z",
    "source": "NewsAPI",
    "headline_count": len(headlines),
    "average_score": round(
        sum(h["score"] for h in headlines) / len(headlines), 3
    ) if headlines else 0,
    "headlines": headlines,
}

# ----------------------------------------------------------------------
# 4) Write YAML & print hash
# ----------------------------------------------------------------------
raw_yaml = yaml.safe_dump(payload, sort_keys=False, width=120, allow_unicode=True)
os.makedirs("output", exist_ok=True)
fname = f"output/NEWS_{now_utc.strftime('%Y-%m-%dT%H-%M-%SZ')}.yaml"

with open(fname, "w", encoding="utf-8") as f:
    f.write(raw_yaml)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
