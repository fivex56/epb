# feee_prices.py
# pip install requests
# python feee_prices.py
import os, json, time, math, argparse, tempfile, logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import requests

BASE_URL = "https://feee.io/open"
PRICE_EP = "/v2/order/price"
TIMEOUT = 45
UA = "feee-flat/1.0 (+https://feee.io)"

# Жёстко заданные сроки и секунды
TERMS_SEC = {
    "15m": None,
    "1h":  60 * 60,
    "1d":  24 * 60 * 60,
    "3d":  3 * 24 * 60 * 60,
    "10d": 10 * 24 * 60 * 60,
}

VOLUMES = {
    "65k": 65000,
    "130k": 131000,  # исторически "130k", считаем 131k
}

# Встроенный API ключ
API_KEY = "fa51483c-867b-4551-97c7-2b0f6bee15f7"

def round6(x: float) -> float:
    return round(float(x), 6)

def derive_unit_and_duration(seconds: int) -> tuple[str, int]:
    """Подставим rent_time_unit/rent_duration согласованные с seconds.
    Важно: по доке, если указан валидный rent_time_second, unit/duration игнорируются,
    но мы их всё равно заполняем корректно. :contentReference[oaicite:1]{index=1}
    """
    if seconds % 86400 == 0:
        return "d", seconds // 86400
    if seconds % 3600 == 0:
        return "h", seconds // 3600
    return "m", seconds // 60

def get_price_trx(sess: requests.Session, api_key: str, energy: int, seconds: int) -> Optional[float]:
    """Запрашиваем цену. Возвращаем pay_amount (TRX) или None."""
    unit, duration = derive_unit_and_duration(seconds)
    params = {
        "resource_value": energy,
        "rent_time_unit": unit,         # 'd' | 'h' | 'm' (GET) :contentReference[oaicite:2]{index=2}
        "rent_duration": duration,      # если rent_time_second валиден — эти поля будут проигнорированы
        "rent_time_second": seconds,    # >600 и кратно 3 — наши сроки подходят :contentReference[oaicite:3]{index=3}
    }
    url = f"{BASE_URL}{PRICE_EP}"
    try:
        r = sess.get(url, params=params, timeout=TIMEOUT)
        logging.info("GET %s?%s -> %s; body[:300]=%r", url, r.request.url.split("?")[1] if r.request.url else "", r.status_code, r.text[:300])
    except requests.RequestException as e:
        logging.warning("HTTP error: %s", e)
        return None

    # Пытаемся разобрать JSON даже при 4xx/5xx
    try:
        data = r.json()
    except Exception:
        return None

    # Успех по коду 0, тогда берём data.pay_amount как TRX
    # (документация для /v2/order/price). :contentReference[oaicite:4]{index=4}
    if isinstance(data, dict) and data.get("code") == 0:
        payload = data.get("data") or {}
        pay_amount = payload.get("pay_amount")
        if isinstance(pay_amount, (int, float)) and math.isfinite(pay_amount):
            return round6(pay_amount)
    return None

def atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".feee_", dir=os.path.dirname(path) or ".", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)

def build_flat(sess: requests.Session, api_key: str) -> Dict[str, Any]:
    # Рейт-лимит: не чаще ~3–5 qps (ограничения 5–10 qps в доке) — поставим небольшую паузу. :contentReference[oaicite:5]{index=5}
    pause = 0.25

    prices: Dict[str, Any] = {}
    for vol_key, E in VOLUMES.items():
        for term_key, sec in TERMS_SEC.items():
            if sec is None:
                prices[f"{vol_key}_{term_key}_price"] = "N/A"
                continue
            val = get_price_trx(sess, api_key, E, sec)
            prices[f"{vol_key}_{term_key}_price"] = val if isinstance(val, (int, float)) else "N/A"
            time.sleep(pause)


    obj = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "platform_id": "feee",
        "platform_name": "Feee.io",
        "url": "https://feee.io/",
        "chain": "TRON",
        "product_type": "energy_purchase",

        # Лимиты платформа не публикует в общедоступной части — ставим "N/A".
        "minimum_order_energy": "N/A",
        "maximum_order_energy": "N/A",
        "platform_max_energy": "N/A",

        "65k_15m_price": prices["65k_15m_price"],
        "65k_1h_price":  prices["65k_1h_price"],
        "65k_1d_price":  prices["65k_1d_price"],
        "65k_3d_price":  prices["65k_3d_price"],
        "65k_10d_price": prices["65k_10d_price"],

        "130k_15m_price": prices["130k_15m_price"],
        "130k_1h_price":  prices["130k_1h_price"],
        "130k_1d_price":  prices["130k_1d_price"],
        "130k_3d_price":  prices["130k_3d_price"],
        "130k_10d_price": prices["130k_10d_price"],
    }
    return obj

def validate(obj: Dict[str, Any]) -> None:
    required = [
        "ts","platform_id","platform_name","url","chain","product_type",
        "minimum_order_energy","maximum_order_energy","platform_max_energy",
        "65k_15m_price","65k_1h_price","65k_1d_price","65k_3d_price","65k_10d_price",
        "130k_15m_price","130k_1h_price","130k_1d_price","130k_3d_price","130k_10d_price",
    ]
    for k in required:
        if k not in obj:
            raise SystemExit(f"Missing key: {k}")

    # строки-идентификаторы
    for k in ["ts","platform_id","platform_name","url","chain","product_type"]:
        if not isinstance(obj[k], str):
            raise SystemExit(f"Bad value for {k}: {obj[k]!r}")

    # остальное: число или "N/A"
    import math
    def is_num(x): return isinstance(x, (int, float)) and math.isfinite(float(x))
    for k in set(required) - {"ts","platform_id","platform_name","url","chain","product_type"}:
        v = obj[k]
        if not (is_num(v) or v == "N/A"):
            raise SystemExit(f"Bad value for {k}: {v!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=".", help="куда писать feee_prices.json")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sess = requests.Session()
    sess.headers.update({
        "key": API_KEY,                 # заголовок с встроенным ключом API
        "User-Agent": UA,               # может быть в вайтлисте UA :contentReference[oaicite:7]{index=7}
        "Accept": "application/json",
    })

    flat = build_flat(sess, API_KEY)
    validate(flat)
    out_path = os.path.join(args.out_dir, "feee_prices.json")
    atomic_write_json(out_path, flat)
    print(json.dumps(flat, ensure_ascii=False, indent=2))
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()