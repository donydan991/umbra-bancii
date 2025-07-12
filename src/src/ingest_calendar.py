import os, requests, datetime, yaml, hashlib, xml.etree.ElementTree as ET

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

resp = requests.get(URL, timeout=15)
resp.raise_for_status()
root = ET.fromstring(resp.content)

events = []
for item in root.findall(".//event"):
    impact = item.findtext("impact")
    if impact not in ("High", "Medium"):   # filtrăm doar Medium/High
        continue
    ts = item.findtext("date") + " " + item.findtext("time")
    events.append({
        "title": item.findtext("title"),
        "ccy": item.findtext("country"),
        "impact": impact,
        "timestamp": ts
    })
    if len(events) >= 5:        # luăm doar primele 5 evenimente viitoare
        break

payload = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "source": "ForexFactory RSS",
    "events_count": len(events),
    "events": events
}

raw_yaml = yaml.dump(payload, sort_keys=False)
safe_ts = payload["timestamp"].replace(":", "-")
fname = f"output/CALENDAR_{safe_ts}.yaml"
os.makedirs("output", exist_ok=True)
with open(fname, "w") as f:
    f.write(raw_yaml)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
