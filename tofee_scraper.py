#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tofee scraper — Playwright + generic fallback."""
import logging, re
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)

class TofeeScraper(PlaywrightBaseScraper):
    platform_id = "tofee"
    platform_name = "Tron Fee Energy Rental"
    url = "https://tofee.net/"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        import re

        try:
            text = page.inner_text("body")
        except Exception:
            return {}

        result = {}

        # Parse "Send X TRX per 65k Energy" patterns grouped by duration
        # Page has sections like:
        #   15 Minute Duration  Send 2.5 TRX per 65k Energy
        #   1 Hour Duration     Send 3.0 TRX per 65k Energy

        # Find all duration + price pairs
        # Pattern: (15 Minute|1 Hour) Duration ... Send X.XX TRX per 65k
        pairs = list(re.finditer(
            r"(15\s*Minute|1\s*Hour)\s+Duration.*?Send\s+([0-9]+(?:\.[0-9]+)?)\s*TRX\s+per\s+65k",
            text, re.I | re.DOTALL
        ))

        p15m = None
        p1h = None
        for m in pairs:
            duration = m.group(1).lower()
            price = float(m.group(2))
            if "15" in duration or "minute" in duration:
                p15m = price
            elif "1" in duration or "hour" in duration:
                p1h = price

        if p1h is not None:
            result["65k_1h_price"] = r6(p1h)
            result["130k_1h_price"] = r6(p1h * 2)
        if p15m is not None:
            result["65k_15m_price"] = r6(p15m)
            result["130k_15m_price"] = r6(p15m * 2)

        if result:
            log.info("Tofee: 15m=%s, 1h=%s", p15m, p1h)
            return result

        # Fallback: plain TRX price scan
        trx_vals = []
        for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I):
            try:
                val = float(m.group(1))
                if 0.3 < val < 100:
                    trx_vals.append(val)
            except ValueError:
                pass
        trx_vals = sorted(set(trx_vals))
        if trx_vals:
            result["65k_1h_price"] = r6(trx_vals[0])
            result["130k_1h_price"] = r6(trx_vals[0] * 2)
        return result

if __name__ == "__main__":
    TofeeScraper.main()
