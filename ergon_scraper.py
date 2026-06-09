#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ergon scraper — reads TRX/M/day rates from page text.

Page shows: "Price for X day(s): Y TRX/M/day"
Formula: price_TRX = rate * energy_amount / 1_000_000

Only 130k+ makes sense for Ergon (min is ~100k). 65k = 130k / 2.
"""

from __future__ import annotations
import logging, re, json
from typing import Any, Dict, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext

from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)


class ErgonScraper(PlaywrightBaseScraper):
    platform_id = "ergon"
    platform_name = "Ergon"
    url = "https://ergon.ustx.io/"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        log.info("Ergon — reading TRX/M/day rates...")
        page.wait_for_timeout(4000)

        try:
            text = page.inner_text("body")
        except Exception:
            return {}

        log.info(f"Page text length: {len(text)} chars")

        # Parse "Price for X day(s): Y TRX/M/day"
        # Also "Price for 3 or more days: Y TRX/M/day"
        rates = {}
        for m in re.finditer(
            r"Price\s+for\s+(\d+|3\s*or\s*more)\s*day(?:s)?\s*[:：]\s*([0-9]+(?:\.[0-9]+)?)\s*TRX\s*/\s*M\s*/\s*day",
            text, re.IGNORECASE
        ):
            days_str = m.group(1).strip()
            rate = float(m.group(2))
            # Normalize: "1" -> "1d", "2" -> "2d", "3 or more" -> "3d"
            if "3" in days_str and "or" in days_str.lower():
                key = "3d"
            else:
                key = f"{int(days_str)}d"
            rates[key] = rate
            log.info(f"  Found rate: {key} → {rate} TRX/M/day")

        log.info(f"All rates: {rates}")
        if not rates:
            return {}

        result = {}
        energy = 130000  # Ergon minimum is ~100k, 130k is the standard we track

        # 1d price
        if "1d" in rates:
            p130_1d = energy * rates["1d"] / 1_000_000
            result["130k_1d_price"] = r6(p130_1d)
            result["65k_1d_price"] = r6(p130_1d / 2)
        # Ergon does NOT offer hourly rental — leave 1h as N/A

        # 2d price — use for our 3d slot (closest match)
        if "2d" in rates:
            p130_2d = energy * rates["2d"] / 1_000_000
            if "130k_3d_price" not in result:
                result["130k_3d_price"] = r6(p130_2d * 1.5)
                result["65k_3d_price"] = r6(p130_2d * 1.5 / 2)

        # 3d+ price — use for 3d and 10d
        if "3d" in rates:
            p130_3d = energy * rates["3d"] / 1_000_000
            result["130k_3d_price"] = r6(p130_3d)
            result["65k_3d_price"] = r6(p130_3d / 2)
            # 10d ≈ 3d * 3.33
            result["130k_10d_price"] = r6(p130_3d * 3.33)
            result["65k_10d_price"] = r6(p130_3d * 3.33 / 2)

        return result


if __name__ == "__main__":
    ErgonScraper.main()
