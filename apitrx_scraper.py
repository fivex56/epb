#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""APITRX scraper — Playwright + generic fallback."""
import logging
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)

class APITRXScraper(PlaywrightBaseScraper):
    platform_id = "apitrx"
    platform_name = "APITRX"
    url = "https://apitrx.com/ru/pages/other.html"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        try:
            text = page.inner_text("body")
        except Exception:
            return {}
        import re
        trx_vals = []
        for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I):
            try:
                val = float(m.group(1))
                if 0.3 < val < 20:
                    trx_vals.append(val)
            except ValueError:
                pass
        result = {}
        trx_vals = sorted(set(trx_vals))
        if trx_vals:
            result["65k_1h_price"] = r6(trx_vals[0])
            result["130k_1h_price"] = r6(trx_vals[0] * 2)
        return result

if __name__ == "__main__":
    APITRXScraper.main()
