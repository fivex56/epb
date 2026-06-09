#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EnergyFather via API (1 hour + 1 day)
# 65k_* = чистая цена заказа (order_cost - energy_delegation_fee - address_activation_fee)
# 130k_* = 2 × 65k_*
import argparse, json, math, os, tempfile, logging, urllib.request, urllib.error
from datetime import datetime, timezone

BASE  = "https://panel.energyfather.com/api/v1/private"
TOKEN = "54WOUTDTh4G3c5w0ykX1bEGSzcV9xuPd"   # вшит по запросу
NA = "N/A"

log = logging.getLogger("energyfather_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def r6(x: float) -> float: return round(float(x), 6)
def isnum(x) -> bool:
    try: return isinstance(x,(int,float)) and math.isfinite(float(x))
    except Exception: return False

def atomic_write_json(path: str, obj: dict):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".energyfather_", dir=os.path.dirname(path) or ".", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False); f.write("\n")
    os.replace(tmp, path)

def _post(path: str, payload: dict, timeout_ms: int) -> dict | None:
    url = f"{BASE}/{path.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Token", TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=timeout_ms/1000.0) as resp:
            txt = resp.read().decode("utf-8", errors="replace")
            return json.loads(txt)
    except urllib.error.HTTPError as e:
        log.error("HTTP %s %s: %s", e.code, url, e.read().decode("utf-8", errors="replace"))
    except Exception as e:
        log.error("POST %s failed: %s", url, e)
    return None

def _to_float(x, default=0.0):
    try:
        if x is None: return default
        return float(str(x).replace(",", "."))
    except Exception:
        return default

def get_65k_price(period_type: str, period_amount: int, timeout_ms: int) -> float | None:
    """Возвращает чистую цену TRX для 65k энергии на запрошенный период."""
    payload = {
        "format": "json",
        "to": "TQHAAJWLLEjBgYq2sjUnq4kbKfajEXEvyE",  # из доки
        "amount_source": "amount",
        "amount": 65000,
        "period_type": period_type,       # "hours" | "days"
        "period_amount": period_amount    # 1
    }
    resp = _post("buy/energy", payload, timeout_ms)
    if not resp: return None
    data = resp.get("data") or {}
    order_cost = _to_float(data.get("order_cost"))
    fee_energy = _to_float(data.get("energy_delegation_fee"))
    fee_addr   = _to_float(data.get("address_activation_fee"))
    base_cost  = max(0.0, order_cost - fee_energy - fee_addr)
    if base_cost == 0.0:
        base_cost = max(0.0, _to_float(data.get("order_cost_paid")) - fee_energy - fee_addr)
    log.debug("period=%s %s -> order_cost=%s, fees=%s/%s, base=%s, status=%s, guid=%s",
              period_amount, period_type, order_cost, fee_energy, fee_addr, base_cost,
              data.get("status"), data.get("guid"))
    return r6(base_cost) if base_cost > 0 else None

def build_payload(p65_1h, p65_1d) -> dict:
    v = lambda x: r6(x) if isnum(x) else NA
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "platform_id": "energyfather",
        "platform_name": "EnergyFather",
        "url": "https://energyfather.com/",
        "chain": "TRON",
        "product_type": "energy_purchase",

        "minimum_order_energy": NA,
        "maximum_order_energy": NA,
        "platform_max_energy": NA,

        "65k_15m_price": NA,
        "65k_1h_price": v(p65_1h),
        "65k_1d_price": v(p65_1d),
        "65k_3d_price": NA,
        "65k_10d_price": NA,

        "130k_15m_price": NA,
        "130k_1h_price": v(p65_1h * 2) if isnum(p65_1h) else NA,
        "130k_1d_price": v(p65_1d * 2) if isnum(p65_1d) else NA,
        "130k_3d_price": NA,
        "130k_10d_price": NA,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="energyfather_prices.json")
    ap.add_argument("--timeout", type=int, default=15000)
    ap.add_argument("--log", default="info", choices=["debug","info","warning","error"])
    args = ap.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log.upper()))

    p65_1h = get_65k_price("hours", 1, args.timeout)
    p65_1d = get_65k_price("days",  1, args.timeout)

    obj = build_payload(p65_1h, p65_1d)
    atomic_write_json(args.out, obj)
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    log.info("Wrote %s", args.out)

if __name__ == "__main__":
    main()
