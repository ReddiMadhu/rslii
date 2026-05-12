import urllib.request
import json

code = 'import pandas as pd\ndf = pd.read_csv("orders.csv")\ndf = df.dropna()\ndf.to_csv("output.csv")\n'

data = json.dumps({"code": code, "filename": "test.py"}).encode()
req = urllib.request.Request("http://localhost:8000/api/analyze", data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print("STATUS: 200")
    print("nodes:", len(result.get("nodes", [])))
    print("summary:", json.dumps(result.get("summary", {}), indent=2))
except urllib.error.HTTPError as e:
    print("STATUS:", e.code)
    print("BODY:", e.read().decode())
