#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brutus.finance scraper — types 65k, reads SUN for 1h/1d/3d. 130k = 65k × 2.

Formula: price_TRX = 65000 × SUN / 1_000_000
Always starts fresh: types amount, clicks duration, waits for update, reads SUN.
"""

from __future__ import annotations
import logging, re, json
from typing import Any, Dict, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PwTimeout

from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)


class BrutusScraper(PlaywrightBaseScraper):
    platform_id = "brutus"
    platform_name = "Brutus.finance"
    url = "https://dapp.brutus.finance/#/ebot"

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        log.info("Brutus dApp — looking for input + duration buttons...")
        page.wait_for_timeout(4000)  # dApp hydration

        # Find the amount input
        inputs = page.locator('input:not([type="hidden"]):visible').all()
        amount_input = None
        for inp in inputs:
            try:
                ph = (inp.get_attribute("placeholder") or "").strip()
                tp = inp.evaluate("el => el.type")
                val = (inp.input_value() or "").strip()
                if tp not in ("hidden", "submit", "button", "checkbox", "radio"):
                    # prefer input with numeric placeholder (32000) or numeric value
                    if ph.isdigit() or (val and val.isdigit()):
                        amount_input = inp
                        break
            except Exception:
                pass
        if not amount_input:
            for inp in inputs:
                try:
                    tp = inp.evaluate("el => el.type")
                    if tp not in ("hidden", "submit", "button", "checkbox", "radio"):
                        amount_input = inp
                        break
                except Exception:
                    pass
        if not amount_input:
            log.warning("No amount input found")
            return {}

        log.info(f"Using input placeholder='{(amount_input.get_attribute('placeholder') or '').strip()}'")

        # Read the initial default value — save it so we can observe change
        try:
            initial_val = amount_input.input_value()
            log.info(f"Initial input value: {initial_val}")
        except Exception:
            initial_val = ""

        result = {}
        terms = [("1h", 3600), ("1d", 86400), ("3d", 259200)]

        for term_label, _ in terms:
            sun = self._type_amount_and_read_sun(page, amount_input, 65000, term_label)
            if sun is None:
                log.warning(f"  {term_label}: no SUN")
                continue

            price_65k = 65000 * sun / 1_000_000
            price_130k = price_65k * 2  # 130k ≈ 2× 65k

            result[f"65k_{term_label}_price"] = r6(price_65k)
            result[f"130k_{term_label}_price"] = r6(price_130k)
            log.info(f"  {term_label}: {sun} SUN → 65k={price_65k:.4f} TRX, 130k={price_130k:.4f} TRX")

        return result

    def _type_amount_and_read_sun(self, page: Page, amount_input, amount: int, term: str) -> Optional[float]:
        """Types amount, double-clicks duration (with 5s gap), reads SUN."""
        try:
            # Clear and type amount
            amount_input.click()
            page.wait_for_timeout(500)
            amount_input.fill("")
            page.wait_for_timeout(300)
            amount_input.type(str(amount), delay=80)
            page.wait_for_timeout(1000)

            # Double-click the duration with 5s wait between
            dur = page.get_by_text(term, exact=True).first
            if not dur.is_visible():
                dur = page.locator(f'button:has-text("{term}"), [role="button"]:has-text("{term}"), [class*="tab"]:has-text("{term}"), [class*="button"]:has-text("{term}"), span:has-text("{term}")').first

            dur.click()
            page.wait_for_timeout(5000)  # wait 5s
            dur.click()                   # click again
            page.wait_for_timeout(2000)  # wait for SUN update

            sun = self._read_sun(page)
            if sun and sun > 1.0:
                return sun

            # One more try with longer wait
            page.wait_for_timeout(3000)
            sun = self._read_sun(page)
            if sun and sun > 1.0:
                return sun

        except Exception as e:
            log.warning(f"  error for {term}: {e}")
        return None

    def _read_sun(self, page: Page) -> Optional[float]:
        """Read Energy Unit SUN value from the page."""
        try:
            text = page.inner_text("body")
        except Exception:
            return None

        m = re.search(r"Energy\s*Unit\s*[:：]\s*([0-9]+(?:\.[0-9]+)?)\s*SUN", text, re.IGNORECASE)
        if m:
            return float(m.group(1))

        m = re.search(r"([0-9]+)\s*SUN", text, re.IGNORECASE)
        if m:
            return float(m.group(1))

        return None


if __name__ == "__main__":
    BrutusScraper.main()
