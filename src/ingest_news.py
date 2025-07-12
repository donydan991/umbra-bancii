import os, requests, datetime, yaml, hashlib, textwrap

API_KEY = os.environ["NEWS_API_KEY"]
ENDPOINT = "https://newsapi.org/v2/top-headlines"

params = {
    "q": "EUR OR USD",         # cuvinte‑cheie; poți extinde
    "language": "en",
    "pageSize": 20,
    "apiKey": API_KEY
}

r = requests.get(ENDPOINT, params=params, timeout=15)
r.raise_for_status()
data = r.json()

# mini‑sentiment: +1 dacă titlul conține cuv. bullish, –1 bearish
bullish_kw = ("rises", "higher", "beats")
bearish_kw = ("falls", "lower", "misses")

def title_score(title):
    t = title.lower()
    if any(k in t for k in bullish_kw):
        return 1
    if any(k in t for k in bearish_kw):
        return -1
    return 0

headlines = [
    {
        "title": h["title"],
        "publishedAt": h["publishedAt"],
        "score": title_score(h["title"])
    }
    for h in data.get("articles", [])[:10]
]

payload = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "source": "NewsAPI",
    "headline_count": len(headlines),
    "average_score": sum(h["score"] for h in headlines)/len(headlines) if headlines else 0,
    "headlines": headlines
}

raw_yaml = yaml.dump(payload, sort_keys=False, width=120)
safe_ts = payload["timestamp"].replace(":", "-")
fname = f"output/NEWS_{safe_ts}.yaml"

os.makedirs("output", exist_ok=True)
with open(fname, "w") as f:
    f.write(raw_yaml)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
