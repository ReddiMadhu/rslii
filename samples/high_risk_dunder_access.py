"""High Risk Example: Accessing private/dunder attributes.

This script is classified as HIGH RISK and is BLOCKED from execution
because it attempts to access python internal attributes (__code__).
"""

import pandas as pd

def inspect_internals():
    # DANGEROUS: Accessing dunder/private objects
    # Blocks sandboxing escapes via python frame reflection
    func_code = inspect_internals.__code__
    print(func_code)
    
    df = pd.read_csv("uploads/persons.csv")
    df.to_csv("output/out.csv")

if __name__ == "__main__":
    inspect_internals()
