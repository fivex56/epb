#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TronZap scraper — Playwright + generic fallback."""
import logging
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)


class TronZapScraper(PlaywrightBaseScraper):
    platform_id = "tronzap"
    platform_name = "TronZap"
    url = "https://tronzap.com/"

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
                if 0.5 < val < 100:
                    trx_vals.append(val)
            except ValueError:
                pass

        result = {}
        trx_vals = sorted(set(trx_vals))
        # trx_vals[0] = 65k price, trx_vals[1] = 130k price (if present)
        # Do NOT compute 130k as 65k*2 — use actual scraped value
        if trx_vals:
            result["65k_1h_price"] = r6(trx_vals[0])
        if len(trx_vals) >= 2:
            result["130k_1h_price"] = r6(trx_vals[1])
        if len(trx_vals) >= 3:
            result["65k_1d_price"] = r6(trx_vals[2])
        if len(trx_vals) >= 4:
            result["130k_1d_price"] = r6(trx_vals[3])

        return result


if __name__ == "__main__":
    TronZapScraper.main()
