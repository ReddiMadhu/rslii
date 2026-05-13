"""Phase 1 checks: extract_sources + /api/parse shape (run from backend/)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"


def _load(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


def main() -> int:
    from parser.ast_parser import ASTParser

    # --- complex_sales_pipeline: three file reads inside functions ---
    code = _load("complex_sales_pipeline.py")
    p = ASTParser(code)
    p.parse()
    sources = p.extract_sources()
    assert len(sources) == 3, f"expected 3 sources, got {len(sources)}: {sources}"
    methods = [s["method"] for s in sources]
    assert methods == ["read_csv", "read_excel", "read_parquet"], methods
    for s in sources:
        assert s["requires_upload"] is True, s
        assert s["skip_reason"] is None, s
    assert sources[0]["format"] == "csv" and sources[0]["filename"] == "sales_2023.csv"
    assert sources[1]["format"] == "excel" and sources[1]["filename"] == "customers.xlsx"
    assert sources[2]["format"] == "parquet" and sources[2]["filename"] == "products.parquet"

    sk = p.build_parse_skeleton()
    assert "nodes" in sk and "edges" in sk
    assert len(sk["nodes"]) == len(p.nodes)
    print("OK: complex_sales_pipeline sources + skeleton")

    # --- inline DataFrame ---
    df_code = 'import pandas as pd\ndf = pd.DataFrame({"x": [1, 2]})\n'
    p2 = ASTParser(df_code)
    p2.parse()
    src2 = p2.extract_sources()
    assert len(src2) == 1 and src2[0]["method"] == "DataFrame"
    assert src2[0]["requires_upload"] is False
    assert src2[0]["format"] == "inline"
    print("OK: DataFrame inline source")

    # --- external read_sql ---
    sql_code = 'import pandas as pd\nx = pd.read_sql("SELECT 1", con)\n'
    p3 = ASTParser(sql_code)
    p3.parse()
    src3 = p3.extract_sources()
    assert len(src3) == 1 and src3[0]["method"] == "read_sql"
    assert src3[0]["requires_upload"] is False
    assert src3[0]["skip_reason"] == "External source"
    print("OK: read_sql external skip")

    # --- validate_upload_extension (operations) ---
    from parser.operations import validate_upload_extension

    ok, _ = validate_upload_extension("csv", "data.tsv")
    assert ok
    ok_xlsx, msg = validate_upload_extension("csv", "x.xlsx")
    assert ok_xlsx is False and "Expected" in msg
    print("OK: validate_upload_extension")

    print("\nAll Phase 1 parse checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
