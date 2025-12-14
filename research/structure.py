from __future__ import annotations

from typing import Any, Dict


def analyze_market_structure(
    *,
    options: Dict[str, Any],
    vix: Dict[str, Any],
    price: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Market structure: gamma regime, flip, max pain, walls, VIX term state.

    Stub behavior uses config.thresholds.gamma_flip_default and any data in 'options'.
    """
    gamma_flip = options.get("gamma_flip") or (config.get("thresholds", {}) or {}).get("gamma_flip_default")
    regime = options.get("regime") or "Transition->NegativeGamma"

    mp_low = options.get("max_pain_low")
    mp_high = options.get("max_pain_high")
    if mp_low is None or mp_high is None:
        # Default to a "below price" zone using fallback support, for sensible outputs
        last = float(price.get("last") or price.get("close") or 0.0)
        fb_sup = float((config.get("thresholds", {}) or {}).get("fallback_support", max(0.0, last - 50)))
        mp_high = fb_sup - 50
        mp_low = mp_high - 130

    vix_spot = vix.get("spot") or 16.0
    vix_term = vix.get("term") or "Contango->Flattening"

    return {
        "regime": regime,
        "gamma_flip": float(gamma_flip) if gamma_flip is not None else None,
        "max_pain_zone": [float(mp_low), float(mp_high)],
        "walls": {
            "call_wall": options.get("call_wall") or None,
            "put_wall": options.get("put_wall") or None,
        },
        "vix_state": {
            "spot": float(vix_spot),
            "term": str(vix_term),
        },
    }
