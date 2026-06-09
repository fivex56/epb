#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TronSave scraper — table parsing (all 9 columns) + generic fallback."""
import logging, re
from typing import Any, Dict
from playwright.sync_api import Page
from base_playwright_scraper import PlaywrightBaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)

# Все 9 колонок в таблице TronSave
COLUMN_MAPPING = {
    0: "15m",
    1: "1h",
    2: "3h",
    3: "1d",
    4: "3d",
    5: "7d",
    6: "10d",
    7: "15d",
    8: "30d",
}
ALL_COLUMNS = list(range(9))  # парсим все 9


class TronSaveScraper(PlaywrightBaseScraper):
    platform_id = "tronsave"
    platform_name = "TronSave"
    url = "https://tronsave.io/"
    min_order = 100000

    def extract_prices(self, page: Page) -> Dict[str, Any]:
        result = {"minimum_order_energy": self.min_order}
        try:
            result.update(self._parse_table(page))
        except Exception as e:
            log.info("Table parsing failed: %s — trying generic fallback", e)
            try:
                result.update(self._generic_extract(page))
            except Exception:
                pass
        return result

    def _parse_table(self, page: Page) -> Dict[str, Any]:
        """Try to find and parse the tariff table."""
        tables = page.locator("table")
        cnt = tables.count()
        log.debug("Found %s tables", cnt)

        for i in range(cnt):
            t = tables.nth(i)
            try:
                t.wait_for(state="visible", timeout=3000)
                rows = t.locator("tbody tr")
                if rows.count() < 2:
                    continue
            except Exception:
                continue

            data = {}
            for r in range(rows.count()):
                cells = rows.nth(r).locator("td")
                if cells.count() < 2:
                    continue
                raw_amt = cells.nth(0).inner_text().strip()
                amt_txt = re.sub(r"[^\d]", "", raw_amt)
                if not amt_txt:
                    continue
                try:
                    amount = int(amt_txt)
                except ValueError:
                    continue
                if amount < 100_000:
                    continue

                row = {}
                for col_idx in ALL_COLUMNS:
                    cell_idx = col_idx + 1  # +1 потому что 0-я колонка — сумма
                    if cell_idx < cells.count():
                        try:
                            vtxt = cells.nth(cell_idx).inner_text().strip().replace(",", ".")
                            val = float(re.sub(r"[^\d\.]", "", vtxt))
                            row[COLUMN_MAPPING[col_idx]] = val
                        except Exception:
                            pass

                if row:
                    data[amount] = row

            if data:
                log.info("Parsed table with %d rows: amounts=%s", len(data), sorted(data.keys()))
                return self._build_prices_from_table(data)

        return {}

    def _build_prices_from_table(self, data: Dict[int, Dict[str, float]]) -> Dict[str, Any]:
        """Convert table rows to flat price keys for 65k and 130k."""
        result = {}

        def pick_row(energy: int) -> Dict[str, float]:
            keys = sorted(data.keys())
            chosen = keys[0]
            for a in keys:
                if a <= energy:
                    chosen = a
                else:
                    break
            return data[chosen]

        for amount_key, amount_val in [("65k", 65000), ("130k", 131000)]:
            row = pick_row(amount_val)
            for col_idx, term_key in COLUMN_MAPPING.items():
                if term_key in row:
                    unit_price = row[term_key]  # цена за 100k энергии
                    price = r6(amount_val * unit_price / 1_000_000.0)
                    # Костыль TronSave: 10d цена умножается на 10
                    if term_key == "10d":
                        price = r6(price * 10)
                    result[f"{amount_key}_{term_key}_price"] = price
                else:
                    result[f"{amount_key}_{term_key}_price"] = NA

        return result

    def _generic_extract(self, page: Page) -> Dict[str, Any]:
        """Fallback: regex scan for TRX prices."""
        try:
            text = page.inner_text("body")
        except Exception:
            return {}
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
    TronSaveScraper.main()
