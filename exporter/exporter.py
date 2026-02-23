import requests
import json
import os
import subprocess
from datetime import datetime, UTC

PROM = "http://localhost:9090"
REPO_BASE = "/home/dev/vps-monitoring"
METRICS_PATH = f"{REPO_BASE}/docs/metrics.json"
MAX_POINTS = 50


def query(promql):
    try:
        r = requests.get(f"{PROM}/api/v1/query", params={"query": promql}, timeout=5)
        r.raise_for_status()
        result = r.json().get("data", {}).get("result", [])
        if not result:
            return 0.0
        return float(result[0]["value"][1])
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        return 0.0


# ---- Collect Metrics ----
cpu = query('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)')
memory = query('(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100')
disk = query(
    '(1 - (node_filesystem_avail_bytes{mountpoint="/",fstype!="tmpfs"} '
    '/ node_filesystem_size_bytes{mountpoint="/",fstype!="tmpfs"})) * 100'
)

timestamp = datetime.now(UTC).strftime("%H:%M:%S")

# ---- Load Existing Data Safely ----
data = {
    "timestamps": [],
    "cpu": [],
    "memory": [],
    "disk": []
}

if os.path.exists(METRICS_PATH) and os.path.getsize(METRICS_PATH) > 0:
    try:
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("[WARN] Corrupted metrics.json, resetting file")

# ---- Append New Data ----
data["timestamps"].append(timestamp)
data["cpu"].append(round(cpu, 2))
data["memory"].append(round(memory, 2))
data["disk"].append(round(disk, 2))

# ---- Trim History ----
for key in data:
    data[key] = data[key][-MAX_POINTS:]

# ---- Write File ----
with open(METRICS_PATH, "w") as f:
    json.dump(data, f, indent=2)

print("[INFO] Metrics updated")

# ---- Git Push ----
try:
    subprocess.run(["git", "-C", REPO_BASE, "add", "docs/metrics.json"], check=True)
    subprocess.run(
        ["git", "-C", REPO_BASE, "commit", "-m", "Update metrics"],
        check=False
    )
    subprocess.run(["git", "-C", REPO_BASE, "push"], check=True)
    print("[INFO] Changes pushed to GitHub")
except Exception as e:
    print(f"[ERROR] Git push failed: {e}")
