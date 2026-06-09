"""Test all rewritten scrapers quickly."""
import subprocess, sys, os, json
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

SCRAPERS = [
    "catfee_scraper.py",
    "brutus_scraper.py",
    "mefree_scraper.py",
    "tofee_scraper.py",
    "tronex_scraper.py",
    "tronsave_scraper.py",
    "ergon_scraper.py",
    "feesaver_scraper.py",
    "justlend_dao_scraper.py",
    "renttron_scraper.py",
]

for s in SCRAPERS:
    price_file = s.replace("_scraper.py", "_prices.json")
    old_ts = "none"
    if os.path.exists(price_file):
        try:
            old = json.load(open(price_file))
            old_ts = old.get("ts", "none")[:19]
        except: pass

    print(f"Running {s}...", flush=True)
    try:
        r = subprocess.run([sys.executable, s], capture_output=True, text=True, timeout=40)
        new_ts = "none"
        if os.path.exists(price_file):
            try:
                new = json.load(open(price_file))
                new_ts = new.get("ts", "none")[:19]
            except: pass

        updated = "FRESH" if new_ts != old_ts and "2026" in new_ts else "STALE"
        has_1h = "N/A"
        try:
            new = json.load(open(price_file))
            has_1h = new.get("65k_1h_price", "N/A")
        except: pass
        print(f"  {updated} | ts: {old_ts} -> {new_ts} | 65k_1h: {has_1h}", flush=True)
        if r.stderr and 'Error' in r.stderr:
            print(f"  ERR: {r.stderr[:200]}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT", flush=True)
    except Exception as e:
        print(f"  FAIL: {e}", flush=True)

print("\nDone.", flush=True)
