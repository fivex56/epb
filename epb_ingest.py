# epb_ingest.py
# Python 3.11+
# Инжест *_prices.json -> SQLite (epb.db) + Rollup JSON для фронта (history_7d.json, history_30d.json, service_history/*)
#
# Запуск (цикл 15 мин):
#   python epb_ingest.py
# Однократно:
#   python epb_ingest.py --once
#
# Ключевые опции:
#   --db epb.db
#   --interval 900                 # шаг цикла, сек (по умолчанию 900 = 15 мин)
#   --fresh-within 45              # включать в агрегаты только сервисы, чьи данные свежее Х минут
#   --rollup-7d history_7d.json
#   --rollup-30d history_30d.json
#   --make-service-history         # формировать service_history/<slug>_30d.json (по умолчанию включено)
#   --no-service-history           # отключить формирование серв. файлов
#   --log info|debug

from __future__ import annotations
import argparse, json, os, sqlite3, sys, time, math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


HERE = Path(__file__).resolve().parent

PRICE_TERMS = ["15m","1h","1d","3d","10d"]
AMOUNT_LABELS = [("65k", 65000), ("130k", 131000)]  # 130k ключ → 131000 по ТЗ
PRICE_KEYS = [f"{a}_{t}_price" for a,_ in AMOUNT_LABELS for t in PRICE_TERMS]

def log(level: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} | {level.upper():5} | {msg}", flush=True)

def iso_to_epoch_ms(s: str | None) -> int | None:
    if not s: return None
    try:
        if s.endswith("Z"): s = s[:-1] + "+00:00"
        return int(datetime.fromisoformat(s).timestamp() * 1000)
    except Exception:
        return None

def epoch_ms_now() -> int:
    return int(time.time() * 1000)

def round_to_bucket_ms(ms: int, step_min: int) -> int:
    step = step_min * 60 * 1000
    return ms - (ms % step)

def atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    # добавим перевод строки в конце
    with tmp.open("a", encoding="utf-8") as f:
        f.write("\n")
    tmp.replace(path)

# --------------------------- БД ---------------------------

def open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    migrate(conn)
    return conn

def migrate(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY,
        slug TEXT NOT NULL UNIQUE,
        name TEXT,
        url TEXT,
        chain TEXT,
        product_type TEXT,
        last_seen_ts INTEGER
    ) STRICT;
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY,
        key TEXT NOT NULL UNIQUE,
        amount INTEGER,
        term TEXT
    ) STRICT;
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS points (
        ts INTEGER NOT NULL,            -- время снапшота (кратное 15 мин)
        service_id INTEGER NOT NULL,
        metric_id INTEGER NOT NULL,
        value REAL,                     -- NULL, если "N/A"
        PRIMARY KEY (ts, service_id, metric_id),
        FOREIGN KEY(service_id) REFERENCES services(id),
        FOREIGN KEY(metric_id) REFERENCES metrics(id)
    ) STRICT;
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_points_metric_ts ON points(metric_id, ts);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_points_service_ts ON points(service_id, ts);")

    # предзаполним metrics всеми ключами, чтобы были стабильные id
    for a_lbl, amount in AMOUNT_LABELS:
        for term in PRICE_TERMS:
            key = f"{a_lbl}_{term}_price"
            conn.execute("""
                INSERT INTO metrics(key, amount, term)
                VALUES(?,?,?)
                ON CONFLICT(key) DO NOTHING;
            """, (key, amount, term))

def ensure_service(conn: sqlite3.Connection, slug: str, name: str | None, url: str | None,
                   chain: str | None, product_type: str | None, last_seen_ts: int | None) -> int:
    conn.execute("""
        INSERT INTO services(slug, name, url, chain, product_type, last_seen_ts)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(slug) DO UPDATE SET
            name=excluded.name,
            url=excluded.url,
            chain=excluded.chain,
            product_type=excluded.product_type,
            last_seen_ts=COALESCE(excluded.last_seen_ts, services.last_seen_ts);
    """, (slug, name, url, chain, product_type, last_seen_ts))
    cur = conn.execute("SELECT id FROM services WHERE slug=?", (slug,))
    return cur.fetchone()[0]

def metric_id(conn: sqlite3.Connection, key: str) -> int:
    cur = conn.execute("SELECT id FROM metrics WHERE key=?", (key,))
    row = cur.fetchone()
    if row: return row[0]
    # если внезапно добавят новый ключ — аккуратно создадим
    amount = None; term = None
    for a_lbl, a_val in AMOUNT_LABELS:
        for t in PRICE_TERMS:
            if key == f"{a_lbl}_{t}_price":
                amount, term = a_val, t
    conn.execute("INSERT INTO metrics(key, amount, term) VALUES(?,?,?)", (key, amount, term))
    cur = conn.execute("SELECT id FROM metrics WHERE key=?", (key,))
    return cur.fetchone()[0]

def parse_price_value(v):
    if v is None: return None
    if isinstance(v, (int, float)):
        try:
            val = float(v)
            if math.isfinite(val): return val
            return None
        except Exception:
            return None
    if isinstance(v, str):
        return None if v.strip().upper() == "N/A" else None
    return None

# --------------------------- Ingest ---------------------------

def ingest_once(conn: sqlite3.Connection, folder: Path, sample_step_min: int = 15) -> Tuple[int,int]:
    """
    Возвращает: (вставлено_точек, снимок_ts)
    """
    snap_ts = round_to_bucket_ms(epoch_ms_now(), sample_step_min)
    files = sorted(folder.glob("*_prices.json"))
    if not files:
        log("warning", "Не найдено *_prices.json")
        return 0, snap_ts

    inserted = 0
    affected_services = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            log("warning", f"Ошибка чтения {f.name}: {e}")
            continue

        slug = str(data.get("platform_id") or f.stem.replace("_prices",""))
        name = data.get("platform_name")
        url = data.get("url")
        chain = data.get("chain")
        product_type = data.get("product_type")
        svc_ts = iso_to_epoch_ms(data.get("ts"))

        sid = ensure_service(conn, slug, name, url, chain, product_type, svc_ts)
        affected_services += 1

        for key in PRICE_KEYS:
            mid = metric_id(conn, key)
            val = parse_price_value(data.get(key))
            conn.execute("""
                INSERT INTO points(ts, service_id, metric_id, value)
                VALUES(?,?,?,?)
                ON CONFLICT(ts, service_id, metric_id)
                DO UPDATE SET value=excluded.value;
            """, (snap_ts, sid, mid, val))
            inserted += 1

    log("info", f"Снапшот @ {datetime.fromtimestamp(snap_ts/1000, tz=timezone.utc).isoformat()} -> записано {inserted} точек, сервисов: {affected_services}")
    return inserted, snap_ts

# --------------------------- Rollup ---------------------------

def fetch_services(conn: sqlite3.Connection) -> Dict[int, Dict[str, Any]]:
    d = {}
    for row in conn.execute("SELECT id, slug, name, url, last_seen_ts FROM services"):
        d[row[0]] = {"slug": row[1], "name": row[2], "url": row[3], "last_seen_ts": row[4]}
    return d

def fetch_metrics(conn: sqlite3.Connection) -> Dict[int, Dict[str, Any]]:
    d = {}
    for row in conn.execute("SELECT id, key, amount, term FROM metrics"):
        d[row[0]] = {"key": row[1], "amount": row[2], "term": row[3]}
    return d

def select_points(conn: sqlite3.Connection, metric_id: int, t_from: int, t_to: int) -> List[Tuple[int,int,Optional[float]]]:
    cur = conn.execute("""
        SELECT ts, service_id, value
        FROM points
        WHERE metric_id=? AND ts BETWEEN ? AND ?
        ORDER BY ts ASC
    """, (metric_id, t_from, t_to))
    return list(cur.fetchall())

def median(xs: List[float]) -> Optional[float]:
    if not xs: return None
    xs_sorted = sorted(xs)
    n = len(xs_sorted)
    mid = n // 2
    if n % 2 == 1:
        return xs_sorted[mid]
    else:
        return (xs_sorted[mid-1] + xs_sorted[mid]) / 2

def downsample_to_hour(buckets_15m: List[Tuple[int,float]]) -> List[Tuple[int,float]]:
    """Схлопывает 4 подряд 15-мин точки в 1 часовую (среднее по доступным)."""
    if not buckets_15m: return []
    out: List[Tuple[int,float]] = []
    H = 60 * 60 * 1000
    g: Dict[int, List[float]] = {}
    for ts, v in buckets_15m:
        hour_ts = ts - (ts % H)
        g.setdefault(hour_ts, []).append(v)
    for ts in sorted(g.keys()):
        vals = [x for x in g[ts] if x is not None]
        if vals:
            out.append((ts, sum(vals)/len(vals)))
    return out

def rollup_window(conn: sqlite3.Connection,
                  out_path: Path,
                  window_days: int,
                  step_min: int,
                  fresh_within_min: int,
                  also_service_history: bool,
                  service_history_dir: Path,
                  downsample_to_hour_for_30d: bool = False) -> None:
    now_ms = epoch_ms_now()
    start_ms = now_ms - window_days * 24 * 60 * 60 * 1000
    services = fetch_services(conn)
    metrics = fetch_metrics(conn)

    # Список всех сервисов (slug) в метаданных
    all_slugs = sorted({s["slug"] for s in services.values()})

    # Подготовим структуру вывода
    result = {
        "schema": "epb-history@1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_interval_min": step_min,
        "amounts": [a for _, a in AMOUNT_LABELS],
        "terms": PRICE_TERMS,
        "services": all_slugs,
        "aggregates": {},      # per metric_key → dict of series
        "services_data": {}    # per slug → per metric_key → [[t,v],...]
    }

    fresh_ms = fresh_within_min * 60 * 1000

    # Готовим карманы для пер-сервисных рядов
    for sid, sinfo in services.items():
        result["services_data"][sinfo["slug"]] = {}

    # Для каждого метрика собираем ряды
    for mid, minfo in metrics.items():
        key = minfo["key"]
        # вытащим точки в окне
        rows = select_points(conn, mid, start_ms, now_ms)

        # Группируем по ts
        by_ts: Dict[int, List[Tuple[int, Optional[float]]]] = {}
        for ts, service_id, value in rows:
            by_ts.setdefault(ts, []).append((service_id, value))

        # идём сеткой по шагу (15 мин)
        t = round_to_bucket_ms(start_ms, step_min)
        end = round_to_bucket_ms(now_ms, step_min)
        agg_median: List[Tuple[int,float]] = []
        agg_min: List[Tuple[int,float]] = []
        agg_max: List[Tuple[int,float]] = []
        agg_count: List[Tuple[int,int]] = []
        best_id: List[Tuple[int,str]] = []

        # Для пер-сервисных рядов копим только имеющиеся точки (списками)
        per_service_series: Dict[int, List[Tuple[int, Optional[float]]]] = {}

        while t <= end:
            pts = by_ts.get(t, [])
            vals: List[Tuple[int,float]] = []
            for sid, v in pts:
                if v is None: 
                    # пустую точку в индивидуальном ряду тоже сохраним
                    per_service_series.setdefault(sid, []).append((t, None))
                    continue
                # фильтр свежести: last_seen_ts относительно t
                last_seen = services[sid]["last_seen_ts"]
                if last_seen is not None and (t - last_seen) > fresh_ms:
                    # старое — игнор в агрегатах, но в индивидуальном ряду оставим
                    per_service_series.setdefault(sid, []).append((t, v))
                    continue
                vals.append((sid, v))
                per_service_series.setdefault(sid, []).append((t, v))

            only_vals = [v for _, v in vals]
            if only_vals:
                m = median(only_vals)
                mi = min(only_vals)
                ma = max(only_vals)
                agg_median.append((t, float(m)))
                agg_min.append((t, float(mi)))
                agg_max.append((t, float(ma)))
                agg_count.append((t, len(only_vals)))
                # лучший — минимальный (дешевле)
                sid_best = min(vals, key=lambda x: x[1])[0]
                best_id.append((t, services[sid_best]["slug"]))
            # если значений нет — просто пропускаем точку в агрегатах
            t += step_min * 60 * 1000

        # Пишем агрегаты по ключу
        result["aggregates"][key] = {
            "median": agg_median,
            "min": agg_min,
            "max": agg_max,
            "count": agg_count,
            "best_id": best_id
        }

        # Запишем пер-сервисные ряды для этого ключа
        for sid, series in per_service_series.items():
            slug = services[sid]["slug"]
            result["services_data"].setdefault(slug, {})[key] = series

    # Если это 30d и нужно даунсэмплить агрегаты/ряды до часа — применим
    if downsample_to_hour_for_30d:
        for key, agg in result["aggregates"].items():
            for k2 in ("median","min","max"):
                agg[k2] = downsample_to_hour(agg[k2])
            # count и best_id оставим по 15 мин — но для компактности тоже схлопнем:
            agg["count"] = downsample_to_hour([(t, float(c)) for t,c in agg["count"]])
            # best_id (категориальная) не усредняется — уберём, чтобы не плодить шум
            agg["best_id"] = []

        for slug, perkey in result["services_data"].items():
            for key, series in perkey.items():
                perkey[key] = downsample_to_hour(series)

    atomic_write_json(out_path, result)
    log("info", f"Rollup: записан {out_path.name} ({window_days}d, step={('1h' if downsample_to_hour_for_30d else f'{result['sample_interval_min']}m')})")

    # Пер-сервисные файлы (30d)
    if also_service_history and window_days >= 30:
        for slug in result["services_data"].keys():
            svc_out = {
                "schema": "epb-service@1",
                "platform_id": slug,
                "generated_at": result["generated_at"],
                "series": result["services_data"][slug]
            }
            svc_path = service_history_dir / f"{slug}_30d.json"
            atomic_write_json(svc_path, svc_out)
        log("info", f"Rollup: обновлён каталог {service_history_dir} (per-service 30d)")

# --------------------------- CLI / MAIN ---------------------------

def main():
    ap = argparse.ArgumentParser(description="EPB Ingest + Rollup (SQLite → JSON for frontend)")
    ap.add_argument("--db", default=str(HERE / "epb.db"))
    ap.add_argument("--interval", type=int, default=900, help="Интервал цикла, сек (по умолчанию 900 = 15 мин)")
    ap.add_argument("--fresh-within", type=int, default=45, help="Свежесть цен для агрегатов, минут (default: 45)")
    ap.add_argument("--rollup-7d", default=str(HERE / "history_7d.json"))
    ap.add_argument("--rollup-30d", default=str(HERE / "history_30d.json"))
    ap.add_argument("--make-service-history", dest="svc_hist", action="store_true", default=True)
    ap.add_argument("--no-service-history", dest="svc_hist", action="store_false")
    ap.add_argument("--service-history-dir", default=str(HERE / "service_history"))
    ap.add_argument("--log", choices=["info","debug"], default="info")
    ap.add_argument("--once", action="store_true", help="Один прогон и выход")
    args = ap.parse_args()

    log("info", f"DB: {args.db}")
    conn = open_db(Path(args.db))

    try:
        while True:
            t0 = time.time()
            try:
                # 1) Ingest
                inserted, snap_ts = ingest_once(conn, HERE, sample_step_min=15)

                # 2) Rollup 7d (15 минут)
                rollup_window(
                    conn=conn,
                    out_path=Path(args.rollup_7d),
                    window_days=7,
                    step_min=15,
                    fresh_within_min=args.fresh_within,
                    also_service_history=False,
                    service_history_dir=Path(args.service_history_dir),
                    downsample_to_hour_for_30d=False
                )
                # 3) Rollup 30d (даунсэмпл до 1 часа)
                rollup_window(
                    conn=conn,
                    out_path=Path(args.rollup_30d),
                    window_days=30,
                    step_min=15,
                    fresh_within_min=args.fresh_within,
                    also_service_history=args.svc_hist,
                    service_history_dir=Path(args.service_history_dir),
                    downsample_to_hour_for_30d=True
                )
            except Exception as e:
                log("error", f"Сбой цикла: {e}")

            if args.once:
                break

            # Спим до конца интервала (ровные шаги)
            elapsed = time.time() - t0
            sleep_s = max(5.0, args.interval - elapsed)
            log("info", f"Пауза {int(sleep_s)} сек…")
            time.sleep(sleep_s)
    except KeyboardInterrupt:
        log("info", "Остановлено пользователем.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
