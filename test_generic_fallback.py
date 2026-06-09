"""Quick test: can generic regex find prices on broken scraper sites?"""
from playwright.sync_api import sync_playwright
from base_playwright_scraper import extract_all_trx_prices
import sys

SITES = [
    ("catfee", "https://catfee.io/en/"),
    ("tronzap", "https://tronzap.com/"),
    ("netts", "https://netts.io/"),
]

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(locale="en-US", timezone_id="UTC")

    for name, url in SITES:
        print(f"\n=== {name} ({url}) ===", flush=True)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(800)
            text = page.inner_text("body")
            prices = extract_all_trx_prices(text)
            print(f"  Found {len(prices)} TRX prices: {prices[:8]}", flush=True)
        except Exception as e:
            print(f"  Error: {e}", flush=True)
        finally:
            page.close()

    browser.close()
    print("\nDone.", flush=True)
