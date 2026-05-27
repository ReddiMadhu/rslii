"""High Risk Example: Endless loop without break statement.

This script is classified as HIGH RISK and is BLOCKED from execution
because it contains a 'while True' structure without any exit break nodes.
"""

import pandas as pd

def parse_loop():
    # DANGEROUS: Endless loop without any break condition in the body
    # Flagged statically by the AST checker to prevent worker process lockups
    while True:
        pass
        
    df = pd.read_csv("uploads/policies.csv")
    df.to_csv("output/out.csv")

if __name__ == "__main__":
    parse_loop()
