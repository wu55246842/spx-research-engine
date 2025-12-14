from __future__ import annotations

from typing import Any, Dict, List


def analyze_macro(
    *,
    rates: Dict[str, Any],
    fx: Dict[str, Any],
    calendar: List[Dict[str, Any]],
    earnings: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Macro context: determine bias, rate pressure score, event risk.

    This is a conservative stub implementation that you can replace with real logic.
    """
    y10 = float(rates.get("us10y", 4.2))
    dxy = float(fx.get("dxy", 104.0))

    # Simple heuristic: higher yields + stronger dollar increases pressure.
    # Score is 0-100.
    score = 50.0
    score += (y10 - 4.0) * 25.0
    score += (dxy - 103.0) * 5.0
    score = max(0.0, min(100.0, score))

    # Event risk: any events/earnings in next 48h => Medium/High
    has_events = len(calendar) > 0 or len(earnings) > 0
    event_risk_level = "High" if has_events and len(calendar) + len(earnings) >= 2 else ("Medium" if has_events else "Low")

    macro_bias = "Risk-Off" if score >= 60 else ("Risk-On" if score <= 40 else "Mixed")

    return {
        "macro_bias": macro_bias,
        "rate_pressure_score": round(score, 2),
        "event_risk_level": event_risk_level,
        "key_events": calendar,
        "key_earnings": earnings,
    }
