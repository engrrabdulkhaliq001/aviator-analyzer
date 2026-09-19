from dataclasses import dataclass, field
from fastapi.testclient import TestClient
from app import fastapi_backend

@dataclass
class FakePrediction:
    probabilities: dict[str, float] = field(default_factory=lambda: {"reach_1_50x": .8, "reach_2_00x": .6, "reach_4_00x": .2})
    input_rounds: list[float] = field(default_factory=lambda: [1.12, 1.25])
    metadata: dict = field(default_factory=lambda: {"dataset_rows": 1375})
    error: str | None = None
    estimated_range: str = "1.50x - 2.00x"
    confidence_level: str = "Medium"
    model_type: str = "two_round"
    def to_dict(self):
        return {"input_rounds": self.input_rounds, "model_type": self.model_type, "probabilities": self.probabilities, "estimated_range": self.estimated_range, "confidence_level": self.confidence_level, "metadata": self.metadata, "error": self.error}

def test_health_contract(monkeypatch):
    monkeypatch.setattr(fastapi_backend, "get_model_status", lambda: {"status":"healthy", "models_dir":"/private/models", "dataset_rows":1375})
    response = TestClient(fastapi_backend.app).get("/health")
    assert response.status_code == 200
    assert response.json()["model_status"] == "online"

def test_predict_contract(monkeypatch):
    monkeypatch.setattr(fastapi_backend, "predict_next_round", lambda rounds: FakePrediction())
    response = TestClient(fastapi_backend.app).post("/predict", json={"recent_rounds":[1.12,1.25], "include_ai_explanation":False})
    assert response.status_code == 200
    body = response.json()
    assert body["prediction"]["raw_probabilities"]["reach_2_00x"] == .6
    assert abs(sum(body["probabilities"].values()) - 1) < .001

def test_invalid_round_count_is_rejected():
    response = TestClient(fastapi_backend.app).post("/predict", json={"recent_rounds":[1.1,1.2,1.3]})
    assert response.status_code == 422

def test_health_does_not_expose_keys(monkeypatch):
    monkeypatch.setattr(fastapi_backend, "get_model_status", lambda: {"status":"healthy", "models_dir":"/private/models", "dataset_rows":1})
    text = TestClient(fastapi_backend.app).get("/health").text
    assert "GROQ_API_KEY" not in text and "gsk_" not in text
