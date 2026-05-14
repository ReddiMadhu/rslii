import sys
import os

sys.path.append(os.path.dirname(__file__))

from rsli.parser.ast_parser import PipelineParser

p = PipelineParser('../samples/demo/life_insurance_etl.py')
p.parse()
for n in p.nodes:
    if "groupby" in n.code or "agg" in n.code:
        print(f"Node ID: {n.id}")
        print(f"Method: {n.method}")
        print(f"Code:\n{n.code}")
        print("-" * 40)
