# COSA Phase C Delegation Runbook

**Status:** Production operations baseline

**Scope:** `RunStep` → `DelegationJob` → provider → continuation

## Safety rules

- Derive `workspace_id` from authentication. Never copy it from a request body.
- Treat every `DelegationJob` row as an immutable attempt. Operator retry appends
  `attempt_no + 1`; it does not edit a terminal attempt.
- Never paste `lease_token`, device raw tokens, credentials, prompts containing
  secrets, or unredacted provider payloads into tickets or metrics labels.
- Disable both `agent_delegation` and the provider-specific flag before incident
  intervention. Existing leased work is not magically cancelled by a kill switch;
  request cancellation explicitly.

## Read-only diagnosis

Use the authenticated API for one job:

~~~text
GET /api/v1/agents/delegations/{job_id}
~~~

Cross-workspace IDs deliberately return `404`. For database operators, these
queries are read-only and contain no secret-bearing payload columns:

~~~sql
SELECT status, count(*)
FROM delegation_jobs
GROUP BY status
ORDER BY status;

SELECT id, run_step_id, attempt_no, provider_name, status,
       available_at, next_poll_at, lease_expires_at, error_code
FROM delegation_jobs
WHERE status NOT IN ('succeeded', 'failed', 'cancelled', 'denied')
ORDER BY available_at ASC
LIMIT 100;

SELECT id, claimed_by, status, lease_expires_at, heartbeat_at
FROM delegation_jobs
WHERE lease_expires_at < now()
  AND status NOT IN ('succeeded', 'failed', 'cancelled', 'denied');
~~~

`delegation_metrics_snapshot(db)` reports bounded aggregate queue depth/age,
expired leases, retry/dead-letter counts, approval waits, latency, reservations
and continuation lag. It emits no workspace/job/device identifiers.

## Cancel and retry

Request cancellation with:

~~~text
POST /api/v1/agents/delegations/{job_id}/cancel
~~~

Queued work becomes `cancel_requested` and is finalized by the worker. A provider
that cannot honestly cancel returns that limitation; do not report it as stopped.

Retry only after the cause is corrected and the prior attempt is `failed` or
`cancelled`:

~~~text
POST /api/v1/agents/delegations/{job_id}/retry
~~~

The response is a new job ID and idempotency key. `409` means the source is not in
a retryable state. Repeated retry of the same terminal attempt returns the already
materialized next attempt rather than creating duplicates.

## Dead letters and continuation lag

1. Inspect `error_code`, provider health and the last ordered `run_events` entries.
2. Confirm the provider name/runtime still exists; unknown routing fails closed.
3. Check expired leases. Recovery preserves a known provider handle and never
   repeats `start` merely because a worker died.
4. For a CoS run whose required specialist steps are all terminal but the
   `OutcomeRun` remains `running`, call the internal continuation reconciler.
   Synthesis is protected by a PostgreSQL advisory lock and the durable
   `mission_completed` event, so retries are idempotent.
5. Retry only after remediation; never rewrite status/result fields by hand.

## Provider caveats

- `in_process`: runtime selection is explicit; an unknown runtime does not fall
  back to mock.
- `codex_device` / `claude_device`: raw lease tokens are shown once and stored only
  as hashes. Device trust, capability and allowed-project checks happen at claim.
- `n8n`: callbacks require HMAC + timestamp and Phase-C workspace/provider/external
  run/correlation identity. Duplicate signatures return `409`. Native cancellation
  is not supported by the current n8n API.
- `sandbox`: registered only with `COSA_DELEGATION_SANDBOX_PROVIDER`; there is no
  implicit default/mock sandbox for delegated work.

## Recovery confirmation

After intervention, verify queue age falls, expired lease count reaches zero,
reserved root budget returns to zero for terminal work, each step has only one job
per attempt number, and each completed CoS mission has exactly one
`mission_completed` materialization event.
