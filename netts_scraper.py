#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NETTS scraper — Playwright + generic fallback."""
import logging
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)


class NETTSScraper(PlaywrightBaseScraper):
    platform_id = "netts"
    platform_name = "NETTS"
    url = "https://netts.io/"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        import re

        # NETTS shows price as SUN rate (SUN per energy unit per hour)
        # 65k price = SUN * 65000 / 1_000_000 TRX
        # 130k price = 2 * 65k price

        try:
            text = page.inner_text("body")
        except Exception:
            return {}

        # Look for "SUN: 33.00" or "SUN 33.00" or just "33.00 SUN"
        sun_patterns = [
            r"SUN\s*:?\s*([0-9]+(?:\.[0-9]+)?)",
            r"([0-9]+(?:\.[0-9]+)?)\s*SUN",
        ]
        for pat in sun_patterns:
            m = re.search(pat, text, re.I)
            if m:
                sun_rate = float(m.group(1))
                if 1 < sun_rate < 1000:  # reasonable SUN rate
                    p65_1h = r6(sun_rate * 65000 / 1_000_000)
                    p130_1h = r6(p65_1h * 2)
                    log.info("NETTS SUN=%.2f -> 65k/1h=%.4f TRX, 130k/1h=%.4f TRX",
                             sun_rate, p65_1h, p130_1h)
                    return {
                        "65k_1h_price": p65_1h,
                        "130k_1h_price": p130_1h,
                    }

        # Fallback: scan for any TRX prices
        trx_vals = []
        for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*TRX", text, re.I):
            try:
                val = float(m.group(1))
                if 0.3 < val < 100:
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
    NETTSScraper.main()
