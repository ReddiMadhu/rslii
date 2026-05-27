"""High Risk Example: Dangerous system commands and command execution.

This script is classified as HIGH RISK and is BLOCKED from execution
because it attempts to perform shell command execution using forbidden standard libraries.
"""

import os
import pandas as pd

def execute_unauthorized_command():
    # DANGEROUS: os.system / subprocess call
    # The AST risk engine blocks all system execution functions for sandboxing safety
    os.system("echo 'Executing unauthorized shell script'")
    
    df = pd.read_csv("uploads/persons.csv")
    df.to_csv("output/out.csv")

if __name__ == "__main__":
    execute_unauthorized_command()
