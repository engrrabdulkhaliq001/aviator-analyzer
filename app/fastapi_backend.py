"""Aviator M6 FastAPI service for VM-only inference."""
from __future__ import annotations
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
load_dotenv()
from app.groq_client import generate_roman_urdu_explanation, get_fallback_explanation
from app.input_validation import validate_round_values
from app.model_utils import get_model_status, load_models, predict_next_round
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aviator_m6_api")
app = FastAPI(title="Aviator M6 Prediction API", version="3.2.0")
_origins = [item.strip() for item in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if item.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

class PredictRequest(BaseModel):
    recent_rounds: list[Any] = Field(..., min_length=1, max_length=2)
    include_ai_explanation: bool = True
    @field_validator("recent_rounds", mode="before")
    @classmethod
    def validate_recent_rounds(cls, values: Any) -> list[float]:
        return validate_round_values(values)

class PredictResponse(BaseModel):
    status: str
    prediction: dict[str, Any]
    probabilities: dict[str, float]
    model_status: str
    ai_explanation: str | None
    processing_time_ms: float

@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.time()
    response = await call_next(request)
    logger.info("%s %s -> %s (%.2fms)", request.method, request.url.path, response.status_code, (time.time() - started) * 1000)
    return response

@app.on_event("startup")
async def startup() -> None:
    load_models()

@app.get("/health")
async def health() -> dict[str, Any]:
    model = get_model_status()
    return {"status": "online" if model["status"] == "healthy" else "degraded", "model_status": "online" if model["status"] == "healthy" else "offline", "models_dir": model["models_dir"], "dataset_rows": model["dataset_rows"], "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip()), "timestamp": time.time()}

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    started = time.time()
    result = predict_next_round(request.recent_rounds)
    if result.error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    p15 = result.probabilities["reach_1_50x"]
    p20 = result.probabilities["reach_2_00x"]
    p40 = result.probabilities["reach_4_00x"]
    raw = [max(0.01, 1 - p15), max(0.01, p15 - p20), max(0.01, p20 - p40 * 0.7), max(0.01, p40 * 0.5), max(0.01, p40 * 0.2)]
    total = sum(raw)
    names = ["under_1_50", "1_50_to_2", "2_to_5", "5_to_10", "10_plus"]
    buckets = dict(zip(names, [round(value / total, 4) for value in raw]))
    explanation = generate_roman_urdu_explanation(result.to_dict()) if request.include_ai_explanation else get_fallback_explanation(result.to_dict())
    return PredictResponse(status="success", prediction={"estimated_range": result.estimated_range, "confidence_level": result.confidence_level, "model_type": result.model_type, "input_rounds": result.input_rounds, "dataset_rows": result.metadata.get("dataset_rows", 0), "raw_probabilities": result.probabilities}, probabilities=buckets, model_status="online", ai_explanation=explanation, processing_time_ms=round((time.time() - started) * 1000, 2))
