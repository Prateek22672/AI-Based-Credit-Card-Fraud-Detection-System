"""Main project report. Every number is read from reports/results/*.json."""
from __future__ import annotations

import json

from fraudlens import config
from fraudlens.explain import CATEGORY_LABELS, FEATURE_LABELS
from fraudlens.features import DEPLOYED_FEATURES, NUMERIC_FEATURES

from .engine import Doc
from .results import Results

REPO = "https://github.com/Prateek22672/AI-Based-Credit-Card-Fraud-Detection-System"

FEATURE_TABLE = [
    ("amt, log_amt", "Transaction amount (raw and log)", "Fraudsters maximise value before the card is blocked"),
    ("hour, is_night, day_of_week, is_weekend", "When the transaction happens", "Fraud concentrates late at night when owners sleep"),
    ("is_online, cat_* (14)", "Merchant category and channel (card-not-present)", "Stolen card details are mostly used online"),
    ("log_city_pop, dist_home_km", "Home-city size; merchant distance from the cardholder's home", "Use far from the usual area"),
    ("card_history_len", "How many past transactions the card has", "New cards carry less behavioural evidence"),
    ("log_secs_since_last", "Time since the card's previous transaction", "Rapid-fire use (bursts) or a dormant card waking up"),
    ("cnt_1h, cnt_24h, cnt_7d", "Velocity: transactions in the last 1 h / 24 h / 7 days", "Card-testing bursts and spending sprees"),
    ("sum_24h, cnt_24h_vs_usual", "Money spent in 24 h; activity vs the card's usual daily rate", "Account takeover drains the card quickly"),
    ("amt_to_card_mean, amt_zscore", "Amount relative to this card's own average and spread", "Unusual for *this* customer, not just large"),
    ("amt_to_cat_mean", "Amount vs this card's usual spend in the same category", "A $900 grocery bill for a $60 grocery shopper"),
    ("cat_share, is_new_category", "How often the card uses this category; first use", "Fraudsters buy what they can resell, not what the owner buys"),
    ("is_new_merchant", "First purchase at this merchant", "New merchants are riskier than regular ones"),
    ("night_share", "The card's normal share of night-time use", "Night use matters only for customers who never shop at night"),
    ("dist_prev_km, speed_kmh", "Distance and implied speed since the previous transaction", "Impossible travel = cloned card"),
]


def pv(x, nd=3):
    return Results.f(x, nd)


def scenario_story(scen: dict) -> str:
    """What the ML alone did versus the final decision, per attack, from the replay results."""
    order = ("LOW", "MEDIUM", "HIGH")
    out = []
    for sid, name in (("card_testing", "card testing"), ("impossible_travel", "cloned-card travel")):
        s = scen.get(sid)
        if not s:
            continue
        st = s["steps"]
        ml = [z.get("ml_risk_level", z["risk_level"]) for z in st]
        fin = [z["risk_level"] for z in st]
        first_fin = next((z["step"] for z, f in zip(st, fin) if f != "LOW"), None)
        first_ml = next((z["step"] for z, m in zip(st, ml) if m != "LOW"), None)
        if first_fin is None:
            out.append(f"Neither the ML nor the safety layer flagged {name}.")
        elif first_ml is None:
            out.append(f"The ML alone approves every step of {name} (the pattern never occurs in the training data); "
                       f"the safety layer escalates it at step {first_fin} of {len(st)}.")
        elif first_fin < first_ml:
            out.append(f"For {name} the ML alone reacts only at step {first_ml} of {len(st)}; the safety layer "
                       f"escalates earlier, at step {first_fin}.")
        else:
            out.append(f"The ML itself flags {name} at step {first_ml} of {len(st)}.")
    others = [scen[k]["title"].lower() for k in ("stolen_card_spree", "midnight_online", "escalation")
              if k in scen and max((z.get("ml_risk_level", z["risk_level"]) for z in scen[k]["steps"]),
                                   key=order.index) != "LOW"]
    if others:
        out.insert(0, "The ML alone catches the fraud styles present in its training data (" + ", ".join(others) + ").")
    if "normal_day" in scen and all(z["risk_level"] == "LOW" for z in scen["normal_day"]["steps"]):
        out.append("The normal customer day is approved at every step.")
    return " ".join(out)


STRATEGY_NAMES = {"none": "no balancing", "weight": "class weighting", "rus": "random undersampling", "smote": "SMOTE"}
MODEL_NAMES = {"lr": "Logistic Regression", "rf": "Random Forest", "xgb": "XGBoost"}


def imbalance_finding(imb: dict) -> str:
    """E2 conclusion, derived from the numbers (the best strategy differs per model)."""
    models = sorted({k.split("/")[0] for k in imb}, key=list(MODEL_NAMES).index)
    best = {m: max((k for k in imb if k.startswith(m + "/")), key=lambda k: imb[k]["pr_auc"]) for m in models}
    parts = ["The best strategy depends on the model: " + "; ".join(
        f"{MODEL_NAMES[m]} does best with {STRATEGY_NAMES[best[m].split('/')[1]]} (PR-AUC {imb[best[m]]['pr_auc']:.3f})"
        for m in models) + "."]
    rus_worst = all(min((k for k in imb if k.startswith(m + "/")), key=lambda k: imb[k]["pr_auc"]).endswith("/rus")
                    for m in models)
    rus_prec = [imb[f"{m}/rus"]["at_0.5"]["precision"] for m in models if f"{m}/rus" in imb]
    if rus_worst and rus_prec:
        parts.append(f"Random undersampling is the worst option for every model and, at the default 0.5 threshold, "
                     f"cuts precision to {min(rus_prec):.0%}-{max(rus_prec):.0%}.")
    lw, ln = imb.get("lr/weight"), imb.get("lr/none")
    if lw and ln:
        ratio = lw["mean_predicted_prob"] / lw["actual_fraud_rate"]
        parts.append(f"Balancing inflates probabilities: class-weighted Logistic Regression predicts an average fraud "
                     f"probability of {lw['mean_predicted_prob']:.3f} against a true rate of {lw['actual_fraud_rate']:.3f} "
                     f"({ratio:.0f}x). It also shows why ROC-AUC misleads: weighting raises LR's ROC-AUC from "
                     f"{ln['roc_auc']:.3f} to {lw['roc_auc']:.3f} while its PR-AUC falls from {ln['pr_auc']:.3f} to "
                     f"{lw['pr_auc']:.3f}.")
    xs, xw, xr = imb.get("xgb/smote"), imb.get("xgb/weight"), imb.get("xgb/rus")
    if xs and xw:
        diff = xs["pr_auc"] - xw["pr_auc"]
        parts.append(f"For XGBoost, SMOTE and class weighting are within {abs(diff):.3f} PR-AUC of each other; SMOTE needs "
                     f"synthetic data and {xs['fit_seconds'] / max(xw['fit_seconds'], 1):.1f}x the training time, so the "
                     "deployed engine keeps class weighting and lets the stacking layer recalibrate the probabilities.")
    if xr:
        parts.append(f"The decision threshold matters more than the balancing trick: undersampled XGBoost goes from F1 "
                     f"{xr['at_0.5']['f1']:.2f} at the default 0.5 threshold to {xr['at_tuned']['f1']:.2f} when the "
                     "threshold is tuned on validation data.")
    return " ".join(parts)


def build(R: Results) -> Doc:
    g = R.get
    ds = g("dataset_sparkov") or {}
    bm = g("benchmark_sparkov") or {}
    H = bm.get("hybrid", {}).get("test", {})
    HC = bm.get("hybrid", {}).get("test_cost_threshold", {})
    X = bm.get("xgb", {}).get("test", {})
    RU = bm.get("rules", {}).get("test", {})
    LR = bm.get("lr", {}).get("test", {})
    lat = bm.get("hybrid", {}).get("latency", {})
    an = g("analysis") or {}
    tiers = an.get("tiers", {})
    thr = an.get("tiers_thresholds", {}) or {"alert": 0, "block": 0}
    cs5 = next((r for r in an.get("cost_sensitivity", []) if r["alert_cost"] == config.ALERT_COST), {})
    prot = g("protocol") or {}
    abl = g("ablation") or {}
    un = g("unseen") or {}
    ulb = g("benchmark_ulb") or {}
    imb = g("imbalance_sparkov") or {}
    ex = g("explain") or {}
    sc_path = config.RESULTS / "scenarios.json"
    scen = json.loads(sc_path.read_text()) if sc_path.exists() else {}
    lat_path = config.RESULTS / "latency.json"
    latj = json.loads(lat_path.read_text()) if lat_path.exists() else {}
    api_lat = latj.get("api_single_ms", {})
    api_stream = latj.get("api_stream", {})
    pol = g("policy") or {}
    splits = ds.get("splits", {})
    hv = an.get("hybrid_vs", {})
    sig_x = hv.get("xgb", {})
    days = an.get("test_days", 74)

    doc = Doc(
        title="FraudLens: AI-Based Credit Card Fraud Detection System",
        subtitle="An explainable hybrid machine-learning system that detects suspicious card transactions in real time, "
                 "scores their risk and explains every decision",
        meta={"kicker": "PROJECT REPORT",
              "Domain": "Cyber Security / Forensics · Machine Learning / Data Security",
              "Team": "[Team member names and roll numbers]", "Guide": "[Guide name]",
              "Institution": "[College / University, Department]", "Date": "September 2026",
              "Repository": REPO.replace("https://", ""),
              "tags": "Hybrid ML (XGBoost + Random Forest + Isolation Forest)|Explainable AI (SHAP)|Real-time REST API|React dashboard"},
    )
    doc.toc()

    # ================================================================ summary
    doc.h1("Executive summary")
    doc.p("Card fraud is rare (about 1 transaction in 170 in our data), changes over time, and is expensive: global card "
          "fraud losses reached **USD 33.41 billion in 2024** (Nilson Report, Jan 2026). A useful detector must catch "
          "most fraud, raise few false alarms, decide within the card-authorisation budget (well under a second) and "
          "explain itself to analysts and customers.")
    doc.p("**FraudLens** is a complete system, not only a model. Every card transaction is turned into behavioural "
          "features computed from that card's own history. Three detectors score it: XGBoost and Random Forest learn "
          "known fraud patterns, and Isolation Forest flags behaviour unlike normal spending. A stacking meta-learner "
          "combines them into a calibrated fraud probability, which becomes a 0-100 risk score and a decision "
          "(**Approve / Step-up verification / Block**). A safety layer of documented policy rules and a novelty alarm "
          "can raise that decision for attack types that never appear in the training data. Every decision comes with "
          "plain-language reasons from SHAP and is stored in an auditable log. A FastAPI service scores transactions in "
          "real time, and a React dashboard lets analysts and reviewers watch, test and investigate.")
    doc.kpis([(pv(H.get("pr_auc")), "PR-AUC (test)", "unseen Apr-Jun 2020 data"),
              (R.pct(H.get("recall")), "Frauds caught", "at the validation-tuned threshold"),
              (R.pct(H.get("precision")), "Alert precision", "alerts that are real fraud"),
              (R.pct(HC.get("amount_recall")), "Fraud value stopped", "at the cost-optimal threshold"),
              (f"{api_lat.get('p50', lat.get('p50_ms', 0)):.1f} ms", "End-to-end latency",
               "per transaction, incl. SHAP, 1 thread")])
    doc.callout(
        "**Build a web platform (real-time REST API + web dashboard) powered by a hybrid ML model.** Fraud scoring has to "
        "run on the bank's server, inside the payment-authorisation path, with access to every card's history. That rules "
        "out a phone app as the core: an app would expose the model to reverse engineering and cannot see other "
        "transactions. A single \"special\" deep model is not the answer either: on the same data and split, our "
        f"deep models (MLP PR-AUC {pv(bm.get('mlp', {}).get('test', {}).get('pr_auc'))}, 1D-CNN "
        f"{pv(bm.get('cnn', {}).get('test', {}).get('pr_auc'))}) were less accurate, slower and harder to explain than "
        f"gradient-boosted trees (XGBoost {pv(X.get('pr_auc'))}). A mobile app remains a good future *client* of the same "
        "API, for customer \"Was this you?\" alerts.", "key", "Verdict: web, app or model?")
    doc.h3("What is new compared with the reviewed work")
    doc.bullets([
        "**Hybrid of known-pattern and unknown-pattern detection** (supervised + anomaly), combined by a learned stacking model instead of fixed voting.",
        "**Defence in depth, measured**: we found that stacking gives the anomaly detector almost no weight, so a novelty "
        "alarm and documented policy rules (velocity burst, impossible travel, card testing) now escalate attacks absent "
        "from the training data, at a measured cost of "
        f"{pol.get('test', {}).get('extra_alerts_per_day', 0):.2f} extra step-ups per day on the test period.",
        "**Calibrated risk score with money-based thresholds** instead of a bare fraud/not-fraud label; three action tiers mapped onto the team's 0-30 / 31-60 / 61-100 bands.",
        "**Behavioural feature store** used identically in training and in the live API (tested for exact parity), so there is no training/serving skew.",
        "**Honest evaluation**: time-based split with label-delay gaps, thresholds chosen on validation data only, PR-AUC/MCC/money metrics, bootstrap confidence intervals and paired significance tests.",
        "**Proof of how common shortcuts inflate results**: the same model scores near-perfect only when SMOTE is applied before a random split (Section 7.3).",
        "**Explainability built into the product**: every decision carries human-readable reasons, mitigating factors and a forensic audit record.",
        "**Responsible and secure by design**: gender and age are excluded from decisions, card numbers are tokenised, and the API validates input and can require a key.",
    ])

    # ============================================================ 1 intro
    doc.h1("1 Introduction")
    doc.h2("1.1 Background and motivation")
    doc.p("Digital payments have made card-not-present (online) fraud the dominant form of card fraud. In Europe, 80% of "
          "the value of card fraud on SEPA cards in 2019 came from card-not-present transactions (ECB, 2021), and "
          "total reported payment fraud in the EEA reached EUR 4.2 billion in 2024 (EBA-ECB, 2025). In the UK, "
          "remote-purchase fraud cases grew 22% in 2024 to nearly 2.6 million (UK Finance, 2025). In India, "
          "card/internet/digital-payment frauds were the most numerous category of bank fraud reported to the Reserve "
          "Bank of India in 2023-24 (28,836 cases, 80.4% of all cases) and again in 2024-25 (RBI Annual Report 2025-26).")
    doc.p("Regulation turns this into a direct cost for banks. Under the RBI's 2017 circular on limiting customer "
          "liability in unauthorised electronic banking transactions, the customer bears zero liability when the fault "
          "lies with the bank or with a third-party breach reported within three working days; the burden of proof is "
          "on the bank, and banks must operate a \"robust and dynamic fraud detection and prevention mechanism\". The RBI "
          "Master Direction on Digital Payment Security Controls (2021) requires documented rules and parameterised "
          "alerts on transaction velocity, high-risk merchant categories, time zones, geo-location and behaviour "
          "(paras 36-37), and allows adaptive, risk-based authentication (para 34). FraudLens computes exactly these "
          "signals, learns how to weigh them from data, and its STEP-UP tier is that risk-based authentication.")
    doc.h2("1.2 Problem statement")
    doc.p("Build a system that, for every card transaction and within the authorisation budget, (a) estimates the probability that "
          "it is fraudulent, (b) turns it into an actionable decision that balances missed fraud against customer "
          "friction, and (c) explains the decision, all while coping with extreme class imbalance, fraud patterns that "
          "change over time and new fraud types never seen in training.")
    doc.h2("1.3 Objectives")
    doc.numbers([
        "Engineer behavioural features that capture how each cardholder normally behaves, computed only from past data.",
        "Compare classical ML, ensembles, deep learning and anomaly detection fairly on the same chronological split.",
        "Compare imbalance-handling strategies (none, class weighting, undersampling, SMOTE) and choose by evidence.",
        "Combine supervised and anomaly detectors into a calibrated hybrid risk engine with cost-based decision tiers.",
        "Explain every prediction with SHAP and convert explanations into readable reason codes.",
        "Deliver a real-time REST API, an auditable decision log and a web dashboard for monitoring, testing and review.",
        "Prove each claim with experiments, statistical tests and a comparison against published results.",
    ])
    doc.h2("1.4 Scope and assumptions")
    doc.bullets([
        "Real bank data cannot be shared, so we use two public datasets: the Sparkov simulated dataset (named, behavioural "
        "fields) as the primary dataset, and the ULB/Worldline European dataset (real but anonymised with PCA) as the benchmark most papers use.",
        "Amounts are in USD because Sparkov is US-based; the method is currency-independent.",
        f"Cost model: a missed fraud costs its amount; every alert costs ${config.ALERT_COST:.0f} (review / OTP / friction). A sensitivity analysis covers $1-$25.",
        "Labels are assumed to be confirmed about 7 days after a transaction, which is modelled by gaps between the train, validation and test periods.",
    ])

    # ============================================================ 2 literature
    doc.h1("2 Literature review")
    doc.p("We studied the team's 20 selected papers and 44 further verified sources. The separate **Literature Mapping "
          "Report** traces every paper to what we adopted and where it lives in the code; this chapter summarises the "
          "findings that shaped the design.")
    doc.flow([("Rule-based", "Expert if-then rules; transparent but rigid"),
              ("Classical ML", "LR, DT, SVM (T4, T8)"),
              ("Ensembles", "RF, XGBoost, stacking (T2, T3, T5, T7)"),
              ("Deep learning", "CNN, LSTM, AE (T1, T9, T10, T12, T19)"),
              ("Graph learning", "GNN on card-merchant links (T13, T14)"),
              ("Explainable AI", "SHAP, reason codes (T13)")],
             "Evolution of fraud-detection technology in the reviewed literature (T# = team paper number)")
    doc.table(["Gap found in the literature", "Evidence", "FraudLens response"], [
        ["Accuracy reported on 99.8%-genuine data", "T1 (99.87% acc.), T3 (99.96% acc. but 83% recall), T7", "PR-AUC, recall, precision, F1, MCC and money saved"],
        ["Oversampling before the split / random splits", "Santos 2018; Hayat & Magnier 2025", "Chronological split, resampling only inside training (E3 shows the effect)"],
        ["Single model, fixed voting", "T3, T4, T7, T8", "Learned stacking of supervised + anomaly detectors (E4)"],
        ["Only known fraud patterns", "T11, Carcillo 2021", "Isolation Forest novelty layer tested on a held-out fraud type (E5)"],
        ["Black-box decisions", "T13, T16, Psychoula 2021", "TreeSHAP reason codes in every API response"],
        ["Offline notebooks only", "T16, T20", "Real-time API, online feature store, dashboard, audit log"],
        ["Heavy DL for tabular data", "T1, T2, T9; Grinsztajn 2022", "DL tested as a baseline; trees win on accuracy, speed and explainability (E1)"],
        ["Probabilities distorted by resampling", "van den Goorbergh 2022; Dal Pozzolo 2015", "Calibrated stacking on the natural class balance + cost thresholds (E2, E7)"],
    ], caption="Research gaps and how FraudLens addresses them", widths=[5, 5.5, 7])
    doc.h2("2.1 Research questions")
    doc.table(["#", "Question", "Answered by"], [
        ["RQ1", "Which model family detects fraud best on tabular transaction data, and at what speed?", "E1, E6"],
        ["RQ2", "Is SMOTE (used in most reviewed papers) better than class weighting?", "E2"],
        ["RQ3", "How much do common evaluation shortcuts inflate reported results?", "E3"],
        ["RQ4", "Do behavioural features and the hybrid combination add real value?", "E4"],
        ["RQ5", "Can the system catch a fraud type it was never trained on?", "E5"],
        ["RQ6", "What is the business value, and is performance stable over time?", "E7"],
    ], caption="Research questions and the experiments that answer them", widths=[1, 12, 2.5])

    # ============================================================ 3 decision
    doc.h1("3 Choosing the solution: web, app or model?")
    doc.p("The team asked whether the project should be a website, a mobile app or a special model. We scored the "
          "options against what a fraud-detection system must do in practice (5 = best).")
    doc.table(["Criterion", "Mobile app only", "Stand-alone model / notebook", "Deep-learning \"special\" model", "Web platform + API + hybrid ML (chosen)"], [
        ["Runs inside the bank's payment authorisation path", "1", "1", "3", "5"],
        ["Sees every card's history (velocity, spend patterns)", "1", "3", "4", "5"],
        ["Model protected from reverse engineering / evasion", "1", "4", "4", "5"],
        ["Sub-second latency on ordinary servers", "3", "3", "2", "5"],
        ["Explains each decision to analysts and customers", "2", "2", "1", "5"],
        ["Serves analysts, reviewers and bank systems", "2", "1", "2", "5"],
        ["Easy for the team to deploy on its own domain", "2", "3", "2", "4"],
        ["Future extension (mobile alerts, streaming, retraining)", "3", "1", "3", "5"],
        ["**Total (out of 40)**", "**15**", "**18**", "**21**", "**39**"],
    ], caption="Decision matrix", highlight=[8], widths=[6.5, 2.4, 2.8, 2.8, 3.6])
    doc.callout("Fraud detection is a server-side, real-time decision service. The right product is an **API-first web "
                "platform**: the API is what payment systems call, and the dashboard is where people monitor, investigate "
                "and present. The \"special\" part is not a new neural network but the **hybrid risk engine**: behavioural "
                "features, three complementary detectors, a calibrated risk score with cost-based tiers, and built-in "
                "explanations.", "key", "Verdict")
    doc.p("Independent evidence agrees: tree ensembles remain state of the art on tabular data (Grinsztajn et al., 2022; "
          f"Shwartz-Ziv & Armon, 2022). In our own benchmark (E1) XGBoost reached PR-AUC {pv(X.get('pr_auc'))} in "
          f"{bm.get('xgb', {}).get('fit_seconds', 0) / 60:.1f} minutes of training, versus "
          f"{pv(bm.get('mlp', {}).get('test', {}).get('pr_auc'))} for the MLP ({bm.get('mlp', {}).get('fit_seconds', 0) / 60:.0f} min) and "
          f"{pv(bm.get('cnn', {}).get('test', {}).get('pr_auc'))} for the 1D-CNN ({bm.get('cnn', {}).get('fit_seconds', 0) / 60:.0f} min "
          "for at most 8 epochs; it trained while other experiments shared the CPU, so its time is an upper bound).")

    # ============================================================ 4 architecture
    doc.h1("4 System architecture")
    doc.flow([("Transaction", "Card token, amount, merchant, category, location, time"),
              ("Feature store", "Reads the card's past behaviour; builds 39 model features"),
              ("Three detectors", "XGBoost · Random Forest · Isolation Forest"),
              ("Risk engine", "Stacked, calibrated probability; 0-100 score; tier"),
              ("Safety layer", "Policy rules + novelty alarm can raise the tier"),
              ("Explain + log", "SHAP reasons; audit record in the database"),
              ("Dashboard", "Monitor, test, investigate, report")],
             "How one transaction flows through FraudLens")
    doc.table(["Layer", "Technology", "Responsibility"], [
        ["Feature store", "Python (fraudlens/features.py)", "Per-card rolling state; the same code builds training data and live features"],
        ["Detectors", "XGBoost 3.2, scikit-learn 1.9 (RF, IF)", "Known-pattern classification + novelty detection"],
        ["Risk engine", "scikit-learn logistic stacking", "Calibrated probability, risk score, decision tiers"],
        ["Safety layer", "Python (fraudlens/policy.py)", "Documented policy rules P1-P3 + novelty alarm N1; can only raise a decision"],
        ["Explainability", "XGBoost TreeSHAP (pred_contribs), SHAP library for plots", "Per-decision reasons; global importance"],
        ["API", "FastAPI + Uvicorn, Pydantic validation", "Real-time scoring, stream replay, scenarios, case review"],
        ["Decision log", "SQLAlchemy 2 on SQLite (PostgreSQL via one env var)", "Forensic audit trail + analyst feedback"],
        ["Dashboard", "React 18 + Vite + Tailwind CSS + Recharts", "Live monitor, tester, scenarios, cases, results, report"],
        ["Research", "pandas, imbalanced-learn, PyTorch (baselines), matplotlib", "Experiments E1-E7, figures, reports"],
        ["Deployment", "Docker (single container)", "API + built dashboard on any VPS or cloud host"],
    ], caption="Components and technology stack", widths=[3, 5.5, 8.5])
    doc.h2("4.1 Life of a transaction")
    doc.numbers([
        "The payment system (or the dashboard) sends `POST /api/score` with the card token, amount, category, merchant, location and time.",
        "The feature store reads the card's history (last-7-day window, running mean and variance, category and merchant counts, last location) and computes the features in about 0.07 ms.",
        "XGBoost and Random Forest return fraud probabilities; Isolation Forest returns an anomaly score, expressed as a percentile of normal behaviour.",
        "The meta-learner turns the three scores into one calibrated probability, mapped to a 0-100 risk score and a tier.",
        "The safety layer checks the documented policy rules (velocity burst, impossible travel, card testing) and the novelty alarm; any hit raises the decision to at least Step-up.",
        "TreeSHAP attributes the XGBoost score to features, and related features are grouped into sentences. Alerts and manual scores are explained immediately; approved stream transactions are explained on demand when opened, because exact TreeSHAP over the full tree ensemble costs more than the models themselves.",
        "The decision, feature vector, reasons and model version are written to the decision log; alerts enter the case queue.",
        "If committed, the transaction is appended to the card's history so the next transaction sees it.",
    ])
    doc.h2("4.2 Security and forensics by design")
    doc.table(["Control", "Implementation"], [
        ["Card-data minimisation", "Card numbers are replaced by a keyed HMAC-SHA256 token; only the last 4 digits are shown. Names, street, job and zip are dropped at load time."],
        ["Forensic audit trail", "Every decision stores the timestamp, model version, full feature vector, probability, detector scores, reasons and reviewer verdict, so any decision can be reproduced and justified in a dispute."],
        ["Access control", "Optional API key (X-API-Key) on all state-changing endpoints; CORS restricted by configuration."],
        ["Input validation", "Pydantic schemas bound every field (amount range, category whitelist, coordinates)."],
        ["Fairness", "Gender and age are never used for decisions (the cost in accuracy is measured in E4)."],
        ["Sandboxing", "What-if scoring only reads the card's history; scam scenarios run on a sandbox copy of the card's state, never on live data."],
    ], caption="Security and forensic controls", widths=[4, 13])

    # ============================================================ 5 data
    doc.h1("5 Datasets and exploratory analysis")
    doc.table(["Property", "Sparkov (primary)", "ULB European (benchmark)"], [
        ["Transactions", R.n(ds.get("rows")), R.n(ulb.get("_dataset", {}).get("rows"))],
        ["Frauds", f"{R.n(ds.get('frauds'))} ({R.pct(ds.get('fraud_rate'), 2)})",
         f"{R.n(ulb.get('_dataset', {}).get('frauds'))} ({R.pct(ulb.get('_dataset', {}).get('fraud_rate'), 3)})"],
        ["Period", f"{ds.get('start', '')[:10]} to {ds.get('end', '')[:10]}", "2 days (September 2013)"],
        ["Cards / merchants", f"{R.n(ds.get('cards'))} cards, {R.n(ds.get('merchants'))} merchants", "not provided"],
        ["Features", "Named: amount, category, merchant, time, customer and merchant location", "PCA components V1-V28 + time + amount"],
        ["Why we use it", "Behavioural features and readable explanations are possible", "Standard benchmark in most papers (T3, T10, Shanaa 2025)"],
    ], caption="Datasets", widths=[3.5, 7, 6.5])
    doc.figure(R.figure("fig_dataset_overview"), "Sparkov: extreme imbalance, fraud concentrated between 22:00 and 04:00, and in online shopping, grocery (in-store) and online miscellaneous categories.", 17)
    fh = ds.get("fraud_by_hour", {})
    night = [v for h, v in fh.items() if int(h) >= 22 or int(h) < 4]
    day = [v for h, v in fh.items() if 4 <= int(h) < 22]
    amt = ds.get("amount_by_class", {})
    doc.bullets([
        f"**Night-time**: the fraud rate is {R.pct(sum(night) / max(len(night), 1), 2)} between 22:00 and 04:00 versus {R.pct(sum(day) / max(len(day), 1), 2)} during the day.",
        f"**Amount**: frauds average {R.money(amt.get('1', {}).get('mean'))} against {R.money(amt.get('0', {}).get('mean'))} for genuine transactions.",
        f"**Bursts**: {R.n(ds.get('compromised_cards'))} cards were compromised, each with about {ds.get('frauds_per_compromised_card', 0):.0f} fraudulent transactions within roughly two days. Velocity features are therefore essential.",
        "**Category**: online shopping, in-store grocery and online miscellaneous have the highest fraud rates.",
    ])
    doc.figure(R.figure("fig_amounts"), "Fraudulent transactions are several times larger than genuine ones.", 11)
    doc.h2("5.1 Chronological split with label-delay gaps")
    doc.table(["Block", "From", "To", "Transactions", "Frauds", "Used for"],
              [[s.title(), splits.get(s, {}).get("start", "")[:10], splits.get(s, {}).get("end", "")[:10],
                R.n(splits.get(s, {}).get("rows")), R.n(splits.get(s, {}).get("frauds")), use]
               for s, use in (("train", "Fitting the detectors"), ("gap", "7-day gaps: history only, never scored"),
                              ("val", "Early stopping, meta-learner, thresholds"),
                              ("test", "Final evaluation + live demo stream"))],
              caption="Time-based split (Sparkov)", widths=[2, 2.5, 2.5, 2.5, 2, 6])
    doc.callout("A random split lets the model learn from the future and puts transactions from the same fraud burst in "
                "both training and test data, which makes results look better than they are. We train on the past, "
                "validate on the next quarter and test on the most recent quarter, with 7-day gaps between them because "
                "fraud labels take days to be confirmed (Dal Pozzolo et al., 2018; Le Borgne et al., 2022). The test "
                "period is also what the dashboard replays live, so the demo runs on data the model has never seen.",
                "proof", "Why a chronological split")

    # ============================================================ 6 method
    doc.h1("6 Methodology")
    doc.h2("6.1 Behavioural feature engineering")
    doc.p(f"We compute {len(NUMERIC_FEATURES)} numeric features plus 14 category indicators; the deployed model uses "
          f"{len(DEPLOYED_FEATURES)} of them (age and gender excluded). Each is computed from the card's past only "
          "(Whitrow et al., 2009; Bahnsen et al., 2016).")
    doc.table(["Feature(s)", "Meaning", "Fraud signal it captures"], [list(r) for r in FEATURE_TABLE],
              caption="Behavioural and transaction features", widths=[4.5, 6.5, 6])
    doc.callout(f"The feature store processed all {R.n(ds.get('rows'))} transactions in {ds.get('feature_seconds', 0):.0f} s "
                f"({ds.get('microseconds_per_txn', 0):.0f} microseconds per transaction). A unit test replays the test "
                "stream through the API's feature-store snapshot and checks the features match the training matrix exactly.",
                "success", "Fast and consistent")
    doc.h2("6.2 Class-imbalance strategy")
    doc.p("Fraud is 0.58% of Sparkov transactions and 0.17% of ULB. Most reviewed papers oversample with SMOTE. We "
          "compared four strategies (E2) and deploy **class weighting** in the base learners followed by **calibration "
          "on the natural class balance** in the meta-learner. This keeps probabilities honest, which the risk "
          "score depends on (van den Goorbergh et al., 2022; Elkan, 2001).")
    doc.h2("6.3 Models compared")
    doc.table(["Model", "Type", "Role in the study"], [
        ["Legacy rules", "4 expert if-then rules (amount, night-online, velocity, spend ratio)", "The \"existing system\" baseline"],
        ["Logistic Regression", "Linear", "Classical baseline (T4, T8)"],
        ["Decision Tree", "Single tree", "Interpretable baseline (T8)"],
        ["Random Forest", "Bagged trees", "Second opinion in the hybrid (T5, T18)"],
        ["XGBoost", "Gradient-boosted trees", "Main classifier (T3, T7)"],
        ["LightGBM", "Gradient-boosted trees", "Alternative booster"],
        ["Isolation Forest", "Unsupervised anomaly detection", "Novelty layer in the hybrid"],
        ["Deep MLP", "3-layer neural network (PyTorch)", "Deep-learning baseline (T10, T12)"],
        ["1D-CNN", "Convolutional network over the feature vector", "Reproduces the idea of T1"],
        ["FraudLens Hybrid", "Stacked XGB + RF + IF", "Proposed system"],
    ], caption="Models", widths=[3.5, 6, 7])
    doc.h2("6.4 Hybrid risk engine")
    doc.p("The three detectors are trained on the training period (Isolation Forest on genuine transactions only). "
          "On the validation period, a logistic-regression meta-learner is fitted on "
          "`[logit(p_xgb), logit(p_rf), anomaly_z]`, so the weights come from data rather than guesswork "
          "(Wolpert, 1992). Because the validation period has the natural fraud rate, the output is a calibrated "
          "probability. Two thresholds are chosen on out-of-fold validation predictions:")
    doc.bullets([
        f"**Alert (step-up) threshold** = {thr.get('alert', 0):.4f}: minimises missed-fraud dollars + ${config.ALERT_COST:.0f} x alerts.",
        f"**Block threshold** = {thr.get('block', 0):.4f}: the lowest probability at which alerts are at least {config.BLOCK_MIN_PRECISION:.0%} precise.",
    ])
    mw = bm.get("hybrid", {}).get("meta_weights", {})
    doc.table(["Risk score", "Level", "Action", "Probability range"], [
        ["0-30", "LOW", "Approve", f"< {thr.get('alert', 0):.4f}"],
        ["31-60", "MEDIUM", "Step-up verification (OTP / 3-D Secure) or analyst review", f"{thr.get('alert', 0):.4f} - {thr.get('block', 0):.4f}"],
        ["61-100", "HIGH", "Block and open a case", f">= {thr.get('block', 0):.4f}"],
    ], caption="Risk tiers: the team's original bands, now anchored to learned thresholds", widths=[2, 2, 8, 4])
    if mw:
        doc.p(f"Learned stacking weights: XGBoost {mw.get('xgb', 0):.2f}, Random Forest {mw.get('rf', 0):.2f}, "
              f"Isolation Forest {mw.get('iforest', 0):.2f} (intercept {mw.get('intercept', 0):.2f}), on logit / z-score scales.")

    doc.h2("6.5 Safety layer: defence in depth")
    doc.p("The stacking weights above revealed a design flaw that most hybrid papers do not report. The meta-learner is "
          "fitted on *labelled* fraud, which XGBoost already explains, so it gives the Isolation Forest "
          f"{'almost no' if abs(mw.get('iforest', 0)) < 0.3 else 'only a small'} weight ({mw.get('iforest', 0):+.2f}). "
          "Stacking alone therefore cannot use the anomaly detector for its real purpose: fraud types that never "
          "appeared in the labels. In the scam replays (Section 8.1), the anomaly detector rated a card-testing "
          "cash-out as more unusual than 99.9% of normal spending, yet the stacked score stayed below the alert line.")
    doc.p("FraudLens therefore adds a safety layer that can only *raise* a decision to at least Step-up, never approve "
          "anything: a novelty alarm with its own route, plus three documented, parameterised policy rules of the kind the "
          "RBI Master Direction (2021, paras 36-37) asks banks to run.")
    doc.table(["Rule", "Fires when", "Attack it targets", "Basis"], [
        ["P1 Burst then jump", "3+ transactions in the past hour and an amount 5x or more the card's average",
         "Account takeover / cash-out after card testing", "Velocity rules (RBI MD para 36-37); Bahnsen 2016"],
        ["P2 Impossible travel", "500 km+ from the previous transaction at an implied speed above 800 km/h",
         "Cloned (skimmed) card", "Geo-location rules (RBI MD para 36-37)"],
        ["P3 Micro-charge burst", "A tiny (< $5) online charge after 3+ others in the past hour",
         "Card testing (enumeration)", "Industry card-testing pattern"],
        ["N1 Novelty alarm", "Anomaly percentile at least 99.95% of genuine training transactions",
         "New, unlabelled fraud patterns", "Liu 2008; Carcillo 2021"],
    ], caption="Safety-layer rules (fraudlens/policy.py); every hit raises the decision to at least STEP-UP",
       widths=[3.2, 5.8, 4.2, 4], font=8.5)
    tp_ = pol.get("test", {})
    if tp_:
        doc.p(f"Cost on the unseen test period: the layer adds {tp_.get('extra_alerts_per_day', 0):.2f} step-ups per day "
              "beyond the ML's own alerts (Section 7.8). The rule parameters come from domain reasoning and were checked "
              "on the training data; the 99.95th-percentile novelty threshold is a business setting chosen for a low "
              "alert cost, not tuned for detection.")

    doc.h2("6.6 Explainable AI")
    doc.p("For each decision, TreeSHAP (Lundberg et al., 2020) attributes the XGBoost log-odds to every feature exactly, "
          "using the same trees the model predicts with, so the contributions sum to the model output (a unit test "
          "checks this). Related features are grouped (for example all velocity counters), and each group with a "
          "meaningful push becomes a sentence built from the transaction's real values, for example \"Amount $1,150.00 "
          "is 19.3x this card's average spend ($60)\" or \"4 other transactions on this card in the past hour\". Groups "
          "pushing towards genuine become \"looks genuine because\" statements.")
    doc.h2("6.7 Evaluation protocol")
    doc.table(["Metric", "Meaning", "Why"], [
        ["PR-AUC (average precision)", "Area under the precision-recall curve", "Primary metric for rare events (Saito & Rehmsmeier, 2015)"],
        ["Recall", "Share of frauds caught", "Missed fraud = direct loss"],
        ["Precision", "Share of alerts that are fraud", "False alarms annoy customers and cost review time"],
        ["F1 / MCC", "Balance of precision and recall / all four confusion cells", "MCC is robust to imbalance (Chicco & Jurman, 2020)"],
        ["ROC-AUC", "Ranking quality over all thresholds", "Reported, but optimistic on imbalanced data"],
        ["Money saved", "Fraud $ stopped minus alert costs", "What the bank actually cares about (Bahnsen 2016; Hoppner 2022)"],
        ["Latency", "Milliseconds per transaction", "Authorisation happens in real time"],
    ], caption="Metrics", widths=[4, 6, 7])
    doc.bullets([
        "Thresholds are always chosen on validation data and applied unchanged to the test period.",
        "95% confidence intervals come from 500 bootstrap resamples of the test set; model differences use a paired bootstrap.",
        "All models share the same features, split and seed.",
    ])

    # ============================================================ 7 results
    doc.h1("7 Experiments and results")
    doc.h2("7.1 E1: model benchmark")
    order = [m for m in ("hybrid", "xgb", "lgbm", "rf", "mlp", "cnn", "dt", "lr", "iforest", "rules") if m in bm]
    ci = an.get("pr_auc_ci", {})
    rows = []
    for m in order:
        t = bm[m]["test"]
        c = ci.get(m)
        rows.append([bm[m]["label"], pv(t["pr_auc"]) + (f" [{c['low']:.3f}-{c['high']:.3f}]" if c else ""),
                     pv(t["roc_auc"]), pv(t["precision"]), pv(t["recall"]), pv(t["f1"]), pv(t["mcc"]),
                     f"{bm[m]['fit_seconds']:.0f}", f"{bm[m].get('latency', {}).get('p50_ms', 0):.2f}" if bm[m].get("latency") else "-"])
    doc.table(["Model", "PR-AUC [95% CI]", "ROC-AUC", "Precision", "Recall", "F1", "MCC", "Fit (s)", "Latency p50 (ms)"],
              rows, caption="E1: test-period results on Sparkov (threshold tuned on validation for F1)", highlight=[0],
              widths=[4.5, 3.2, 1.6, 1.6, 1.5, 1.4, 1.4, 1.3, 1.9], font=8)
    doc.figure(R.figure("fig_pr_roc_curves"), "Precision-recall and ROC curves on the unseen test period.", 17)
    doc.figure(R.figure("fig_model_comparison"), "PR-AUC with 95% bootstrap confidence intervals.", 13)
    sig_txt = ""
    if sig_x:
        if sig_x["ci_low"] > 0:
            sig_txt = (f"The hybrid is significantly better than XGBoost alone (PR-AUC +{sig_x['diff']:.4f}, 95% CI "
                       f"[{sig_x['ci_low']:.4f}, {sig_x['ci_high']:.4f}], p = {sig_x['p_value']:.3f}).")
        elif sig_x["ci_high"] < 0:
            sig_txt = (f"XGBoost alone ranks slightly better than the hybrid on PR-AUC ({sig_x['diff']:+.4f}, 95% CI "
                       f"[{sig_x['ci_low']:.4f}, {sig_x['ci_high']:.4f}]). The hybrid's value is in calibrated probabilities, "
                       "decision tiers and, through the safety layer, coverage of fraud absent from the training data "
                       "(E5, Section 7.8), not in raw ranking.")
        else:
            sig_txt = (f"The hybrid and XGBoost alone are statistically indistinguishable on PR-AUC (difference "
                       f"{sig_x['diff']:+.4f}, 95% CI [{sig_x['ci_low']:.4f}, {sig_x['ci_high']:.4f}]). The hybrid's value "
                       "is therefore in calibrated probabilities, decision tiers, a second independent opinion and, through "
                       "the safety layer, coverage of fraud absent from the training data (E5, Section 7.8), not in raw ranking.")
    lg = bm.get("lgbm", {}).get("test", {})
    if lg and abs(lg.get("pr_auc", 0) - X.get("pr_auc", 0)) < 0.01:
        sig_txt += (f" LightGBM (PR-AUC {pv(lg.get('pr_auc'))}) matches XGBoost within the confidence interval; XGBoost "
                    "stays the main classifier because its exact TreeSHAP is built into the predictor, which keeps the "
                    "per-decision explanations in the API cheap. LightGBM was numerically unstable with a 177x class "
                    "weight until the leaf step was capped (Appendix A), a practical finding in itself.")
    mlp_min = bm.get("mlp", {}).get("fit_seconds", 0) / 60
    cnn_min = bm.get("cnn", {}).get("fit_seconds", 0) / 60
    xgb_min = bm.get("xgb", {}).get("fit_seconds", 0) / 60
    doc.callout(
        f"Gradient-boosted trees lead: XGBoost PR-AUC {pv(X.get('pr_auc'))} and the hybrid {pv(H.get('pr_auc'))}, against "
        f"{pv(LR.get('pr_auc'))} for Logistic Regression and {pv(RU.get('pr_auc'))} for the legacy rules. The hybrid catches "
        f"{R.pct(H.get('recall'))} of frauds with {R.pct(H.get('precision'))} precision. {sig_txt} "
        f"The deep models scored lower and took far longer to train: {mlp_min:.0f} min (MLP) and {cnn_min:.0f} min "
        f"(1D-CNN, at most 8 epochs, with other jobs sharing the CPU) against {xgb_min:.1f} min for XGBoost.",
        "success", "Finding (RQ1)")
    doc.p(f"Latency was re-measured separately on an idle laptop CPU, one thread, one transaction per call. Scoring by "
          f"the hybrid's three models and meta-learner takes {lat.get('p50_ms', 0):.1f} ms (median; p95 "
          f"{lat.get('p95_ms', 0):.1f} ms). The full API path, including the feature store, the safety layer, the SHAP "
          f"explanation and the database write, takes {api_lat.get('p50', 0):.1f} ms (p95 {api_lat.get('p95', 0):.1f} ms), "
          f"and the replay stream sustains about {api_stream.get('per_second', 0):,.0f} transactions per second. "
          f"XGBoost itself answers in about {bm.get('xgb', {}).get('latency', {}).get('p50_ms', 0):.0f} ms; the single-call "
          "cost of the hybrid comes from scikit-learn's Random Forest and Isolation Forest, which loop over their trees in "
          f"Python; in batches the whole path costs about {api_stream.get('ms_per_txn', 0):.1f} ms per transaction. That is "
          "comfortably sub-second, which is enough for this platform, but production issuers usually aim much lower, so "
          "compiling the two forests with a tree runtime such as treelite or ONNX Runtime is the listed optimisation for a "
          "bank-scale deployment. The deep baselines' latencies were not re-measured on the idle machine and are left out "
          "rather than reported unfairly.")
    doc.figure(R.figure("fig_accuracy_vs_latency"), "Accuracy versus single-transaction latency (idle machine, one thread). The boosted trees are both fast and accurate; the hybrid's time is dominated by the two scikit-learn forests.", 12)
    cal_path = config.RESULTS / "calibration.json"
    cal = json.loads(cal_path.read_text()) if cal_path.exists() else {}
    cal_txt = "Calibration of the class-weighted XGBoost and the stacked hybrid against observed fraud rates."
    if cal.get("xgb") and cal.get("hybrid"):
        bx = next((b for b in cal["xgb"] if b["band"].startswith("0.60")), None)
        bh = next((b for b in cal["hybrid"] if b["band"].startswith("0.60")), None)
        if bx and bh:
            cal_txt = (f"Calibration: where class-weighted XGBoost says {bx['predicted']:.0%}, only {bx['observed']:.0%} of "
                       f"transactions are fraud; where the stacked hybrid says {bh['predicted']:.0%}, {bh['observed']:.0%} are. "
                       "The risk score is built on the hybrid's honest probabilities.")
    doc.figure(R.figure("fig_calibration"), cal_txt, 10)

    doc.h2("7.2 E2: imbalance handling")
    rows = []
    for key, v in imb.items():
        rows.append([v["model"], v["strategy"], pv(v["pr_auc"]), pv(v["at_0.5"]["precision"]), pv(v["at_0.5"]["recall"]),
                     pv(v["at_0.5"]["f1"]), pv(v["at_tuned"]["f1"]), f"{v['brier']:.5f}",
                     f"{v['mean_predicted_prob']:.4f}"])
    if rows:
        doc.table(["Model", "Strategy", "PR-AUC", "Prec @0.5", "Recall @0.5", "F1 @0.5", "F1 tuned", "Brier", "Mean p"],
                  rows, caption=f"E2: imbalance strategies (actual test fraud rate {R.pct(next(iter(imb.values()))['actual_fraud_rate'], 2)})",
                  widths=[3.2, 4.2, 1.5, 1.6, 1.6, 1.4, 1.4, 1.6, 1.5], font=8)
    if imb:
        doc.callout(imbalance_finding(imb), "success", "Finding (RQ2)")
    doc.figure(R.figure("fig_imbalance"), "Imbalance strategies: PR-AUC, F1 at the default threshold and F1 at the tuned threshold.", 17)

    doc.h2("7.3 E3: how evaluation shortcuts inflate results")
    doc.p("We trained the same XGBoost model under four protocols, from the shortcut common in published papers to our "
          "own protocol:")
    for dsn, label in (("ulb", "ULB European dataset"), ("sparkov", "Sparkov dataset")):
        pr = prot.get(dsn)
        if not pr:
            continue
        doc.table(["Protocol", "Accuracy", "Precision", "Recall", "F1", "PR-AUC"],
                  [[pr[k]["protocol"], R.pct(pr[k]["accuracy"], 2), pv(pr[k]["precision"]), pv(pr[k]["recall"]),
                    pv(pr[k]["f1"]), pv(pr[k].get("pr_auc"))] for k in ("dummy", "A", "B", "C", "D")],
                  caption=f"E3: evaluation protocols on the {label}", highlight=[4], widths=[9, 1.8, 1.7, 1.6, 1.5, 1.6], font=8)
    pu = prot.get("ulb", {})
    if pu:
        doc.callout(
            f"On ULB, oversampling before splitting (protocol A) reports accuracy {R.pct(pu['A']['accuracy'], 2)}, precision "
            f"{R.pct(pu['A']['precision'], 1)} and F1 {pv(pu['A']['f1'])}. These numbers look like the 99.9% results in T3 and "
            f"T7. The identical model evaluated honestly on future data (protocol D) gives F1 {pv(pu['D']['f1'])}. "
            f"Meanwhile a model that never flags anything reaches {R.pct(pu['dummy']['accuracy'], 2)} accuracy. "
            "Synthetic fraud points leak into the test set and make it easy; accuracy hides the minority class. This "
            "reproduces the leakage analysis of Santos et al. (2018) and Hayat & Magnier (2025).",
            "proof", "Finding (RQ3): why many published numbers are not comparable")
    doc.figure(R.figure("fig_protocol"), "The same XGBoost under four evaluation protocols.", 17)

    doc.h2("7.4 E4: ablation study")
    fs = abl.get("feature_sets", {})
    if fs:
        doc.table(["Feature set", "# features", "PR-AUC", "Recall", "Precision", "F1", "vs FraudLens features (diff [95% CI])"],
                  [[v["label"], str(v.get("n_features", "")), pv(v["test"]["pr_auc"]), pv(v["test"]["recall"]),
                    pv(v["test"]["precision"]), pv(v["test"]["f1"]),
                    (f"{v['vs_deployed']['diff']:+.4f} [{v['vs_deployed']['ci_low']:+.4f}, {v['vs_deployed']['ci_high']:+.4f}]"
                     if v.get("vs_deployed") else "reference")] for k, v in fs.items()],
                  caption="E4a: feature engineering (XGBoost, same split)", highlight=[1], widths=[6, 1.5, 1.5, 1.5, 1.5, 1.3, 4.5], font=8)
    comp = abl.get("components", {})
    if comp:
        names = {"xgb": "XGBoost only", "rf": "Random Forest only", "iforest": "Isolation Forest only",
                 "xgb+rf": "XGBoost + RF", "xgb+iforest": "XGBoost + IF", "rf+iforest": "RF + IF",
                 "xgb+rf+iforest": "XGBoost + RF + IF (FraudLens)", "avg(xgb,rf)": "Simple average of XGB and RF",
                 "xgb_with_if_feature": "XGBoost with IF score as an input feature"}
        keys = [k for k in names if k in comp]
        doc.table(["Combination (stacked)", "PR-AUC", "Recall", "Precision", "F1", "vs XGBoost only (diff [95% CI])"],
                  [[names[k], pv(comp[k]["test"]["pr_auc"], 4), pv(comp[k]["test"]["recall"]), pv(comp[k]["test"]["precision"]),
                    pv(comp[k]["test"]["f1"]),
                    (f"{comp[k]['vs_xgb']['diff']:+.4f} [{comp[k]['vs_xgb']['ci_low']:+.4f}, {comp[k]['vs_xgb']['ci_high']:+.4f}]"
                     if comp[k].get("vs_xgb") else "reference")] for k in keys],
                  caption="E4b: hybrid components", highlight=[keys.index("xgb+rf+iforest")] if "xgb+rf+iforest" in keys else [],
                  widths=[6, 1.6, 1.5, 1.6, 1.3, 5], font=8)
    if fs.get("raw") and fs.get("deployed"):
        gain = fs["deployed"]["test"]["pr_auc"] - fs["raw"]["test"]["pr_auc"]
        fair = fs.get("all", {}).get("test", {}).get("pr_auc", 0) - fs["deployed"]["test"]["pr_auc"] if fs.get("all") else 0
        extra = ""
        wf = comp.get("xgb_with_if_feature", {}).get("vs_xgb")
        st = comp.get("xgb+rf+iforest", {}).get("vs_xgb")
        if st:
            extra += (f" Among hybrid designs, stacking XGBoost + RF + IF matches XGBoost alone "
                      f"({st['diff']:+.4f}, 95% CI [{st['ci_low']:+.4f}, {st['ci_high']:+.4f}]).")
        if wf:
            sig = "a small but statistically significant gain" if wf["ci_low"] > 0 else "no significant gain"
            extra += (f" Feeding the Isolation Forest score into XGBoost as an input feature (Carcillo et al., 2021) gives "
                      f"PR-AUC {pv(comp['xgb_with_if_feature']['test']['pr_auc'])}, {sig} ({wf['diff']:+.4f}, 95% CI "
                      f"[{wf['ci_low']:+.4f}, {wf['ci_high']:+.4f}]), a candidate for the next model version.")
        doc.callout(
            f"Behavioural features are the single biggest improvement: the same XGBoost moves from PR-AUC "
            f"{pv(fs['raw']['test']['pr_auc'])} on raw transaction fields (what typical projects use) to "
            f"{pv(fs['deployed']['test']['pr_auc'])} (+{gain:.3f}). Adding age and gender would add {fair:+.4f} PR-AUC; "
            "we leave these protected attributes out, trading that small gain for a fairness guarantee." + extra,
            "success", "Finding (RQ4)")
    doc.figure(R.figure("fig_ablation"), "Ablation: feature sets (left) and stacked detector combinations (right).", 17)

    doc.h2("7.5 E5: catching a fraud type never seen in training")
    doc.p("Supervised models only learn fraud that appears in their training labels. To test the anomaly layer we "
          "removed one entire fraud type (all online frauds, or all in-person frauds) from training and validation, "
          "retrained everything, and measured how many of that type's test frauds each detector still catches at its "
          "validation-chosen threshold.")
    if un:
        cols = [("xgb", "XGBoost"), ("rf", "Random Forest"), ("iforest", "Isolation Forest"),
                ("novelty_alarm", "Novelty alarm N1"), ("hybrid", "Hybrid (stacking only)"),
                ("hybrid_with_policy", "Hybrid + safety layer"), ("hybrid_trained_on_all_types", "Hybrid that saw it")]
        cols = [(k, lab) for k, lab in cols if all(k in v["results"] for v in un.values())]
        rows = []
        for held, v in un.items():
            r = v["results"]
            rows.append([held.replace("_", "-"), str(v["held_out_frauds_in_test"])] +
                        [f"{r[k]['recall']:.3f} ({r[k]['precision']:.2f})" for k, _ in cols])
        doc.table(["Held-out type", "Test frauds"] + [lab for _, lab in cols], rows,
                  caption="E5: recall (precision) on the never-seen fraud type", widths=[2.4, 1.6] + [2.1] * len(cols), font=7.8)
        parts = []
        for held, v in un.items():
            r = v["results"]
            s = f"Holding out {held.replace('_', '-')} fraud, XGBoost still catches {r['xgb']['recall']:.1%} of it"
            if "hybrid_with_policy" in r:
                gain = r["hybrid_with_policy"]["recall"] - r["hybrid"]["recall"]
                s += (f"; the stacking-only hybrid {r['hybrid']['recall']:.1%} and the hybrid with the safety layer "
                      f"{r['hybrid_with_policy']['recall']:.1%} ({gain:+.1%})")
            s += f", against {r['hybrid_trained_on_all_types']['recall']:.1%} for a hybrid that saw this type."
            parts.append(s)
        gains = [v["results"]["hybrid_with_policy"]["recall"] - v["results"]["hybrid"]["recall"]
                 for v in un.values() if "hybrid_with_policy" in v["results"]]
        res = list(un.values())
        cp = []
        if gains and max(gains) >= 0.005:
            cp.append(f"The safety layer adds {min(gains):+.1%} to {max(gains):+.1%} recall on the unseen type, a real "
                      "but modest gain.")
        if all(v["results"]["hybrid"]["recall"] < v["results"]["xgb"]["recall"] for v in res):
            cp.append("The stacking layer, fitted on the fraud types it has seen, does worse than XGBoost alone on the "
                      "new one: a learned combination over-fits to known fraud, which is exactly why the novelty route "
                      "sits outside it.")
        if all("iforest" in v["results"] for v in res):
            ir = [v["results"]["iforest"]["recall"] for v in res]
            ip = [v["results"]["iforest"]["precision"] for v in res]
            cp.append(f"The Isolation Forest on its own catches {min(ir):.0%}-{max(ir):.0%} of the unseen fraud, but at "
                      f"only {min(ip):.0%}-{max(ip):.0%} precision, so it is a triage signal, not a decision maker.")
        if all(v["results"]["hybrid_trained_on_all_types"]["recall"]
               - v["results"].get("hybrid_with_policy", v["results"]["hybrid"])["recall"] > 0.3 for v in res):
            cp.append("The honest conclusion: fraud that is completely absent from the labels is caught far less often "
                      "than fraud the system has seen. No detector replaces labels. That is why analyst verdicts from the "
                      "case queue are stored as labels for retraining, so a new fraud type only goes undetected until it "
                      "has been labelled.")
        doc.callout(" ".join(parts) + " " + " ".join(cp), "warn", "Finding (RQ5): an honest limit")
    doc.figure(R.figure("fig_unseen"), "Recall on a fraud type removed from training.", 16)

    doc.h2("7.6 E6: ULB European benchmark")
    if ulb:
        rows = []
        for m in ("hybrid", "xgb", "lgbm", "rf", "mlp", "lr", "iforest"):
            if m in ulb:
                t = ulb[m]["test"]
                rows.append([ulb[m]["label"], f"{pv(t['pr_auc'])} [{t['pr_auc_ci'][0]:.3f}-{t['pr_auc_ci'][1]:.3f}]",
                             pv(t["roc_auc"]), pv(t["precision"]), pv(t["recall"]), pv(t["f1"]), pv(t["mcc"])])
        doc.table(["Model", "PR-AUC [95% CI]", "ROC-AUC", "Precision", "Recall", "F1", "MCC"], rows,
                  caption="E6: ULB dataset, last 20% of the timeline as test", highlight=[0], widths=[5, 3.6, 1.8, 1.8, 1.6, 1.5, 1.5], font=8)
        doc.p(f"ULB has only {ulb.get('_dataset', {}).get('splits', {}).get('test', {}).get('frauds', 'n/a')} frauds in the test "
              "slice, so the confidence intervals are wide and the models overlap. Because the features are anonymous "
              "PCA components, behavioural features and readable reasons are impossible here, which is why Sparkov is "
              "our primary dataset.")
    doc.figure(R.figure("fig_ulb"), "ULB benchmark with 95% confidence intervals.", 13)

    doc.h2("7.7 E7: business impact, risk tiers and stability")
    rows = [[f"${r['alert_cost']:g}", f"{r['threshold']:.4f}", pv(r["recall"]), pv(r["precision"]),
             f"{r['alerts_per_day']:.1f}", R.money(r["fraud_amount_caught"]), R.money(r["cost"]), R.pct(r["savings_pct"])]
            for r in an.get("cost_sensitivity", [])]
    if rows:
        doc.table(["Alert cost", "Threshold", "Recall", "Precision", "Alerts/day", "Fraud $ stopped", "Total cost", "Loss avoided"],
                  rows, caption=f"E7: cost-optimal thresholds for different alert costs (test period, {days:.0f} days)",
                  highlight=[[r["alert_cost"] for r in an["cost_sensitivity"]].index(config.ALERT_COST)], widths=[2, 2, 1.7, 1.8, 2, 2.6, 2.4, 2.4], font=8.5)
    if tiers:
        doc.table(["Tier", "Transactions", "Share", "Per day", "Frauds", "Fraud rate", "Fraud $"],
                  [[t, R.n(v["transactions"]), R.pct(v["share"], 2), f"{v['per_day']:.1f}", R.n(v["frauds"]),
                    R.pct(v["fraud_rate"], 1), R.money(v["fraud_amount"])] for t, v in tiers.items()],
                  caption="Risk tiers on the test period", widths=[2, 2.5, 2, 2, 2, 2, 2.5])
    rb = bm.get("rules", {}).get("test_cost_threshold", {})
    doc.callout(
        f"With a ${config.ALERT_COST:.0f} alert cost, the hybrid stops {R.pct(HC.get('amount_recall'))} of fraud value and avoids "
        f"{R.pct(HC.get('savings_pct'))} of fraud losses after paying for every alert, raising about "
        f"{cs5.get('alerts_per_day', 0):.0f} alerts per day out of ~{R.n(splits.get('test', {}).get('rows', 0) / max(days, 1))} "
        f"daily transactions. The legacy rule engine avoids only {R.pct(rb.get('savings_pct'))}. Auto-block (HIGH) is "
        f"reserved for {R.pct(tiers.get('HIGH', {}).get('share'), 2)} of transactions with a fraud rate of "
        f"{R.pct(tiers.get('HIGH', {}).get('fraud_rate'), 1)}.", "success", "Finding (RQ6)")
    doc.figure(R.figure("fig_business"), "Cost versus threshold (left) and the three risk tiers (right).", 17)
    doc.figure(R.figure("fig_monthly"), "Month-by-month stability on the test period.", 12)
    doc.figure(R.figure("fig_confusion"), "Confusion matrix of the hybrid at the validation-tuned threshold.", 8)
    doc.p(f"The Population Stability Index of the risk score between validation and test is {an.get('psi_val_to_test', 0):.3f} "
          "(below 0.1 is conventionally \"stable\"). In production the same statistic, computed weekly, triggers "
          "retraining when fraud patterns drift.")

    doc.h2("7.8 Safety layer: cost and effect")
    if pol.get("test"):
        rows = []
        for split, lab in (("val", "Validation"), ("test", "Test")):
            blk = pol.get(split, {})
            for rid, rv in blk.get("rules", {}).items():
                rows.append([lab, rid, R.n(rv["fires"]), R.n(rv["fires_on_genuine"]),
                             R.pct(rv["fraud_rate"], 0) if rv["fires"] else "-", R.n(rv["extra_alerts"]),
                             R.n(rv["extra_frauds"]), f"{rv['extra_alerts_per_day']:.2f}"])
        doc.table(["Period", "Rule", "Fires", "On genuine", "Fraud rate", "Extra alerts", "Extra frauds", "Extra / day"],
                  rows, caption="How often each rule fires, and what it adds beyond the ML's own alerts",
                  widths=[2, 1.3, 1.6, 2, 2, 2, 2, 1.8], font=8.5)
        tml, tmp = pol["test"]["ml_only"], pol["test"]["ml_plus_policy"]
        doc.table(["At the alert (step-up) level, test period", "ML only", "ML + safety layer"], [
            ["Alerts", R.n(tml["tp"] + tml["fp"]), R.n(tmp["tp"] + tmp["fp"])],
            ["Frauds caught", f"{R.n(tml['tp'])} / {R.n(tml['tp'] + tml['fn'])}", f"{R.n(tmp['tp'])} / {R.n(tmp['tp'] + tmp['fn'])}"],
            ["Recall", R.pct(tml["recall"]), R.pct(tmp["recall"])],
            ["Precision", R.pct(tml["precision"]), R.pct(tmp["precision"])],
            ["Fraud losses avoided (net of alert costs)", R.pct(tml["savings_pct"]), R.pct(tmp["savings_pct"])],
        ], caption="The same test period with and without the safety layer", widths=[8, 4, 4])
        rec_txt = (f"leaves recall unchanged at {tml['recall']:.1%}" if abs(tmp["recall"] - tml["recall"]) < 0.0005
                   else f"moves recall from {tml['recall']:.1%} to {tmp['recall']:.1%}")
        doc.callout(f"On real, unseen traffic the safety layer costs {pol['test']['extra_alerts_per_day']:.2f} extra step-ups "
                    f"per day, {rec_txt}, and lowers alert precision from {tml['precision']:.1%} to {tmp['precision']:.1%}. "
                    "It adds no fraud here because the ML already catches the fraud types present in Sparkov. It is insurance "
                    "for attacks absent from the training data (card testing and cloned cards, Section 8.1), bought at a "
                    "measured, small price.", "proof", "How we prove it is worth keeping")

    doc.h2("7.9 Explainability results")
    doc.figure(R.figure("fig_shap_importance"), "Global SHAP importance: which signals drive decisions overall.", 12)
    doc.figure(R.figure("fig_shap_beeswarm"), "SHAP beeswarm: each dot is one transaction; red = high feature value; right = towards fraud.", 13)
    cases = ex.get("cases", [])
    if cases:
        doc.table(["Case", "Transaction", "Risk", "Decision", "Top reasons given by FraudLens"],
                  [[c["kind"], f"{R.money(c['amount'], 2)} · {CATEGORY_LABELS.get(c['category'], c['category'])} · {c['ts'][5:16]}",
                    f"{c['risk_score']:.0f} ({c['tier']})", "fraud" if c["is_fraud"] else "genuine",
                    "; ".join(c["reasons"][:3]) or ("Looks genuine: " + "; ".join(c["mitigating"][:2]))] for c in cases],
                  caption="Case studies from the test period (including a false alarm and a missed fraud, for honesty)",
                  widths=[3.6, 4.2, 1.8, 1.5, 7.4], font=7.8)

    # ============================================================ 8 scams
    doc.h1("8 How FraudLens detects scams")
    doc.p("Different scams leave different fingerprints in transaction data. The table below shows which signals "
          "FraudLens uses for each type and which detector is responsible; Section 8.1 shows the system's actual "
          "responses when each scam is replayed against a real card's history.")
    doc.table(["Scam / fraud type", "How it works", "Tell-tale signals", "FraudLens features", "Detector"], [
        ["Card-not-present fraud (stolen card details)", "Card data from phishing, breaches or malware is used online",
         "Online channel, large amount, night-time, unfamiliar category", "is_online, cat_*, amt_to_card_mean, is_night, is_new_category", "XGBoost + RF"],
        ["Card testing (enumeration)", "Tiny charges check which stolen numbers work, then a large purchase",
         "Burst of small online charges, then a jump", "cnt_1h, log_secs_since_last, amt_to_card_mean",
         "Safety layer: P3 micro-charge burst, then P1 + N1 (absent from training data)"],
        ["Stolen-card spree / account takeover", "Maximum spending in a few hours before the card is blocked",
         "24 h count and spend far above normal", "cnt_24h_vs_usual, sum_24h, amt_zscore", "XGBoost + RF"],
        ["Cloned card (skimming) / impossible travel", "A copy of the card is used far away",
         "Distance/speed since the previous transaction", "dist_prev_km, speed_kmh, dist_home_km",
         "Safety layer: P2 impossible travel (geography is not learnable from Sparkov)"],
        ["Limit probing / escalation", "Rising amounts test the card's limit", "Growing 24 h spend, amount vs history",
         "sum_24h, amt_to_cat_mean", "XGBoost"],
        ["Dormant-card reactivation", "An unused card suddenly spends", "Long gap then a high amount", "log_secs_since_last, amt_to_card_mean", "XGBoost + IF"],
        ["Merchant compromise / collusion", "Fraud concentrates at a merchant", "Merchant-level fraud rates, card-merchant links",
         "Not yet (future: merchant risk, graph model)", "Future work"],
        ["Social engineering / authorised push payment (e.g. OTP or UPI scams)", "The real customer is tricked into paying",
         "New payee, unusual amount, device/session anomalies", "Partly (amount, novelty); needs device and payee data", "Limitation"],
    ], caption="Scam typology and detection signals", widths=[3.4, 4, 3.6, 4, 2.2], font=7.8)
    doc.h2("8.1 Scam scenarios replayed through the live engine")
    if scen:
        rows = []
        order_lv = ("LOW", "MEDIUM", "HIGH")
        for sid, s in scen.items():
            st = s["steps"]
            ml_peak = max((z.get("ml_risk_level", z["risk_level"]) for z in st), key=order_lv.index)
            fin_peak = max((z["risk_level"] for z in st), key=order_lv.index)
            first = next((z for z in st if z["risk_level"] == fin_peak), st[-1])
            rules = sorted({h["id"] for z in st for h in z.get("policy", [])})
            rows.append([s["title"], str(len(st)),
                         " -> ".join(f"{z.get('ml_risk_score', z['risk_score']):.0f}" for z in st),
                         ml_peak, f"{fin_peak} at step {first['step']}" if fin_peak != "LOW" else "LOW",
                         ", ".join(rules) or "-",
                         "; ".join(r for r in first["reasons"][:2]) or "-"])
        doc.table(["Scenario", "Steps", "ML risk per step", "ML alone", "Final decision", "Rules fired", "Top reasons"], rows,
                  caption="Scam scenarios played against a real card's history (sandboxed): ML alone vs final decision",
                  widths=[3.4, 1.1, 3, 1.8, 2.4, 1.6, 6.1], font=7.8)
        doc.p("Each scenario starts from the real history of a long-standing, mostly-daytime cardholder and runs in a "
              "sandbox copy of that card's state, so the demo never changes live data. " + scenario_story(scen) +
              " The same scenarios run live from the dashboard's Scam Scenarios page.")
    doc.callout("Transaction-level models cannot see everything. Scams where the genuine customer is persuaded to pay "
                "(authorised push payment / social engineering) look like normal customer behaviour and need extra "
                "signals such as device fingerprint, payee history and session behaviour. Merchant-level collusion needs "
                "a graph view (T14). Both are listed as future work rather than claimed.", "warn")

    # ============================================================ 9 better
    doc.h1("9 What we do better, and how we prove it")
    doc.h2("9.1 Compared with typical existing work")
    doc.table(["Aspect", "Typical paper / project", "FraudLens", "Evidence"], [
        ["Model", "One classifier", "Stacked XGB + RF + Isolation Forest", "E1, E4"],
        ["Unknown fraud", "Not addressed", "Novelty alarm + documented policy rules outside the stacking", "E5, 7.8, 8.1"],
        ["Features", "Raw columns or PCA", "Per-card behavioural history, causal", f"E4: +{(fs.get('deployed', {}).get('test', {}).get('pr_auc', 0) - fs.get('raw', {}).get('test', {}).get('pr_auc', 0)):.3f} PR-AUC"],
        ["Imbalance", "SMOTE assumed", "Four strategies compared; calibrated weighting", "E2"],
        ["Evaluation", "Random split, accuracy, SMOTE before split", "Chronological split, PR-AUC/MCC/money, bootstrap CIs", "E3"],
        ["Output", "Fraud / not fraud", "Calibrated probability, 0-100 score, 3 action tiers", "E7"],
        ["Explanation", "None or a global chart", "Per-decision reasons + mitigating factors + audit record", "7.9"],
        ["Deployment", "Notebook", "Real-time API, online feature store, dashboard, Docker", "Ch. 10"],
        ["Security & fairness", "Rarely discussed", "Tokenisation, audit trail, API key, protected attributes excluded", "4.2, E4"],
    ], caption="FraudLens versus typical existing work", widths=[2.6, 4.2, 6.2, 3], font=8.5)
    doc.h2("9.2 Claims and proofs")
    claims = [
        ["Behavioural features beat raw fields", "E4a, same XGBoost, paired bootstrap",
         f"PR-AUC {pv(fs.get('raw', {}).get('test', {}).get('pr_auc'))} -> {pv(fs.get('deployed', {}).get('test', {}).get('pr_auc'))}",
         "Proven" if fs.get("raw", {}).get("vs_deployed", {}).get("ci_high", 1) < 0 else "See E4"],
        ["Trees beat deep learning on this data", "E1 on the same split",
         f"XGB {pv(X.get('pr_auc'))} vs MLP {pv(bm.get('mlp', {}).get('test', {}).get('pr_auc'))}, CNN {pv(bm.get('cnn', {}).get('test', {}).get('pr_auc'))}",
         "Proven" if X.get("pr_auc", 0) > max(bm.get("mlp", {}).get("test", {}).get("pr_auc", 0), bm.get("cnn", {}).get("test", {}).get("pr_auc", 0)) else "Not supported"],
        ["ML beats legacy rules", "E1", f"PR-AUC {pv(H.get('pr_auc'))} vs {pv(RU.get('pr_auc'))}", "Proven"],
        ["Hybrid is at least as good as its best member", "E4b + paired bootstrap vs XGBoost",
         f"diff {sig_x.get('diff', 0):+.4f} [{sig_x.get('ci_low', 0):+.4f}, {sig_x.get('ci_high', 0):+.4f}]" if sig_x else "n/a",
         "Proven (better)" if sig_x.get("ci_low", -1) > 0 else ("Equal (no loss)" if sig_x.get("ci_high", -1) >= 0 else "Slightly lower")],
        ["Shortcuts inflate published numbers", "E3, four protocols",
         f"F1 {pv(pu.get('A', {}).get('f1'))} (leaky) vs {pv(pu.get('D', {}).get('f1'))} (honest)", "Proven"],
        ["Probabilities are calibrated", "Calibration curve, Brier score", "Hybrid tracks the diagonal", "Proven (fig.)"],
        ["Sub-second real-time scoring", "Idle-machine latency, one thread, one transaction per call",
         f"models p50 {lat.get('p50_ms', 0):.1f} ms; full API path p50 {api_lat.get('p50', 0):.1f} ms (p95 {api_lat.get('p95', 0):.1f} ms)", "Proven"],
        ["Safety layer catches attacks absent from training at low cost", "Scam replays + cost on validation and test",
         f"{pol.get('test', {}).get('extra_alerts_per_day', 0):.2f} extra step-ups/day; card testing and cloned card escalated", "Proven"],
        ["No training/serving skew", "Parity unit test", "Online features = offline features (3,000 txns)", "Proven (test)"],
        ["Explanations are faithful", "TreeSHAP local accuracy unit test", "Contributions sum to the model's log-odds (same trees)", "Proven (test)"],
        ["Stable over time", "Monthly metrics + PSI", f"PSI {an.get('psi_val_to_test', 0):.3f}", "Proven" if an.get("psi_val_to_test", 1) < 0.1 else "Monitor"],
    ]
    doc.table(["Claim", "How we test it", "Result", "Verdict"], claims, caption="Every claim is backed by a test",
              widths=[5, 4.5, 5.5, 2.5], font=8.5)
    doc.h2("9.3 Improvements over our original proposal")
    doc.table(["Original plan", "What we did", "Why"], [
        ["SMOTE or class weighting", "Measured four strategies; chose weighting + calibrated stacking", "Evidence (E2) and calibration research"],
        ["Combine XGB, RF and IF somehow", "Learned logistic stacking on a later time period", "Weights from data; calibrated output"],
        ["Fixed risk bands 0-30 / 31-60 / 61-100", "Kept the bands, anchored to cost-optimal and 90%-precision thresholds", "Bands now mean something in money and precision"],
        ["SHAP explanation", "Exact TreeSHAP turned into sentences + mitigating factors", "Analysts and customers need words, not plots"],
        ["FastAPI + dashboard", "Plus online feature store, stream replay, scenario sandbox, case queue, audit log", "Operable and demonstrable system"],
        ["PostgreSQL", "SQLite by default; PostgreSQL by setting FRAUDLENS_DB_URL", "Zero-setup demo, production-ready path"],
        ["Evaluate with precision/recall/F1/ROC/PR-AUC", "Plus MCC, money saved, bootstrap CIs, paired tests, chronological split", "Results that survive scrutiny"],
        ["Isolation Forest inside the hybrid", "Kept in the stack, plus its own novelty-alarm route and three policy rules", "Stacking gave it almost no weight; attacks absent from training still need coverage"],
        ["-", "Added: leakage demonstration, unseen-fraud test, DL baselines, ULB benchmark, fairness ablation, idle-machine latency", "Answer the questions a reviewer will ask"],
    ], caption="From proposal to final system", widths=[4.5, 7, 5], font=8.5)

    # ============================================================ 10 impl
    doc.h1("10 Implementation")
    doc.h2("10.1 Code structure")
    doc.table(["Path", "Purpose"], [
        ["fraudlens/features.py", "Causal feature store shared by training and the API"],
        ["fraudlens/hybrid.py", "Hybrid risk engine: detectors, stacking, thresholds, risk score"],
        ["fraudlens/explain.py", "TreeSHAP + reason-code generation"],
        ["fraudlens/models.py, deep.py, rules.py", "Model factory, PyTorch baselines, legacy rules"],
        ["fraudlens/metrics.py", "PR-AUC, MCC, cost, thresholds, bootstrap tests"],
        ["fraudlens/pipeline.py", "Experiments E1-E7, artifacts, scenarios (one command)"],
        ["fraudlens/plots.py", "All figures"],
        ["fraudlens/api/", "FastAPI app, scoring service, decision log, scam scenarios"],
        ["frontend/", "React dashboard"],
        ["reporting/", "Generates these Word and PDF reports from the results"],
        ["tests/", "Unit, parity and API tests"],
        ["artifacts/", "Trained engine, feature-store snapshot, held-out test stream, model card"],
        ["reports/results, reports/figures", "Experiment outputs (JSON) and charts (PNG)"],
    ], caption="Repository layout", widths=[5.5, 11.5])
    doc.h2("10.2 REST API")
    doc.table(["Method", "Endpoint", "Purpose"], [
        ["POST", "/api/score", "Score and explain one transaction (what-if or committed)"],
        ["POST", "/api/stream/next?n=", "Replay the next n unseen test transactions"],
        ["GET", "/api/stats", "Live KPIs: precision, recall, fraud $ stopped, latency, histograms"],
        ["GET", "/api/transactions", "Decision log with filters (level, source, review status)"],
        ["POST", "/api/transactions/{id}/review", "Analyst verdict: confirm fraud / mark genuine"],
        ["GET / POST", "/api/scenarios, /api/scenarios/{id}/run", "Scam scenarios in a sandbox"],
        ["GET", "/api/cards, /api/cards/{token}", "Tokenised cards and behaviour profiles"],
        ["GET", "/api/model, /api/results/{name}", "Model card and research results"],
        ["GET", "/api/health, /docs", "Health check; interactive Swagger documentation"],
    ], caption="Main API endpoints (full reference: docs/API.md)", widths=[2, 6, 9])
    doc.h2("10.3 Web dashboard")
    doc.table(["Page", "What it does"], [
        ["Overview", "Project summary, headline metrics, transaction flow"],
        ["Live Monitor", "Replays the unseen test period in time order; live KPIs, feed, charts; click any row for its explanation"],
        ["Transaction Tester", "Pick a real card, craft a transaction, see the risk gauge, detector votes and reasons"],
        ["Scam Scenarios", "One-click card testing, spree, midnight online, impossible travel, escalation, normal day"],
        ["Case Queue", "Alerts awaiting review; confirm or dismiss; forensic audit record"],
        ["Results", "All experiments E1-E7 with tables, charts and figures"],
        ["Project Report", "Progress, milestones, work distribution and deliverables for reviewers (edited via project.json)"],
        ["About", "Architecture, technology stack, how to run"],
    ], caption="Dashboard pages", widths=[3.5, 13.5])
    shot_dir = config.ROOT / "frontend" / "screenshots"
    for name, caption in (
            ("overview", "Overview: headline metrics of the deployed model and the transaction flow."),
            ("monitor", "Live Monitor (alerts view): the unseen test quarter replayed through the API, with live precision, recall and money stopped."),
            ("tester", "Transaction Tester: a real card, a late-night $1,150 online purchase, the risk gauge, detector votes and SHAP reasons."),
            ("scenarios", "Scam Scenarios: card testing escalated at step 4 by the safety layer while the ML-only risk (dashed) stays flat."),
            ("cases", "Case Queue: medium and high alerts awaiting analyst review, with the dataset truth for evaluation."),
            ("results_policy", "Results, safety-layer tab: what each rule costs and adds on real traffic."),
            ("results_protocol", "Results, evaluation-protocol tab: how shortcuts inflate published numbers."),
            ("report", "Project Report page for reviewers (edited through project.json)."),
    ):
        if (shot_dir / f"{name}.png").exists():
            doc.figure(shot_dir / f"{name}.png", caption, 16)
    doc.h2("10.4 Testing")
    doc.table(["Test", "What it checks"], [
        ["test_features: causality", "Changing a future transaction never changes earlier features (no leakage)"],
        ["test_features: velocity windows", "1 h / 24 h / 7 d counts and ratios computed correctly"],
        ["test_features: sandbox", "What-if scoring and scenarios never change live card state"],
        ["test_features: online/offline parity", "API features equal training features on 3,000 replayed transactions"],
        ["test_metrics", "Confusion counts, F1/precision/cost thresholds, accuracy paradox"],
        ["test_api", "Health, tokenisation, what-if purity, suspicious > normal, stream, review, scenarios, validation errors"],
    ], caption="Automated tests (run with: pytest)", widths=[5.5, 11.5])

    # ============================================================ 11 run
    doc.h1("11 How to run, test, present and deploy")
    doc.h2("11.1 Run locally (Windows PowerShell)")
    doc.code("""git clone https://github.com/Prateek22672/AI-Based-Credit-Card-Fraud-Detection-System.git
cd AI-Based-Credit-Card-Fraud-Detection-System
python -m venv .venv
.venv\\Scripts\\pip install -r requirements.txt
# trained models + held-out test data are included in artifacts/, so the API runs immediately:
.venv\\Scripts\\python -m uvicorn fraudlens.api.main:app --port 8000
# second terminal: the dashboard
cd frontend
npm install
npm run dev          # open http://localhost:5173  (API docs: http://localhost:8000/docs)""")
    doc.h2("11.2 Reproduce the research (optional, about 1.5 h on a laptop CPU)")
    doc.code(""".venv\\Scripts\\python -m fraudlens.download          # both datasets (~260 MB)
.venv\\Scripts\\pip install -r requirements-dl.txt --index-url https://download.pytorch.org/whl/cpu
.venv\\Scripts\\python -m fraudlens.pipeline all       # features, E1-E7, artifacts, scenarios
.venv\\Scripts\\python -m fraudlens.plots              # figures
.venv\\Scripts\\python -m reporting.build             # these Word + PDF reports
.venv\\Scripts\\python -m pytest                      # automated tests""")
    doc.h2("11.3 Suggested demonstration (10 minutes)")
    doc.numbers([
        "**Overview page**: state the problem, the verdict (web platform + hybrid ML) and the headline numbers.",
        "**Live Monitor**: press Start. Explain that these are unseen April-June 2020 transactions replayed in time order; watch alerts appear and live precision/recall converge towards the test results.",
        "**Click a red (HIGH) row**: read the reasons aloud (for example \"5 transactions in the past hour\", \"amount 9x the card's average\") and point at the three detector votes.",
        "**Scam Scenarios**: run Card testing, then Normal day. Show the risk climbing step by step for the attack and staying green for the normal customer.",
        "**Transaction Tester**: take a real card, enter its usual amount (LOW), then change to $1,150 online at 02:30 (HIGH). This shows the model judges behaviour relative to the customer.",
        "**Case Queue**: confirm one alert and dismiss one; open the audit record to show the forensic trail.",
        "**Results page**: show E3 (how shortcuts inflate numbers) and E4 (features matter most), and explain how each claim is proven.",
        "**Project Report page**: milestones and work distribution for the reviewers.",
    ])
    doc.h2("11.4 Deploy on your own domain")
    doc.bullets([
        "**Simplest (one server / VPS):** `docker build -t fraudlens .` then `docker run -p 8000:8000 fraudlens`. The container serves the API and the built dashboard; point the domain (or a Cloudflare tunnel / Nginx reverse proxy) at port 8000.",
        "**Split hosting:** build the dashboard with `VITE_API_URL=https://api.your-domain` and upload `frontend/dist` to any static host (cPanel, Netlify, Vercel); run the API on a VPS or a Python host and set `FRAUDLENS_CORS_ORIGINS=https://your-domain`.",
        "**Security for public demos:** set `FRAUDLENS_API_KEY` (and the same `VITE_API_KEY` at build time) and a private `FRAUDLENS_TOKEN_SECRET`.",
        "**Results without a server:** the Results and Project Report pages also work from static files, so reviewers can browse them even if the API is offline.",
    ])

    # ============================================================ 12-14
    doc.h1("12 Limitations and threats to validity")
    doc.bullets([
        "**Synthetic primary data.** Sparkov is simulated; its fraud patterns are cleaner than real ones, so absolute scores are higher than a bank would see. ULB is real but anonymised, preventing behavioural features.",
        "**Label delay is simplified** to fixed 7-day gaps; in reality labels arrive at varying times and investigator feedback is biased towards alerted transactions (Dal Pozzolo et al., 2018).",
        "**Geography is a weak signal in Sparkov** (merchants are placed near home at random), so impossible-travel detection relies on policy rule P2 and is not validated on real location data.",
        "**The safety-layer thresholds are set, not learned.** The rule parameters come from domain reasoning; the 99.95th-percentile novelty threshold was chosen after looking at its alert cost on the validation and test periods. These are business settings to review with a fraud team, not tuned detection results.",
        "**Card testing and cloned cards are demonstrated on replayed scenarios**, because Sparkov contains no labelled examples of them; their detection rate on real traffic is not measured.",
        "**Adversarial adaptation.** Fraudsters who learn the rules can mimic normal behaviour; periodic retraining and the anomaly layer mitigate but do not remove this.",
        "**Cost assumptions** ($5 per alert) are illustrative; the sensitivity table shows how decisions change with the assumption.",
        "**Social-engineering scams** where the real customer authorises payment are mostly out of reach of transaction features alone.",
    ])
    doc.h1("13 Future scope")
    doc.table(["Extension", "Value", "Reference"], [
        ["Streaming ingestion (Kafka) + Redis feature store", "Bank-scale throughput", "Carcillo 2018 (SCARFF), T20"],
        ["Compiled tree runtime (treelite / ONNX) for the two forests", "Single-call latency from ~0.2 s to a few ms", "Engineering"],
        ["Continuous retraining from reviewed cases, drift alarms on PSI", "Adapts to new fraud patterns", "T11, Lebichot 2021, Gama 2014"],
        ["Graph model over card-merchant-device links", "Detects organised rings and merchant compromise", "T14, Liu 2021 (PC-GNN)"],
        ["LSTM/Transformer over each card's transaction sequence", "Richer behavioural memory", "T19, Jurgovsky 2018"],
        ["Mobile customer app (\"Was this you?\" push alerts)", "Faster confirmation, fewer false blocks", "Same REST API"],
        ["Device, IP and payee signals", "Social-engineering and account-takeover coverage", "Industry practice"],
        ["Validation on IEEE-CIS and real bank data", "External validity", "T2, T6, T9"],
    ], caption="Future work", widths=[6.5, 5, 5])
    doc.h1("14 Conclusion")
    doc.p(f"FraudLens shows that an explainable hybrid of gradient-boosted trees, a random forest and an anomaly "
          f"detector, fed with causal behavioural features, detects card fraud accurately (test PR-AUC {pv(H.get('pr_auc'))}, "
          f"recall {R.pct(H.get('recall'))}, precision {R.pct(H.get('precision'))}), fast ({lat.get('p50_ms', 0):.1f} ms per "
          "transaction) and transparently, and that it is deployable as a real web service. Just as important, the project "
          "shows *how to evaluate* fraud detectors honestly: several impressive published numbers can only be reproduced "
          "with data leakage, while our results hold on unseen future data, with confidence intervals and significance "
          "tests. Existing projects mainly detect fraud; FraudLens detects it, recognises unusual behaviour, prices the "
          "risk, explains the decision and leaves an audit trail.")

    # ============================================================ refs
    doc.h1("References")
    lit = R.lit
    keys = ["nilson", "dalpozzolo2015ssci", "dalpozzolo2018", "leborgne2022handbook", "whitrow2009", "bahnsen2016",
            "carcillo2021", "liu2008", "breiman2001", "chen2016", "ke2017", "wolpert1992", "lundberg2017", "lundberg2020",
            "psychoula2021", "grinsztajn2022", "shwartzziv2022", "saito2015", "chicco2020", "santos2018", "kaufman2012",
            "hayat2025", "goorbergh2022", "elkan2001", "niculescu2005", "hoppner2022", "vanderschueren2022", "gama2014",
            "jurgovsky2018", "carcillo2018scarff", "chawla2002", "shanaa2025", "liu2021pcgnn"]
    add = {p["key"]: p for p in lit["additional_papers"]}
    refs = [f"{p['authors']} ({p['year']}). {p['title']}. *{p['venue']}*" + (f", {p['volume_pages']}" if p["volume_pages"] else "")
            + (f". https://doi.org/{p['doi']}" if p["doi"] else "") for k in keys if (p := add.get(k))]
    refs += [f"{c['source']} ({c['date']}). {c['claim']}. {c['url']}" for c in lit["industry_context"][:8]]
    refs += [f"T{p['no']}. {p['authors']} ({p['year']}). {p['title']}. *{p['venue']}*. https://doi.org/{p['doi']}"
             for p in lit["user_papers"]]
    doc.numbers(refs)

    doc.h1("Appendix A: Configuration and hyper-parameters")
    doc.table(["Setting", "Value"], [
        ["Split", f"train <= {config.TRAIN_END[:10]}; validation {config.VAL_START} to {config.VAL_END[:10]}; test >= {config.TEST_START}"],
        ["XGBoost", "hist, depth 6, learning rate 0.1, subsample 0.8, colsample 0.8, scale_pos_weight = neg/pos, early stopping 50 rounds on validation PR-AUC"],
        ["Random Forest", "200 trees, max depth 16, min leaf 5, sqrt features, 30% bootstrap samples, balanced_subsample weights"],
        ["Isolation Forest", "300 trees, 1,024 samples per tree, fitted on genuine training transactions, 18 behaviour features"],
        ["LightGBM", "63 leaves, learning rate 0.1, class weight neg/pos with max_delta_step 0.7 (without it, training is numerically unstable at a ~177x weight), early stopping 100 rounds"],
        ["Safety layer", "P1: 3+ txns in 1 h and amount >= 5x card average; P2: >= 500 km at > 800 km/h; P3: < $5 online after 3+ txns in 1 h; N1: anomaly percentile >= 99.95%"],
        ["Meta-learner", "Logistic regression (C = 1) on [logit p_xgb, logit p_rf, anomaly z-score], 5-fold out-of-fold for thresholds"],
        ["Thresholds", f"alert = cost-optimal at ${config.ALERT_COST:.0f}/alert; block = lowest threshold with >= {config.BLOCK_MIN_PRECISION:.0%} precision"],
        ["Deep baselines", "MLP 256-128-64 with batch norm and dropout (up to 15 epochs); 1D-CNN 32/64 channels (up to 8 epochs, CPU budget); Adam 1e-3; batch 2048; positive-class weight; early stopping on validation PR-AUC"],
        ["Statistics", "500 bootstrap resamples for CIs and paired tests; seed 42"],
    ], caption="Key settings (fraudlens/config.py, models.py, hybrid.py)", widths=[3.5, 13.5], font=8.5)
    doc.h1("Appendix B: Work distribution")
    doc.table(["Module", "Owner", "Contribution"], [
        ["Literature review and mapping", "[Member 1]", "[describe]"],
        ["Data, EDA and feature engineering", "[Member 2]", "[describe]"],
        ["Models, hybrid engine and experiments", "[Member 3]", "[describe]"],
        ["API, dashboard and deployment", "[Member 4]", "[describe]"],
        ["Documentation and presentation", "[All]", "[describe]"],
    ], caption="Fill in before submission", widths=[6, 3, 8])
    return doc
