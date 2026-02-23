from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPO")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


def find_issue_by_title(title):
    query = f'repo:{REPO} "{title}" in:title'
    r = requests.get(
        "https://api.github.com/search/issues",
        headers=HEADERS,
        params={"q": query},
    )
    items = r.json().get("items", [])
    return items[0] if items else None


def create_issue(title, body, severity):
    requests.post(
        f"https://api.github.com/repos/{REPO}/issues",
        headers=HEADERS,
        json={
            "title": title,
            "body": body,
            "labels": ["monitoring", severity]
        }
    )


def close_issue(issue_number):
    requests.patch(
        f"https://api.github.com/repos/{REPO}/issues/{issue_number}",
        headers=HEADERS,
        json={"state": "closed"}
    )


@app.post("/alert")
async def receive_alert(request: Request):
    payload = await request.json()

    for alert in payload.get("alerts", []):
        fingerprint = alert.get("fingerprint")
        status = alert.get("status")
        severity = alert.get("labels", {}).get("severity", "info")
        summary = alert["annotations"].get("summary", "Prometheus Alert")

        # Unique title includes fingerprint
        title = f"[ALERT] {summary} ({fingerprint})"

        body = f"""
### Prometheus Alert

- **Fingerprint:** {fingerprint}
- **Status:** {status}
- **Severity:** {severity}
- **Instance:** {alert.get("labels", {}).get("instance")}
- **Job:** {alert.get("labels", {}).get("job")}
- **Starts At:** {alert.get("startsAt")}
"""

        existing = find_issue_by_title(title)

        if status == "firing":
            if not existing:
                create_issue(title, body, severity)

        elif status == "resolved":
            if existing and existing["state"] == "open":
                close_issue(existing["number"])

    return {"status": "processed"}
