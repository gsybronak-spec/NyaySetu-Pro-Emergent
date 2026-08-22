"""
Detailed comparison between Production MongoDB API, backend/seed_data.py, and frontend/src/services/catalogSeed.ts
"""
import json
import urllib.request
import sys
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# 1. Live Production API
PROD_BASE = 'https://nyaysetu-backend-nwp2.onrender.com/api/catalog'
def fetch_prod(endpoint):
    req = urllib.request.Request(f'{PROD_BASE}/{endpoint}', headers={'User-Agent': 'NyaySetu-Audit'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

print("=" * 60)
print("FETCHING LIVE PRODUCTION CATALOG FROM RENDER...")
print("=" * 60)

prod_districts = fetch_prod('districts')
prod_talukas = fetch_prod('talukas')
prod_courts = fetch_prod('courts')

print(f"Production Districts Count: {len(prod_districts)}")
print(f"Production Talukas Count:   {len(prod_talukas)}")
print(f"Production Courts Count:    {len(prod_courts)}")

# 2. backend/seed_data.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import seed_data

seed_districts = seed_data.DISTRICTS
seed_talukas = seed_data.TALUKAS
seed_courts = seed_data.COURTS

print(f"\nseed_data.py Districts Count: {len(seed_districts)}")
print(f"seed_data.py Talukas Count:   {len(seed_talukas)}")
print(f"seed_data.py Courts Count:    {len(seed_courts)}")

# 3. Check COURTS in seed_data.py vs Production
prod_court_ids = {c['id']: c for c in prod_courts}
seed_court_ids = {c['id']: c for c in seed_courts}

missing_in_seed = [c for cid, c in prod_court_ids.items() if cid not in seed_court_ids]
missing_in_prod = [c for cid, c in seed_court_ids.items() if cid not in prod_court_ids]
common = [c for cid, c in prod_court_ids.items() if cid in seed_court_ids]

print("\n" + "=" * 60)
print("COURTS COMPARISON")
print("=" * 60)
print(f"Total in Production: {len(prod_courts)}")
print(f"Total in seed_data.py: {len(seed_courts)}")
print(f"Common count: {len(common)}")

print(f"\nPresent in Production but MISSING in seed_data.py ({len(missing_in_seed)}):")
for c in missing_in_seed:
    print(f"  ID: {c.get('id')} | District: {c.get('district_id')} | EN: {c.get('en')} | GU: {c.get('gu')}")

print(f"\nPresent in seed_data.py but MISSING in Production ({len(missing_in_prod)}):")
for c in missing_in_prod:
    print(f"  ID: {c.get('id')} | District: {c.get('district_id')} | EN: {c.get('en')} | GU: {c.get('gu')}")

# Inspect seed_data.py COURTS definition
print("\n" + "=" * 60)
print("INSPECTING seed_data.py COURTS DEFINITION")
print("=" * 60)
print("seed_data.py has:")
print("  - 6 Generic Courts")
print("  - 2 Ahmedabad Specific (ahd_metro, ahd_city_civil)")
print(f"  - len(_DISTRICT_COURTS) = {len(seed_data._DISTRICT_COURTS)}")
print(f"  Total = 6 + 2 + {len(seed_data._DISTRICT_COURTS)} = {6 + 2 + len(seed_data._DISTRICT_COURTS)}")

# Let's inspect production courts by district
print("\nProduction courts by district:")
prod_by_district = {}
for c in prod_courts:
    d = c.get("district_id", "none")
    prod_by_district.setdefault(d, []).append(c)

for d, clist in sorted(prod_by_district.items()):
    print(f"  District '{d}': {len(clist)} courts")
    for c in clist:
        print(f"    - {c.get('id')}: {c.get('en')} ({c.get('gu')})")
