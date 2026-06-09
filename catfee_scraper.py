#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CatFee scraper — Playwright + generic fallback."""
import logging
from typing import Any, Dict, Optional
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)


class CatFeeScraper(PlaywrightBaseScraper):
    platform_id = "catfee"
    platform_name = "CatFee"
    url = "https://catfee.io/"

    def get_url(self) -> str:
        return "https://catfee.io/en/"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        import re

        # 1) Priority: direct aria-label with the displayed hourly price
        #    Live site has: aria-label="Hourly price 2.340 TRX"
        try:
            hourly = page.locator('[aria-label*="Hourly price"]')
            if hourly.count() > 0:
                raw = (hourly.first.get_attribute("aria-label") or "").strip()
                m = re.search(r"([0-9]+(?:\s*[.,]\s*[0-9]+)?)\s*TRX", raw, re.I)
                if m:
                    val = float(m.group(1).replace(" ", "").replace(",", "."))
                    if isnum(val):
                        log.info("CatFee 65k/1h = %s TRX (from Hourly price aria-label)", r6(val))
                        return {"65k_1h_price": r6(val), "130k_1h_price": r6(val * 2)}
        except Exception:
            pass

        # 2) Fallback: scan all aria-labels for TRX+hour pattern
        try:
            lab_loc = page.locator("[aria-label]")
            cnt = lab_loc.count()
            for i in range(min(cnt, 200)):
                raw = (lab_loc.nth(i).get_attribute("aria-label") or "").strip()
                if not raw:
                    continue
                low = raw.lower()
                # "Hourly price" is the actual price; skip marketing "Rent ... for only"
                if "hourly price" in low:
                    m = re.search(r"([0-9]+(?:\s*[.,]\s*[0-9]+)?)\s*TRX", raw, re.I)
                    if m:
                        val = float(m.group(1).replace(" ", "").replace(",", "."))
                        if isnum(val):
                            log.info("CatFee 65k/1h = %s TRX (from aria-label scan)", r6(val))
                            return {"65k_1h_price": r6(val), "130k_1h_price": r6(val * 2)}
                # Broad fallback: any TRX + hour label (but log which one was picked)
                elif "trx" in low and any(x in low for x in ["hour", "час", "小时", "小時"]):
                    m = re.search(r"([0-9]+(?:\s*[.,]\s*[0-9]+)?)\s*TRX", raw, re.I)
                    if m:
                        val = float(m.group(1).replace(" ", "").replace(",", "."))
                        if isnum(val):
                            log.warning("CatFee using broad fallback label: %s", raw[:100])
                            return {"65k_1h_price": r6(val), "130k_1h_price": r6(val * 2)}
        except Exception:
            pass
        return {}  # let generic fallback handle it


if __name__ == "__main__":
    CatFeeScraper.main()
