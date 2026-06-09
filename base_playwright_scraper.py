#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Playwright-based scraper base class with fallback price extraction.

When specific selectors fail (site changed HTML), tries generic regex
to find TRX prices on the page.  Never leaves stale data on disk."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright, Page, BrowserContext

from base_scraper import BaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)

# -- Generic TRX price extraction -------------------------------------------

# Patterns for finding ANY TRX price on a page
TRX_PRICE_RE = re.compile(
    r"(?:price|cost|total|amount|TRX|fee|pay)\D{0,40}"  # anchor word
    r"([0-9]+(?:\s*[.,]\s*[0-9]+)?)"                     # number
    r"\s*TRX",
    re.IGNORECASE,
)

# Generic "X TRX" anywhere on the page
ANY_TRX_RE = re.compile(
    r"([0-9]+(?:\s*[.,]\s*[0-9]+)?)\s*TRX",
    re.IGNORECASE,
)


def extract_all_trx_prices(text: str, max_count: int = 20) -> List[float]:
    """Find all TRX prices in a text blob, return sorted."""
    prices = []
    for m in ANY_TRX_RE.finditer(text):
        raw = m.group(1).replace(" ", "").replace(",", ".")
        try:
            val = float(raw)
            if 0 < val < 1000:  # reasonable TRX price range
                prices.append(val)
        except ValueError:
            pass
    return sorted(prices)


def guess_energy_price(text: str, energy_amount: int = 65000) -> Optional[float]:
    """Try to guess the price for a given energy amount from page text.

    Heuristic: energy prices are typically 1-20 TRX for 65k energy.
    For 130k, roughly 2× the 65k price.
    """
    prices = extract_all_trx_prices(text)
    if not prices:
        return None

    # For 65k energy, hourly price is usually 1-10 TRX
    if energy_amount == 65000:
        candidates = [p for p in prices if 0.5 < p < 20]
        if candidates:
            return r6(candidates[0])  # cheapest
    elif energy_amount == 131000:
        candidates = [p for p in prices if 1.0 < p < 40]
        if candidates:
            return r6(candidates[0])

    return None


# -- Playwright base class --------------------------------------------------

class PlaywrightBaseScraper(BaseScraper):
    """Base for Playwright-based scrapers with graceful degradation.

    Subclasses override `extract_prices(page)` — return a dict of price fields.
    If extraction fails (exception or empty), the generic fallback kicks in:
    scans page text for any TRX prices.
    """

    timeout_ms: int = 45_000
    headless: bool = True

    def __init__(self, headless: bool = True):
        super().__init__()
        self.headless = headless

    # ---- subclasses override this ----
    def extract_prices(self, page: Page) -> Dict[str, Any]:
        """Override: use Playwright selectors to extract prices from the page.
        Return at minimum the price fields you can extract.
        Raise exception on failure — base class handles fallback."""
        raise NotImplementedError

    def get_url(self) -> str:
        """Override if URL needs dynamic construction."""
        return self.url

    # ---- generic fallback ----
    def generic_extract(self, page: Page) -> Dict[str, Any]:
        """Fallback: scan page for any TRX prices using regex."""
        text = ""
        try:
            text = page.inner_text("body")
        except Exception:
            try:
                text = page.content()
            except Exception:
                pass

        if not text:
            log.warning("Generic fallback: no page text found")
            return {}

        prices = extract_all_trx_prices(text)
        log.info("Generic fallback found %d TRX prices: %s", len(prices), prices[:5])

        result = {}
        # Try to find the hourly 65k price (usually the smallest TRX value < 10)
        small = [p for p in prices if p < 20]
        if small:
            p65 = r6(small[0])
            result["65k_1h_price"] = p65

            # Look for actual 130k price among other values (1.5x-3x of 65k)
            p130_direct = None
            for p in small[1:]:
                ratio = p / p65
                if 1.5 <= ratio <= 3.0:
                    p130_direct = r6(p)
                    break
            result["130k_1h_price"] = p130_direct if p130_direct else r6(p65 * 2)

        # Try to find 1d price (usually 3-6x the 1h price)
        mid = [p for p in prices if p > 2 and p < 60]
        if len(mid) >= 2:
            result["65k_1d_price"] = r6(mid[1])
            # Same logic: try to find actual 130k/1d or compute 2x
            p65d = mid[1]
            p130d_direct = None
            for p in mid[2:]:
                if p65d > 0 and 1.5 <= p / p65d <= 3.0:
                    p130d_direct = r6(p)
                    break
            result["130k_1d_price"] = p130d_direct if p130d_direct else r6(p65d * 2)

        return result

    # ---- main scrape ----
    def scrape(self) -> Dict[str, Any]:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            ctx = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"),
                locale="en-US",
                timezone_id="UTC",
                viewport={"width": 1400, "height": 900},
            )
            page = ctx.new_page()
            page.set_default_navigation_timeout(self.timeout_ms)
            page.set_default_timeout(10_000)

            url = self.get_url()
            log.info("Goto %s ...", url)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_timeout(500)  # let JS hydrate
            except Exception as e:
                log.error("Page load failed: %s", e)
                browser.close()
                return {}

            result = {}
            try:
                result = self.extract_prices(page)
                has_data = any(isnum(v) for v in result.values())
                if not has_data:
                    log.warning("Specific extraction returned no data, trying fallback")
                    result = self.generic_extract(page)
            except Exception as e:
                log.warning("Specific extraction failed: %s — trying generic fallback", e)
                try:
                    result = self.generic_extract(page)
                except Exception as e2:
                    log.error("Generic fallback also failed: %s", e2)

            browser.close()
            return result

    @classmethod
    def main(cls, argv: Optional[list] = None):
        import argparse
        ap = argparse.ArgumentParser(description=f"{cls.platform_name} scraper (Playwright)")
        ap.add_argument("--out", default=None)
        ap.add_argument("--headful", action="store_true", help="Show browser window")
        ap.add_argument("--timeout", type=int, default=45000)
        ap.add_argument("--log", default="info", choices=["debug", "info", "warning", "error"])
        args = ap.parse_args(argv)

        logging.basicConfig(
            level=getattr(logging, args.log.upper()),
            format="%(asctime)s %(levelname)s %(message)s",
        )

        instance = cls(headless=not args.headful)
        instance.timeout_ms = args.timeout
        if args.out:
            instance.out_file = args.out

        payload = instance.run()
        print(json.dumps(payload, ensure_ascii=False, indent=2))


# Need this import at the bottom to avoid circular import
import json
