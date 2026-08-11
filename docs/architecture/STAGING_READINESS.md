# Staging readiness

Before staging: validate production-only secrets from a secret manager; rehearse Postgres
backup/restore and MinIO/S3 recovery; add request IDs, error tracking, rate limits and web
CORS; load-test worker concurrency; set AI-provider budgets; and review dependencies for
vulnerabilities. Personal Zalo automation requires a separate risk decision before any
exposure outside controlled development.
