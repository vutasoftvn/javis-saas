-- Migration 028: Startup OS Core Schema & Operational Flows (COSA v1.0)
-- Reference: docs/cosa.md
-- Defines: Onboard (7 dimensions, sessions, snapshots, cadence),
--          Goals (nested tree, time-boxed), Objectives, Key Results,
--          Triggers (demote_current, link_goal_to_snapshot),
--          Views (v_current_company_context, v_goal_tree),
--          Functions (fn_goals_needing_review, fn_suggest_dimension_review).

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =========================================================
-- 1. EXTEND strategy.projects
-- =========================================================
ALTER TABLE strategy.projects ADD COLUMN IF NOT EXISTS objective_id BIGINT;
ALTER TABLE strategy.projects ADD COLUMN IF NOT EXISTS origin TEXT CHECK (origin IN ('okr_driven', 'discovery', 'maintenance', 'reactive'));
ALTER TABLE strategy.projects ADD COLUMN IF NOT EXISTS link_status TEXT DEFAULT 'linked' CHECK (link_status IN ('linked', 'pending_review', 'intentionally_unlinked'));

CREATE INDEX IF NOT EXISTS idx_projects_objective ON strategy.projects(objective_id) WHERE objective_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_pending ON strategy.projects(workspace_id, link_status) WHERE link_status = 'pending_review';

-- =========================================================
-- 2. ONBOARD SESSIONS & AUDIT
-- =========================================================
CREATE TABLE IF NOT EXISTS strategy.onboard_sessions (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_type        TEXT NOT NULL CHECK (session_type IN ('initial', 'partial_update', 'event_driven')),
    status              TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    duration_minutes    INT,
    dimensions_touched  TEXT[] DEFAULT '{}',
    summary             TEXT,
    transcript          JSONB,
    metadata            JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON strategy.onboard_sessions(workspace_id, started_at DESC);

CREATE TABLE IF NOT EXISTS strategy.conversation_turns (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id) ON DELETE CASCADE,
    turn_number     INT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    dimension       TEXT CHECK (dimension IN (
                        'identity', 'stage_scale', 'founder',
                        'team_culture', 'market', 'challenges', 'goals_ambition'
                    )),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, turn_number)
);

CREATE INDEX IF NOT EXISTS idx_turns_session   ON strategy.conversation_turns(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_turns_dimension ON strategy.conversation_turns(session_id, dimension);
CREATE INDEX IF NOT EXISTS idx_turns_trgm      ON strategy.conversation_turns USING gin (content gin_trgm_ops);

-- =========================================================
-- 3. ONBOARD SNAPSHOTS
-- =========================================================
CREATE TABLE IF NOT EXISTS strategy.onboard_snapshots (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    full_context        JSONB NOT NULL,
    changed_dimensions  TEXT[] DEFAULT '{}',
    change_reason       TEXT,
    is_current          BOOLEAN NOT NULL DEFAULT false,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_snapshot_current ON strategy.onboard_snapshots(workspace_id) WHERE is_current;
CREATE INDEX IF NOT EXISTS idx_snapshots_workspace      ON strategy.onboard_snapshots(workspace_id, captured_at DESC);

-- =========================================================
-- 4. BẢY CHIỀU ONBOARD
-- =========================================================

-- CHIỀU 1: IDENTITY & VALUES
CREATE TABLE IF NOT EXISTS strategy.onboard_identity (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    what_they_do        TEXT,
    who_they_serve      TEXT,
    founding_why        TEXT,
    one_sentence_pitch  TEXT,
    not_captured        TEXT[] DEFAULT '{}',
    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS strategy.onboard_values (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    identity_id         BIGINT NOT NULL REFERENCES strategy.onboard_identity(id) ON DELETE CASCADE,
    value_text          TEXT NOT NULL,
    is_fire_worthy      BOOLEAN DEFAULT false,
    reality_status      TEXT CHECK (reality_status IN ('real', 'poster', 'unclear')),
    display_order       INT DEFAULT 0
);

-- CHIỀU 2: STAGE & SCALE
CREATE TABLE IF NOT EXISTS strategy.onboard_stage_scale (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    headcount_ft        INT,
    headcount_contractor INT,
    revenue_arr         NUMERIC(14,2),
    revenue_currency    TEXT DEFAULT 'USD',
    runway_months       NUMERIC(5,1),
    stage               TEXT CHECK (stage IN ('pre_pmf', 'scaling', 'optimizing')),
    what_broke_last_90d TEXT,
    not_captured        TEXT[] DEFAULT '{}',
    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CHIỀU 3: FOUNDERS
CREATE TABLE IF NOT EXISTS strategy.onboard_founders (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    founder_name        TEXT NOT NULL,
    role                TEXT,
    superpower          TEXT,
    blind_spots         TEXT,
    archetype           TEXT CHECK (archetype IN ('product','sales','technical','operator','hybrid')),
    what_keeps_up       TEXT,
    cofounder_critique  TEXT,
    not_captured        TEXT[] DEFAULT '{}',
    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_founders_current ON strategy.onboard_founders(workspace_id, founder_name) WHERE is_current;

-- CHIỀU 4: TEAM & CULTURE
CREATE TABLE IF NOT EXISTS strategy.onboard_team_culture (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    three_words         TEXT[],
    last_real_conflict  TEXT,
    conflict_resolution TEXT,
    strongest_leader    TEXT,
    weakest_leader      TEXT,
    has_real_conflict   BOOLEAN,
    not_captured        TEXT[] DEFAULT '{}',
    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CHIỀU 5: MARKET & COMPETITION
CREATE TABLE IF NOT EXISTS strategy.onboard_market (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    market_description  TEXT,
    unfair_advantage    TEXT,
    competitive_threat  TEXT,
    has_real_competition BOOLEAN,
    not_captured        TEXT[] DEFAULT '{}',
    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS strategy.onboard_competitors (
    id                  BIGINT PRIMARY KEY,
    market_id           BIGINT NOT NULL REFERENCES strategy.onboard_market(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    why_winning         TEXT,
    threat_level        TEXT CHECK (threat_level IN ('low','medium','high','critical')),
    display_order       INT DEFAULT 0
);

-- CHIỀU 6: CHALLENGES
CREATE TABLE IF NOT EXISTS strategy.onboard_challenges (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    priority_product    INT CHECK (priority_product BETWEEN 1 AND 5),
    priority_growth     INT CHECK (priority_growth BETWEEN 1 AND 5),
    priority_people     INT CHECK (priority_people BETWEEN 1 AND 5),
    priority_money      INT CHECK (priority_money BETWEEN 1 AND 5),
    priority_operations INT CHECK (priority_operations BETWEEN 1 AND 5),
    avoided_decision    TEXT,
    extra_day_answer    TEXT,
    not_captured        TEXT[] DEFAULT '{}',
    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CHIỀU 7: GOALS & AMBITION
CREATE TABLE IF NOT EXISTS strategy.onboard_goals_ambition (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES strategy.onboard_sessions(id),
    goal_12_months_text TEXT,
    goal_36_months_text TEXT,
    exit_orientation    TEXT CHECK (exit_orientation IN ('exit', 'build_forever', 'undecided')),
    personal_success_definition TEXT,
    not_captured        TEXT[] DEFAULT '{}',
    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- PARTIAL UNIQUE INDEXES cho is_current
CREATE UNIQUE INDEX IF NOT EXISTS uniq_identity_current    ON strategy.onboard_identity(workspace_id)       WHERE is_current;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_stage_current       ON strategy.onboard_stage_scale(workspace_id)    WHERE is_current;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_team_current        ON strategy.onboard_team_culture(workspace_id)   WHERE is_current;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_market_current      ON strategy.onboard_market(workspace_id)         WHERE is_current;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_challenges_current  ON strategy.onboard_challenges(workspace_id)     WHERE is_current;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_ambition_current    ON strategy.onboard_goals_ambition(workspace_id) WHERE is_current;

-- =========================================================
-- 5. REVIEW CADENCE (BSC-style)
-- =========================================================
CREATE TABLE IF NOT EXISTS strategy.onboard_review_cadence (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    dimension           TEXT NOT NULL CHECK (dimension IN (
                            'identity','stage_scale','founder','team_culture',
                            'market','challenges','goals_ambition'
                        )),
    cadence             TEXT NOT NULL CHECK (cadence IN ('slow','medium','fast','event')),
    interval_days       INT,
    last_reviewed_at    TIMESTAMPTZ,
    next_due_at         TIMESTAMPTZ,
    UNIQUE (workspace_id, dimension)
);

-- =========================================================
-- 6. GOALS (nested tree, time-boxed)
-- =========================================================
CREATE TABLE IF NOT EXISTS strategy.goals (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    parent_id           BIGINT REFERENCES strategy.goals(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    goal_type           TEXT NOT NULL CHECK (goal_type IN ('vision', 'strategic', 'tactical', 'sprint')),
    start_date          DATE,
    end_date            DATE,
    duration_weeks      NUMERIC(4,1),
    CONSTRAINT chk_goal_dates CHECK (
        (start_date IS NULL AND end_date IS NULL)
        OR (start_date IS NOT NULL AND end_date IS NOT NULL)
    ),
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft', 'active', 'completed', 'abandoned')),
    onboard_snapshot_id BIGINT REFERENCES strategy.onboard_snapshots(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_goals_workspace_active ON strategy.goals(workspace_id, status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_goals_parent           ON strategy.goals(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_goals_dates            ON strategy.goals(workspace_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_goals_type             ON strategy.goals(workspace_id, goal_type, status);

-- =========================================================
-- 7. OBJECTIVES
-- =========================================================
CREATE TABLE IF NOT EXISTS strategy.objectives (
    id                  BIGINT PRIMARY KEY,
    goal_id             BIGINT NOT NULL REFERENCES strategy.goals(id) ON DELETE CASCADE,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    owner_user_id       BIGINT,
    weight              NUMERIC(4,2) DEFAULT 1.0,
    display_order       INT DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    progress_pct        NUMERIC(5,2) DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_objectives_goal      ON strategy.objectives(goal_id, display_order);
CREATE INDEX IF NOT EXISTS idx_objectives_workspace ON strategy.objectives(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_objectives_owner     ON strategy.objectives(owner_user_id) WHERE owner_user_id IS NOT NULL;

-- Link strategy.projects(objective_id) to strategy.objectives(id)
DO $$ BEGIN
    ALTER TABLE strategy.projects ADD CONSTRAINT fk_projects_objective FOREIGN KEY (objective_id) REFERENCES strategy.objectives(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =========================================================
-- 8. COSA KEY RESULTS
-- =========================================================
CREATE TABLE IF NOT EXISTS strategy.cosa_key_results (
    id              BIGINT PRIMARY KEY,
    objective_id    BIGINT NOT NULL REFERENCES strategy.objectives(id) ON DELETE CASCADE,
    metric_name     TEXT NOT NULL,
    baseline        NUMERIC,
    target          NUMERIC NOT NULL,
    current_value   NUMERIC DEFAULT 0,
    unit            TEXT,
    status          TEXT DEFAULT 'active' CHECK (status IN ('active', 'achieved', 'missed', 'archived')),
    display_order   INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cosa_kr_objective ON strategy.cosa_key_results(objective_id, display_order);

-- =========================================================
-- 9. TRIGGERS
-- =========================================================

-- DEMOTE is_current (generic)
CREATE OR REPLACE FUNCTION strategy.fn_demote_current()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current = true THEN
        EXECUTE format(
            'UPDATE %I.%I SET is_current = false 
             WHERE workspace_id = $1 AND is_current = true AND id != $2',
            TG_TABLE_SCHEMA, TG_TABLE_NAME
        ) USING NEW.workspace_id, NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_identity_current   ON strategy.onboard_identity;
CREATE TRIGGER trg_identity_current   BEFORE INSERT ON strategy.onboard_identity       FOR EACH ROW EXECUTE FUNCTION strategy.fn_demote_current();

DROP TRIGGER IF EXISTS trg_stage_current      ON strategy.onboard_stage_scale;
CREATE TRIGGER trg_stage_current      BEFORE INSERT ON strategy.onboard_stage_scale    FOR EACH ROW EXECUTE FUNCTION strategy.fn_demote_current();

DROP TRIGGER IF EXISTS trg_team_current       ON strategy.onboard_team_culture;
CREATE TRIGGER trg_team_current       BEFORE INSERT ON strategy.onboard_team_culture   FOR EACH ROW EXECUTE FUNCTION strategy.fn_demote_current();

DROP TRIGGER IF EXISTS trg_market_current     ON strategy.onboard_market;
CREATE TRIGGER trg_market_current     BEFORE INSERT ON strategy.onboard_market         FOR EACH ROW EXECUTE FUNCTION strategy.fn_demote_current();

DROP TRIGGER IF EXISTS trg_challenges_current ON strategy.onboard_challenges;
CREATE TRIGGER trg_challenges_current BEFORE INSERT ON strategy.onboard_challenges     FOR EACH ROW EXECUTE FUNCTION strategy.fn_demote_current();

DROP TRIGGER IF EXISTS trg_ambition_current   ON strategy.onboard_goals_ambition;
CREATE TRIGGER trg_ambition_current   BEFORE INSERT ON strategy.onboard_goals_ambition FOR EACH ROW EXECUTE FUNCTION strategy.fn_demote_current();

DROP TRIGGER IF EXISTS trg_snapshot_current   ON strategy.onboard_snapshots;
CREATE TRIGGER trg_snapshot_current   BEFORE INSERT ON strategy.onboard_snapshots      FOR EACH ROW EXECUTE FUNCTION strategy.fn_demote_current();

-- AUTO-LINK GOAL -> CURRENT SNAPSHOT
CREATE OR REPLACE FUNCTION strategy.fn_link_goal_to_snapshot()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.onboard_snapshot_id IS NULL THEN
        SELECT id INTO NEW.onboard_snapshot_id
        FROM strategy.onboard_snapshots
        WHERE workspace_id = NEW.workspace_id AND is_current = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_goal_snapshot ON strategy.goals;
CREATE TRIGGER trg_goal_snapshot
    BEFORE INSERT ON strategy.goals
    FOR EACH ROW EXECUTE FUNCTION strategy.fn_link_goal_to_snapshot();

-- =========================================================
-- 10. VIEWS
-- =========================================================

CREATE OR REPLACE VIEW strategy.v_current_company_context AS
SELECT
    w.id AS workspace_id,
    w.name AS workspace_name,

    jsonb_build_object(
        'identity', (
            SELECT jsonb_build_object(
                'what_they_do', oi.what_they_do,
                'who_they_serve', oi.who_they_serve,
                'founding_why', oi.founding_why,
                'one_sentence_pitch', oi.one_sentence_pitch,
                'not_captured', oi.not_captured,
                'values', (
                    SELECT COALESCE(jsonb_agg(jsonb_build_object(
                        'value', ov.value_text,
                        'is_fire_worthy', ov.is_fire_worthy,
                        'reality', ov.reality_status
                    ) ORDER BY ov.display_order), '[]'::jsonb)
                    FROM strategy.onboard_values ov WHERE ov.identity_id = oi.id
                )
            )
            FROM strategy.onboard_identity oi
            WHERE oi.workspace_id = w.id AND oi.is_current LIMIT 1
        ),
        'stage_scale', (
            SELECT to_jsonb(oss.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM strategy.onboard_stage_scale oss
            WHERE oss.workspace_id = w.id AND oss.is_current LIMIT 1
        ),
        'founders', (
            SELECT COALESCE(jsonb_agg(to_jsonb(ofr.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current'), '[]'::jsonb)
            FROM strategy.onboard_founders ofr
            WHERE ofr.workspace_id = w.id AND ofr.is_current
        ),
        'team_culture', (
            SELECT to_jsonb(otc.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM strategy.onboard_team_culture otc
            WHERE otc.workspace_id = w.id AND otc.is_current LIMIT 1
        ),
        'market', (
            SELECT jsonb_build_object(
                'description', om.market_description,
                'unfair_advantage', om.unfair_advantage,
                'threat', om.competitive_threat,
                'competitors', (
                    SELECT COALESCE(jsonb_agg(jsonb_build_object(
                        'name', oc.name, 'why_winning', oc.why_winning, 'threat', oc.threat_level
                    )), '[]'::jsonb)
                    FROM strategy.onboard_competitors oc WHERE oc.market_id = om.id
                )
            )
            FROM strategy.onboard_market om
            WHERE om.workspace_id = w.id AND om.is_current LIMIT 1
        ),
        'challenges', (
            SELECT to_jsonb(och.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM strategy.onboard_challenges och
            WHERE och.workspace_id = w.id AND och.is_current LIMIT 1
        ),
        'goals_ambition', (
            SELECT to_jsonb(oga.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM strategy.onboard_goals_ambition oga
            WHERE oga.workspace_id = w.id AND oga.is_current LIMIT 1
        )
    ) AS full_context,

    (SELECT captured_at FROM strategy.onboard_snapshots WHERE workspace_id = w.id AND is_current) AS snapshot_at

FROM core.workspaces w;


CREATE OR REPLACE VIEW strategy.v_goal_tree AS
WITH RECURSIVE tree AS (
    SELECT 
        g.id, g.parent_id, g.workspace_id, g.title, g.goal_type, g.status,
        g.start_date, g.end_date, g.duration_weeks, g.onboard_snapshot_id,
        0 AS depth,
        ARRAY[g.id] AS path,
        g.title::TEXT AS hierarchy
    FROM strategy.goals g
    WHERE g.parent_id IS NULL
    
    UNION ALL
    
    SELECT 
        g.id, g.parent_id, g.workspace_id, g.title, g.goal_type, g.status,
        g.start_date, g.end_date, g.duration_weeks, g.onboard_snapshot_id,
        t.depth + 1,
        t.path || g.id,
        t.hierarchy || ' › ' || g.title
    FROM strategy.goals g
    JOIN tree t ON g.parent_id = t.id
)
SELECT 
    t.*,
    (SELECT COUNT(*) FROM strategy.objectives o WHERE o.goal_id = t.id) AS objective_count,
    (SELECT COUNT(*) FROM strategy.cosa_key_results kr
     JOIN strategy.objectives o ON o.id = kr.objective_id
     WHERE o.goal_id = t.id AND kr.current_value >= kr.target) AS kr_achieved,
    (SELECT COUNT(*) FROM strategy.cosa_key_results kr
     JOIN strategy.objectives o ON o.id = kr.objective_id
     WHERE o.goal_id = t.id) AS kr_total,
    (SELECT captured_at FROM strategy.onboard_snapshots os WHERE os.id = t.onboard_snapshot_id) AS snapshot_at
FROM tree t;

-- =========================================================
-- 11. FUNCTIONS
-- =========================================================

CREATE OR REPLACE FUNCTION strategy.fn_goals_needing_review(p_workspace_id BIGINT)
RETURNS TABLE (
    goal_id             BIGINT,
    goal_title          TEXT,
    goal_type           TEXT,
    snapshot_age_days   INT,
    urgency             TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.id,
        g.title,
        g.goal_type,
        EXTRACT(DAY FROM now() - os.captured_at)::INT,
        CASE
            WHEN g.goal_type IN ('sprint','tactical') 
                 AND os.captured_at < now() - INTERVAL '14 days' THEN 'high'
            WHEN g.goal_type = 'strategic' 
                 AND os.captured_at < now() - INTERVAL '60 days' THEN 'medium'
            ELSE 'low'
        END AS urgency
    FROM strategy.goals g
    JOIN strategy.onboard_snapshots os ON os.id = g.onboard_snapshot_id
    WHERE g.workspace_id = p_workspace_id
      AND g.status = 'active'
      AND os.id != (SELECT id FROM strategy.onboard_snapshots 
                    WHERE workspace_id = p_workspace_id AND is_current)
    ORDER BY urgency;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION strategy.fn_suggest_dimension_review(p_workspace_id BIGINT)
RETURNS TABLE (
    dimension       TEXT,
    cadence         TEXT,
    days_since      INT,
    urgency         TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rc.dimension,
        rc.cadence,
        COALESCE(EXTRACT(DAY FROM now() - rc.last_reviewed_at)::INT, 999),
        CASE
            WHEN rc.next_due_at < now() - INTERVAL '14 days' THEN 'critical'
            WHEN rc.next_due_at < now() THEN 'recommended'
            ELSE 'optional'
        END AS urgency
    FROM strategy.onboard_review_cadence rc
    WHERE rc.workspace_id = p_workspace_id
      AND rc.next_due_at <= now() + INTERVAL '7 days'
    ORDER BY 
        CASE rc.cadence WHEN 'fast' THEN 1 WHEN 'medium' THEN 2 WHEN 'slow' THEN 3 ELSE 4 END;
END;
$$ LANGUAGE plpgsql;
