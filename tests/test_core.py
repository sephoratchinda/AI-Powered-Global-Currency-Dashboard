import math, numpy as np, pytest
from fastapi.testclient import TestClient
from app import analytics as an, ml
from app.main import app


def test_pct_change():
    assert an.pct_change(110, 100) == pytest.approx(10)


def test_volatility_zero_for_flat_series():
    assert an.volatility([1.0] * 20) == 0


def test_volatility_positive_and_labels():
    v = list(np.cumprod(1 + np.random.default_rng(1).normal(0, .01, 100)))
    assert an.volatility(v) > 5 and an.vol_label(3) == "Low" and an.vol_label(20) == "High"


def test_sentiment_scoring():
    assert an.score_headline("Dollar rallies on strong growth") == 1
    assert an.score_headline("Euro falls on recession fear") == -1
    assert an.score_headline("Markets await decision") == 0


def test_forecast_shape_and_bands():
    rng = np.random.default_rng(0)
    v = 80 * np.exp(np.cumsum(rng.normal(0, .003, 300)))
    r = ml.forecast(v, 7)
    assert len(r["forecast"]) == 7 and r["model"] in r["metrics"]
    assert all(l < f < u for l, f, u in zip(r["lower"], r["forecast"], r["upper"]))


def test_forecast_needs_history():
    with pytest.raises(ValueError):
        ml.forecast([1.0] * 20)


def test_api_validation():
    with TestClient(app) as c:
        assert c.get("/api/currencies").json()[0] == "USD"
        assert c.get("/api/convert?amount=1&from=XXX&to=INR").status_code == 400
        assert c.post("/api/alerts", json={"pair": "bad", "direction": "above", "threshold": 1}).status_code == 422
        a = c.post("/api/alerts", json={"pair": "USD/INR", "direction": "above", "threshold": 90})
        assert a.status_code == 201
        assert c.delete(f"/api/alerts/{a.json()['id']}").status_code == 200
        assert c.delete("/api/alerts/99999").status_code == 404
