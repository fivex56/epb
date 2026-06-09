#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

import requests

API = "https://open.tronify.io/api/tronRent"
URL_CFG = f"{API}/pledgeConfig"
URL_QUOTE = f"{API}/queryPreorderInfo"

HEADERS = {"Content-Type": "application/json;charset=UTF-8"}
TIMEOUT = 15
RETRIES = 3
SLEEP = 0.8

# Все сроки которые отдаёт Tronify API
DURATIONS = {
    "1h":  {"d": 0, "h": 1, "m": 0},
    "3h":  {"d": 0, "h": 3, "m": 0},
    "1d":  {"d": 1, "h": 0, "m": 0},
    "3d":  {"d": 3, "h": 0, "m": 0},
    "10d": {"d": 10, "h": 0, "m": 0},
}
# Tronify не имеет 15m тарифа — оставляем "N/A"

# Все объёмы которые запрашиваем
AMOUNTS = {
    "10k":  10_000,
    "20k":  20_000,
    "32k":  32_000,
    "50k":  50_000,
    "65k":  65_000,
    "100k": 100_000,
    "130k": 131_000,  # по ТЗ 130k = 131000
    "200k": 200_000,
    "500k": 500_000,
    "1M":   1_000_000,
}


def _post(url: str, payload: dict) -> dict:
    last = None
    for i in range(RETRIES):
        try:
            r = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            logging.warning("POST %s failed (%d/%d): %s", url, i + 1, RETRIES, e)
            time.sleep(SLEEP)
    raise RuntimeError(f"API request failed: {last}")


def fetch_cfg(address: str, source_flag: str) -> dict:
    resp = _post(URL_CFG, {"address": address, "sourceFlag": source_flag})
    if str(resp.get("resCode")) != "100":
        logging.warning("pledgeConfig non-100: %s", resp)
        return {}
    return resp.get("data") or {}


def quote_trx(from_addr: str, recv_addr: str, source_flag: str,
              energy: int, d: int, h: int, m: int) -> Optional[float]:
    payload = {
        "fromAddress": from_addr,
        "pledgeAddress": recv_addr,
        "tradeType": "fastTrade",
        "pledgeDay": str(d),
        "pledgeHour": str(h),
        "pledgeMinute": str(m),
        "orderType": "ENERGY",
        "pledgeNum": int(energy),
        "sourceFlag": source_flag,
        "extraTrxNum": "0",
        "pledgeBandwidthNum": "0",
    }
    resp = _post(URL_QUOTE, payload)
    if str(resp.get("resCode")) != "100":
        logging.warning("queryPreorderInfo non-100: %s", resp)
        return None
    try:
        return round(float((resp.get("data") or {}).get("pledgeTrxNum")), 6)
    except Exception:
        return None


def build_output(cfg: dict,
                 all_prices: Dict[str, Dict[str, Optional[float]]]) -> dict:
    """Собирает плоский JSON со всеми объёмами и сроками."""
    def num_or_na(key: str):
        v = cfg.get(key)
        return int(v) if isinstance(v, (int, float)) else "N/A"

    out = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "platform_id": "tronify",
        "platform_name": "Tronify",
        "url": "https://tronify.io/",
        "chain": "TRON",
        "product_type": "energy_purchase",
        "minimum_order_energy": num_or_na("lowEnergyCanBuy"),
        "maximum_order_energy": num_or_na("topEnergyCanBuy"),
        "platform_max_energy": num_or_na("topEnergyCanBuy"),
    }

    # Все комбинации amounts × durations
    for amount_key in AMOUNTS:
        for term_key in DURATIONS:
            price = all_prices.get(amount_key, {}).get(term_key)
            out[f"{amount_key}_{term_key}_price"] = price if isinstance(price, (int, float)) else "N/A"
        # 15m отсутствует в Tronify
        out[f"{amount_key}_15m_price"] = "N/A"

    return out


def scrape(from_addr: str, recv_addr: str, source_flag: str) -> dict:
    logging.info("Fetching config…")
    cfg = fetch_cfg(from_addr, source_flag)

    all_prices: Dict[str, Dict[str, Optional[float]]] = {}

    for amount_key, amount_val in AMOUNTS.items():
        logging.info("Quoting %s (%s energy)…", amount_key, amount_val)
        all_prices[amount_key] = {}
        for term_key, dhm in DURATIONS.items():
            p = quote_trx(from_addr, recv_addr, source_flag, amount_val, **dhm)
            if isinstance(p, (int, float)):
                logging.info("  %s %s = %s TRX", amount_key, term_key, p)
            all_prices[amount_key][term_key] = p
        time.sleep(0.15)  # рейт-лимит

    return build_output(cfg, all_prices)


def main():
    ap = argparse.ArgumentParser(description="Tronify scraper (API)")
    ap.add_argument("--from-address", default="TKghVbeEzvrV8GLK3YE1gRrjVHSf8rGB6k")
    ap.add_argument("--recv-address", default="TKghVbeEzvrV8GLK3YE1gRrjVHSf8rGB6k")
    ap.add_argument("--source-flag", default="tronify")
    ap.add_argument("--out", default="tronify_prices.json")
    ap.add_argument("--log", default="info", choices=["debug", "info", "warning", "error"])
    args = ap.parse_args()

    logging.basicConfig(level=getattr(logging, args.log.upper()),
                        format="%(asctime)s %(levelname)s %(message)s")

    data = scrape(args.from_address, args.recv_address, args.source_flag)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info("Saved: %s", args.out)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
