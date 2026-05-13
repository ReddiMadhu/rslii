"""Simple actuarial demo: persons + policies (CSV) → enriched Parquet base."""

import pandas as pd

persons = pd.read_csv("persons_actuarial.csv")
policies = pd.read_csv("policies_individual.csv")

book = persons.merge(policies, on="person_id", how="inner", validate="one_to_many")
book["segment_key"] = book["region"].astype(str) + "_" + book["product_code"].astype(str)
book["earned_premium_proxy"] = (book["written_premium"] * 0.87).round(2)

book.to_parquet("person_policy_actuarial_base.parquet", index=False)
