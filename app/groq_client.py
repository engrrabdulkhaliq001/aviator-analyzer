"""VM-only Groq explanation client with a safe fallback."""
from __future__ import annotations
import logging
import os
from typing import Any
import httpx
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger("aviator_m6.groq_client")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_fallback_explanation(data: dict[str, Any]) -> str:
    probs = data.get("probabilities", {})
    rounds = ", ".join(f"{value}x" for value in data.get("input_rounds", []))
    return (f"Model ne recent rounds [{rounds}] ke liye {data.get('estimated_range', 'N/A')} ka experimental estimate diya hai.\n\n"
            f"1.50x: {float(probs.get('reach_1_50x', 0)) * 100:.1f}% | "
            f"2.00x: {float(probs.get('reach_2_00x', 0)) * 100:.1f}% | "
            f"4.00x: {float(probs.get('reach_4_00x', 0)) * 100:.1f}%\n\n"
            "Yeh statistical estimate hai, guarantee nahi. Aviator random game hai aur yeh dashboard analytics/research ke liye hai.")

def generate_roman_urdu_explanation(data: dict[str, Any], timeout: float = 12.0) -> str:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return get_fallback_explanation(data)
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    probabilities = data.get("probabilities", {})
    prompt = ("Explain these verified M6 model results in concise Roman Urdu. Do not invent values. "
              "State that the estimate is experimental and Aviator is random.\n\n" + str({
                  "rounds": data.get("input_rounds"),
                  "model": data.get("model_type"),
                  "probabilities": probabilities,
                  "range": data.get("estimated_range"),
              }))
    try:
        response = httpx.post(GROQ_API_URL, headers={"Authorization": f"Bearer {key}"}, json={
            "model": model,
            "messages": [{"role": "system", "content": "You explain verified ML output only."}, {"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 350,
        }, timeout=timeout)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq explanation unavailable: %s", type(exc).__name__)
        return get_fallback_explanation(data)
