# Staging release checklist

- Validate production-only secrets with no development fallback; use a secret manager.
- Perform a Postgres backup/restore drill and MinIO/S3 recovery test.
- Enable structured request-ID logs and error tracking.
- Configure rate limits and a web CORS policy.
- Load-test worker concurrency and set provider budget controls.
- Review dependency vulnerabilities.
- Make a separate security, legal, and account-risk decision before exposing the personal
  Zalo connector outside controlled development.
