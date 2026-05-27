"""PII and sensitive data sanitization for LLM contexts."""

import os
import re
from typing import List, Dict, Tuple, Any

class LLMDataSanitizer:
    """Strips sample data and sensitive values from LLM context."""
    
    DEFAULT_SENSITIVE_COLUMN_PATTERNS = [
        "name", "email", "phone", "ssn", "social_security",
        "address", "dob", "date_of_birth", "salary", "income",
        "account", "credit_card", "passport", "license",
        "beneficiary", "dependent", "zip", "postal",
    ]
    
    STRUCTURED_PII_REGEX = {
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),
        "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    }
    
    def __init__(self):
        self.sensitive_patterns = list(self.DEFAULT_SENSITIVE_COLUMN_PATTERNS)
        extra_cols = os.environ.get("RSLI_SENSITIVE_COLUMNS", "")
        if extra_cols:
            for part in extra_cols.split(","):
                c = part.strip().lower()
                if c and c not in self.sensitive_patterns:
                    self.sensitive_patterns.append(c)

    def sanitize_for_llm(self, nodes: List[Dict[str, Any]], code: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Returns sanitized nodes (no sample_output/sample_input) and code.
        Code is passed through as-is (it's the user's script, not data).
        """
        sanitized = []
        for node in nodes:
            n = dict(node)
            
            # 1. Clean runtime attributes
            if "runtime" in n and isinstance(n["runtime"], dict):
                runtime = dict(n["runtime"])
                runtime.pop("sample_output", None)
                runtime.pop("sample_input", None)
                n["runtime"] = runtime
                
            # 2. Clean trace/snapshot nodes (e.g. from column journey trace)
            n.pop("sample_output", None)
            n.pop("sample_input", None)
            n.pop("sampleOutput", None)
            n.pop("sampleInput", None)
            
            # 3. Clean schema values if they contain sample row outputs
            if "sample_data" in n:
                n.pop("sample_data", None)
            if "sampleData" in n:
                n.pop("sampleData", None)
                
            sanitized.append(n)
            
        return sanitized, code
    
    def flag_sensitive_columns(self, columns: List[str]) -> List[str]:
        """Returns list of column names that match sensitive patterns."""
        flagged = []
        for col in columns:
            col_lower = col.lower()
            if any(pat in col_lower for pat in self.sensitive_patterns):
                flagged.append(col)
        return flagged
