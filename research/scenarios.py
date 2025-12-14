from __future__ import annotations

from typing import Any, Dict, List, Tuple
import math


def build_scenarios(
    macro: Dict[str, Any],
    technicals: Dict[str, Any],
    structure: Dict[str, Any],
    price: Dict[str, Any],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build Bear/Neutral/Bull scenarios with probabilities and rule-based triggers.

    This is intentionally interpretable and config-driven (Research-as-Code).
    """

    last = float(price.get("last") or price.get("close") or 0.0)
    prev_close = float(price.get("prev_close") or 0.0)

    levels = technicals.get("levels", {}) or {}
    supports = list(levels.get("supports", []))
    resistances = list(levels.get("resistances", []))
    weekly_pivot = levels.get("weekly_pivot")

    indicators = technicals.get("indicators", {}) or {}
    rsi14 = indicators.get("rsi14")
    macd_hist = indicators.get("macd_hist")

    gamma_flip = structure.get("gamma_flip") or (config.get("thresholds", {}) or {}).get("gamma_flip_default")
    regime = (structure.get("regime") or "").lower()

    max_pain_zone = structure.get("max_pain_zone") or [None, None]
    mp_low, mp_high = max_pain_zone[0], max_pain_zone[1]

    vix_state = structure.get("vix_state", {}) or {}
    vix_term = (vix_state.get("term") or "").lower()

    event_risk_level = (macro.get("event_risk_level") or "low").lower()
    rate_pressure_score = float(macro.get("rate_pressure_score") or 50.0)
    macro_bias = (macro.get("macro_bias") or "mixed").lower()

    engine = (config.get("scenario_engine", {}) or {})
    hold_minutes = int(engine.get("hold_minutes", 30))
    close_confirm = bool(engine.get("use_close_confirmation", True))

    feats = _compute_features(
        last=last,
        prev_close=prev_close,
        weekly_pivot=weekly_pivot,
        supports=supports,
        resistances=resistances,
        rsi14=rsi14,
        macd_hist=macd_hist,
        gamma_flip=gamma_flip,
        regime=regime,
        mp_low=mp_low,
        mp_high=mp_high,
        vix_term=vix_term,
        event_risk_level=event_risk_level,
        rate_pressure_score=rate_pressure_score,
        macro_bias=macro_bias,
    )

    weights = _load_weights(config)

    bear_score = _score("bear", feats, weights, config)
    neutral_score = _score("neutral", feats, weights, config)
    bull_score = _score("bull", feats, weights, config)

    bear_p, neutral_p, bull_p = _softmax3(bear_score, neutral_score, bull_score)

    key = _select_key_levels(last, supports, resistances, weekly_pivot, gamma_flip, mp_low, mp_high, config)

    scenarios = [
        _scenario_bear(last, key, bear_p, hold_minutes, close_confirm),
        _scenario_neutral(last, key, neutral_p, hold_minutes),
        _scenario_bull(last, key, bull_p, hold_minutes, close_confirm),
    ]

    scenarios = _post_adjust_scenarios(scenarios, feats, config)
    return scenarios


def _compute_features(
    *,
    last: float,
    prev_close: float,
    weekly_pivot: float | None,
    supports: List[float],
    resistances: List[float],
    rsi14: float | None,
    macd_hist: float | None,
    gamma_flip: float | None,
    regime: str,
    mp_low: float | None,
    mp_high: float | None,
    vix_term: str,
    event_risk_level: str,
    rate_pressure_score: float,
    macro_bias: str,
) -> Dict[str, Any]:
    price_vs_pivot = None if weekly_pivot is None else (last - float(weekly_pivot))
    below_pivot = (price_vs_pivot is not None) and (price_vs_pivot < 0)

    below_flip = (gamma_flip is not None) and (last < float(gamma_flip))

    mp_mid = None
    mp_gravity = 0.0
    if mp_low is not None and mp_high is not None:
        mp_mid = (float(mp_low) + float(mp_high)) / 2.0
        mp_gravity = max(0.0, last - mp_mid)

    nearest_sup = _nearest_below(last, supports)
    nearest_res = _nearest_above(last, resistances)

    dist_to_sup = None if nearest_sup is None else (last - nearest_sup)
    dist_to_res = None if nearest_res is None else (nearest_res - last)

    rsi_weak = (rsi14 is not None) and (rsi14 < 45)
    rsi_oversold = (rsi14 is not None) and (rsi14 < 30)
    macd_bear = (macd_hist is not None) and (macd_hist < 0)

    neg_gamma = ("negative" in regime) or ("neg" in regime)
    pos_gamma = ("positive" in regime) or ("pos" in regime)

    vix_flattening = ("flatten" in vix_term) or ("flat" in vix_term)
    vix_backward = ("backward" in vix_term) or ("backwardation" in vix_term)

    risk_off = ("off" in macro_bias)
    risk_on = ("on" in macro_bias)

    event_risk_high = event_risk_level in {"high", "med", "medium"}

    return {
        "below_pivot": below_pivot,
        "below_flip": below_flip,
        "mp_gravity": mp_gravity,
        "nearest_sup": nearest_sup,
        "nearest_res": nearest_res,
        "dist_to_sup": dist_to_sup,
        "dist_to_res": dist_to_res,
        "rsi_weak": rsi_weak,
        "rsi_oversold": rsi_oversold,
        "macd_bear": macd_bear,
        "neg_gamma": neg_gamma,
        "pos_gamma": pos_gamma,
        "vix_flattening": vix_flattening,
        "vix_backward": vix_backward,
        "risk_off": risk_off,
        "risk_on": risk_on,
        "rate_pressure_score": rate_pressure_score,
        "event_risk_high": event_risk_high,
        "last": last,
        "weekly_pivot": weekly_pivot,
        "gamma_flip": gamma_flip,
        "mp_mid": mp_mid,
        "rsi14": rsi14,
        "macd_hist": macd_hist,
        "prev_close": prev_close,
    }


def _load_weights(config: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    engine = (config.get("scenario_engine", {}) or {})
    w = engine.get("weights") or {}
    # Ensure presence of keys
    out: Dict[str, Dict[str, float]] = {"bear": {}, "neutral": {}, "bull": {}}
    for side in out:
        side_w = w.get(side) or {}
        if isinstance(side_w, dict):
            out[side] = {str(k): float(v) for k, v in side_w.items()}
    return out


def _score(side: str, feats: Dict[str, Any], weights: Dict[str, Dict[str, float]], config: Dict[str, Any]) -> float:
    engine = (config.get("scenario_engine", {}) or {})
    scalers = (engine.get("scalers", {}) or {})
    prox = (engine.get("proximity", {}) or {})

    mp_scale = float(scalers.get("max_pain_gravity_points", 150))
    rp_center = float(scalers.get("rate_pressure_center", 50))
    rp_span = float(scalers.get("rate_pressure_span", 50))
    near_th = float(prox.get("near_level_points", 25))

    mp_gravity_scaled = _clamp((feats.get("mp_gravity") or 0.0) / mp_scale, 0.0, 1.5)

    # rate pressure: map [center, center+span] -> [0,1], clamp
    rate_pressure_scaled = _clamp(((feats.get("rate_pressure_score") or rp_center) - rp_center) / rp_span, 0.0, 1.0)

    near_support = _near(feats.get("dist_to_sup"), threshold=near_th)
    near_resistance = _near(feats.get("dist_to_res"), threshold=near_th)

    last = float(feats.get("last") or 0.0)
    weekly_pivot = feats.get("weekly_pivot")
    gamma_flip = feats.get("gamma_flip")

    above_pivot = (weekly_pivot is not None) and (last > float(weekly_pivot))
    above_flip = (gamma_flip is not None) and (last > float(gamma_flip))

    not_event_risk = not bool(feats.get("event_risk_high"))
    not_macd_bear = not bool(feats.get("macd_bear"))
    not_rsi_weak = not bool(feats.get("rsi_weak"))
    low_rate_pressure = float(feats.get("rate_pressure_score") or rp_center) < (rp_center + 5)

    b = lambda x: 1.0 if x else 0.0

    fmap = {
        "below_pivot": b(feats.get("below_pivot")),
        "below_flip": b(feats.get("below_flip")),
        "macd_bear": b(feats.get("macd_bear")),
        "rsi_weak": b(feats.get("rsi_weak")),
        "mp_gravity_scaled": mp_gravity_scaled,
        "neg_gamma": b(feats.get("neg_gamma")),
        "vix_flattening": b(feats.get("vix_flattening")),
        "vix_backward": b(feats.get("vix_backward")),
        "risk_off": b(feats.get("risk_off")),
        "rate_pressure_scaled": rate_pressure_scaled,
        "event_risk_high": b(feats.get("event_risk_high")),

        "near_support": b(near_support),
        "near_resistance": b(near_resistance),
        "pos_gamma": b(feats.get("pos_gamma")),
        "not_event_risk": b(not_event_risk),

        "above_pivot": b(above_pivot),
        "above_flip": b(above_flip),
        "not_macd_bear": b(not_macd_bear),
        "not_rsi_weak": b(not_rsi_weak),
        "risk_on": b(feats.get("risk_on")),
        "low_rate_pressure": b(low_rate_pressure),
    }

    score = 0.0
    for name, weight in (weights.get(side) or {}).items():
        score += float(weight) * float(fmap.get(name, 0.0))

    # tiny epsilon to stabilize
    return score + 1e-6


def _softmax3(a: float, b: float, c: float) -> Tuple[float, float, float]:
    m = max(a, b, c)
    ea, eb, ec = math.exp(a - m), math.exp(b - m), math.exp(c - m)
    s = ea + eb + ec
    return (ea / s, eb / s, ec / s)


def _select_key_levels(
    last: float,
    supports: List[float],
    resistances: List[float],
    weekly_pivot: float | None,
    gamma_flip: float | None,
    mp_low: float | None,
    mp_high: float | None,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    sup1 = _nearest_below(last, supports)
    sup2 = _second_below(last, supports)
    res1 = _nearest_above(last, resistances)
    res2 = _second_above(last, resistances)

    mp_target = None
    if mp_low is not None and mp_high is not None:
        mp_target = float(mp_high)

    thresholds = (config.get("thresholds", {}) or {})
    if sup1 is None:
        sup1 = thresholds.get("fallback_support")
    if res1 is None:
        res1 = thresholds.get("fallback_resistance")

    return {
        "weekly_pivot": weekly_pivot,
        "gamma_flip": gamma_flip,
        "support_1": sup1,
        "support_2": sup2,
        "resistance_1": res1,
        "resistance_2": res2,
        "max_pain_target": mp_target,
        "max_pain_zone": [mp_low, mp_high],
    }


def _scenario_bear(last: float, key: Dict[str, Any], prob: float, hold_minutes: int, close_confirm: bool) -> Dict[str, Any]:
    s1 = key.get("support_1")
    s2 = key.get("support_2")
    mp = key.get("max_pain_target")
    pivot = key.get("weekly_pivot")
    res1 = key.get("resistance_1")

    trigger_level = s1
    if key.get("gamma_flip") is not None and s1 is not None:
        trigger_level = min(float(s1), float(key["gamma_flip"]))

    targets: List[float] = []
    if s2 is not None:
        targets.append(float(s2))
    if mp is not None:
        targets.append(float(mp))
    if not targets and s1 is not None:
        targets = [float(s1) - 50.0]

    if close_confirm:
        invalid_level = None
        if pivot is not None:
            invalid_level = max(float(pivot), float(res1) if res1 is not None else float(pivot))
        elif res1 is not None:
            invalid_level = float(res1)
        invalid = f"Daily close > {invalid_level:.0f}" if invalid_level is not None else "Daily close above key resistance"
    else:
        invalid = f"Reclaim > {float(res1):.0f}" if res1 is not None else "Reclaim key resistance"

    return {
        "name": "Bearish pull-to-support/maxpain",
        "prob": round(prob, 4),
        "trigger": f"Break < {float(trigger_level):.0f} and hold {hold_minutes}m" if trigger_level is not None else f"Break below support and hold {hold_minutes}m",
        "target": [round(t, 0) for t in targets],
        "invalid": invalid,
    }


def _scenario_neutral(last: float, key: Dict[str, Any], prob: float, hold_minutes: int) -> Dict[str, Any]:
    low = key.get("support_1") or key.get("max_pain_target")
    high = key.get("weekly_pivot") or key.get("resistance_1")

    if low is None:
        low = last - 40.0
    if high is None:
        high = last + 40.0

    return {
        "name": "Neutral range / consolidation",
        "prob": round(prob, 4),
        "trigger": f"Hold above {float(low):.0f} and fail to sustain > {float(high):.0f} for {hold_minutes}m",
        "target": [round(float(low), 0), round(float(high), 0)],
        "invalid": "Range expansion with momentum/volume (breakout or breakdown)",
    }


def _scenario_bull(last: float, key: Dict[str, Any], prob: float, hold_minutes: int, close_confirm: bool) -> Dict[str, Any]:
    pivot = key.get("weekly_pivot")
    res1 = key.get("resistance_1")
    res2 = key.get("resistance_2")
    flip = key.get("gamma_flip")

    reclaim = pivot if pivot is not None else flip

    confirm = None
    if res1 is not None and pivot is not None:
        confirm = max(float(res1), float(pivot))
    elif res1 is not None:
        confirm = float(res1)
    elif pivot is not None:
        confirm = float(pivot) + 12.0

    targets: List[float] = []
    if res2 is not None:
        targets.append(float(res2))
    else:
        targets = [last + 50.0, last + 100.0]

    if close_confirm and reclaim is not None:
        invalid = f"Daily close < {float(reclaim):.0f}"
    else:
        invalid = f"Reject < {float(reclaim):.0f} after reclaim" if reclaim is not None else "Reversal back into range"

    return {
        "name": "Bullish reversal / breakout",
        "prob": round(prob, 4),
        "trigger": f"Reclaim > {float(reclaim):.0f} and sustain > {float(confirm):.0f} for {hold_minutes}m" if reclaim is not None and confirm is not None else f"Reclaim key level and hold {hold_minutes}m",
        "target": [round(t, 0) for t in targets],
        "invalid": invalid,
    }


def _post_adjust_scenarios(scenarios: List[Dict[str, Any]], feats: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not feats.get("event_risk_high"):
        return scenarios

    engine = (config.get("scenario_engine", {}) or {})
    tilt = float(engine.get("event_week_tilt", 0.05))
    if tilt <= 0:
        return scenarios

    n_i = next((i for i, s in enumerate(scenarios) if "neutral" in s["name"].lower()), None)
    b_i = next((i for i, s in enumerate(scenarios) if "bear" in s["name"].lower()), None)
    u_i = next((i for i, s in enumerate(scenarios) if "bull" in s["name"].lower()), None)
    if n_i is None or b_i is None or u_i is None:
        return scenarios

    n = float(scenarios[n_i]["prob"])
    cut = min(tilt, n * 0.5)
    scenarios[n_i]["prob"] = n - cut
    scenarios[b_i]["prob"] = float(scenarios[b_i]["prob"]) + cut / 2
    scenarios[u_i]["prob"] = float(scenarios[u_i]["prob"]) + cut / 2

    total = sum(float(s["prob"]) for s in scenarios)
    for s in scenarios:
        s["prob"] = round(float(s["prob"]) / total, 4)

    return scenarios


def _nearest_below(x: float, levels: List[float]) -> float | None:
    below = [float(v) for v in levels if float(v) <= x]
    return max(below) if below else None


def _second_below(x: float, levels: List[float]) -> float | None:
    below = sorted({float(v) for v in levels if float(v) <= x}, reverse=True)
    return below[1] if len(below) >= 2 else None


def _nearest_above(x: float, levels: List[float]) -> float | None:
    above = [float(v) for v in levels if float(v) >= x]
    return min(above) if above else None


def _second_above(x: float, levels: List[float]) -> float | None:
    above = sorted({float(v) for v in levels if float(v) >= x})
    return above[1] if len(above) >= 2 else None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _near(dist: float | None, threshold: float) -> bool:
    return (dist is not None) and (dist <= threshold)
