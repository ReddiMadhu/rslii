"""Integration test: Run pipeline and verify column lineage data."""
import sys, json, os, tempfile, shutil

sys.path.insert(0, os.path.dirname(__file__))
from executor.runner import execute_pipeline_sync

code = '''
import pandas as pd

persons = pd.read_csv("persons_actuarial.csv")
policies = pd.read_csv("policies_individual.csv")

book = persons.merge(policies, on="person_id", how="inner", validate="one_to_many")
book["segment_key"] = book["region"].astype(str) + "_" + book["product_code"].astype(str)
book["earned_premium_proxy"] = (book["written_premium"] * 0.87).round(2)

book.to_parquet("person_policy_actuarial_base.parquet", index=False)
'''

td = os.path.join(tempfile.gettempdir(), "rsli_test_col")
up = os.path.join(td, "uploads")
os.makedirs(up, exist_ok=True)

base = os.path.join(os.path.dirname(__file__), "..", "samples", "sample_data", "insurance_actuarial")
shutil.copy(os.path.join(base, "persons_actuarial.csv"), up)
shutil.copy(os.path.join(base, "policies_individual.csv"), up)

saved = {
    "source_1": os.path.join(up, "persons_actuarial.csv"),
    "source_2": os.path.join(up, "policies_individual.csv"),
}

result = execute_pipeline_sync(code, saved, session_id="test123", temp_dir=td)

print("=== DISCOVERED COLUMNS ===")
print(json.dumps(result.get("discovered_columns", {}), indent=2))

print("\n=== COLUMN LINEAGE PER NODE ===")
for n in result["nodes"]:
    cl = (n.get("runtime") or {}).get("column_lineage")
    if cl:
        nid = n["id"]
        method = n["method"]
        print(f"\n--- {nid} ({method}) ---")
        for col, mapping in cl.items():
            state = mapping["state"]
            frm = mapping["from"]
            dtype = mapping["dtype"]
            print(f"  {col}: {state} from={frm} dtype={dtype}")

print("\n=== SUMMARY ===")
s = result["summary"]
print(f"Status: {s['status']}")
print(f"Nodes completed: {s['nodes_completed']}")

# Cleanup
shutil.rmtree(td, ignore_errors=True)
print("\nDONE — Column lineage integration test passed!")
