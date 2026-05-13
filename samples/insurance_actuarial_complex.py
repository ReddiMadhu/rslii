"""Complex actuarial demo: persons, policies (CSV) + claims & rates (Parquet) + monthly exposure (CSV).

Multiple merges / join dependencies for an individual-life style rollforward by product and region.
"""

import pandas as pd

persons = pd.read_csv("persons_actuarial.csv")
policies = pd.read_csv("policies_individual.csv")
claims = pd.read_parquet("claims_by_policy.parquet")
rates = pd.read_parquet("cohort_rating_factors.parquet")
expo = pd.read_csv("monthly_exposures.csv")

base = persons.merge(policies, on="person_id", how="inner", suffixes=("_per", "_pol"))
base = base.merge(claims, on="policy_id", how="left")
base["claim_cnt"] = base["claim_cnt"].fillna(0).astype(int)
base["incurred_loss"] = base["incurred_loss"].fillna(0.0)

base["age_at_val"] = 2024 - base["birth_year"]
base["age_band"] = pd.cut(
    base["age_at_val"],
    bins=[0, 29, 44, 54, 64, 120],
    labels=["18-29", "30-44", "45-54", "55-64", "65+"],
    right=True,
).astype(str)

rated = base.merge(rates, on=["region", "age_band"], how="left")
rated["factor"] = rated["factor"].fillna(1.0)
rated["risk_adjusted_premium"] = (rated["written_premium"] * rated["factor"]).round(4)

monthly = rated.merge(expo, on="policy_id", how="inner")
monthly["earned_component"] = (
    monthly["written_premium"] * monthly["earned_fraction"] * monthly["factor"]
).round(4)

roll = monthly.groupby(["product_code", "region"], as_index=False).agg(
    policy_count=("policy_id", "nunique"),
    sum_earned=("earned_component", "sum"),
    mean_incurred=("incurred_loss", "mean"),
    sum_claims=("claim_cnt", "sum"),
)
roll = roll.sort_values(["product_code", "region"])
roll.to_csv("actuarial_demo_rollforward_by_segment.csv", index=False)
