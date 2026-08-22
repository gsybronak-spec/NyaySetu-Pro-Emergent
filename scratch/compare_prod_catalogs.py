import json
import urllib.request
import sys
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

PROD_BASE = 'https://nyaysetu-backend-nwp2.onrender.com/api/catalog'
def fetch_prod(endpoint):
    req = urllib.request.Request(f'{PROD_BASE}/{endpoint}', headers={'User-Agent': 'NyaySetu-Audit'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

prod_districts = fetch_prod('districts')
prod_talukas = fetch_prod('talukas')
prod_courts = fetch_prod('courts')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import seed_data

seed_districts = seed_data.DISTRICTS
seed_talukas = seed_data.TALUKAS
seed_courts = seed_data.COURTS

out = []
out.append("=== TOTAL COUNTS ===")
out.append(f"Districts: Production = {len(prod_districts)} | seed_data.py = {len(seed_districts)}")
out.append(f"Talukas:   Production = {len(prod_talukas)} | seed_data.py = {len(seed_talukas)}")
out.append(f"Courts:    Production = {len(prod_courts)} | seed_data.py = {len(seed_courts)}")

prod_court_ids = {c['id']: c for c in prod_courts}
seed_court_ids = {c['id']: c for c in seed_courts}

missing_in_seed = [c for cid, c in prod_court_ids.items() if cid not in seed_court_ids]
missing_in_prod = [c for cid, c in seed_court_ids.items() if cid not in prod_court_ids]
common = [c for cid, c in prod_court_ids.items() if cid in seed_court_ids]

out.append(f"\nCommon Court IDs: {len(common)}")
out.append(f"Court IDs in Production but NOT in seed_data.py ({len(missing_in_seed)}):")
for c in missing_in_seed:
    out.append(f"  + ID: {c.get('id')} | District: {c.get('district_id')} | EN: {c.get('en')} | GU: {c.get('gu')}")

out.append(f"\nCourt IDs in seed_data.py but NOT in Production ({len(missing_in_prod)}):")
for c in missing_in_prod:
    out.append(f"  - ID: {c.get('id')} | District: {c.get('district_id')} | EN: {c.get('en')} | GU: {c.get('gu')}")

# Check differences in Districts and Talukas too
prod_dist_ids = {d['id']: d for d in prod_districts}
seed_dist_ids = {d['id']: d for d in seed_districts}
out.append(f"\nDistricts missing in seed: {[d for did, d in prod_dist_ids.items() if did not in seed_dist_ids]}")
out.append(f"Districts missing in prod: {[d for did, d in seed_dist_ids.items() if did not in prod_dist_ids]}")

prod_tal_ids = {t['id']: t for t in prod_talukas}
seed_tal_ids = {t['id']: t for t in seed_talukas}
out.append(f"\nTalukas missing in seed: {len([t for tid, t in prod_tal_ids.items() if tid not in seed_tal_ids])}")
out.append(f"Talukas missing in prod: {len([t for tid, t in seed_tal_ids.items() if tid not in prod_tal_ids])}")

report_text = "\n".join(out)
print(report_text)

with open("scratch/courts_comparison_report.txt", "w", encoding="utf-8") as f:
    f.write(report_text)
