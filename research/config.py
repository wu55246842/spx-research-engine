from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Tuple
import copy

import yaml


class ConfigError(RuntimeError):
    """Raised when configuration is missing, malformed, or fails validation."""


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load YAML config, deep-merge with defaults, validate schema & ranges."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise ConfigError(f"Failed to parse YAML: {path} -> {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"Config root must be a mapping/dict. Got: {type(raw).__name__}")

    defaults = _default_config()
    cfg = _deep_merge(copy.deepcopy(defaults), raw)

    _validate_config(cfg, source_path=str(path))
    return cfg


def _default_config() -> Dict[str, Any]:
    """Minimal safe defaults. YAML can override any of these."""
    return {
        "timezone": "Asia/Singapore",
        "version": "1.0.0",
        "symbols": {"spx": "SPX", "proxy": "ES"},
        "scenario_engine": {
            "hold_minutes": 30,
            "use_close_confirmation": True,
            "event_week_tilt": 0.05,
            "scalers": {
                "max_pain_gravity_points": 150,
                "rate_pressure_center": 50,
                "rate_pressure_span": 50,
            },
            "proximity": {"near_level_points": 25},
            "weights": {"bear": {}, "neutral": {}, "bull": {}},
        },
        "thresholds": {
            "gamma_flip_default": 6850,
            "fallback_support": 6800,
            "fallback_resistance": 6888,
        },
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge override into base (dicts only). Lists/other types overwrite."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _validate_config(cfg: Dict[str, Any], source_path: str = "") -> None:
    """Schema + range validation with helpful errors."""
    errors: list[str] = []

    def req(path: str) -> Any:
        val, ok = _get_path(cfg, path)
        if not ok:
            errors.append(f"Missing required config key: '{path}'")
        return val

    def typ(path: str, expected: Tuple[type, ...]) -> Any:
        val, ok = _get_path(cfg, path)
        if not ok:
            return None
        if not isinstance(val, expected):
            errors.append(
                f"Invalid type for '{path}': expected {', '.join(t.__name__ for t in expected)}, "
                f"got {type(val).__name__}"
            )
        return val

    def num_range(path: str, lo: float | None = None, hi: float | None = None) -> None:
        val = typ(path, (int, float))
        if val is None:
            return
        x = float(val)
        if lo is not None and x < lo:
            errors.append(f"Out of range '{path}': {x} < {lo}")
        if hi is not None and x > hi:
            errors.append(f"Out of range '{path}': {x} > {hi}")

    # --- required / basic types ---
    tz = req("timezone")
    if tz is not None and not isinstance(tz, str):
        errors.append(f"Invalid type for 'timezone': expected str, got {type(tz).__name__}")

    typ("version", (str,))
    typ("symbols", (dict,))
    typ("symbols.spx", (str,))
    typ("symbols.proxy", (str,))

    # scenario engine
    typ("scenario_engine", (dict,))
    num_range("scenario_engine.hold_minutes", lo=1, hi=240)
    typ("scenario_engine.use_close_confirmation", (bool,))
    num_range("scenario_engine.event_week_tilt", lo=0.0, hi=0.30)

    # scalers
    typ("scenario_engine.scalers", (dict,))
    num_range("scenario_engine.scalers.max_pain_gravity_points", lo=10, hi=1000)
    num_range("scenario_engine.scalers.rate_pressure_center", lo=0, hi=100)
    num_range("scenario_engine.scalers.rate_pressure_span", lo=1, hi=100)

    # proximity
    typ("scenario_engine.proximity", (dict,))
    num_range("scenario_engine.proximity.near_level_points", lo=1, hi=500)

    # weights
    typ("scenario_engine.weights", (dict,))
    for side in ("bear", "neutral", "bull"):
        p = f"scenario_engine.weights.{side}"
        w = req(p)
        if w is not None and not isinstance(w, dict):
            errors.append(f"Invalid type for '{p}': expected dict, got {type(w).__name__}")
        if isinstance(w, dict):
            for k, v in w.items():
                if not isinstance(k, str):
                    errors.append(f"Invalid weight key in '{p}': keys must be str")
                if not isinstance(v, (int, float)):
                    errors.append(f"Invalid weight value '{p}.{k}': expected number, got {type(v).__name__}")
                else:
                    if abs(float(v)) > 5.0:
                        errors.append(f"Suspicious weight '{p}.{k}': |{float(v)}| > 5.0 (check config)")

    # thresholds
    typ("thresholds", (dict,))
    num_range("thresholds.gamma_flip_default", lo=1000, hi=20000)
    num_range("thresholds.fallback_support", lo=1000, hi=20000)
    num_range("thresholds.fallback_resistance", lo=1000, hi=20000)

    fs = cfg["thresholds"]["fallback_support"]
    fr = cfg["thresholds"]["fallback_resistance"]
    if isinstance(fs, (int, float)) and isinstance(fr, (int, float)) and float(fs) >= float(fr):
        errors.append("Invalid thresholds: fallback_support must be < fallback_resistance")

    hm = cfg["scenario_engine"]["hold_minutes"]
    if isinstance(hm, (int, float)) and float(hm) > 120 and cfg["scenario_engine"]["use_close_confirmation"] is False:
        errors.append("If hold_minutes > 120, consider enabling use_close_confirmation for stability.")

    if errors:
        prefix = f"Config validation failed ({source_path}):" if source_path else "Config validation failed:"
        msg = "\n".join([prefix] + [f"- {e}" for e in errors])
        raise ConfigError(msg)


def _get_path(d: Mapping[str, Any], path: str) -> Tuple[Any, bool]:
    """Safe nested get: 'a.b.c' -> (value, ok)."""
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True
