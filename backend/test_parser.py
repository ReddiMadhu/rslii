"""Complex ETL test script — exercises all advanced parsing patterns."""
from parser.ast_parser import ASTParser
from parser.templates import apply_descriptions
import json

# ─── Test 1: Function-wrapped ETL with __main__ guard ───
test1 = '''
import pandas as pd

def load_data(path):
    df = pd.read_csv(path)
    df = df.dropna()
    return df

def transform(df):
    df = df[df["amount"] > 100]
    df["tax"] = df["amount"] * 0.1
    df = df.rename(columns={"amount": "total"})
    return df

if __name__ == "__main__":
    raw = load_data("orders.csv")
    result = transform(raw)
    result.to_parquet("output.parquet")
'''

# ─── Test 2: Chained method calls ───
test2 = '''
import pandas as pd

df = (pd.read_csv("data.csv")
      .dropna()
      .query("age > 18")
      .sort_values("name")
      .reset_index(drop=True))
df.to_csv("cleaned.csv")
'''

# ─── Test 3: Multiple independent pipelines ───
test3 = '''
import pandas as pd

# Pipeline 1
orders = pd.read_csv("orders.csv")
orders = orders.dropna()
orders.to_csv("clean_orders.csv")

# Pipeline 2
users = pd.read_excel("users.xlsx")
users = users.drop_duplicates()
users.to_json("clean_users.json")
'''

# ─── Test 4: Loop + conditional ───
test4 = '''
import pandas as pd

df = pd.read_csv("data.csv")
for col in ["a", "b", "c"]:
    df[col] = df[col].fillna(0)

if len(df) > 100:
    df = df.sample(100)

df.to_csv("output.csv")
'''

# ─── Test 5: Fan-in merge ───
test5 = '''
import pandas as pd

orders = pd.read_csv("orders.csv")
customers = pd.read_excel("customers.xlsx")
products = pd.read_parquet("products.parquet")

merged = orders.merge(customers, on="customer_id", how="left")
merged = merged.merge(products, on="product_id")
merged = merged.groupby("category").agg({"amount": "sum", "quantity": "mean"})
merged.to_csv("summary.csv")
'''

tests = {
    "1. __main__ + functions": test1,
    "2. Chained methods": test2,
    "3. Multiple pipelines": test3,
    "4. Loop + conditional": test4,
    "5. Fan-in merge": test5,
}

for name, code in tests.items():
    parser = ASTParser(code)
    result = parser.parse()
    result["nodes"] = apply_descriptions(result["nodes"])
    s = result["summary"]
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"  Nodes: {s['total_nodes']}  |  Edges: {len(result['edges'])}  |  Pipelines: {s['pipeline_count']}")
    print(f"  Sources: {len(s['sources'])}  |  Targets: {len(s['targets'])}")
    for n in result["nodes"]:
        loop = " [LOOP]" if n["is_loop"] else ""
        print(f"    [{n['category']:10}] {n['label']}{loop}")
    for e in result["edges"]:
        print(f"    {e['source']} --({e['variable']})--> {e['target']}")
