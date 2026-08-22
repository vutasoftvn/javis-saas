CREATE TABLE strategy.okr_cycles (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  brain_id BIGINT,
  mvp_stage_id BIGINT,
  name TEXT NOT NULL,
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE strategy.okr_objectives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT NOT NULL REFERENCES strategy.okr_cycles(id),
  strategic_objective_id BIGINT,
  title TEXT NOT NULL,
  why TEXT,
  owner_id BIGINT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE strategy.key_results (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  objective_id BIGINT NOT NULL REFERENCES strategy.okr_objectives(id),
  title TEXT,
  metric_id BIGINT,
  baseline_value DOUBLE PRECISION,
  current_value DOUBLE PRECISION,
  target_value DOUBLE PRECISION,
  unit TEXT,
  cadence TEXT,
  metric_type TEXT,
  evidence_refs JSONB,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_okr_cycles_workspace_id ON strategy.okr_cycles(workspace_id);
CREATE INDEX idx_okr_objectives_workspace_id ON strategy.okr_objectives(workspace_id);
CREATE INDEX idx_okr_objectives_cycle_id ON strategy.okr_objectives(cycle_id);
CREATE INDEX idx_key_results_workspace_id ON strategy.key_results(workspace_id);
CREATE INDEX idx_key_results_objective_id ON strategy.key_results(objective_id);
