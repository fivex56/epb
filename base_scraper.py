#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base class for Energy Price Board scrapers.

Shared logic: browser lifecycle, atomic JSON writes, validation,
graceful fallback (N/A on failure — never leave stale data)."""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional

NA = "N/A"

# -- schema ------------------------------------------------------------------

TERMS = ["15m", "1h", "1d", "3d", "10d"]
AMOUNT_LABELS = [("65k", 65000), ("130k", 131000)]

SCHEMA_KEYS = [
    "ts", "platform_id", "platform_name", "url", "chain", "product_type",
    "minimum_order_energy", "maximum_order_energy", "platform_max_energy",
]
# Add all price keys
for a_lbl, _ in AMOUNT_LABELS:
    for t in TERMS:
        SCHEMA_KEYS.append(f"{a_lbl}_{t}_price")


# -- helpers -----------------------------------------------------------------

def r6(x: float) -> float:
    return round(float(x), 6)


def isnum(x: Any) -> bool:
    try:
        return isinstance(x, (int, float)) and math.isfinite(float(x)) and float(x) >= 0
    except Exception:
        return False


def atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    prefix = f".{os.path.basename(path).replace('.json','')}_"
    fd, tmp = tempfile.mkstemp(prefix=prefix, dir=os.path.dirname(path) or ".", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


# -- base scraper ------------------------------------------------------------

class BaseScraper:
    """Base scraper with schema validation and atomic writes.

    Subclass and override `scrape()` — return a dict with at minimum
    the price fields you can extract.  The base class fills missing
    fields with "N/A" and always writes fresh JSON (never leaves stale
    data on failure)."""

    # Override in subclass
    platform_id: str = ""
    platform_name: str = ""
    url: str = ""
    chain: str = "TRON"
    product_type: str = "energy_purchase"
    out_file: str = ""  # set automatically if left empty

    def __init__(self):
        if not self.out_file:
            self.out_file = f"{self.platform_id}_prices.json"

    # ---- subclasses override this ----
    def scrape(self) -> Dict[str, Any]:
        """Override: return at minimum the price fields you can get.
        Missing fields will be filled with 'N/A'."""
        raise NotImplementedError

    # ---- helpers for subclasses ----
    @staticmethod
    def na_prices() -> Dict[str, Any]:
        """Return a dict with all price keys set to 'N/A'."""
        d = {}
        for a_lbl, _ in AMOUNT_LABELS:
            for t in TERMS:
                d[f"{a_lbl}_{t}_price"] = NA
        return d

    @staticmethod
    def make_price_dict(prices_65k: Dict[str, Optional[float]],
                        prices_130k: Dict[str, Optional[float]]) -> Dict[str, Any]:
        """Convert {term: float} dicts into flat price keys."""
        d = {}
        for t in TERMS:
            v65 = prices_65k.get(t)
            v130 = prices_130k.get(t)
            d[f"65k_{t}_price"] = r6(v65) if isnum(v65) else NA
            d[f"130k_{t}_price"] = r6(v130) if isnum(v130) else NA
        return d

    # ---- build / validate / write ----
    def build_payload(self, scraped: Dict[str, Any]) -> Dict[str, Any]:
        """Merge scraped data with defaults, fill missing, return full record."""
        base = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "platform_id": self.platform_id,
            "platform_name": self.platform_name,
            "url": self.url,
            "chain": self.chain,
            "product_type": self.product_type,
            "minimum_order_energy": NA,
            "maximum_order_energy": NA,
            "platform_max_energy": NA,
        }
        base.update(self.na_prices())       # fill all prices with N/A
        base.update(scraped)                # overwrite with actual data
        return base

    def validate(self, obj: Dict[str, Any]) -> None:
        for k in SCHEMA_KEYS:
            if k not in obj:
                raise SystemExit(f"Missing key: {k}")
        for k in ("minimum_order_energy", "maximum_order_energy", "platform_max_energy"):
            v = obj[k]
            if not (v == NA or isnum(v)):
                raise SystemExit(f"Bad value for {k}: {v!r}")
        for k in [key for key in obj if key.endswith("_price")]:
            v = obj[k]
            if not (v == NA or isnum(v)):
                raise SystemExit(f"Bad value for {k}: {v!r}")

    def run(self) -> Dict[str, Any]:
        """Main entry: scrape → build → validate → write. Returns payload."""
        logging.info("Scraping %s ...", self.platform_id)
        try:
            scraped = self.scrape()
        except Exception as e:
            logging.exception("Scrape failed for %s: %s", self.platform_id, e)
            # On failure, write N/A for everything (don't leave stale data)
            scraped = {}

        payload = self.build_payload(scraped)
        try:
            self.validate(payload)
        except SystemExit as e:
            logging.error("Validation failed: %s", e)
            # Write anyway — better N/A than stale data
        atomic_write_json(self.out_file, payload)
        logging.info("Wrote %s", self.out_file)
        return payload

    # ---- CLI ----
    @classmethod
    def main(cls, argv: Optional[list] = None):
        ap = argparse.ArgumentParser(description=f"{cls.platform_name} scraper")
        ap.add_argument("--out", default=cls.out_file if hasattr(cls, 'out_file') else None)
        ap.add_argument("--log", default="info", choices=["debug", "info", "warning", "error"])
        args = ap.parse_args(argv)

        logging.basicConfig(
            level=getattr(logging, args.log.upper()),
            format="%(asctime)s %(levelname)s %(message)s",
        )

        instance = cls()
        if args.out:
            instance.out_file = args.out

        payload = instance.run()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
