#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TronMax scraper — pure API, 15M only (order book). Rest filled by fill_prices.py"""

import json, logging, requests
from typing import Any, Dict
from datetime import datetime, timezone

from base_scraper import BaseScraper, NA, isnum, r6

log = logging.getLogger(__name__)


class TronMaxScraper(BaseScraper):
    platform_id = "tronmax"
    platform_name = "TronMax"

    def scrape(self) -> Dict[str, Any]:
        log.info("Fetching TronMax /Setting/UI ...")
        r = requests.get("https://api.tronmax.io/Setting/UI", timeout=15)
        data = r.json()
        rates = data["data"]["ratesByDuration"]

        sun_15m = None
        for entry in rates:
            if entry.get("exactDurationSeconds") == 900:
                sun_15m = entry["rate"]["energy"]
                break

        if sun_15m is None:
            log.warning("No 15M rate found")
            return {}

        p65 = 65000 * sun_15m / 1_000_000
        p130 = 130000 * sun_15m / 1_000_000

        log.info(f"15M: {sun_15m} SUN -> 65k={r6(p65)} TRX, 130k={r6(p130)} TRX")

        result = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "platform_id": self.platform_id,
            "platform_name": self.platform_name,
            "url": "https://tronmax.io/",
            "chain": "TRON",
            "product_type": "energy_purchase",
            "minimum_order_energy": 20000,
            "maximum_order_energy": 2000000,
            "platform_max_energy": "N/A",
        }
        for term in ["15m", "1h", "1d", "3d", "10d"]:
            for vol in ["65k", "130k"]:
                result[f"{vol}_{term}_price"] = "N/A"

        result["65k_15m_price"] = r6(p65)
        result["130k_15m_price"] = r6(p130)

        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = TronMaxScraper()
    payload = scraper.run()
    if payload:
        with open("tronmax_prices.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        log.info("Wrote tronmax_prices.json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
