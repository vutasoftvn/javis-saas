-- Down Migration 015: agent_memory.* và agent_evals.*.
-- Không xoá memory/eval evidence thật: chỉ rollback khi các bảng còn rỗng.

DO $$
BEGIN
  IF to_regclass('agent_memory.agent_memories') IS NOT NULL
     AND EXISTS (SELECT 1 FROM agent_memory.agent_memories LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 015: agent_memory.agent_memories contains data.';
  END IF;
  IF to_regclass('agent_evals.promotion_evidence') IS NOT NULL
     AND EXISTS (SELECT 1 FROM agent_evals.promotion_evidence LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 015: agent_evals.promotion_evidence contains data.';
  END IF;
  IF to_regclass('agent_evals.runs') IS NOT NULL
     AND EXISTS (SELECT 1 FROM agent_evals.runs LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 015: agent_evals.runs contains data.';
  END IF;
END $$;

DROP SCHEMA IF EXISTS agent_evals CASCADE;
DROP SCHEMA IF EXISTS agent_memory CASCADE;
