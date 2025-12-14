from __future__ import annotations

from typing import Any, Dict, List


def analyze_technicals(*, price_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Technical framework: trend/momentum + key levels.

    Stub behavior:
    - Pulls levels from config.thresholds if price_data does not provide them.
    - Expects upstream data source to eventually populate indicators/levels.
    """
    thresholds = (config.get("thresholds", {}) or {})

    # In production, you would compute SMA/EMA/RSI/MACD and Pivot/Fib levels from candles.
    levels = price_data.get("levels") or {
        "weekly_pivot": thresholds.get("fallback_resistance"),
        "supports": [thresholds.get("fallback_support")],
        "resistances": [thresholds.get("fallback_resistance")],
    }

    indicators = price_data.get("indicators") or {
        "rsi14": price_data.get("rsi14"),
        "macd_hist": price_data.get("macd_hist"),
    }

    # Simple qualitative labels
    rsi = indicators.get("rsi14")
    macd_hist = indicators.get("macd_hist")

    momentum_state = "Neutral"
    if isinstance(macd_hist, (int, float)) and macd_hist < 0:
        momentum_state = "Bearish"
    if isinstance(rsi, (int, float)) and rsi > 55 and isinstance(macd_hist, (int, float)) and macd_hist > 0:
        momentum_state = "Bullish"

    return {
        "trend_state": price_data.get("trend_state") or "Unknown",
        "momentum_state": momentum_state,
        "indicators": indicators,
        "levels": levels,
    }
