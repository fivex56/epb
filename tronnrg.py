# tronnrg.py — TRONRG Rent Energy (quote/real) с дефолтами от пользователя
# - mode=quote (по умолчанию): POST /rentenergy, парсим cost даже при code:402 (нет баланса)
# - mode=real: реальный заказ
# - --hourly: повторять каждый час
# - пишет снапшоты в tronrg.json с разделителем

from __future__ import annotations
import json, re, sys, time, logging, argparse
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
import requests

API_URL = "https://tronrg.com/rentenergy"
HARDCODED_API_KEY = "ef3be753-74c7-4099-add4-aa88f25df43f"
OUTFILE_DEFAULT = "tronrg.json"

# Твои дефолты
DEFAULT_ADDRESS = "TVXzsEZATjdxfYMwtGuu1dJerVDcGnFiSh"
DEFAULT_AMOUNT = 131_000
DEFAULT_DURATION = 1  # час

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tronrg")

# ---------- validators ----------
def validate_tron_address(addr: str) -> None:
    if not addr or addr[0] != "T" or not (30 <= len(addr) <= 40):
        raise ValueError("Некорректный TRON адрес (TRC20, начинается на 'T').")

def validate_amount(amount: int) -> None:
    if not (32_000 <= amount <= 10_000_000):
        raise ValueError("amount должен быть 32000..10000000.")

def validate_duration(hours: int) -> None:
    if hours < 1:
        raise ValueError("duration >= 1 (сейчас поддерживается только 1 час).")

# ---------- helpers ----------
def write_snapshot(outfile: str, snapshot: Dict[str, Any]) -> None:
    with open(outfile, "a", encoding="utf-8") as f:
        f.write(f"----- {snapshot['ts']} -----\n")
        f.write(json.dumps(snapshot, ensure_ascii=False))
        f.write("\n")
    log.info("Снапшот записан в %s", outfile)

def extract_cost(resp: Dict[str, Any]) -> Optional[float]:
    """
    Стоимость может лежать в разных местах/типах:
      resp['data']['cost']  -> number | "4.45" | "4,45 TRX"
      resp['data']['amount'] -> иногда так называют цену
      resp['message'] -> может содержать 'Amount: 4.45 TRX'
    """
    cand = None
    data = resp.get("data", {})
    if isinstance(data, dict):
        cand = data.get("cost", data.get("amount"))
        if cand is None:
            for k, v in data.items():
                if any(x in k.lower() for x in ("cost", "amount", "price")):
                    cand = v
                    break
    if cand is None:
        msg = str(resp.get("message", ""))
        m = re.search(r"Amount:\s*([0-9]+[.,]?[0-9]*)\s*TRX", msg, re.I)
        if m:
            cand = m.group(1)

    if cand is None:
        return None
    if isinstance(cand, str):
        s = cand.lower().replace("trx", "").strip()
        s = s.replace(" ", "").replace(",", ".")
        m = re.search(r"[-+]?\d+(\.\d+)?", s)
        if not m:
            return None
        return float(m.group(0))
    try:
        return float(cand)
    except Exception:
        return None

def derive_metrics(cost_trx: Optional[float], amount: int, duration_h: int) -> Dict[str, Any]:
    if cost_trx is None:
        return {}
    per_1m_per_hour = cost_trx * (1_000_000 / float(amount))
    per_1m_per_day = per_1m_per_hour * 24 / max(1, duration_h)
    return {
        "cost_trx": round(cost_trx, 6),
        "price_per_1M_energy_per_hour": round(per_1m_per_hour, 6),
        "price_per_1M_energy_per_day": round(per_1m_per_day, 6),
    }

def sleep_until_next_hour():
    now = datetime.now()
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    secs = (next_hour - now).total_seconds()
    log.info("Жду до начала следующего часа: %.0f сек", secs)
    time.sleep(max(1, secs))

# ---------- API ----------
def post_rent(api_key: str, address: str, amount: int, duration: int) -> Dict[str, Any]:
    payload = {"apikey": api_key, "address": address, "duration": duration, "amount": amount}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "tronrg-client/1.2"}
    log.info("POST %s | address=%s amount=%s duration=%sh", API_URL, address, amount, duration)
    r = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=45)
    preview = r.text[:400]
    log.info("→ %s %s | %s", r.request.method, r.status_code, preview)
    try:
        resp = r.json()
    except Exception:
        resp = {"raw": preview}
    return resp  # HTTP 200 приходит и для code:402 — это ок для котировки

# ---------- CLI ----------
@dataclass
class Config:
    api_key: str
    address: str
    amount: int
    duration: int
    outfile: str
    mode: str  # "quote" | "real"
    hourly: bool
    verbose: bool

def parse_args() -> Config:
    p = argparse.ArgumentParser(description="TRONRG Rent Energy (quote or real order)")
    p.add_argument("--address", default=DEFAULT_ADDRESS, help="TRC20 адрес (по умолчанию задан)")
    p.add_argument("--amount", type=int, default=DEFAULT_AMOUNT, help="объем энергии (по умолчанию задан)")
    p.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="часы аренды (по умолчанию 1)")
    p.add_argument("--outfile", default=OUTFILE_DEFAULT, help="файл снапшотов (tronrg.json)")
    p.add_argument("--mode", choices=["quote", "real"], default="quote", help="quote=котировка, real=покупка")
    p.add_argument("--hourly", action="store_true", help="повторять запрос каждый час")
    p.add_argument("--api-key", default=None, help="API key (иначе захардкоженный)")
    p.add_argument("--verbose", action="store_true", help="подробные логи")
    args = p.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    validate_tron_address(args.address)
    validate_amount(args.amount)
    validate_duration(args.duration)

    return Config(
        api_key=args.api_key or HARDCODED_API_KEY,
        address=args.address,
        amount=args.amount,
        duration=args.duration,
        outfile=args.outfile,
        mode=args.mode,
        hourly=args.hourly,
        verbose=args.verbose,
    )

def run_once(cfg: Config) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    resp = post_rent(cfg.api_key, cfg.address, cfg.amount, cfg.duration)
    cost = extract_cost(resp)
    metrics = derive_metrics(cost, cfg.amount, cfg.duration)

    if cost is not None:
        log.info("Котировка: cost=%.6f TRX | норм.: %.6f TRX/1M/сутки",
                 cost, metrics.get("price_per_1M_energy_per_day", 0.0))
    else:
        log.warning("Стоимость не найдена в ответе. Полный JSON будет в файле.")

    snapshot = {
        "ts": ts,
        "platform_id": "tronrg",
        "platform_name": "TRONRG",
        "url": "https://tronrg.com",
        "chain": "TRON",
        "product_type": "energy_purchase",
        "asset": "TRX",
        "request": {
            "address": cfg.address,
            "duration_h": cfg.duration,
            "amount_energy": cfg.amount,
            "mode": cfg.mode,
        },
        "response": resp,
        "derived": metrics,
        "data_source": "api",
    }
    write_snapshot(cfg.outfile, snapshot)

    if cfg.mode == "real" and str(resp.get("code")) != "200":
        log.warning("Реальный заказ не прошёл: code=%s message=%s",
                    resp.get("code"), resp.get("message"))

def main() -> int:
    cfg = parse_args()
    if not cfg.hourly:
        run_once(cfg)
        return 0
    # hourly loop
    while True:
        try:
            run_once(cfg)
        except Exception as e:
            log.exception("Ошибка запроса/записи: %s", e)
        sleep_until_next_hour()

if __name__ == "__main__":
    sys.exit(main())
