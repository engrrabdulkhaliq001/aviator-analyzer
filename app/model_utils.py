"""Private VM model loading, feature construction, and M6 inference."""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger("aviator_m6.model_utils")
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(BASE_DIR / "models")))
_ONE_ROUND_MODEL: dict[str, Any] | None = None
_TWO_ROUND_MODEL: dict[str, Any] | None = None
_METADATA: dict[str, Any] | None = None
_INIT_ERROR: str | None = None

@dataclass
class PredictionOutput:
    input_rounds: list[float]
    num_rounds: int
    model_type: str
    probabilities: dict[str, float]
    estimated_range: str
    confidence_level: str
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_rounds": self.input_rounds,
            "num_rounds": self.num_rounds,
            "model_type": self.model_type,
            "probabilities": self.probabilities,
            "estimated_range": self.estimated_range,
            "confidence_level": self.confidence_level,
            "metadata": self.metadata,
            "error": self.error,
        }

def load_models(force_reload: bool = False) -> bool:
    global _ONE_ROUND_MODEL, _TWO_ROUND_MODEL, _METADATA, _INIT_ERROR
    if _ONE_ROUND_MODEL is not None and _TWO_ROUND_MODEL is not None and not force_reload:
        return True
    models_path = Path(os.getenv("MODELS_DIR", str(MODELS_DIR)))
    errors: list[str] = []
    for attr, filename in (("_ONE_ROUND_MODEL", "m6_one_round_model.pkl"), ("_TWO_ROUND_MODEL", "m6_two_round_model.pkl")):
        path = models_path / filename
        if not path.exists():
            errors.append(f"File not found: {path}")
            continue
        try:
            globals()[attr] = joblib.load(path)
        except Exception as exc:
            errors.append(f"Could not load {filename}: {type(exc).__name__}")
    metadata_path = models_path / "model_metadata.json"
    if metadata_path.exists():
        try:
            _METADATA = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Could not read metadata: {type(exc).__name__}")
    if _ONE_ROUND_MODEL is None and _TWO_ROUND_MODEL is None:
        _INIT_ERROR = "; ".join(errors) or "No M6 models loaded"
        return False
    _INIT_ERROR = None
    return True

def get_model_status() -> dict[str, Any]:
    return {
        "status": "healthy" if _ONE_ROUND_MODEL is not None or _TWO_ROUND_MODEL is not None else "unhealthy",
        "models_dir": str(MODELS_DIR),
        "one_round_model_loaded": _ONE_ROUND_MODEL is not None,
        "two_round_model_loaded": _TWO_ROUND_MODEL is not None,
        "metadata_loaded": _METADATA is not None,
        "dataset_rows": (_METADATA or {}).get("dataset", {}).get("total_rows", 0),
        "error": _INIT_ERROR,
    }

def validate_rounds(rounds: list[Any]) -> list[float]:
    if not rounds:
        raise ValueError("At least one multiplier round is required.")
    if len(rounds) > 2:
        raise ValueError("Only one or two recent rounds are supported.")
    cleaned: list[float] = []
    for index, raw in enumerate(rounds):
        try:
            value = float(str(raw).replace(",", ".").strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Round {index + 1} is not a valid number.") from exc
        if not math.isfinite(value) or value < 1.0 or value > 10000.0:
            raise ValueError(f"Round {index + 1} must be between 1.0 and 10000.0.")
        cleaned.append(round(value, 2))
    return cleaned

def build_features(rounds: list[float]) -> tuple[str, list[list[float]]]:
    if len(rounds) == 1:
        latest = rounds[0]
        return "one_round", [[latest, float(latest < 1.5), float(2.0 <= latest <= 5.0), float(latest > 10.0)]]
    older, latest = rounds
    return "two_round", [[latest, older, (latest + older) / 2, min(latest, older), max(latest, older), float(latest < 1.5), float(2.0 <= latest <= 5.0), float(latest > 10.0)]]

def predict_next_round(rounds: list[Any]) -> PredictionOutput:
    if not load_models():
        return PredictionOutput([], 0, "none", {}, "N/A", "Low", error=_INIT_ERROR or "M6 models are not loaded.")
    try:
        clean = validate_rounds(rounds)
        mode, features = build_features(clean)
    except ValueError as exc:
        return PredictionOutput(list(rounds), len(rounds), "invalid", {}, "N/A", "Low", error=str(exc))
    bundle = _ONE_ROUND_MODEL if mode == "one_round" else _TWO_ROUND_MODEL
    if not bundle or "classifiers" not in bundle:
        return PredictionOutput(clean, len(clean), mode, {}, "N/A", "Low", error=f"Required {mode} model is unavailable.")
    probabilities: dict[str, float] = {}
    for classifier_key, output_key in (("1_5x", "reach_1_50x"), ("2_0x", "reach_2_00x"), ("4_0x", "reach_4_00x")):
        classifier = bundle["classifiers"].get(classifier_key)
        if classifier is None:
            return PredictionOutput(clean, len(clean), mode, {}, "N/A", "Low", error=f"Required classifier {classifier_key} is unavailable.")
        try:
            probability = float(classifier.predict_proba(features)[0, 1])
        except Exception as exc:
            logger.exception("M6 inference failed for %s", classifier_key)
            return PredictionOutput(clean, len(clean), mode, {}, "N/A", "Low", error=f"M6 inference failed for {classifier_key}.")
        probabilities[output_key] = round(max(0.0, min(1.0, probability)), 3)
    p15, p20, p40 = (probabilities[key] for key in ("reach_1_50x", "reach_2_00x", "reach_4_00x"))
    if p15 < 0.45:
        estimated, confidence = "1.00x - 1.49x (High Crash Risk)", "Medium"
    elif p20 >= 0.65 and p40 >= 0.35:
        estimated, confidence = "2.00x - 5.00x+ (High Multiplier Potential)", "High" if mode == "two_round" else "Medium"
    elif p20 >= 0.65:
        estimated, confidence = "1.80x - 3.00x (Moderate Safe Band)", "High" if mode == "two_round" else "Medium"
    elif p15 >= 0.65:
        estimated, confidence = "1.50x - 2.00x (Short Safe Run)", "Medium"
    else:
        estimated, confidence = "1.20x - 2.20x (Volatile / Mixed Signal)", "Low"
    metadata = _METADATA or {}
    return PredictionOutput(clean, len(clean), mode, probabilities, estimated, confidence, {"dataset_rows": metadata.get("dataset", {}).get("total_rows", 0), "feature_count": len(features[0]), "model_version": metadata.get("version", "unknown")})

load_models()
