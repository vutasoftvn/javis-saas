# Founder Trial MVP baseline migrations — DRAFT (Task 10)

Plan: `docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md` §Task 10.

These six `001_founder_trial_mvp_baseline` files were extracted by
`extract_baseline.py` from a `pg_dump --schema-only` of the fully-migrated dev
databases, then filtered to the Founder Trial R1 **retained** table allowlist
(spec §4). They are the starting point for Task 10 — **not yet installed**.

## Why they are drafts, not the real migration files

Installing them means, atomically:

1. `git rm` the entire historical migration trees under
   `packages/agent/migrations`, `services/cosa/migrations`, and
   `services/company/{identity,operations,commercial,finance-legal,academy}/migrations`;
2. dropping `--baseline` mode from all three runners
   (`packages/agent/scripts/migrate.py`, `services/cosa/scripts/migrate.mjs`,
   `services/company/scripts/migrate.mjs`) and making a pre-baseline ledger fail
   with an instruction to run only `make test-db-reset`;
3. updating `scripts/check-migration-backward-compat.mjs` and
   `scripts/test-migration-rollback.mjs` so 001 has no down migration and only
   migrations numbered after 001 need paired down SQL + compat review;
4. regenerating `deploy/schema/fingerprints.json`.

The spec's acceptance gate is: run `make test-db-reset` twice and prove the
resulting schema fingerprint is **identical**, then run the app smoke/E2E
against the freshly reset databases. That requires the three disposable test
databases (`javis_agent_test`, `javis_cosa_test`, `javis_workspace_test`).

Per the spec ("No workstream may delete historic migrations ... until its
replacement has passed its own fresh-database test evidence") and CLAUDE.md
rules 6/10/11, the destructive step must not land before that evidence exists.

## To proceed

```bash
bash scripts/provision-founder-trial-test-dbs.sh    # creates the 3 test DBs
# add the printed *_TEST_*_DATABASE_URL lines to .env, then:
#  - move these files to their real migration dirs (drop the middle segment
#    from the filename), git rm the historical trees, do steps 2–4 above
#  - make test-db-reset && make test-db-reset   # must yield identical fingerprints
#  - make schema-fingerprint-write && make schema-fingerprint-check
```

## Retained schemas (spec §7.3 inventory)

- Company: `core`, `strategy`, `operating`, `sales`, `commercial`, `finance`, `integration`
- COSA: `cosa`, `control_plane`
- Agent: `agent`, `agent_governance`, `agent_registry`, `agent_conversation`, `models`

Absent by design: `academy`, `legal`, `validation`, `engagement`, `vault`,
`knowledge`, `agent_evals`, `agent_artifact`, `agent_memory`.
