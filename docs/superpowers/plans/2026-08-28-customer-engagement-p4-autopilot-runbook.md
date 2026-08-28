# Customer Engagement P4: Autopilot Runbook & Operations Manual

## 1. Overview
The Customer Support Autopilot provides automated FAQ answering, message drafting, and intelligent queue routing for customer messaging channels (Zalo OA, Facebook, WebChat).

---

## 2. Emergency Procedures (Kill Switch)

### 2.1 Instant Disable via API
```bash
curl -X POST https://api.javis.vn/commercial/engagement/autopilot/kill-switch \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"workspaceId": "<WORKSPACE_ID>"}'
```

### 2.2 Instant Disable via Database
```sql
UPDATE engagement.engagement_autopilot_settings
SET enabled = FALSE, updated_at = NOW()
WHERE workspace_id = <WORKSPACE_ID>;
```

---

## 3. Threshold Monitoring & Metrics
Monitor health via:
`GET /agent/autopilot/metrics?workspaceId=<WORKSPACE_ID>`

Key metrics and thresholds:
- **Containment Rate**: Minimum target >= 80%.
- **Error Rate**: Maximum allowable <= 5%.
- **Human Takeover Rate**: Maximum allowable <= 15%.
- **Approval Latency P95**: Target < 60 seconds.

---

## 4. Production Promotion Checklist
Before enabling Autopilot in a production workspace:
1. Complete staging E2E evaluation (`.venv/bin/pytest tests/apps/cosa/evals/test_customer_support_autopilot_evals.py`).
2. Verify all templates are registered in `engagement_autopilot_templates`.
3. Set environment variable `ENGAGEMENT_AUTOPILOT_PROD_GATE_OVERRIDE=true` in deployment environment.
4. Call `PUT /commercial/engagement/autopilot/settings` with `"enabled": true, "envAllowlist": ["test", "staging", "production"]`.
