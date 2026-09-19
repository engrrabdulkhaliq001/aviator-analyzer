"""Shared strict multiplier validation for Streamlit and FastAPI."""
from __future__ import annotations
import math
import re
from typing import Any

_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")

def validate_round_values(values: Any) -> list[float]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("At least one valid multiplier round is required.")
    if len(values) > 2:
        raise ValueError("Only one or two recent rounds are supported.")
    cleaned = []
    for index, raw in enumerate(values):
        token = str(raw).strip()
        if not token or not _PATTERN.fullmatch(token):
            raise ValueError(f"Round {index + 1} is invalid. Examples: 1.01, 1, or 2.5.")
        number = float(token)
        if not math.isfinite(number) or not 1.0 <= number <= 10000.0:
            raise ValueError(f"Round {index + 1} must be between 1.0 and 10000.0.")
        cleaned.append(round(number, 2))
    return cleaned

def parse_rounds_text(value: str) -> list[float]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Enter at least one valid multiplier round.")
    tokens = [item.strip() for item in value.split(",")]
    if any(not item for item in tokens):
        raise ValueError("Each round must contain a valid number.")
    return validate_round_values(tokens)
