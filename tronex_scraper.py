#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tronex Energy scraper — uses API /api/v1/precountOrder.

GET /balance + POST /precountOrder for all energy-volume combos.
"""

import json, requests, logging
from datetime import datetime, timezone
from typing import Any, Dict

log = logging.getLogger(__name__)

import os
API_KEY = os.environ.get("TRONEX_API_KEY", "YOUR_KEY_HERE")
API_BASE = "https://api.tronex.energy"
HEADERS = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

TERMS = ["1h", "1d", "3d", "7d"]  # 7d maps to our 10d-ish slot
VOLUMES = [65000, 130000, 200000, 500000, 1000000]


def precount(volume: int, days: str) -> dict:
    """Query price estimate."""
    try:
        r = requests.post(f"{API_BASE}/api/v1/precountOrder",
            json={"days": days, "volume": volume}, headers=HEADERS, timeout=15)
        return r.json()
    except Exception as e:
        log.error(f"precount error ({volume}/{days}): {e}")
        return {}


def balance() -> dict:
    try:
        r = requests.get(f"{API_BASE}/api/v1/balance", headers=HEADERS, timeout=15)
        return r.json()
    except Exception as e:
        log.error(f"balance error: {e}")
        return {}


def scrape() -> Dict[str, Any]:
    bal = balance()
    log.info(f"Balance: {bal}")

    # Query 65k and 130k for all terms
    prices = {}
    for vol in [65000, 130000]:
        for term in TERMS:
            data = precount(vol, term)
            price = data.get("summa")  # summa = TRX amount, not SUN
            summa = data.get("summa")
            if price is not None:
                vol_key = "65k" if vol == 65000 else "130k"
                # Map "7d" -> "10d" (closest)
                term_key = "10d" if term == "7d" else term
                key = f"{vol_key}_{term_key}_price"
                prices[key] = price
                log.info(f"  {vol_key}/{term_key}: price={price} summa={summa}")

    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "platform_id": "tronex",
        "platform_name": "Tronex Energy",
        "url": "https://tronex.energy/pricing",
        "chain": "TRON",
        "product_type": "energy_purchase",
        "minimum_order_energy": 65000,
        "maximum_order_energy": 4000000,
        "platform_max_energy": "N/A",
    }
    for term in ["15m", "1h", "1d", "3d", "10d"]:
        for vol in ["65k", "130k"]:
            key = f"{vol}_{term}_price"
            result[key] = prices.get(key, "N/A")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    payload = scrape()
    if payload:
        with open("tronex_prices.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        log.info("Wrote tronex_prices.json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
