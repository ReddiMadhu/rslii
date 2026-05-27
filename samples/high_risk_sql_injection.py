"""High Risk Example: Dynamic SQL construction (SQL Injection vulnerability).

This script is classified as HIGH RISK and is BLOCKED from execution
because it constructs a database query dynamically using string interpolation (f-string).
"""

import pandas as pd

def process_data():
    user_input_id = "105 OR 1=1"
    
    # DANGEROUS: Constructing SQL query dynamically via f-string
    # The AST risk engine detects this inside read_sql/execute/query calls
    query = f"SELECT * FROM policyholders WHERE id = {user_input_id}"
    df = pd.read_sql(query, con=None)
    
    df = df.dropna()
    df.to_csv("output/filtered_policyholders.csv")

if __name__ == "__main__":
    process_data()
