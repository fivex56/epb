#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# refee_scraper.py — берёт цены из re:Fee API и пишет в refee_prices.json
# pip install requests

import argparse
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional

import requests

API_BASE = "https://api.refee.bot"
NA = "N/A"

# Вшитый API-ключ
TOKEN_DEFAULT = "dSvPsCyRUDP0Zc9SC5b6npMG45H7wjRwXiwdVFmkOHZWPp5hWzjygQhKRZgGn7IW"

# Объёмы: 65k как есть, «дабл» — как в боте: 135k
VOL_65K = 65000
VOL_130K_EFFECTIVE = 135000  # чтобы совпадать с ботом re:Fee

SCHEMA_KEYS = [
    "ts", "platform_id", "platform_name", "url", "chain", "product_type",
    "minimum_order_energy", "maximum_order_energy", "platform_max_energy",
    "65k_15m_price", "65k_1h_price", "65k_1d_price", "65k_3d_price", "65k_10d_price",
    "130k_15m_price", "130k_1h_price", "130k_1d_price", "130k_3d_price", "130k_10d_price",
]

HEADERS = {"User-Agent": "EPB/1.0 (+https://energypriceboard.tech)"}

def r6(x: float) -> float:
    return round(float(x), 6)

def atomic_write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".refee_", dir=os.path.dirname(path) or ".", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)

def get_summa(token: str, days: str, volume: int,
              timeout_ms: int = 15000, retries: int = 3) -> Optional[float]:
    """
    GET /precountOrder?token=...&days=1h|1d|3d&volume=...
    Возвращает поле 'summa' (TRX) либо None.
    """
    url = f"{API_BASE}/precountOrder"
    params = {"token": token, "days": days, "volume": volume}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout_ms/1000)
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                time.sleep(0.35 * attempt)
                continue
            data = resp.json()
            if isinstance(data, dict) and data.get("summa") is not None:
                try:
                    return r6(float(str(data["summa"]).replace(",", ".")))
                except Exception as e:
                    last_err = f"parse summa: {e}"
            else:
                last_err = f"no 'summa' in response: {data!r}"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.35 * attempt)
    logging.warning("precountOrder %s/%s failed: %s", days, volume, last_err)
    return None

def build_payload(p65_1h, p65_1d, p65_3d, p130_1h, p130_1d, p130_3d) -> dict:
    def v(x): return r6(x) if x is not None else NA
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "platform_id": "refee",
        "platform_name": "re:Fee",
        "url": f"{API_BASE}/",
        "chain": "TRON",
        "product_type": "energy_purchase",

        "minimum_order_energy": NA,
        "maximum_order_energy": NA,
        "platform_max_energy": NA,

        # 65k
        "65k_15m_price": NA,
        "65k_1h_price": v(p65_1h),
        "65k_1d_price": v(p65_1d),
        "65k_3d_price": v(p65_3d),
        "65k_10d_price": NA,

        # 130k_* — берём из реального 135k, чтобы совпасть с ботом
        "130k_15m_price": NA,
        "130k_1h_price": v(p130_1h),
        "130k_1d_price": v(p130_1d),
        "130k_3d_price": v(p130_3d),
        "130k_10d_price": NA,
    }

def validate_schema(obj: dict) -> None:
    for k in SCHEMA_KEYS:
        if k not in obj:
            raise SystemExit(f"Missing key: {k}")
    for k, val in obj.items():
        if k.endswith("_price") and val != NA:
            float(val)

def run(token: str, out_path: str):
    # 65k
    p65_1h = get_summa(token, "1h", VOL_65K)
    p65_1d = get_summa(token, "1d", VOL_65K)
    p65_3d = get_summa(token, "3d", VOL_65K)

    # "130k" — запрашиваем как 135k, чтобы совпасть с ботом
    p130_1h = get_summa(token, "1h", VOL_130K_EFFECTIVE)
    p130_1d = get_summa(token, "1d", VOL_130K_EFFECTIVE)
    p130_3d = get_summa(token, "3d", VOL_130K_EFFECTIVE)

    # Fallback: если 135k не вернулось — используем ×2 от 65k (лучше, чем пусто)
    if p130_1h is None and p65_1h is not None:
        p130_1h = r6(p65_1h * 2)
    if p130_1d is None and p65_1d is not None:
        p130_1d = r6(p65_1d * 2)
    if p130_3d is None and p65_3d is not None:
        p130_3d = r6(p65_3d * 2)

    payload = build_payload(p65_1h, p65_1d, p65_3d, p130_1h, p130_1d, p130_3d)
    validate_schema(payload)
    atomic_write_json(out_path, payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    logging.info("Wrote %s", out_path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", help="API token (не обязательно — вшит по умолчанию)")
    ap.add_argument("--out", default="refee_prices.json", help="куда писать JSON")
    ap.add_argument("--log", default="info", choices=["debug", "info", "warning", "error"])
    args = ap.parse_args()

    logging.basicConfig(level=getattr(logging, args.log.upper()),
                        format="%(asctime)s %(levelname)s %(message)s")

    token = args.token or os.getenv("REFEETOKEN") or TOKEN_DEFAULT
    run(token=token, out_path=args.out)

if __name__ == "__main__":
    main()
