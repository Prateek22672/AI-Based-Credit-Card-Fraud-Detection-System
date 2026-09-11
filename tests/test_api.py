"""End-to-end API tests (need the trained artifacts: python -m fraudlens.pipeline all)."""
import pytest

from fraudlens import config

pytestmark = pytest.mark.skipif(not (config.ARTIFACTS / "model_card.json").exists(),
                                reason="run the pipeline first")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from fraudlens.api.main import app
    with TestClient(app) as c:
        c.post("/api/reset")
        yield c


@pytest.fixture(scope="module")
def card(client):
    return client.get("/api/cards?limit=5").json()[0]


def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["thresholds"]["alert"] <= r["thresholds"]["block"]


def test_card_numbers_are_tokenised(client, card):
    assert len(card["token"]) == 16 and len(card["last4"]) == 4
    assert "cc_num" not in card


def test_what_if_scoring_does_not_change_history(client, card):
    body = {"card_token": card["token"], "amount": 40.0, "category": "grocery_pos"}
    a, b = client.post("/api/score", json=body).json(), client.post("/api/score", json=body).json()
    assert a["probability"] == b["probability"]
    assert a["risk_level"] in {"LOW", "MEDIUM", "HIGH"} and 0 <= a["risk_score"] <= 100
    assert a["shap"] and "xgboost" in a["components"]


def test_suspicious_transaction_scores_higher_than_normal(client, card):
    normal = client.post("/api/score", json={"card_token": card["token"], "amount": card["mean_amt"],
                                              "category": "grocery_pos", "known_merchant": True}).json()
    night = client.post("/api/score", json={"card_token": card["token"], "amount": 1150.0,
                                             "category": "shopping_net",
                                             "timestamp": "2020-04-09T02:30:00"}).json()
    assert night["probability"] > normal["probability"]
    assert night["reasons"]


def test_stream_and_case_review(client):
    rows = client.post("/api/stream/next?n=40").json()
    assert len(rows) == 40 and all("label" in r for r in rows)
    stats = client.get("/api/stats").json()
    assert stats["total"] >= 40
    did = rows[0]["id"]
    r = client.post(f"/api/transactions/{did}/review", json={"label": "genuine", "note": "test"}).json()
    assert r["review_status"] == "dismissed" and r["features"]


def test_scenario_runs_in_sandbox(client, card):
    before = client.get(f"/api/cards/{card['token']}").json()["n_txns"]
    res = client.post("/api/scenarios/card_testing/run", json={"card_token": card["token"]}).json()
    assert len(res["steps"]) == 5
    assert res["steps"][-1]["probability"] >= res["steps"][0]["probability"]
    assert client.get(f"/api/cards/{card['token']}").json()["n_txns"] == before


def test_safety_layer_escalates_card_testing_and_impossible_travel(client):
    """Neither attack exists in the training data; the policy layer must still raise them."""
    for sid, rule in (("card_testing", "P3"), ("impossible_travel", "P2")):
        res = client.post(f"/api/scenarios/{sid}/run", json={}).json()
        assert res["verdict"] in ("MEDIUM", "HIGH"), sid
        fired = {h["id"] for s in res["steps"] for h in s["policy"]}
        assert rule in fired, (sid, fired)
        esc = [s for s in res["steps"] if s["policy"]]
        assert all(s["risk_level"] != "LOW" and s["risk_score"] > 30 for s in esc)
    normal = client.post("/api/scenarios/normal_day/run", json={}).json()
    assert normal["verdict"] == "LOW" and not any(s["policy"] for s in normal["steps"])


def test_stream_explains_alerts_and_detail_explains_on_demand(client):
    rows = client.post("/api/stream/next?n=300").json()
    low = next(r for r in rows if r["risk_level"] == "LOW")
    assert low["explained"] is False and low["shap"] == []
    full = client.get(f"/api/transactions/{low['id']}").json()
    assert full["shap"] and full.get("explained_on_demand") is True
    alerts = [r for r in rows if r["risk_level"] != "LOW"]
    assert all(r["explained"] and r["shap"] for r in alerts)


def test_validation_and_errors(client, card):
    assert client.post("/api/score", json={"card_token": card["token"], "amount": -5,
                                           "category": "grocery_pos"}).status_code == 422
    assert client.post("/api/score", json={"card_token": card["token"], "amount": 5,
                                           "category": "casino"}).status_code == 422
    assert client.post("/api/score", json={"card_token": "nope", "amount": 5,
                                           "category": "home"}).status_code == 404
