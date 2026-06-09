#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JustLend DAO scraper — Playwright + generic fallback."""
import logging, re
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)

class JustLendDAOScraper(PlaywrightBaseScraper):
    platform_id = "justlend_dao"
    platform_name = "JustLend DAO — Energy Rental"
    url = "https://app.justlend.org/energyRental"
    min_order = 100000

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        result = {"minimum_order_energy": self.min_order}
        try:
            text = page.inner_text("body")
        except Exception:
            return result
        trx_vals = []
        for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I):
            try:
                val = float(m.group(1))
                if 0.3 < val < 200: trx_vals.append(val)
            except ValueError: pass
        trx_vals = sorted(set(trx_vals))
        if trx_vals:
            result["130k_1h_price"] = r6(trx_vals[0])
            result["65k_1h_price"] = r6(trx_vals[0] / 2)
        return result

if __name__ == "__main__":
    JustLendDAOScraper.main()
