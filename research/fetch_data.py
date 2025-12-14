from __future__ import annotations

from typing import Any, Dict, List
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def fetch_all_inputs(
    *,
    symbol: str,
    proxy: str,
    asof_utc: str,
    session: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Fetch all inputs needed by the research pipeline.
    
    Tiered System Implementation:
    - Tier 1 (Base): Prices via yfinance (works for any symbol).
    - Tier 3 (Alpha): Options/GEX data via Stub/API (only for SPX).
    """
    
    # --- Tier 1: Price History (yfinance) ---
    print(f"[FETCH] fetching {symbol} via yfinance...")
    try:
        ticker = yf.Ticker(symbol)
        # Fetch enough history for technicals (e.g. 1y for Daily, 5d for Intraday)
        hist = ticker.history(period="1y")
        
        if hist.empty:
            raise ValueError(f"No data found for {symbol}")
            
        current_price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
        
        # Calculate Volatility (ATR-like proxy for now if panda_ta not ready)
        # We pass the raw dataframe to technicals.py for heavy lifting
        price_df = hist.copy()
        
    except Exception as e:
        print(f"[WARN] yfinance failed for {symbol}: {e}. Falling back to stub.")
        # Fallback for CI/CD without network or stub mode
        current_price = float(os.environ.get("SPX_LAST", "6830.0"))
        prev_close = float(os.environ.get("SPX_PREV_CLOSE", "6848.7"))
        price_df = pd.DataFrame()

    price = {
        "last": current_price,
        "prev_close": prev_close,
        "history": price_df, # Pass DataFrame for technicals
    }

    # --- Tier 3: Options / Structure (Stub/API) ---
    # Only available if we have specific data sources. For generic tickers, this is skipped.
    is_spx = symbol in ["SPX", "^SPX", "SPY"]
    
    options = {}
    if is_spx:
        thresholds = config.get("thresholds", {}) or {}
        options = {
            "max_pain_zone": [float(os.environ.get("MAX_PAIN_LOW", "6620")), float(os.environ.get("MAX_PAIN_HIGH", "6750"))],
            "call_wall": float(os.environ.get("CALL_WALL", "6900")),
            "put_wall": float(os.environ.get("PUT_WALL", "6800")),
            "gamma_flip": float(os.environ.get("GAMMA_FLIP", str(thresholds.get("gamma_flip_default", 6850)))),
            "regime": os.environ.get("GAMMA_REGIME", "Transition->NegativeGamma"),
        }

    # --- Macro (Stub for now, could fetch Yields via yfinance too) ---
    rates = {
        "US10Y": float(os.environ.get("US10Y", "4.25")),
        "US2Y": float(os.environ.get("US2Y", "4.55")),
    }
    fx = {"DXY": float(os.environ.get("DXY", "103.2"))}

    # --- VIX (Tier 3) ---
    vix = {
        "spot": float(os.environ.get("VIX", "16.24")),
        "term": os.environ.get("VIX_TERM", "Contango->Flattening"),
    }

    health = {
        "provider": "yfinance" if not price_df.empty else "stub",
        "asof_utc": asof_utc,
        "missing": int(price_df.empty),
    }

    return {
        "price": price,
        "rates": rates,
        "fx": fx,
        "macro_calendar": [],
        "earnings": [],
        "technicals_raw": {"df": price_df}, # Pass full DF
        "options": options,
        "vix": vix,
        "health": health,
    }
