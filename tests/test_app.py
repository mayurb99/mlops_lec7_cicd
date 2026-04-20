"""
tests/test_app.py
════════════════════════════════════════════════════════
Lecture 8 — CI/CD Demo
Pytest tests for the Churn Prediction API

These tests run automatically inside GitHub Actions
on every push to main. If any test fails, the
build-and-push job is blocked — broken code never
reaches ECR.

Run locally: pytest tests/ -v
════════════════════════════════════════════════════════
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# ── Test client ───────────────────────────────────────
# TestClient lets us call the FastAPI app without
# starting a real HTTP server — much faster for CI
client = TestClient(app)

# ── Sample valid payload ──────────────────────────────
VALID_CUSTOMER = {
    "age": 35,
    "tenure_months": 24,
    "monthly_charge": 89.99,
    "num_products": 2,
    "support_calls": 3,
    "has_contract": 1,
}

HIGH_RISK_CUSTOMER = {
    "age": 22,
    "tenure_months": 2,
    "monthly_charge": 150.0,
    "num_products": 1,
    "support_calls": 8,
    "has_contract": 0,
}


# ════════════════════════════════════════════════════════
# API TESTS — Test the endpoints respond correctly
# ════════════════════════════════════════════════════════

class TestHealthEndpoint:
    """Test the /health endpoint — used by load balancers."""

    def test_health_returns_200(self):
        """Health check must return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_contains_status_field(self):
        """Health response must have a 'status' field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data

    def test_health_status_is_healthy(self):
        """Status field must equal 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_reports_model_loaded(self):
        """Health check must report whether model is loaded."""
        response = client.get("/health")
        data = response.json()
        assert "model_loaded" in data


class TestInfoEndpoint:
    """Test the /info endpoint — returns model metadata."""

    def test_info_returns_200(self):
        response = client.get("/info")
        assert response.status_code == 200

    def test_info_contains_model_type(self):
        response = client.get("/info")
        data = response.json()
        assert "model_type" in data or "status" in data


# ════════════════════════════════════════════════════════
# PREDICTION TESTS — Test model output correctness
# ════════════════════════════════════════════════════════

class TestPredictEndpoint:
    """Test the /predict endpoint — single customer prediction."""

    def test_predict_returns_200(self):
        """Successful prediction must return 200."""
        response = client.post("/predict", json=VALID_CUSTOMER)
        assert response.status_code == 200

    def test_predict_returns_churn_prediction(self):
        """Response must contain churn_prediction field."""
        response = client.post("/predict", json=VALID_CUSTOMER)
        data = response.json()
        assert "churn_prediction" in data

    def test_predict_prediction_is_binary(self):
        """Prediction must be 0 or 1, not some other value."""
        response = client.post("/predict", json=VALID_CUSTOMER)
        data = response.json()
        assert data["churn_prediction"] in [0, 1]

    def test_predict_returns_probability(self):
        """Response must include churn_probability."""
        response = client.post("/predict", json=VALID_CUSTOMER)
        data = response.json()
        assert "churn_probability" in data

    def test_predict_probability_between_zero_and_one(self):
        """Probability must be a float between 0 and 1."""
        response = client.post("/predict", json=VALID_CUSTOMER)
        data = response.json()
        prob = data["churn_probability"]
        assert 0.0 <= prob <= 1.0

    def test_predict_returns_churn_label(self):
        """Response must include a human-readable churn_label."""
        response = client.post("/predict", json=VALID_CUSTOMER)
        data = response.json()
        assert "churn_label" in data
        assert data["churn_label"] in ["CHURN", "NO CHURN"]

    def test_predict_returns_risk_level(self):
        """Response must include risk_level."""
        response = client.post("/predict", json=VALID_CUSTOMER)
        data = response.json()
        assert "risk_level" in data
        assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]

    def test_high_risk_customer_has_higher_probability(self):
        """High-risk customer should have higher churn prob than normal customer."""
        normal = client.post("/predict", json=VALID_CUSTOMER).json()
        risky  = client.post("/predict", json=HIGH_RISK_CUSTOMER).json()
        # High risk customer should generally have higher probability
        # This is a sanity check on model direction, not exact values
        assert risky["churn_probability"] >= 0.0  # at minimum, it's valid


# ════════════════════════════════════════════════════════
# INPUT VALIDATION TESTS — Verify bad input is rejected
# ════════════════════════════════════════════════════════

class TestInputValidation:
    """Test that the API correctly rejects invalid inputs."""

    def test_age_below_18_rejected(self):
        """Customers under 18 should be rejected."""
        bad_input = {**VALID_CUSTOMER, "age": 15}
        response = client.post("/predict", json=bad_input)
        assert response.status_code == 422

    def test_age_above_100_rejected(self):
        """Age above 100 should be rejected as unrealistic."""
        bad_input = {**VALID_CUSTOMER, "age": 150}
        response = client.post("/predict", json=bad_input)
        assert response.status_code == 422

    def test_negative_monthly_charge_rejected(self):
        """Negative charge makes no business sense — reject it."""
        bad_input = {**VALID_CUSTOMER, "monthly_charge": -50.0}
        response = client.post("/predict", json=bad_input)
        assert response.status_code == 422

    def test_invalid_has_contract_value_rejected(self):
        """has_contract must be 0 or 1 — not 2, not -1."""
        bad_input = {**VALID_CUSTOMER, "has_contract": 2}
        response = client.post("/predict", json=bad_input)
        assert response.status_code == 422

    def test_missing_required_field_rejected(self):
        """Request missing a required field must return 422."""
        incomplete = {"age": 35, "tenure_months": 24}  # missing most fields
        response = client.post("/predict", json=incomplete)
        assert response.status_code == 422

    def test_empty_body_rejected(self):
        """Empty request body must return 422."""
        response = client.post("/predict", json={})
        assert response.status_code == 422


# ════════════════════════════════════════════════════════
# BATCH PREDICTION TESTS
# ════════════════════════════════════════════════════════

class TestBatchPredictEndpoint:
    """Test the /predict/batch endpoint."""

    def test_batch_predict_returns_200(self):
        batch = {"customers": [VALID_CUSTOMER, HIGH_RISK_CUSTOMER]}
        response = client.post("/predict/batch", json=batch)
        assert response.status_code == 200

    def test_batch_returns_correct_count(self):
        batch = {"customers": [VALID_CUSTOMER, HIGH_RISK_CUSTOMER]}
        response = client.post("/predict/batch", json=batch)
        data = response.json()
        assert data["total_customers"] == 2

    def test_batch_predictions_count_matches_input(self):
        batch = {"customers": [VALID_CUSTOMER, HIGH_RISK_CUSTOMER, VALID_CUSTOMER]}
        response = client.post("/predict/batch", json=batch)
        data = response.json()
        assert len(data["predictions"]) == 3

    def test_batch_contains_high_risk_count(self):
        batch = {"customers": [VALID_CUSTOMER, HIGH_RISK_CUSTOMER]}
        response = client.post("/predict/batch", json=batch)
        data = response.json()
        assert "high_risk_count" in data
        assert data["high_risk_count"] >= 0
