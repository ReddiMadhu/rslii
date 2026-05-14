"""Life Insurance Book Analysis — Actuarial ETL Pipeline

Combines policyholder demographics, policy records, and claims data
to produce a segment-level loss ratio analysis by product and region.

Input:  policyholders.csv, policies.csv, claims.csv
Output: segment_loss_ratio_analysis.csv
"""

import pandas as pd

# ── Read source data ──────────────────────────────────────────────
policyholders = pd.read_csv("policyholders.csv")
policies = pd.read_csv("policies.csv")

# ── Join policyholders with their policies ────────────────────────
book = policyholders.merge(policies, on="policyholder_id", how="inner")

# ── Keep only active policies ─────────────────────────────────────
book = book[book["status"] == "Active"]

# ── Drop agent notes (not needed for analysis) ────────────────────
book = book.drop(columns=["agent_notes"])

# ── Standardize column names ──────────────────────────────────────
book = book.rename(columns={"smoker_status": "is_smoker"})

# ── Parse dates and calculate policyholder age ────────────────────
book["date_of_birth"] = pd.to_datetime(book["date_of_birth"])
book["age"] = 2024 - book["date_of_birth"].dt.year

# ── Bring in claims data (left join — not all policies have claims)
claims = pd.read_csv("claims.csv")
book = book.merge(claims, on="policy_number", how="left")

# ── Clean nulls from left join ────────────────────────────────────
book["claim_amount"] = book["claim_amount"].fillna(0.0)
book["claim_count"] = book["claim_id"].notna().astype(int)

# ── Derive actuarial metrics ──────────────────────────────────────
# Mortality loading factor based on age and smoking status
book["mortality_factor"] = 1.0
book.loc[book["age"] > 50, "mortality_factor"] += 0.35
book.loc[book["is_smoker"] == "Yes", "mortality_factor"] += 0.50

# Risk-adjusted premium
book["risk_adjusted_premium"] = (
    book["annual_premium"] * book["mortality_factor"]
).round(2)

# Loss ratio at policy level
book["loss_ratio"] = (
    book["claim_amount"] / book["risk_adjusted_premium"].replace(0, float("nan"))
).fillna(0.0).round(4)

# ── Aggregate by product × region for segment analysis ────────────
segment_summary = book.groupby(
    ["product_type", "region"], as_index=False
).agg(
    policy_count=("policy_number", "nunique"),
    total_face_amount=("face_amount", "sum"),
    total_premium=("annual_premium", "sum"),
    total_risk_premium=("risk_adjusted_premium", "sum"),
    total_claims=("claim_amount", "sum"),
    avg_age=("age", "mean"),
    avg_loss_ratio=("loss_ratio", "mean"),
)

# ── Write output ──────────────────────────────────────────────────
segment_summary.to_csv("segment_loss_ratio_analysis.csv", index=False)
