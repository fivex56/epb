#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MeFree scraper — reads page text for TRX price display."""
import logging, re
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)

class MeFreeScraper(PlaywrightBaseScraper):
    platform_id = "mefree"
    platform_name = "MeFree"
    url = "https://mefree.net/"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        page.wait_for_timeout(3000)
        try:
            text = page.inner_text("body")
        except Exception:
            return {}

        log.info(f"Page text: {text[:500]}")

        # Find TRX price — "3 TRX" anywhere on the page
        trx_vals = []
        for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I):
            try:
                val = float(m.group(1))
                if 0.5 < val < 100:
                    trx_vals.append(val)
            except ValueError:
                pass

        trx_vals = sorted(set(trx_vals))
        log.info(f"Found TRX: {trx_vals}")

        if not trx_vals:
            return {}

        # Take the lowest TRX value as 65k/1h price
        p65_1h = r6(trx_vals[0])
        return {
            "65k_1h_price": p65_1h,
            "130k_1h_price": r6(p65_1h * 2),
        }


if __name__ == "__main__":
    MeFreeScraper.main()
