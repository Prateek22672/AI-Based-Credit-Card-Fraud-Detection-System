"""Scam scenarios for demonstrations: how each kind of fraud looks to FraudLens.

Each scenario is a short sequence of transactions played against a real
card's history inside a sandbox copy of that card's state. The card's real
state is never modified, so the live demo and later scenarios are unaffected.
"""
from __future__ import annotations

import math

SCENARIOS = {
    "card_testing": {
        "title": "Card-testing attack",
        "scam": ("Criminals who buy stolen card numbers first make tiny online charges to find out which "
                 "cards still work, then make one large purchase before the owner notices."),
        "signals": ["Burst of transactions within minutes", "Night-time activity", "Online (card-not-present) channel",
                    "Sudden jump from $1-3 to a large amount", "Merchants never used by this card"],
        "start": (23, 30),
        "steps": [(0, 1.19, "misc_net", 30, False), (3, 2.05, "misc_net", 30, False),
                  (6, 1.50, "misc_net", 30, False), (9, 3.10, "misc_net", 30, False),
                  (14, 849.99, "shopping_net", 30, False)],
    },
    "stolen_card_spree": {
        "title": "Stolen-card spending spree",
        "scam": ("After a card is stolen or its details are phished, the fraudster spends as much as possible "
                 "in a few hours, usually late at night, before the card is blocked."),
        "signals": ["Many transactions in 24 h compared with the card's normal", "Cumulative spend in 24 h",
                    "Amounts far above the card's average", "Night-time activity"],
        "start": (22, 15),
        "steps": [(0, 312.40, "grocery_pos", 5, False), (35, 489.99, "shopping_pos", 8, False),
                  (70, 64.20, "gas_transport", 6, False), (110, 925.00, "shopping_net", 5, False),
                  (150, 1045.50, "shopping_net", 5, False), (200, 870.00, "misc_net", 5, False)],
    },
    "midnight_online": {
        "title": "Late-night high-value online purchase",
        "scam": ("Card details leaked in a data breach or phishing page are used for a single expensive "
                 "online order at an hour when the real cardholder is asleep."),
        "signals": ["Amount many times the card's average", "Online channel", "Night-time",
                    "Category this card rarely uses"],
        "start": (2, 10),
        "steps": [(0, 1249.00, "shopping_net", 10, False)],
    },
    "impossible_travel": {
        "title": "Impossible travel (cloned card)",
        "scam": ("A skimmed card is cloned and used in a shop far away shortly after the genuine card was "
                 "used near home. A person cannot physically be in both places."),
        "signals": ["Distance and speed since the previous transaction", "Distance from home",
                    "Unsupervised anomaly score (this pattern is rare in labelled training data)"],
        "start": (13, 0),
        "steps": [(0, 42.10, "grocery_pos", 3, True), (25, 389.00, "shopping_pos", 1100, False)],
    },
    "escalation": {
        "title": "Escalating amounts (limit probing)",
        "scam": ("A fraudster probes how much the card will allow, raising the amount each time and moving "
                 "into late evening."),
        "signals": ["Growing 24 h spend", "Amount vs card history", "Transition into night-time",
                    "Online categories"],
        "start": (20, 45),
        "steps": [(0, 85.00, "misc_net", 12, False), (40, 160.00, "misc_net", 12, False),
                  (85, 340.00, "shopping_net", 12, False), (130, 690.00, "shopping_net", 12, False)],
    },
    "normal_day": {
        "title": "Normal customer day (control)",
        "scam": "No fraud: everyday purchases that match the card's usual categories, amounts and times.",
        "signals": ["Amounts close to the card's average", "Categories the card uses often",
                    "Daytime", "Merchants near home"],
        "start": (12, 30),
        "steps": "normal",
    },
}


def offset_point(lat: float, lon: float, km: float, bearing_deg: float = 60.0) -> tuple[float, float]:
    """Point ``km`` away from (lat, lon) along a bearing (flat-earth approximation is fine < 2000 km)."""
    b = math.radians(bearing_deg)
    dlat = km / 111.0 * math.cos(b)
    dlon = km / (111.0 * max(math.cos(math.radians(lat)), 0.2)) * math.sin(b)
    return lat + dlat, lon + dlon


def normal_steps(card_summary: dict) -> list[tuple]:
    mean = card_summary.get("mean_amt") or 60.0
    cats = (card_summary.get("top_categories") or ["grocery_pos", "gas_transport", "home"]) + ["home", "food_dining"]
    return [(0, round(mean * 0.8, 2), cats[0], 5, True), (180, round(mean * 1.1, 2), cats[1], 8, True),
            (360, round(mean * 0.6, 2), cats[2], 4, True)]
