import sys
import os
import hmac
import hashlib
import json
import requests

def main():
    if len(sys.argv) < 4:
        print("Usage: notify_step.py <slug> <step> <status> [message]")
        sys.exit(1)

    slug = sys.argv[1]
    step = sys.argv[2]
    status = sys.argv[3]
    message = sys.argv[4] if len(sys.argv) > 4 else ""

    secret = os.environ.get("PIPELINE_WEBHOOK_SECRET")
    api_url = os.environ.get("PLATFORM_API_URL", "http://localhost:8000")

    if not secret:
        print("Error: PIPELINE_WEBHOOK_SECRET not set in env.")
        sys.exit(1)

    payload = {
        "step": step,
        "status": status,
        "message": message
    }
    data = json.dumps(payload)
    signature = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()

    url = f"{api_url}/api/v1/pipeline/{slug}/step-update/"
    headers = {
        "Content-Type": "application/json",
        "X-Pipeline-Signature": signature
    }

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        print(f"Notification sent to {url}: Status Code {response.status_code}")
        if response.status_code != 200:
            print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"Failed to send notification: {e}")

if __name__ == "__main__":
    main()
