from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd
import numpy as np

def analyze_technicals(*, price_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Technical framework: Calculates indicators and dynamic levels.
    
    Supports:
    - Tier 1: Calculates ATR, RSI, MACD using pandas (no heavy deps required).
    - Tier 3: Falls back to config/upstream levels if Price DF is missing.
    """
    df = price_data.get("df")
    
    # Defaults
    rsi = price_data.get("rsi14")
    macd_hist = price_data.get("macd_hist")
    atr = 50.0 # Fallback ATR for SPX ~0.7%
    levels = price_data.get("levels") or {}

    if df is not None and not df.empty:
        # Standardize columns
        df.columns = [c.lower() for c in df.columns]
        close = df["close"]
        high = df["high"]
        low = df["low"]
        
        # 1. ATR (14) - For dynamic targets
        # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_series = tr.rolling(14).mean() # Simple SMA ATR for robustness
        if not atr_series.empty:
             atr = float(atr_series.iloc[-1])

        # 2. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        if not rsi_series.empty:
            rsi = float(rsi_series.iloc[-1])

        # 3. MACD (12, 26, 9)
        k = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        d = k.ewm(span=9, adjust=False).mean()
        hist = k - d
        if not hist.empty:
            macd_hist = float(hist.iloc[-1])

    # Stub / Config Fallbacks
    thresholds = (config.get("thresholds", {}) or {})
    if not levels:
         levels = {
            "weekly_pivot": thresholds.get("fallback_resistance"),
            "supports": [thresholds.get("fallback_support")],
            "resistances": [thresholds.get("fallback_resistance")],
        }

    # Qualitative Labels
    momentum_state = "Neutral"
    if isinstance(macd_hist, (int, float)) and macd_hist < 0:
        momentum_state = "Bearish"
    if isinstance(rsi, (int, float)) and rsi > 55 and isinstance(macd_hist, (int, float)) and macd_hist > 0:
        momentum_state = "Bullish"
    
    # Trend Bias (Simple SMA check)
    trend_state = "Unknown"
    if df is not None and not df.empty and len(df) > 20:
        sma20 = df["close"].rolling(20).mean().iloc[-1]
        last = df["close"].iloc[-1]
        trend_state = "Uptrend" if last > sma20 else "Downtrend"

    return {
        "trend_state": trend_state,
        "momentum_state": momentum_state,
        "indicators": {
            "rsi14": rsi,
            "macd_hist": macd_hist,
            "atr14": atr, # Key for v2
        },
        "levels": levels,
    }
