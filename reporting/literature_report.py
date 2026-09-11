"""Research-to-implementation mapping report (landscape, table-driven)."""
from __future__ import annotations

from .engine import Doc
from .results import Results

# What the team's 20 papers taught us and where each lesson lives in FraudLens.
TEAM_MAP = {
    1: ("Deep learning can learn fraud patterns once tabular data is reshaped, but the paper reports accuracy only.",
        "Built a 1D-CNN baseline (features as a 1-channel sequence) and judged it by PR-AUC, not accuracy.",
        "fraudlens/deep.py, E1", "cnn"),
    2: ("Combining diverse models (voting/stacking) is more robust than one model, at the cost of complexity.",
        "Kept the stacking idea but with light, explainable learners (XGB + RF + IF) and a logistic meta-learner.",
        "fraudlens/hybrid.py, E4", "hybrid"),
    3: ("XGBoost is the strongest classical learner on card data; 99.96% accuracy hid a recall of only 83%.",
        "XGBoost is the main classifier; recall, PR-AUC and MCC are reported instead of accuracy.",
        "fraudlens/hybrid.py, E1, E6", "xgb"),
    4: ("A plain ML classifier is a useful baseline but does not adapt to new fraud or explain decisions.",
        "Included Logistic Regression, Decision Tree and a legacy rule engine as baselines.",
        "fraudlens/rules.py, E1", "lr"),
    5: ("Same Sparkov dataset; SMOTE + boosting is the usual recipe for imbalance.",
        "Adopted Sparkov as the primary dataset and tested SMOTE against class weighting and undersampling.",
        "fraudlens/models.py, E2", None),
    6: ("Large, imbalanced data needs sampling and per-user separation to scale.",
        "Per-card (per-user) behavioural state in a streaming feature store; undersampling arm in E2.",
        "fraudlens/features.py, E2", None),
    7: ("XGBoost + SMOTE is popular; near-perfect numbers (99.94% precision) raise leakage concerns.",
        "Re-ran XGBoost + SMOTE under four evaluation protocols to show how leakage inflates results.",
        "fraudlens/pipeline.py, E3", None),
    8: ("LR, SVM, DT exceed 98% precision on small data; DT reduces false positives.",
        "LR and DT kept as interpretable baselines on the same chronological split.",
        "E1", "dt"),
    9: ("Hybrid DL on IEEE-CIS still depends on feature engineering.",
        "Invested in behavioural feature engineering (27 engineered features) instead of heavier networks.",
        "fraudlens/features.py, E4", None),
    10: ("Balancing matters as much as the network; undersampling beat oversampling in their CNN.",
         "Four-way imbalance comparison; DL baselines trained with class weights.",
         "fraudlens/models.py, fraudlens/deep.py, E2", "mlp"),
    11: ("Real fraud detection is streaming, non-stationary, with investigator feedback.",
         "Time-ordered replay stream, STEP-UP tier and an analyst case queue whose verdicts are stored as labels.",
         "fraudlens/api/, dashboard /monitor and /cases", None),
    12: ("Survey of CNN/RNN/LSTM for financial fraud.",
         "Background for the DL baselines and the future-scope LSTM.",
         "Report ch. 2, fraudlens/deep.py", None),
    13: ("Weight detectors by reliability (confidence gating) and explain with SHAP.",
         "Detector weights are learned by the meta-learner; SHAP reason codes for every decision.",
         "fraudlens/hybrid.py, fraudlens/explain.py", "hybrid"),
    14: ("Fraud involves relationships (card-merchant-device); GNNs capture them at high cost.",
         "Relationship-aware behavioural features now (new merchant/category for this card); GNN as future work.",
         "fraudlens/features.py; future scope", None),
    15: ("Common datasets, techniques and open gaps.",
         "Gap analysis that shaped the objectives.",
         "Report ch. 2", None),
    16: ("Open challenges: imbalance, real-time, scalability, explainability.",
         "Each challenge has a module: E2 + calibration, real-time API, 67 us/txn feature store, SHAP.",
         "Whole system", None),
    17: ("Evolution from rules to ML to ensembles.",
         "Evolution storyline and the legacy-rules baseline.",
         "Report ch. 2, fraudlens/rules.py", "rules"),
    18: ("RF, DT, ANN compared with an emphasis on feature engineering.",
         "Random Forest as the second opinion; engineered features.",
         "fraudlens/hybrid.py, fraudlens/features.py", "rf"),
    19: ("DL review: CNN/RNN/LSTM/GRU and the right metrics for imbalance.",
         "PR-AUC/MCC metrics; sequence signal via velocity windows; LSTM as future work.",
         "fraudlens/metrics.py; future scope", None),
    20: ("Modern fraud detection needs big-data / cloud-ready, scalable deployment.",
         "API-first design, PostgreSQL-ready decision log, Docker deployment; streaming as future scope.",
         "fraudlens/api/, Dockerfile", None),
}

WHERE = {
    "dalpozzolo2015ssci": "ULB dataset source (E6); calibrated stacking output (hybrid.py)",
    "dalpozzolo2018": "Chronological split with label-delay gaps (config.py); PR-AUC & alert precision (metrics.py)",
    "dalpozzolo2015ijcnn": "Analyst feedback stored separately from dataset labels (api/db.py)",
    "dalpozzolo2014": "E2 imbalance comparison; multi-metric evaluation",
    "bahnsen2016": "Velocity and amount-vs-history features (features.py); money-based thresholds",
    "whitrow2009": "1 h / 24 h / 7 d aggregation windows (features.py)",
    "carcillo2021": "Isolation-Forest score in the stacking layer (hybrid.py); E4 'IF score as XGB feature'",
    "carcillo2018scarff": "Online feature store + real-time API; Kafka/Spark in future scope",
    "carcillo2018active": "STEP-UP tier and case queue (api/, dashboard /cases)",
    "lebichot2021": "Future scope: incremental retraining from reviewed cases",
    "leborgne2022handbook": "7-day delay gaps (config.py); replay simulation (API stream)",
    "jurgovsky2018": "Velocity windows capture sequence signal; LSTM in future scope",
    "chawla2002": "SMOTE arm of E2 and protocols A-C of E3",
    "chen2016": "Main classifier (hybrid.py)",
    "ke2017": "LightGBM benchmark (E1)",
    "liu2008": "Anomaly branch trained on genuine transactions only (hybrid.py)",
    "breiman2001": "Second-opinion classifier (hybrid.py)",
    "wolpert1992": "Logistic meta-learner fitted on the later validation period (hybrid.fit_meta)",
    "lundberg2017": "SHAP reason codes (explain.py)",
    "lundberg2020": "Exact TreeSHAP in the API + global importance figure",
    "psychoula2021": "SHAP computed inside the real-time API (XGBoost pred_contribs)",
    "grinsztajn2022": "E1: tree ensembles vs MLP / 1D-CNN",
    "shwartzziv2022": "E1: tree ensembles vs deep models; ensembling",
    "saito2015": "PR-AUC as the primary metric (metrics.py)",
    "chicco2020": "MCC in every results table",
    "santos2018": "E3 protocols; resampling only inside the training pipeline",
    "kaufman2012": "Causal feature store + online/offline parity test",
    "goorbergh2022": "E2 calibration (Brier) results; stacking instead of resampling",
    "elkan2001": "Cost-optimal alert threshold (metrics.cost_optimal_threshold)",
    "niculescu2005": "Calibration figure; logistic recalibration of boosted-tree scores",
    "vanderschueren2022": "Train normally, then set cost-based thresholds (hybrid.fit_meta)",
    "hoppner2022": "Missed-fraud cost = transaction amount (metrics.money_metrics)",
    "gama2014": "Monthly stability and PSI drift check (E7)",
    "taha2020": "Comparator for E6 (ULB)",
    "alarfaj2022": "ML-vs-DL comparator on ULB (E6)",
    "esenogho2022": "Comparator: ensemble + feature engineering",
    "liu2021pcgnn": "Future scope: card-merchant graph model",
    "grover2023fdb": "Benchmarking discipline; candidate future datasets",
    "hayat2025": "E3 reproduces the leakage effect they describe",
    "shanaa2025": "Closest published comparator for the ULB hybrid (E6)",
    "iqbal2025": "RF + XGBoost with SHAP (hybrid.py, explain.py)",
    "cavdar2026": "Keep both RF and XGBoost; sampling comparison (E2)",
    "thiongo2026": "ROC-vs-PR gap on ULB; drift monitoring (E7)",
    "luong2026": "Class weighting + threshold optimisation over resampling (E2)",
}

GROUPS = [
    ("Evaluation, leakage and metrics", {"evaluation", "dataset"}),
    ("Imbalance, calibration and cost-sensitive decisions", {"imbalance", "calibration", "cost"}),
    ("Behavioural features and sequences", {"features", "sequence"}),
    ("Models and ensembles", {"models"}),
    ("Hybrid and anomaly detection", {"hybrid"}),
    ("Explainable AI", {"xai"}),
    ("Streaming, concept drift and feedback", {"drift"}),
    ("Graph learning (future work)", {"graph", "survey"}),
]


def short_authors(a: str) -> str:
    names = [x.strip() for x in a.split(",") if x.strip()]
    if not names:
        return ""
    last = lambda s: s.split()[-1]
    if len(names) == 1:
        return last(names[0])
    if len(names) == 2:
        return f"{last(names[0])} & {last(names[1])}"
    return f"{last(names[0])} et al."


def cite_team(p: dict) -> str:
    return f"**{p['title']}**. {short_authors(p['authors'])}, {p['venue'].split(',')[0]}, {p['year']}."


def evidence(R: Results, model: str | None) -> str:
    if not model:
        return ""
    t = R.get("benchmark_sparkov", model, "test")
    if not t:
        return ""
    return f"Our {model.upper() if model != 'hybrid' else 'hybrid'}: PR-AUC {t['pr_auc']:.3f}, recall {t['recall']:.3f}"


def build(R: Results) -> Doc:
    lit = R.lit
    team = lit["user_papers"]
    add = lit["additional_papers"]
    ind = lit["industry_context"]
    verified = sum(p["verification"] == "verified" for p in team)
    add_verified = sum(p["verification"] == "verified" for p in add)
    doc = Doc(
        title="Research-to-Implementation Mapping",
        subtitle="How 20 team-selected papers and 44 further verified sources shaped FraudLens: what we learned, "
                 "what we adopted, and where each idea lives in the system",
        meta={"kicker": "LITERATURE MAPPING REPORT", "Project": "FraudLens: AI-Based Credit Card Fraud Detection",
              "Domain": "Cyber Security / Forensics · Machine Learning / Data Security",
              "Team": "[Team member names]", "Guide": "[Guide name]", "Institution": "[College / University]",
              "Date": "September 2026",
              "tags": "20 team papers|44 additional papers|11 industry & regulatory sources|16 techniques traced"},
        landscape=True,
    )
    doc.toc()

    doc.h1("1 How to read this report")
    doc.p("This report shows, paper by paper and technique by technique, **what we learned from the literature, what we "
          "adopted or deliberately rejected, and where it is implemented** in the FraudLens code and experiments. The main "
          "Project Report explains the system; this document is the audit trail from research to implementation.")
    doc.kpis([(str(len(team)), "Team-selected papers", f"{verified} fully verified"),
              (str(len(add)), "Additional papers", f"{add_verified} fully verified"),
              (str(len(ind)), "Industry / regulatory", "sources with dates"),
              ("16", "Techniques traced", "to code + experiment"),
              ("7", "Experiments (E1-E7)", "provide the evidence")])
    doc.table(["Code", "Experiment", "Question it answers"], [
        ["E1", "Model benchmark", "Which model family works best on the same chronological split, and how fast is it?"],
        ["E2", "Imbalance handling", "No balancing vs class weighting vs undersampling vs SMOTE: what really changes?"],
        ["E3", "Evaluation protocol", "How much do common shortcuts (SMOTE before split, random split, accuracy) inflate results?"],
        ["E4", "Ablation", "Do the behavioural features and each hybrid component actually help?"],
        ["E5", "Unseen fraud", "Does the anomaly layer catch a fraud type the supervised models never saw?"],
        ["E6", "ULB benchmark", "How does the system do on the European dataset most papers use?"],
        ["E7", "Business analysis", "Money saved, risk tiers, stability over time, drift, statistical significance"],
    ], caption="Experiments referenced as evidence throughout this report", widths=[1.2, 3.5, 14])
    doc.callout("Every citation was checked against Crossref, OpenAlex, Semantic Scholar or the publisher page. Where the "
                "team's list differed from the published record (title, year or venue), the correction is listed in "
                "Section 2 and the corrected form is used everywhere else.", "info", "Verification")

    doc.h1("2 Corrections to the team's paper list")
    corrections = [
        ["#7", "Enhancing Fraud Detection ... using XGBoost and SMOTE (2024)", "Full title ends with ': A Comparative Study'"],
        ["#8", "Design and Empirical Analysis ... (IEEE-2025)", "Published at ICBAIE **2024** (added to IEEE Xplore in 2025)"],
        ["#10", "... Deep Learning Method Using Data Balance Tools (IEEE-2021)", "ICCSMT **2020** (added to Xplore in 2021)"],
        ["#11", "An Assessment of Streaming Active Learning Strategies ... (IEEE-2018)", "IEEE DSAA **2017** (Xplore 2018); journal extension in IJDSA 2018"],
        ["#13", "XAI for Fraud Detection: An Attention-Based Ensemble ... (IEEE-2025)", "IEEE TIFS vol. 21 (**2026** volume, online Dec 2025); title ends '... for Reliable Decision-Making'"],
        ["#14", "Graph Neural Network-Based Fraud Detection in Credit Card Transactions (IEEE-2025)",
         "Real title: 'Similarity-Navigated Graph Neural Network-Based Fraud Detection in Credit Card Transactions Optimized with the Greylag Goose Algorithm' (ICMLAS 2025)"],
        ["#16", "Credit Card Fraud Detection using ML: Methods, Challenges and Solutions (IEEE-2025)", "BITCON **2024**"],
        ["#17", "Advancement in Credit Card Fraud Detection ... (IEEE-2025)", "ICSCAI **2024**"],
        ["#18", "Advanced Machine Learning Techniques for Credit Card Fraud Detection (IEEE-2024)", "Title ends with ': A Comprehensive Study' (ICOSEC 2024)"],
        ["#20", "Credit Card Fraud Detection in the Era of Disruptive Technologies (IEEE-2023)",
         "**Not IEEE**: Journal of King Saud University - Computer and Information Sciences 35(1), Elsevier, 2023"],
    ]
    doc.table(["#", "As listed by the team", "Verified correction"], corrections,
              caption="Differences between the team's list and the published record", widths=[1, 9, 13])
    doc.p("Titles #4 and #18 are generic (several papers share them); the one matching the stated year and content was "
          "selected, and the alternatives are recorded in docs/sources/literature.json.")

    doc.h1("3 The team's 20 papers: what we learned and where it lives")
    rows = []
    for p in team:
        learned, adopted, where, model = TEAM_MAP[p["no"]]
        res = p["reported_results"] or "-"
        ev = evidence(R, model)
        rows.append([str(p["no"]), cite_team(p), f"{p['methods']}. *Data:* {p['dataset']}", res, learned,
                     adopted + (f" **{ev}.**" if ev else ""), where])
    doc.table(["#", "Paper (verified)", "Approach and dataset", "Reported result", "What we learned",
               "What we adopted / changed", "Where in FraudLens"], rows,
              caption="Paper-by-paper mapping of the team's literature set", font=7.2,
              widths=[0.6, 4.2, 4.6, 2.4, 3.6, 4.2, 2.6], first_col_bold=True)

    doc.h1("4 Technique traceability matrix")
    b = lambda m, k="pr_auc": R.get("benchmark_sparkov", m, "test", k)
    fs = R.get("ablation", "feature_sets") or {}
    comp = R.get("ablation", "components") or {}
    prot = R.get("protocol", "ulb") or {}
    lat = R.get("benchmark_sparkov", "hybrid", "latency") or {}
    un = R.get("unseen") or {}

    def e(text):
        return text if "n/a" not in text else "pending (run the pipeline)"

    tr = [
        ["Gradient boosting (XGBoost) as main classifier", "T3, T7, Chen & Guestrin 2016, Grinsztajn 2022",
         "hybrid.py", e(f"E1: XGBoost PR-AUC {R.f(b('xgb'))} vs Logistic Regression {R.f(b('lr'))}")],
        ["Random Forest second opinion", "T5, T18, Breiman 2001, Cavdar 2026", "hybrid.py",
         e(f"E1: RF PR-AUC {R.f(b('rf'))}; used in the stack")],
        ["Isolation Forest anomaly layer", "Liu 2008, Carcillo 2021, Shanaa 2025", "hybrid.py",
         e(f"IF alone PR-AUC {R.f(b('iforest'))}; stacking weight {R.f(R.get('benchmark_sparkov', 'hybrid', 'meta_weights', 'iforest'), 2)}, so it also gets its own novelty route")],
        ["Safety layer: policy rules + novelty alarm", "RBI Master Direction 2021 (paras 34, 36-37), Carcillo 2021, Bahnsen 2016",
         "policy.py", e(f"{R.f(R.get('policy', 'test', 'extra_alerts_per_day'), 2)} extra step-ups/day on the test period; catches card testing and cloned cards in replays")],
        ["Stacked meta-learner (learned weights)", "T2, T13, Wolpert 1992", "hybrid.fit_meta",
         e(f"E4: stack PR-AUC {R.f(R.get('ablation', 'components', 'xgb+rf+iforest', 'test', 'pr_auc'))} vs XGB alone "
           f"{R.f(R.get('ablation', 'components', 'xgb', 'test', 'pr_auc'))}")],
        ["Behavioural aggregation features", "Whitrow 2009, Bahnsen 2016, T9, T18", "features.py",
         e(f"E4: PR-AUC raw fields {R.f(R.get('ablation', 'feature_sets', 'raw', 'test', 'pr_auc'))} -> behavioural "
           f"{R.f(R.get('ablation', 'feature_sets', 'deployed', 'test', 'pr_auc'))}")],
        ["Imbalance handling comparison", "T5, T6, T7, T10, Chawla 2002, van den Goorbergh 2022", "models.make_model",
         e(f"E2: XGB PR-AUC with SMOTE {R.f(R.get('imbalance_sparkov', 'xgb/smote', 'pr_auc'))} vs class weight "
           f"{R.f(R.get('imbalance_sparkov', 'xgb/weight', 'pr_auc'))}")],
        ["Calibrated probability + cost-based thresholds", "Elkan 2001, Niculescu-Mizil 2005, Vanderschueren 2022, Hoppner 2022",
         "hybrid.py, metrics.py", e(f"E7: {R.pct(R.get('benchmark_sparkov', 'hybrid', 'test_cost_threshold', 'savings_pct'))} of fraud losses avoided net of alert costs")],
        ["Leakage-free evaluation", "Santos 2018, Kaufman 2012, Hayat 2025, Dal Pozzolo 2018", "data.py, pipeline.py",
         e(f"E3 (ULB): F1 {R.f(prot.get('A', {}).get('f1'))} with SMOTE-before-split vs {R.f(prot.get('D', {}).get('f1'))} honest")],
        ["PR-AUC / MCC instead of accuracy", "Saito 2015, Chicco 2020, T19", "metrics.py",
         e(f"'Always genuine' scores {R.pct(R.get('protocol', 'sparkov', 'dummy', 'accuracy'), 2)} accuracy on Sparkov test data")],
        ["SHAP reason codes", "T13, Lundberg 2017/2020, Psychoula 2021, Iqbal 2025", "explain.py", "Every API decision ships its top reasons"],
        ["Deep-learning baselines", "T1, T2, T10, T12, T19", "deep.py",
         e(f"E1: MLP {R.f(b('mlp'))}, 1D-CNN {R.f(b('cnn'))} vs XGBoost {R.f(b('xgb'))}")],
        ["Real-time API + online feature store", "T11, T20, Carcillo 2018 (SCARFF)", "api/, features.py",
         e(f"Hybrid model latency p50 {R.f(lat.get('p50_ms'), 2)} ms per transaction")],
        ["Human-in-the-loop feedback", "T11, Carcillo 2018, Dal Pozzolo 2015", "api/db.py, /cases", "Review verdicts stored with the audit record"],
        ["Graph relationships", "T14, Liu 2021 (PC-GNN)", "features.py (novelty)", "Future work: card-merchant graph"],
        ["Sequence models", "T19, Jurgovsky 2018", "features.py (windows)", "Future work: LSTM on card histories"],
    ]
    doc.table(["Technique", "Source papers", "Implementation", "Evidence"], tr,
              caption="Technique -> sources -> code -> evidence (T# = team paper number)", widths=[5, 6, 3.6, 8.6],
              first_col_bold=True)

    doc.h1("5 Additional literature beyond the team's list")
    doc.p("These papers were added to close gaps the team's list did not cover: evaluation methodology, calibration, "
          "cost-sensitive decisions, the origin of each dataset, and recent work (2025-2026) on leakage, hybrids and XAI.")
    for title, topics in GROUPS:
        items = [p for p in add if p["topic"] in topics]
        if not items:
            continue
        doc.h2(title)
        doc.table(["Paper", "Key finding", "How we applied it", "Where in FraudLens"],
                  [[f"**{p['title']}**. {short_authors(p['authors'])} ({p['year']}), {p['venue'].split(',')[0]}"
                    + (f", {p['volume_pages']}" if p["volume_pages"] else ""),
                    p["key_finding"], p["apply_to_our_system"], WHERE.get(p["key"], "Background")] for p in items],
                  font=7.4, widths=[6, 7, 6, 4])

    doc.h1("6 Our results next to published claims")
    ulb = R.get("benchmark_ulb") or {}
    uh = ulb.get("hybrid", {}).get("test", {})
    ux = ulb.get("xgb", {}).get("test", {})
    sb = R.get("benchmark_sparkov") or {}
    cmp_rows = [
        ["T3 Jayasingh & Sri 2023", "ULB", "XGBoost accuracy 99.96%, recall 83%",
         f"XGBoost recall {R.f(ux.get('recall'))}, precision {R.f(ux.get('precision'))}, accuracy {R.pct(ux.get('accuracy'), 2)}; "
         f"hybrid recall {R.f(uh.get('recall'))}",
         "Same dataset. We split by time and tune the threshold on validation, so our numbers are harder to earn."],
        ["T7 Gupta et al. 2024", "not named", "precision 99.94%, accuracy 99.97%",
         f"E3 protocol A reproduces {R.pct(R.get('protocol', 'ulb', 'A', 'precision'), 2)} precision on ULB only when SMOTE is applied before the split",
         "Such precision is only reached with synthetic fraud in the test set; honest protocol D gives "
         f"{R.pct(R.get('protocol', 'ulb', 'D', 'precision'), 1)}."],
        ["T1 Banoth & Madhavi 2024", "Kaggle (unnamed)", "CNN accuracy 99.87%",
         f"Our 1D-CNN accuracy {R.pct(sb.get('cnn', {}).get('test', {}).get('accuracy'), 2)}, PR-AUC {R.f(sb.get('cnn', {}).get('test', {}).get('pr_auc'))} (Sparkov)",
         f"Accuracy is uninformative: 'always genuine' already scores {R.pct(R.get('protocol', 'sparkov', 'dummy', 'accuracy'), 2)}."],
        ["T10 Zhang & Huang 2020", "ULB", "~93% accuracy (CNN/AE + balancing)",
         f"Our MLP on ULB: PR-AUC {R.f(ulb.get('mlp', {}).get('test', {}).get('pr_auc'))}, F1 {R.f(ulb.get('mlp', {}).get('test', {}).get('f1'))}",
         "Tree ensembles outperform the DL baselines on the same split (E1, E6)."],
        ["Shanaa & Abdallah 2025", "ULB", "AE + XGBoost hybrid: recall 0.925, precision 0.957, F1 0.941",
         f"Hybrid: recall {R.f(uh.get('recall'))}, precision {R.f(uh.get('precision'))}, F1 {R.f(uh.get('f1'))}",
         "Closest design. Differences in split protocol (theirs is not chronological) make direct comparison indicative only."],
        ["Thiong'o et al. 2026", "ULB", "Unsupervised PR-AUC 0.069 (ROC-AUC 0.915)",
         f"Our Isolation Forest (unsupervised) PR-AUC {R.f(ulb.get('iforest', {}).get('test', {}).get('pr_auc'))}",
         "Confirms that unsupervised detectors alone are weak on ULB; they belong inside a hybrid."],
        ["Hayat & Magnier 2025", "ULB", "Leaky pipeline: 99.9% recall; corrected: modest",
         f"E3: F1 {R.f(R.get('protocol', 'ulb', 'A', 'f1'))} (leaky) vs {R.f(R.get('protocol', 'ulb', 'D', 'f1'))} (honest)",
         "Independent replication of the same leakage effect."],
    ]
    doc.table(["Paper", "Dataset", "Their reported result", "Our comparable result", "Comment"], cmp_rows,
              caption="Published numbers versus ours (reported numbers are taken from the papers' abstracts)",
              widths=[3.6, 2, 4.4, 6.6, 6.8], font=7.8)
    doc.callout("Numbers from different papers are rarely comparable: datasets, splits, thresholds and metrics differ. "
                "That is why FraudLens re-implements the competing ideas (CNN, MLP, SMOTE + XGBoost, simple ML, rules) and "
                "tests them on one shared chronological split with the same metrics (E1-E3).", "proof")

    doc.h1("7 Industry and regulatory context")
    doc.table(["Topic", "Figure", "Source", "Date"],
              [[c["claim"], c["figure"], f"{c['source']} ({c['url']})", c["date"]] for c in ind],
              caption="Context used in the introduction of the Project Report", widths=[5, 9, 7, 2], font=7.4)

    doc.h1("8 References")
    doc.h2("Team-selected papers (T1-T20)")
    doc.numbers([f"{p['authors']} ({p['year']}). {p['title']}. *{p['venue']}*. "
                 + (f"https://doi.org/{p['doi']}" if p["doi"] else p.get("url", "")) for p in team])
    doc.h2("Additional papers")
    doc.numbers([f"{p['authors']} ({p['year']}). {p['title']}. *{p['venue']}*"
                 + (f", {p['volume_pages']}" if p["volume_pages"] else "") + ". "
                 + (f"https://doi.org/{p['doi']}" if p["doi"] else p.get("url", "")) for p in add])
    return doc
