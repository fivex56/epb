# trenergy_prices_flat.py — TR Energy → плоский JSON с ценами 65k/131k
# Требования: pip install requests

from __future__ import annotations
import sys, json, signal, logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import requests

API_URL = "https://core.tr.energy/api/config"
OUTFILE_DEFAULT = "trenergy_prices.json"

# объёмы (ключи "130k_*" считаем для 131000 — как в предыдущей программе)
AMOUNT_65K = 65_150
AMOUNT_131K = 131_000

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("trenergy_flat")

@dataclass
class Config:
    outfile: str = OUTFILE_DEFAULT
    hourly: bool = False
    once: bool = True
    verbose: bool = False

def parse_args(argv: list[str]) -> Config:
    import argparse
    p = argparse.ArgumentParser(description="TR Energy → плоский JSON с ценами 65k/131k (перезапись файла)")
    p.add_argument("--outfile", default=OUTFILE_DEFAULT)
    p.add_argument("--hourly", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)
    if args.verbose:
        log.setLevel(logging.DEBUG)
    return Config(
        outfile=args.outfile,
        hourly=args.hourly,
        once=args.once or (not args.hourly),
        verbose=args.verbose,
    )

def fetch_config() -> dict:
    r = requests.get(API_URL, timeout=30, headers={"Accept": "application/json", "User-Agent": "trenergy-flat/1.0"})
    log.info("GET %s → %s", API_URL, r.status_code)
    try:
        data = r.json()
    except Exception:
        raise SystemExit(f"Не удалось распарсить JSON: {r.text[:300]}")
    if not data or not data.get("status") or "data" not in data:
        raise SystemExit(f"Неожиданный ответ: {data}")
    return data["data"]

def calc_price(rate: Optional[float], amount: int) -> Optional[float]:
    """TRX за amount энергии при данной ставке (TRX за 1 energy за период)."""
    if rate is None:
        return None
    try:
        return round(float(rate) * float(amount), 6)
    except Exception:
        return None

def build_record() -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    cfg = fetch_config()

    # ставки по периодам в минутах
    prices = cfg.get("energy_prices", {}) or {}
    r_15   = prices.get("15")      # 15 минут
    r_60   = prices.get("60")      # 1 час
    r_1440 = prices.get("1440")    # 1 день
    # r_480 = prices.get("480")    # 8 часов (нам не нужен для выходных полей)

    # считаем TRX (если ставки нет — вернём None и потом заменим на "N/A")
    p_65_15 = calc_price(r_15,   AMOUNT_65K)
    p_65_1h = calc_price(r_60,   AMOUNT_65K)
    p_65_1d = calc_price(r_1440, AMOUNT_65K)

    p_131_15 = calc_price(r_15,   AMOUNT_131K)
    p_131_1h = calc_price(r_60,   AMOUNT_131K)
    p_131_1d = calc_price(r_1440, AMOUNT_131K)

    NA = "N/A"

    rec = {
        "ts": ts,
        "platform_id": "tr_energy",
        "platform_name": "TR Energy",
        "url": "https://tr.energy/",
        "chain": "TRON",
        "product_type": "energy_purchase",

        # у API нет публичных лимитов заказа — ставим "N/A"
        "minimum_order_energy": NA,
        "maximum_order_energy": NA,
        "platform_max_energy": NA,

        # 65k:
        "65k_15m_price": p_65_15 if p_65_15 is not None else NA,
        "65k_1h_price":  p_65_1h if p_65_1h is not None else NA,
        "65k_1d_price":  p_65_1d if p_65_1d is not None else NA,
        "65k_3d_price":  NA,  # отсутствует в конфиге
        "65k_10d_price": NA,  # отсутствует в конфиге

        # 130k (считаем для 131000)
        "130k_15m_price": p_131_15 if p_131_15 is not None else NA,
        "130k_1h_price":  p_131_1h if p_131_1h is not None else NA,
        "130k_1d_price":  p_131_1d if p_131_1d is not None else NA,
        "130k_3d_price":  NA,
        "130k_10d_price": NA,
    }
    return rec

def write_record(rec: dict, outfile: str) -> None:
    # перезаписываем файл
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
        f.write("\n")
    log.info("Перезаписал %s (1 JSON-объект).", outfile)

def sleep_until_next_hour():
    now = datetime.now()
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    secs = max(1, int((next_hour - now).total_seconds()))
    log.info("Жду до начала следующего часа: %s сек", secs)
    signal.pause() if hasattr(signal, "pause") else time.sleep(secs)

def main(argv: list[str]) -> int:
    cfg = parse_args(argv)

    def handle_sigterm(*_):
        log.info("Завершение…")
        sys.exit(0)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_sigterm)

    if cfg.once:
        rec = build_record()
        write_record(rec, cfg.outfile)
        return 0

    # hourly loop
    while True:
        try:
            rec = build_record()
            write_record(rec, cfg.outfile)
        except Exception as e:
            log.exception("Ошибка цикла: %s", e)
        # ждём до следующего часа
        now = datetime.now()
        nxt = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        secs = max(1, int((nxt - now).total_seconds()))
        try:
            signal.signal(signal.SIGALRM, lambda *_: None)  # для Unix можно было бы будильник, но упростим
        except Exception:
            pass
        import time
        time.sleep(secs)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
