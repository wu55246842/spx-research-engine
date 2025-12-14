from __future__ import annotations

from typing import Any, Dict, List
import os
from datetime import datetime


def fetch_all_inputs(
    *,
    symbol: str,
    proxy: str,
    asof_utc: str,
    session: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Fetch all inputs needed by the research pipeline.

    This repository ships with a **stub** fetcher so the pipeline can run end-to-end in GitHub Actions.
    Replace the stub sections with your real data provider calls (SPX/ES prices, rates, DXY, VIX term structure, options GEX/MaxPain).
    """

    # --- STUB: price snapshot ---
    # You can plug in your own provider here.
    prev_close = float(os.environ.get("SPX_PREV_CLOSE", "6848.7"))
    last = float(os.environ.get("SPX_LAST", str(prev_close - 18.5)))

    price = {
        "last": last,
        "prev_close": prev_close,
    }

    # --- STUB: macro ---
    rates = {
        "US10Y": float(os.environ.get("US10Y", "4.25")),
        "US2Y": float(os.environ.get("US2Y", "4.55")),
    }
    fx = {"DXY": float(os.environ.get("DXY", "103.2"))}

    macro_calendar: List[Dict[str, Any]] = []
    earnings: List[Dict[str, Any]] = []

    # --- STUB: technical price series ---
    technicals_raw: Dict[str, Any] = {
        # In production, include your OHLC arrays here.
        "note": "stub",
    }

    # --- STUB: options / structure ---
    thresholds = config.get("thresholds", {}) or {}
    options = {
        "max_pain_zone": [float(os.environ.get("MAX_PAIN_LOW", "6620")), float(os.environ.get("MAX_PAIN_HIGH", "6750"))],
        "call_wall": float(os.environ.get("CALL_WALL", "6900")),
        "put_wall": float(os.environ.get("PUT_WALL", "6800")),
        "gamma_flip": float(os.environ.get("GAMMA_FLIP", str(thresholds.get("gamma_flip_default", 6850)))),
        "regime": os.environ.get("GAMMA_REGIME", "Transition->NegativeGamma"),
    }

    vix = {
        "spot": float(os.environ.get("VIX", "16.24")),
        "term": os.environ.get("VIX_TERM", "Contango->Flattening"),
    }

    health = {
        "provider": "stub",
        "asof_utc": asof_utc,
        "missing": [],
    }

    return {
        "price": price,
        "rates": rates,
        "fx": fx,
        "macro_calendar": macro_calendar,
        "earnings": earnings,
        "technicals_raw": technicals_raw,
        "options": options,
        "vix": vix,
        "health": health,
    }
