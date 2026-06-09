# aggregate.py
# Python 3.9+
# Читает *_prices.json, валидирует и собирает в result.json (без запуска скриптов)

import os, sys, json, math, tempfile, argparse
from glob import glob
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

# Минимальный набор обязательных полей (мета-данные)
REQUIRED_META_KEYS = {
    "ts", "platform_id", "platform_name", "url", "chain", "product_type",
    "minimum_order_energy", "maximum_order_energy", "platform_max_energy",
}

def is_num(x) -> bool:
    try:
        return isinstance(x,(int,float)) and math.isfinite(float(x))
    except Exception:
        return False

def validate_flat(obj: Dict[str, Any]) -> Tuple[bool, str]:
    """Динамическая валидация: обязательные мета-поля + все _price ключи."""
    # Обязательные мета-ключи
    for k in REQUIRED_META_KEYS:
        if k not in obj:
            return False, f"missing {k}"
    # Строковые идентификаторы
    for k in ["ts", "platform_id", "platform_name", "url", "chain", "product_type"]:
        if not isinstance(obj.get(k), str):
            return False, f"bad string field {k}={obj.get(k)!r}"
    # Все _price ключи динамически: должны быть числом или "N/A"
    for k, v in obj.items():
        if k.endswith("_price"):
            if not (is_num(v) or v == "N/A"):
                return False, f"bad value {k}={v!r}"
    # Лимитные поля (если есть) — число или "N/A"
    for k in ["minimum_order_energy", "maximum_order_energy", "platform_max_energy",
              "available_energy"]:
        v = obj.get(k)
        if v is not None and not (is_num(v) or v == "N/A"):
            return False, f"bad value {k}={v!r}"
    return True, "ok"

def detect_terms_and_volumes(platforms: List[Dict]) -> Tuple[List[str], Dict[str, int]]:
    """Авто-определение доступных terms и volumes из данных."""
    terms = set()
    volumes = {}
    for p in platforms:
        for k in p:
            if k.endswith("_price"):
                # "65k_1h_price" → amount="65k", term="1h"
                parts = k.replace("_price", "").rsplit("_", 1)
                if len(parts) == 2:
                    amount_key, term_key = parts
                    terms.add(term_key)
                    # Определяем числовое значение объёма
                    if amount_key not in volumes:
                        amt = amount_key.lower().replace("k", "000").replace("m", "000000")
                        try:
                            if "m" in amount_key.lower():
                                volumes[amount_key] = int(float(amount_key.lower().replace("m","")) * 1_000_000)
                            else:
                                volumes[amount_key] = int(float(amount_key.lower().replace("k","")) * 1000)
                        except ValueError:
                            volumes[amount_key] = 0
    return sorted(terms), volumes

def parse_iso(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts.replace("Z","+00:00")).timestamp()
    except Exception:
        return 0.0

def atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".result_", dir=os.path.dirname(path) or ".", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)

def collect_inputs(in_dir: str, only_listed: bool, files_list: List[str]):
    errors: List[Dict[str, Any]] = []
    items:  List[Dict[str, Any]] = []

    if only_listed:
        candidates = [os.path.join(in_dir, fn) for fn in files_list]
    else:
        candidates = sorted(glob(os.path.join(in_dir, "*_prices.json")))

    for fp in candidates:
        if not os.path.exists(fp):
            errors.append({"file": fp, "error": "not found"})
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                obj = json.load(f)
        except Exception as e:
            errors.append({"file": fp, "error": f"json_load: {e}"})
            continue
        ok, why = validate_flat(obj)
        if not ok:
            errors.append({"file": fp, "platform_id": obj.get("platform_id"), "error": why})
            continue
        obj["__source_file"] = os.path.basename(fp)
        items.append(obj)

    # дедуп по platform_id → оставляем запись с самым новым ts
    best: Dict[str, Dict[str, Any]] = {}
    for obj in items:
        pid = obj["platform_id"]
        if pid not in best or parse_iso(obj["ts"]) > parse_iso(best[pid]["ts"]):
            best[pid] = obj

    return list(best.values()), errors

def load_referrals(in_dir: str) -> Dict[str, str]:
    """Загружает реферальные ссылки из referrals.json если есть."""
    ref_path = os.path.join(in_dir, "referrals.json")
    if os.path.exists(ref_path):
        try:
            with open(ref_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default=".", help="папка с *_prices.json")
    ap.add_argument("--out", default="result.json", help="куда писать итог")
    ap.add_argument("--only-listed", action="store_true",
                    help="брать только перечисленные в --files (через запятую)")
    ap.add_argument("--files", default="",
                    help="список файлов через запятую (пример: catfee_prices.json,feee_prices.json)")
    args = ap.parse_args()

    files_list = [s.strip() for s in args.files.split(",") if s.strip()]
    platforms, errors = collect_inputs(args.in_dir, args.only_listed, files_list)

    # Подмешиваем реферальные ссылки
    referrals = load_referrals(args.in_dir)
    for p in platforms:
        pid = p.get("platform_id", "")
        ref_url = referrals.get(pid, "")
        p["referral_url"] = ref_url
        p["has_referral"] = bool(ref_url)

    dynamic_terms, dynamic_volumes = detect_terms_and_volumes(platforms)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(platforms),
        "platforms": sorted(platforms, key=lambda x: x["platform_id"]),
        "errors": errors,
        "meta": {"terms": dynamic_terms, "volumes": dynamic_volumes},
    }

    atomic_write_json(args.out, result)
    print(f"[done] platforms={len(platforms)}, errors={len(errors)} -> {args.out}")

if __name__ == "__main__":
    main()