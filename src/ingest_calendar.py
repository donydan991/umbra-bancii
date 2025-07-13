#!/usr/bin/env python3
"""
Umbra Băncii – Ingest Calendar Economic
Cadentă: o dată pe oră
Sursă: RSS ForexFactory "thisweek"
Păstrăm doar evenimentele viitoare cu impact High / Medium (max. 5).
"""

import os
import requests
import datetime as dt
import hashlib
import yaml
import xml.etree.ElementTree as ET

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
HEADERS = {"User-Agent": "UmbraBancii/1.0"}

# ------------------------------------------------------------------
# 1) Download feed
# ------------------------------------------------------------------
resp = requests.get(URL, headers=HEADERS, timeout=15)
resp.raise_for_status()
root = ET.fromstring(resp.content)

# ------------------------------------------------------------------
# 2) Parse & filter events
# ------------------------------------------------------------------
UTC = dt.timezone.utc
now_utc = dt.datetime.utcnow().replace(tzinfo=UTC)

events = []
for item in root.findall(".//event"):
    impact = item.findtext("impact")
    if impact not in ("High", "Medium"):
        continue

    # ForexFactory date/time already UTC ("2025-07-15", "08:30")
    date_str = item.findtext("date")
    time_str = item.findtext("time")
    try:
        evt_dt = dt.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
    except ValueError:
        # Skip malformed entries
        continue

    if evt_dt < now_utc:
        continue  # exclude past events

    events.append(
        {
            "title": item.findtext("title"),
            "ccy": item.findtext("country"),
            "impact": impact,
            "timestamp_utc": evt_dt.isoformat(),
        }
    )
    if len(events) >= 5:  # keep only the next 5 upcoming events
        break

# ------------------------------------------------------------------
# 3) Build payload & write YAML
# ------------------------------------------------------------------
payload = {
    "timestamp_utc": now_utc.isoformat(),
    "source": "ForexFactory RSS",
    "events_count": len(events),
    "events": events,
}

raw_yaml = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

safe_ts = now_utc.strftime("%Y-%m-%dT%H-%M-%SZ")
os.makedirs("output", exist_ok=True)
fname = f"output/CALENDAR_{safe_ts}.yaml"

with open(fname, "w", encoding="utf-8") as f:
    f.write(raw_yaml)

print("Generated:", fname)
print("SHA256:", hashlib.sha256(raw_yaml.encode()).hexdigest())
