#!/usr/bin/env python3
"""
Test script to verify local n8n Docker instance and COSA Webhook integration.
Usage:
    python infra/n8n/test_local_n8n.py
"""

import datetime
import hashlib
import hmac
import json
import sys

import httpx

N8N_BASE_URL = "http://localhost:5678"
COSA_SECRET = "cosa-n8n-default-secret"
AUTOMATION_KEY = "system.telegram_notification"


def generate_hmac_signature(secret: str, payload_str: str, timestamp: str) -> str:
    data_to_sign = f"{timestamp}:{payload_str}".encode()
    return hmac.new(secret.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()


def test_n8n_health():
    print(f"[*] Checking n8n health at {N8N_BASE_URL}/healthz ...")
    try:
        res = httpx.get(f"{N8N_BASE_URL}/healthz", timeout=5.0)
        if res.status_code == 200:
            print(f" [OK] n8n is running and healthy! (Status: {res.status_code})")
            return True
        else:
            print(f" [WARN] n8n returned status {res.status_code}: {res.text}")
            return False
    except Exception as exc:
        print(f" [ERROR] Could not connect to n8n: {exc}")
        print(" -> Hint: Run 'docker compose -f infra/n8n/docker-compose.yml up -d' first.")
        return False


def test_webhook_trigger(test_mode=False):
    # n8n uses /webhook-test/... when workflow is listening in editor, or /webhook/... when active
    endpoint = f"/webhook-test/cosa/{AUTOMATION_KEY}" if test_mode else f"/webhook/cosa/{AUTOMATION_KEY}"
    url = f"{N8N_BASE_URL}{endpoint}"
    
    requested_at = datetime.datetime.now(datetime.UTC).isoformat()
    payload_data = {
        "automation_key": AUTOMATION_KEY,
        "execution_id": "999888777666",
        "workspace_id": "test_ws_001",
        "company_id": "test_co_001",
        "payload": {"message": "Test automation event from local script", "target": "@cosa_dev"},
        "correlation_id": "corr_test_001",
        "idempotency_key": "idem_test_001",
        "callback_url": "http://host.docker.internal:8000/api/v1/automations/callback",
        "requested_at": requested_at,
    }

    payload_json = json.dumps(payload_data, sort_keys=True)
    sig = generate_hmac_signature(COSA_SECRET, payload_json, requested_at)

    headers = {
        "Content-Type": "application/json",
        "X-COSA-Signature": sig,
        "X-COSA-Timestamp": requested_at,
    }

    print(f"\n[*] Triggering n8n webhook at {url} ...")
    try:
        res = httpx.post(url, content=payload_json, headers=headers, timeout=10.0)
        print(f"Response code: {res.status_code}")
        print(f"Response body: {res.text}")
        if res.status_code in (200, 201, 202):
            print(" [OK] Webhook triggered successfully!")
        else:
            print(" [NOTE] Webhook returned non-200. Ensure the workflow is imported and active (or in 'Listen for test event' mode).")
    except Exception as exc:
        print(f" [ERROR] Webhook trigger failed: {exc}")


if __name__ == "__main__":
    healthy = test_n8n_health()
    if healthy:
        # Prompt or try active webhook
        test_mode = "--test" in sys.argv
        test_webhook_trigger(test_mode=test_mode)
