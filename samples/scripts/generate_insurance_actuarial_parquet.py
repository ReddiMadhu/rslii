"""Build Parquet facts used by insurance_complex_demo.py (run from repo root or samples/)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = (HERE.parent / "sample_data" / "insurance_actuarial").resolve()
DATA.mkdir(parents=True, exist_ok=True)

policies = pd.read_csv(DATA / "policies_individual.csv")

# Claims rolled to policy level (actuarial triangle style summary)
rng = [
    ("POL10001", 1, 1200.0, 2023),
    ("POL10002", 0, 0.0, 2024),
    ("POL10003", 2, 4500.0, 2023),
    ("POL10005", 1, 890.0, 2022),
    ("POL10007", 0, 0.0, 2024),
    ("POL10008", 1, 2100.0, 2023),
    ("POL10011", 3, 12500.0, 2021),
    ("POL10013", 0, 0.0, 2024),
    ("POL10015", 2, 3200.0, 2022),
    ("POL10017", 1, 5600.0, 2023),
    ("POL10018", 0, 0.0, 2024),
    ("POL10021", 0, 0.0, 2024),
    ("POL10022", 1, 300.0, 2024),
    ("POL10023", 0, 0.0, 2024),
]
claims = pd.DataFrame(
    rng,
    columns=["policy_id", "claim_cnt", "incurred_loss", "last_claim_year"],
)
claims = claims.merge(policies[["policy_id"]], on="policy_id", how="right")
claims["claim_cnt"] = claims["claim_cnt"].fillna(0).astype(int)
claims["incurred_loss"] = claims["incurred_loss"].fillna(0.0)
claims["last_claim_year"] = claims["last_claim_year"].fillna(0).astype(int)

bands = []
for region in ["Northeast", "South", "Midwest", "West"]:
    for band, factor in [
        ("18-29", 0.92),
        ("30-44", 1.00),
        ("45-54", 1.12),
        ("55-64", 1.28),
        ("65+", 1.45),
    ]:
        bands.append({"region": region, "age_band": band, "factor": factor})
cohort_rates = pd.DataFrame(bands)

claims.to_parquet(DATA / "claims_by_policy.parquet", index=False)
cohort_rates.to_parquet(DATA / "cohort_rating_factors.parquet", index=False)
print("Wrote:", DATA / "claims_by_policy.parquet")
print("Wrote:", DATA / "cohort_rating_factors.parquet")
