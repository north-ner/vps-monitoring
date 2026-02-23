import requests
import json
import os
from datetime import datetime

PROM = "http://localhost:9090"
REPO_PATH = "/home/dev/monitoring/dashboard/metrics.json"
MAX_POINTS = 50

def query(promql):
    r = requests.get(f"{PROM}/api/v1/query", params={"query": promql})
    return float(r.json()["data"]["result"][0]["value"][1])

cpu = query('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)')
memory = query('(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100')
disk = query('(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100')

timestamp = datetime.utcnow().strftime("%H:%M:%S")

if os.path.exists(REPO_PATH):
    with open(REPO_PATH,"r") as f:
        data = json.load(f)
else:
    data = {"timestamps":[], "cpu":[], "memory":[], "disk":[]}

data["timestamps"].append(timestamp)
data["cpu"].append(round(cpu,2))
data["memory"].append(round(memory,2))
data["disk"].append(round(disk,2))

for key in data:
    data[key] = data[key][-MAX_POINTS:]

with open(REPO_PATH,"w") as f:
    json.dump(data,f,indent=2)

os.system("git -C /home/dev/monitoring add dashboard/metrics.json")
os.system('git -C /home/dev/monitoring commit -m "Update metrics"')
os.system("git -C /home/dev/monitoring push")
