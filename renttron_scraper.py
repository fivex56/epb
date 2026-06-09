#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RentTron scraper — page shows: 64k Energy - 3 TRX, 130k Energy - 6 TRX."""
import logging, re
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)

class RentTronScraper(PlaywrightBaseScraper):
    platform_id = "renttron"
    platform_name = "RentTron"
    url = "https://renttron.com/"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        page.wait_for_timeout(3000)
        try:
            text = page.inner_text("body")
        except Exception:
            return {}

        log.info(f"Page text ({len(text)} chars): {text[:400]}")

        # Find "64 285\nEnergy\n3 TRX" and "130 285\nEnergy\n6 TRX"
        # Pattern: number ≈ 65000 or 130000, followed by "Energy", then "X TRX"
        result = {}

        # RentTron shows: "64 285 Energy 3 TRX" → 64,285 ≈ 65k → price = 3
        m = re.search(r"64[\s]*285\s*\n?\s*Energy\s*\n?\s*([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I)
        if m:
            p65 = float(m.group(1))
            result["65k_1h_price"] = r6(p65)
            log.info(f"  Found 64k/Energy = {p65} TRX (65k/1h)")

        # "130 285 Energy 6 TRX" → 130,285 → 130k → price = 6
        m = re.search(r"130[\s]*285\s*\n?\s*Energy\s*\n?\s*([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I)
        if m:
            p130 = float(m.group(1))
            result["130k_1h_price"] = r6(p130)
            log.info(f"  Found 130k/Energy = {p130} TRX (130k/1h)")

        # Page structure: "64 285\nEnergy\n3 TRX" and "130 285\nEnergy\n6 TRX"
        # Match "Energy" followed by newline + "X TRX"
        energy_prices = []
        for m in re.finditer(r"Energy\s*\n\s*([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I):
            val = float(m.group(1))
            if 1 <= val <= 20:
                energy_prices.append(val)
        energy_prices = sorted(set(energy_prices))
        log.info(f"  Energy prices found: {energy_prices}")
        if len(energy_prices) >= 1:
            result["65k_1h_price"] = r6(energy_prices[0])
        if len(energy_prices) >= 2:
            result["130k_1h_price"] = r6(energy_prices[1])
        elif len(energy_prices) >= 1:
            result["130k_1h_price"] = r6(energy_prices[0] * 2)

        # Fallback: find "X 285 Energy Y TRX" with flexible spacing
        if not result:
            for m in re.finditer(r"([0-9]+)\s*[0-9]{3}\s*\n?\s*Energy\s*\n?\s*([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I):
                amount_str = m.group(1).replace(" ", "").strip()
                price_val = float(m.group(2))
                try:
                    amount = int(amount_str)
                    if 50000 < amount < 80000:
                        result["65k_1h_price"] = r6(price_val)
                        log.info(f"  Energy {amount} → {price_val} TRX (65k)")
                    elif 120000 < amount < 150000:
                        result["130k_1h_price"] = r6(price_val)
                        log.info(f"  Energy {amount} → {price_val} TRX (130k)")
                except ValueError:
                    pass
            if not result:
                log.warning(f"  Could not match Energy+TRX pattern from page")

        log.info(f"  Result: {result}")
        return result


if __name__ == "__main__":
    RentTronScraper.main()
