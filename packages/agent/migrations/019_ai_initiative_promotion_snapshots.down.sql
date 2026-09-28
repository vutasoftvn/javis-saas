-- Down 019 — table is a pure idempotency/cache store (no evidence is lost
-- elsewhere by dropping it: Company's ai_initiative_decisions remains the
-- source of truth), so an unconditional drop is safe.
DROP INDEX IF EXISTS models.idx_ai_initiative_snapshots_ws_init_rev;
DROP TABLE IF EXISTS models.ai_initiative_promotion_snapshots;
