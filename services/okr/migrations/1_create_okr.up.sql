CREATE TABLE objectives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  title TEXT NOT NULL,
  period TEXT NOT NULL,
  owner TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE key_results (
  id BIGSERIAL PRIMARY KEY,
  objective_id BIGINT NOT NULL REFERENCES objectives(id),
  title TEXT NOT NULL,
  target_value DOUBLE PRECISION NOT NULL,
  current_value DOUBLE PRECISION NOT NULL DEFAULT 0,
  unit TEXT NOT NULL DEFAULT 'count',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
