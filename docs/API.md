# FraudLens API reference

Base URL: `http://localhost:8000` (interactive Swagger docs at `/docs`).
All bodies are JSON. Card numbers never leave the server: cards are addressed by a 16-character
`token` (keyed HMAC-SHA256 of the card number) and shown as `last4`.

If the environment variable `FRAUDLENS_API_KEY` is set, every `POST` endpoint requires the header
`X-API-Key: <key>`.

## System

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness + model version, stream progress, thresholds |
| GET | `/api/model` | Model card: features, thresholds, stacking weights, test metrics, latency, category list |
| GET | `/api/results/{name}` | Research results: `benchmark_sparkov`, `benchmark_ulb`, `imbalance_sparkov`, `protocol`, `ablation`, `unseen`, `analysis`, `explain`, `dataset_sparkov`, `policy`, `scenarios`, `latency` |
| GET | `/figures/{file}.png` | Report figures (e.g. `fig_pr_roc_curves.png`) |

`GET /api/health`
```json
{"status": "ok", "model_version": "fraudlens-hybrid-1.0", "cards": 983, "stream_position": 0,
 "stream_total": 182774, "simulated_clock": "2020-04-08T00:00:12",
 "thresholds": {"alert": 0.061, "block": 0.52}}
```

## Scoring

`POST /api/score`: score one transaction in real time.
```json
{"card_token": "3f9a0c1b2d4e5f60", "amount": 1150.0, "category": "shopping_net",
 "timestamp": "2020-04-09T02:30:00", "distance_km": 12, "known_merchant": false, "commit": false}
```
* `category`: one of `entertainment, food_dining, gas_transport, grocery_net, grocery_pos, health_fitness,
  home, kids_pets, misc_net, misc_pos, personal_care, shopping_net, shopping_pos, travel`
* `timestamp` optional (default: one hour after the card's last transaction)
* `distance_km` or `merch_lat`/`merch_long` place the merchant; `known_merchant` reuses a merchant the card has used
* `commit=false` is what-if scoring: the card's history is not changed

Response (`ScoreResult`, also used by the stream and scenarios):
```json
{
  "id": 17, "card_token": "3f9a0c1b2d4e5f60", "card_last4": "4821",
  "txn_time": "2020-04-09T02:30:00", "unix": 1586399400, "amount": 1150.0,
  "category": "shopping_net", "category_label": "Online shopping", "merchant": "Unknown merchant",
  "merch_lat": 40.1, "merch_long": -75.0, "home": {"city": "Moravian Falls", "state": "NC", "lat": 36.0, "long": -81.1},
  "probability": 0.9731, "risk_score": 88.4, "risk_level": "HIGH", "decision": "BLOCK",
  "ml_risk_score": 88.4, "ml_risk_level": "HIGH",
  "policy": [{"id": "N1", "title": "Novelty alarm (Isolation Forest)", "level": "MEDIUM",
              "reason": "Novelty alarm: behaviour more unusual than 99.97% of normal transactions; possible new fraud pattern"}],
  "components": {"xgboost": 0.998, "random_forest": 0.91, "anomaly_percentile": 0.9997},
  "reasons": ["Novelty alarm: behaviour more unusual than 99.97% of normal transactions; possible new fraud pattern",
              "Amount $1,150.00 is 19.3x this card's average spend ($60)", "Made late at night (02:00-03:00)"],
  "mitigating": ["Merchant is close to the cardholder's usual area"],
  "shap": [{"feature": "amt", "label": "Amount", "value": 1150.0, "shap": 3.1}],
  "groups": [{"group": "amount", "label": "Transaction amount", "shap": 4.2}],
  "card": {"n_txns": 1432, "mean_amt": 81.2, "std_amt": 120.4, "txns_per_day": 3.1, "night_share": 0.12,
           "top_categories": ["grocery_pos", "gas_transport", "home"], "last_ts": 1586310000, "n_merchants": 512},
  "features": {"amt": 1150.0, "cnt_1h": 0, "...": 0},
  "latency_ms": 6.2, "model_version": "fraudlens-hybrid-1.0"
}
```
`risk_level` / `decision`: `LOW/APPROVE`, `MEDIUM/STEP_UP` (OTP / analyst review), `HIGH/BLOCK`.
`risk_score` is 0-100 with band edges at 30 and 60, placed exactly on the learned thresholds.

**Safety layer.** `risk_level`, `decision` and `risk_score` are final, after the safety layer. `ml_risk_level` and
`ml_risk_score` are what the ML alone decided. `policy` lists the rules that fired (`P1` burst then jump, `P2`
impossible travel, `P3` micro-charge burst, `N1` novelty alarm); a rule can only raise a decision to at least
`STEP_UP`. When a rule escalates a LOW transaction, `risk_score` is lifted to 31 so the gauge matches the tier.

**Explanations.** `/api/score` and scenarios always return `reasons`, `mitigating` and `shap`. The replay stream
explains alerts immediately and returns `"explained": false` for approved transactions; their full explanation is
computed on demand by `GET /api/transactions/{id}` (exact TreeSHAP is the most expensive step of scoring).

## Live demo (replay of the unseen test period)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/stream/next?n=25` | Score the next *n* test-period transactions in time order. Returns `ScoreResult[]`, each with the dataset `label` (1 = fraud) |
| GET | `/api/stream/status` | Stream pointer, total, simulated clock |
| POST | `/api/reset` | Restart the replay: restore card state and clear the decision log |
| GET | `/api/stats` | Live KPIs (see below) |

`GET /api/stats`
```json
{"total": 5000, "levels": {"LOW": 4960, "MEDIUM": 22, "HIGH": 18}, "alerts": 40, "blocked": 18,
 "frauds_seen": 31, "frauds_caught": 30, "frauds_blocked": 17, "frauds_missed": 1, "false_alarms": 10,
 "precision": 0.75, "recall": 0.97, "fraud_amount": 15890.2, "fraud_amount_stopped": 15702.1,
 "false_alarm_rate": 0.002, "avg_latency_ms": 5.1,
 "risk_histogram": [{"bucket": "0-10", "count": 4900}],
 "timeline": [{"day": "2020-04-08", "transactions": 2400, "alerts": 20, "blocked": 9, "frauds": 14}],
 "alerts_by_category": {"shopping_net": 12},
 "reviews": {"open": 30, "confirmed": 5, "dismissed": 5, "n/a": 4960},
 "stream": {"...": "same as /api/health"}}
```

## Case management (forensic decision log)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/transactions?limit=100&level=MEDIUM,HIGH&source=stream&status=open` | Logged decisions, newest first |
| GET | `/api/transactions/{id}` | Full audit record: feature vector, reasons, model version, review |
| POST | `/api/transactions/{id}/review` | Analyst verdict `{"label": "fraud" \| "genuine", "note": "..."}` |

Decision record:
```json
{"id": 12, "source": "stream", "card_token": "...", "card_last4": "4821", "txn_time": "2020-04-08T01:12:44",
 "amount": 912.5, "category": "shopping_net", "category_label": "Online shopping", "merchant": "Kub-Mann",
 "probability": 0.99, "risk_score": 97.0, "risk_level": "HIGH", "decision": "BLOCK",
 "components": {"xgboost": 0.99, "random_forest": 0.95, "anomaly_percentile": 0.99},
 "reasons": ["..."], "label": 1, "review_status": "open", "latency_ms": 4.8}
```
`review_status`: `open` (alert awaiting review), `confirmed` (fraud), `dismissed` (genuine), `n/a` (approved, no review needed).

## Cards

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/cards?limit=60` | Cards with the longest histories: `{token, last4, city, state, n_txns, mean_amt, night_share}` |
| GET | `/api/cards/{token}` | Profile + behaviour summary + 20 most recent decisions |

## Scam scenarios

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/scenarios` | `[{id, title, scam, signals[], n_steps}]` |
| POST | `/api/scenarios/{id}/run` | Body `{"card_token": "..."}` (optional). Plays the attack against a sandbox copy of the card |

Scenario ids: `card_testing`, `stolen_card_spree`, `midnight_online`, `impossible_travel`, `escalation`, `normal_day`.

Response: `{"scenario": {...}, "card": {...}, "steps": [ScoreResult + {"step": 1, "minutes_from_start": 0}], "verdict": "HIGH"}`
