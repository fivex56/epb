#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FeeSaver scraper — reads SUN price from the page header.

Page shows: "for 65k Energy\n42 SUN"
That's the price for 65k/1h. 130k = 65k × 2.
"""

from __future__ import annotations
import logging, re, json
from typing import Any, Dict, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext

from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)


class FeeSaverScraper(PlaywrightBaseScraper):
    platform_id = "feesaver"
    platform_name = "FeeSaver"
    url = "https://feesaver.com/en"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        log.info("FeeSaver — looking for SUN price...")
        page.wait_for_timeout(3000)

        try:
            text = page.inner_text("body")
        except Exception:
            return {}

        # "for 65k Energy\n42 SUN" — the SUN value after "65k Energy"
        m = re.search(r"for\s+65k?\s+Energy\s*\n?\s*([0-9]+(?:\.[0-9]+)?)\s*SUN", text, re.IGNORECASE)
        if not m:
            # Try broader: any SUN near "65k"
            m = re.search(r"65k.*?([0-9]+(?:\.[0-9]+)?)\s*SUN", text, re.IGNORECASE)
        if not m:
            # Last resort: first "X SUN" on the page
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*SUN", text, re.IGNORECASE)

        if not m:
            log.warning("No SUN price found on FeeSaver")
            return {}

        sun = float(m.group(1))
        log.info(f"Found SUN: {sun}")

        # 65k at 42 SUN → TRX = 65000 * SUN / 1_000_000
        p65_1h = 65000 * sun / 1_000_000
        p130_1h = p65_1h * 2

        return {
            "65k_1h_price": r6(p65_1h),
            "130k_1h_price": r6(p130_1h),
        }


if __name__ == "__main__":
    FeeSaverScraper.main()
