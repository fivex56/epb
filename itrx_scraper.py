# itrx_prices_flat.py — iTRX → плоский JSON с ценами 65k/131k
# Требования: pip install requests

from __future__ import annotations
import sys, json, time, signal, logging, hmac, hashlib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import requests

# ====== Константы/API ======
BASES = [
    "https://itrx.io/api/v1/frontend",
    "https://api.itrx.io/api/v1/frontend",
]
OUTFILE_DEFAULT = "itrx_prices.json"

# Ключи из твоей конфы (захардкожены)
HARDCODED_API_KEY = os.environ.get("ITRX_API_KEY", "YOUR_KEY_HERE")
HARDCODED_API_SECRET = os.environ.get("ITRX_API_SECRET", "YOUR_SECRET_HERE")

# Планируемые периоды у iTRX
PERIODS = {"1H": 1/24, "1D": 1, "3D": 3, "30D": 30}
SUN = 1_000_000

# Объёмы (ключи 130k_* считаем для 131000 — классика; имя ключа оставляем, как просил)
AMOUNT_65K = 65_000
AMOUNT_131K = 131_000

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "User-Agent": "itrx-flat/1.1"})

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("itrx_flat")

@dataclass
class Config:
    api_key: str
    api_secret: str
    outfile: str = OUTFILE_DEFAULT
    hourly: bool = False
    once: bool = True
    verbose: bool = False

# ====== Вспомогательные ======
def _headers_with(api_key: str, header_name: str = "API-KEY", extra: dict | None = None) -> Dict[str, str]:
    base = {header_name: api_key}
    if extra:
        base.update(extra)
    return base

def _post_signature_headers(api_key: str, api_secret: str, json_payload_sorted: str) -> Dict[str, str]:
    ts = str(int(time.time()))
    sig = hmac.new(api_secret.encode(), f"{ts}&{json_payload_sorted}".encode(), hashlib.sha256).hexdigest()
    return {"API-KEY": api_key, "TIMESTAMP": ts, "SIGNATURE": sig, "Content-Type": "application/json"}

def _signed_get_headers(api_key: str, api_secret: str) -> Dict[str, str]:
    ts = str(int(time.time()))
    body = "{}"
    sig = hmac.new(api_secret.encode(), f"{ts}&{body}".encode(), hashlib.sha256).hexdigest()
    return {"API-KEY": api_key, "TIMESTAMP": ts, "SIGNATURE": sig}

def _log_preview(resp: requests.Response):
    try:
        preview = resp.text[:300]
    except Exception:
        preview = ""
    log.info("→ %s %s | %s", resp.request.method, resp.status_code, preview)

# ====== HTTP (с фолбэком) ======
def api_get(path: str, api_key: str, api_secret: str, params: Optional[dict] = None) -> dict:
    last_err = None
    for base in BASES:
        url = f"{base}/{path.lstrip('/')}"
        # (1) разные имена заголовка
        for key_hdr in ("API-KEY", "X-API-KEY", "API_KEY"):
            try:
                r = SESSION.get(url, params=params, headers=_headers_with(api_key, key_hdr), timeout=30)
                log.info("GET %s [%s] → %s", url, key_hdr, r.status_code)
                _log_preview(r)
                if r.status_code == 401:
                    last_err = requests.HTTPError(f"401 Unauthorized at {url}", response=r)
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
        # (2) подпись на GET (на всякий)
        try:
            hdrs = _headers_with(api_key, "API-KEY", _signed_get_headers(api_key, api_secret))
            r = SESSION.get(url, params=params, headers=hdrs, timeout=30)
            log.info("GET (signed) %s → %s", url, r.status_code)
            _log_preview(r)
            if r.status_code != 401:
                r.raise_for_status()
                return r.json()
        except Exception as e:
            last_err = e
    raise last_err or RuntimeError("api_get failed")

# ====== Бизнес-логика ======
def fetch_index_data(cfg: Config) -> dict:
    data = api_get("index-data", cfg.api_key, cfg.api_secret)
    log.info("index-data: avail=%s min=%s max=%s small_add=%s",
             data.get("platform_avail_energy"), data.get("minimum_order_energy"),
             data.get("maximum_order_energy"), data.get("small_addition"))
    return data

def fetch_price(cfg: Config, period: str, energy_amount: int) -> dict:
    params = {"period": period, "energy_amount": int(energy_amount)}
    return api_get("order/price", cfg.api_key, cfg.api_secret, params=params)

def infer_price_basis(price_sun: int, total_sun: int, addition_sun: int,
                      energy_amount: int, term_days: float) -> str:
    total_a = price_sun * energy_amount * term_days + addition_sun  # гипотеза per_day
    total_b = price_sun * energy_amount + addition_sun             # гипотеза per_period
    denom = max(1.0, float(total_sun))
    err_a = abs(total_a - total_sun) / denom
    err_b = abs(total_b - total_sun) / denom
    return "per_day" if err_a <= err_b else "per_period"

def normalized_daily_from_prices(cfg: Config) -> Dict[str, float]:
    """Вернёт TRX за 1M/сутки для периодов, которые реально есть у iTRX."""
    daily: Dict[str, float] = {}
    for label in ("1H", "1D", "3D", "30D"):
        pr = fetch_price(cfg, label, 1_000_000)  # удобнее всего запросить на 1M
        term_days = PERIODS[label]
        price_sun = int(pr.get("price", 0))
        total_sun = int(pr.get("total_price", 0))
        addition_sun = int(pr.get("addition", 0))
        basis = infer_price_basis(price_sun, total_sun, addition_sun, 1_000_000, term_days)
        if basis == "per_day":
            daily[label] = float(price_sun)                  # уже TRX/1M/сутки
        else:
            daily[label] = float(price_sun) / term_days      # приведём к TRX/1M/сутки
        log.info("[%s] unit=%s basis=%s → daily=%.6f TRX/1M/day", label, price_sun, basis, daily[label])
    return daily

def price_for(amount: int, wanted_label: str, daily: Dict[str, float]) -> Optional[float]:
    """Цена TRX для amount и нужного периода. Возвращает None, если такого периода нет.
       wanted_label ∈ {'1H','1D','3D'} — эти поддерживаются у iTRX.
    """
    if wanted_label not in daily:
        return None
    term_days = PERIODS[wanted_label]
    daily_price = daily[wanted_label]  # TRX/1M/сутки
    return round(daily_price * (amount / 1_000_000.0) * term_days, 6)

def build_flat_record(cfg: Config) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    idx = fetch_index_data(cfg)
    daily = normalized_daily_from_prices(cfg)

    # iTRX имеет: 1H, 1D, 3D, 30D
    p_65_1h = price_for(AMOUNT_65K, "1H", daily)
    p_65_1d = price_for(AMOUNT_65K, "1D", daily)
    p_65_3d = price_for(AMOUNT_65K, "3D", daily)
    p_65_30d = price_for(AMOUNT_65K, "30D", daily)

    p_131_1h = price_for(AMOUNT_131K, "1H", daily)
    p_131_1d = price_for(AMOUNT_131K, "1D", daily)
    p_131_3d = price_for(AMOUNT_131K, "3D", daily)
    p_131_30d = price_for(AMOUNT_131K, "30D", daily)

    NA = "N/A"

    # avail_energy — важная метрика для юзера
    avail = idx.get("platform_avail_energy")
    platform_max = idx.get("platform_max_energy") or avail

    rec = {
        "ts": ts,
        "platform_id": "itrx",
        "platform_name": "iTRX",
        "url": "https://itrx.io/",
        "chain": "TRON",
        "product_type": "energy_purchase",

        "minimum_order_energy": idx.get("minimum_order_energy"),
        "maximum_order_energy": idx.get("maximum_order_energy"),
        "platform_max_energy": int(platform_max) if isinstance(platform_max, (int, float)) else platform_max,
        "available_energy": int(avail) if isinstance(avail, (int, float)) else (avail or NA),

        # 65k:
        "65k_15m_price": NA,
        "65k_1h_price":   p_65_1h if p_65_1h is not None else NA,
        "65k_1d_price":   p_65_1d if p_65_1d is not None else NA,
        "65k_3d_price":   p_65_3d if p_65_3d is not None else NA,
        "65k_10d_price":  NA,
        "65k_30d_price":  p_65_30d if p_65_30d is not None else NA,

        # 130k (считаем для 131000):
        "130k_15m_price": NA,
        "130k_1h_price":  p_131_1h if p_131_1h is not None else NA,
        "130k_1d_price":  p_131_1d if p_131_1d is not None else NA,
        "130k_3d_price":  p_131_3d if p_131_3d is not None else NA,
        "130k_10d_price": NA,
        "130k_30d_price": p_131_30d if p_131_30d is not None else NA,
    }
    return rec

def write_record(rec: dict, outfile: str) -> None:
    # ПЕРЕЗАПИСЫВАЕМ файл каждый раз
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
        f.write("\n")
    log.info("Перезаписал %s (1 JSON-объект).", outfile)

# ====== CLI ======
def parse_args(argv: list[str]) -> Config:
    import argparse
    p = argparse.ArgumentParser(description="iTRX → плоский JSON с ценами 65k/131k (перезапись файла)")
    p.add_argument("--outfile", default=OUTFILE_DEFAULT)
    p.add_argument("--hourly", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--api-key", default=None)
    p.add_argument("--api-secret", default=None)
    args = p.parse_args(argv)
    if args.verbose:
        log.setLevel(logging.DEBUG)
    return Config(
        api_key=(args.api_key or HARDCODED_API_KEY),
        api_secret=(args.api_secret or HARDCODED_API_SECRET),
        outfile=args.outfile,
        hourly=args.hourly,
        once=args.once or (not args.hourly),
        verbose=args.verbose,
    )

def main(argv: list[str]) -> int:
    cfg = parse_args(argv)

    def handle_sigterm(*_):
        log.info("Завершение…")
        sys.exit(0)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_sigterm)

    if cfg.once:
        rec = build_flat_record(cfg)
        write_record(rec, cfg.outfile)
        return 0

    # hourly loop (перезаписывает файл раз в час)
    while True:
        try:
            rec = build_flat_record(cfg)
            write_record(rec, cfg.outfile)
        except Exception as e:
            log.exception("Ошибка цикла: %s", e)
        # Спим до начала следующего часа
        now = datetime.now()
        nxt = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        time.sleep(max(1, (nxt - now).total_seconds()))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
