# Release Security and Recovery Checklist

This checklist documents mandatory operational and security gates that must be approved and attested prior to production deployment.

## 1. Edge Security & Rate Limiting

| Parameter | Approved Value | Description / Rationale |
|---|---|---|
| **WAF / Edge Provider** | Cloudflare / Caddy Edge Gateway | Edge DDoS protection, managed TLS, and reverse proxying |
| **Login Rate Limit (IP)** | 5 requests / 15 minutes | Mitigates brute-force credential stuffing per origin IP |
| **Login Rate Limit (Identifier)** | 5 attempts / 15 minutes | Mitigates distributed attacks targeting a single account |
| **Registration Rate Limit** | 3 requests / hour per IP | Prevents automated spam tenant creation |
| **Bot-Verification Policy** | Cloudflare Turnstile / Managed Challenge | Required on `/auth/login`, `/auth/register`, and public webhook endpoints |
| **Attestation Variable** | `EDGE_RATE_LIMIT_ATTESTED=true` | Must be explicitly asserted in production deployment configuration |

## 2. Backup & Disaster Recovery Baseline

| Parameter | Approved Value | Description / Rationale |
|---|---|---|
| **Backup Cadence** | Daily at 02:00 UTC | Automated `pg_dump -Fc` via `scripts/backup/pg-backup.sh` |
| **Backup Retention** | 14 daily + 8 weekly snapshots | SHA-256 verified manifests in secure S3/MinIO bucket |
| **Target RPO (Recovery Point Objective)** | 24 hours (Snapshot) / < 1 hour (WAL archive) | Maximum allowable data loss window |
| **Target RTO (Recovery Time Objective)** | 2 hours | Maximum allowable time to complete restore & smoke verification |
| **Restore Drill Cadence** | Every 30 days (≤ 720 hours) | Verified via `scripts/backup/check-backup-freshness.sh` |
| **Preflight Max Age** | `RESTORE_TEST_MAX_AGE_HOURS=720` | Automated gate in `make deploy-preflight` |

## 3. Incident Management & Observability

| Parameter | Approved Value | Description / Rationale |
|---|---|---|
| **Alert Destination** | Operations Slack `#ops-alerts` & PagerDuty | Primary and secondary on-call escalation routes |
| **Dead-Letter Alarm** | `dead_letter_count > 0` for 5m | Immediate notification for unprocessable background tasks |
| **Schedule Retry Alarm** | `schedule_retry_age > 10m` | Alerts if scheduled tasks remain in retry state |
| **Auth Abuse Alarm** | `rate(http_failed_logins[5m]) > 10` | Early detection of active brute force campaigns |

## 4. Attestation Sign-off

- **Infrastructure Owner:** Approved
- **Security & Compliance:** Approved
- **Status:** Release Gate Passed
