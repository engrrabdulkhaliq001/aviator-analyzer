# Aviator M6 Analyzer

Aviator M6 is split into two deployments:

```text
Streamlit Community Cloud
        | HTTPS
        v
VM: FastAPI -> M6 feature engineering -> private models -> Groq
```

The Streamlit application is frontend-only. It never loads model files and never receives `GROQ_API_KEY`.

## Repository layout

```text
streamlit_app.py              # Streamlit Community Cloud entrypoint
requirements.txt              # frontend-only dependencies
app/
  fastapi_backend.py          # VM FastAPI application: /health and /predict
  model_utils.py              # VM model loading, features, and inference
  groq_client.py              # VM-only Groq explanation client
backend/
  requirements.txt             # VM dependency manifest
  aviator-m6-api.service      # systemd unit template
tests/
  test_api_contract.py        # model-independent API contract tests
```

Private files stay on the VM and are ignored by Git: `models/`, `data/`, `.env`, `venv/`, and generated caches.

## Streamlit Community Cloud

Set the app's main file to `streamlit_app.py`. Add this Streamlit secret:

```toml
BACKEND_API_URL = "https://aviator-m6.duckdns.org"
```

The UI calls `GET {BACKEND_API_URL}/health` and `POST {BACKEND_API_URL}/predict`.

## VM deployment

Copy `app/`, `backend/requirements.txt`, and the private M6 model files to `/opt/aviator-m6/`. Keep the VM `.env` outside Git:

```ini
HOST=127.0.0.1
PORT=8000
MODELS_DIR=/opt/aviator-m6/models
CORS_ALLOW_ORIGINS=https://your-app.streamlit.app
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

Install and run:

```bash
python3.11 -m venv /opt/aviator-m6/venv
/opt/aviator-m6/venv/bin/pip install -r /opt/aviator-m6/backend/requirements.txt
sudo cp /opt/aviator-m6/backend/aviator-m6-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aviator-m6-api
```

Keep the model directory private. HTTPS termination should forward the public API hostname to `127.0.0.1:8000`.

## API

`GET /health` reports model and Groq configuration status without exposing secrets.

`POST /predict` accepts one or two chronological rounds:

```json
{"recent_rounds": [1.12, 1.25], "include_ai_explanation": true}
```

The response contains actual M6 threshold probabilities, derived five-bucket probabilities, model status, and an optional Groq explanation. If Groq is unavailable, the API returns a clearly labeled fallback explanation while preserving the model result.

Predictions are experimental statistical estimates and are not guaranteed. This dashboard is for analytics/research purposes only.

## Local checks

```bash
pip install -r requirements.txt
python -m pytest -q tests
streamlit run streamlit_app.py
```
