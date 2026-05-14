import sys, ast
sys.path.insert(0, r'c:\Users\madhu\Desktop\rsli\backend')
from parser.ast_parser import ASTParser

with open(r'c:\Users\madhu\Desktop\rsli\samples\demo\life_insurance_etl.py') as f:
    code = f.read()

parser = ASTParser(code)
result = parser.parse()

print('Nodes:', len(result['nodes']))
print('Edges:', len(result['edges']))
print('injection_steps:', len(parser.injection_steps))

for step in parser.injection_steps:
    print(step['node_id'], step['method'])
