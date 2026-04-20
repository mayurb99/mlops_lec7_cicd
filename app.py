"""
app.py
════════════════════════════════════════════════════════
FastAPI serving endpoint for the churn prediction model
Lecture 6 — Docker Demo
════════════════════════════════════════════════════════

Endpoints:
  GET  /health   → health check
  GET  /info     → model info
  POST /predict  → single prediction
  POST /predict/batch → batch predictions
"""

import os
import pickle
import logging
from typing import List
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────
app = FastAPI(
    title="Churn Prediction API",
    description="Predicts customer churn probability. Lecture 6 — Docker Demo.",
    version="1.0.0",
)

# ── Load model at startup ─────────────────────────────────
MODEL_PATH = os.getenv("MODEL_PATH", "models/churn_model.pkl")

model = None
model_info = {}
def load_model_func():
    global model, model_info
    logger.info(f"Loading model from: {MODEL_PATH}")
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        model_info = {
            "model_type": type(model).__name__,
            "model_path": MODEL_PATH,
            "features": FEATURE_COLS,
            "status": "loaded",
        }
    except FileNotFoundError:
        logger.error(f"Model file not found: {MODEL_PATH}")
        model_info = {"status": "not_found", "model_path": MODEL_PATH}

load_model_func()

# 🔥 IMPORTANT: Call it immediately
@app.on_event("startup")
def startup():
    load_model_func()

# ── Feature columns ───────────────────────────────────────
FEATURE_COLS = [
    "age", "tenure_months", "monthly_charge",
    "num_products", "support_calls", "has_contract"
]

# ── Request / Response schemas ────────────────────────────
class CustomerFeatures(BaseModel):
    age:            int   = Field(..., ge=18, le=100, description="Customer age")
    tenure_months:  int   = Field(..., ge=0,  le=240, description="Months as customer")
    monthly_charge: float = Field(..., ge=0,  le=500, description="Monthly charge in USD")
    num_products:   int   = Field(..., ge=1,  le=10,  description="Number of products")
    support_calls:  int   = Field(..., ge=0,  le=50,  description="Support calls in last 3 months")
    has_contract:   int   = Field(..., ge=0,  le=1,   description="Has contract: 1=yes 0=no")

    class Config:
        json_schema_extra = {
            "example": {
                "age": 35,
                "tenure_months": 24,
                "monthly_charge": 89.99,
                "num_products": 2,
                "support_calls": 3,
                "has_contract": 1,
            }
        }

class PredictionResponse(BaseModel):
    customer_features: dict
    churn_prediction:  int
    churn_probability: float
    churn_label:       str
    risk_level:        str

class BatchRequest(BaseModel):
    customers: List[CustomerFeatures]

class BatchResponse(BaseModel):
    predictions: List[PredictionResponse]
    total_customers: int
    high_risk_count: int

# ── Helper ────────────────────────────────────────────────
def make_prediction(features: CustomerFeatures) -> PredictionResponse:
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Build DataFrame with correct feature order
    X = pd.DataFrame([{col: getattr(features, col) for col in FEATURE_COLS}])

    prediction  = int(model.predict(X)[0])
    probability = float(model.predict_proba(X)[0][1])

    if probability >= 0.7:
        risk_level = "HIGH"
    elif probability >= 0.4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return PredictionResponse(
        customer_features=features.dict(),
        churn_prediction=prediction,
        churn_probability=round(probability, 4),
        churn_label="CHURN" if prediction == 1 else "NO CHURN",
        risk_level=risk_level,
    )

# ── Endpoints ─────────────────────────────────────────────
@app.get("/health")
def health_check():
    """Health check endpoint. Used by Docker + load balancers."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_type": model_info.get("model_type", "unknown"),
    }

@app.get("/info")
def model_information():
    """Returns model metadata."""
    return model_info

@app.post("/predict", response_model=PredictionResponse)
def predict(customer: CustomerFeatures):
    """
    Predict churn for a single customer.
    Returns prediction, probability, and risk level.
    """
    logger.info(f"Prediction request: age={customer.age}, tenure={customer.tenure_months}")
    result = make_prediction(customer)
    logger.info(f"Prediction result: {result.churn_label} ({result.churn_probability:.3f})")
    return result

@app.post("/predict/batch", response_model=BatchResponse)
def predict_batch(request: BatchRequest):
    """Predict churn for multiple customers at once."""
    predictions = [make_prediction(c) for c in request.customers]
    high_risk   = sum(1 for p in predictions if p.risk_level == "HIGH")
    return BatchResponse(
        predictions=predictions,
        total_customers=len(predictions),
        high_risk_count=high_risk,
    )
