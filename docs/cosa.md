```markdown
# Startup OS — Data Architecture & Operations

> Tài liệu kiến trúc dữ liệu và luồng vận hành cho Startup OS.
> Bao gồm: triết lý thiết kế, cấu trúc entity, schema reference (Snowflake ID),
> state machines, workflows, và best practices.

**Version:** 1.0
**Database:** PostgreSQL 14+
**ID Strategy:** Snowflake ID (BIGINT) — generated at application layer
**Last updated:** 2026-04-15

---

## Mục lục

**Phần I — Tổng quan**
1. Triết lý thiết kế
2. Sơ đồ quan hệ & phân tầng
3. Cây Goal — ví dụ thực tế

**Phần II — Schema Reference**
4. Workspace & Members
5. Goals (nested tree)
6. Objectives & Key Results
7. Projects
8. Onboard (sessions, snapshots, dimensions, cadence)
9. Views, Functions & Triggers

**Phần III — Flows & Vận hành**
10. State machines
11. Sáu luồng vận hành chính
12. Review cadence — BSC-style
13. Data flow & events

**Phần IV — Best Practices**
14. Nguyên tắc vàng
15. Anti-patterns
16. Migration path
17. Checklist triển khai

---

# PHẦN I — TỔNG QUAN

## 1. Triết lý thiết kế

### 1.1. Các quyết định kiến trúc cốt lõi

| Quyết định | Lý do |
|---|---|
| **Workspace = Company = Tenant** | Mỗi user có 1-n workspace. Không tách `company` và `workspace` — chúng là một khái niệm. |
| **Goal là container lồng nhau** | Vision (5 năm) → Strategic (12 tháng) → Tactical (4-12 tuần) → Sprint (1-4 tuần). Cùng một bảng, khác `goal_type`. |
| **Goal chứa nhiều Objective** | 1 goal có thể có nhiều outcome song song. Mỗi objective có owner riêng. |
| **Cycle là một Goal** | Không tách `cycle` và `goal` — cycle chỉ là goal có `duration_weeks` cụ thể. |
| **Onboard multi-cadence** | 7 chiều dữ liệu có nhịp review khác nhau (BSC-style). `challenges` review 2 tuần, `identity` review 6 tháng. |
| **Snapshot pattern** | Mỗi lần onboard update tạo snapshot. Goal reference snapshot để biết ngữ cảnh lúc lập. |
| **`is_current` pattern** | Không UPDATE bản ghi chiều — chỉ INSERT bản ghi mới và demote cái cũ. Giữ toàn bộ lịch sử. |
| **Snowflake ID (BIGINT)** | Sortable theo thời gian, không cần DB-generated, hỗ trợ distributed insert. |

### 1.2. Những gì KHÔNG làm

- ❌ Không có bảng `programs` — đã gộp vào `goals` với `parent_id`
- ❌ Không có bảng `goals` riêng cho onboard — đã dùng `goals` chính
- ❌ Không có `quarter` (Q1-Q4) — cycle linh hoạt 1-52 tuần
- ❌ Không auto-merge onboard data vào execution data — chỉ có linking + validation
- ❌ Không auto-link project với goal — cần human review
- ❌ Không UPDATE bản ghi — chỉ INSERT bản ghi mới (append-only cho lịch sử)

### 1.3. Các tầng dữ liệu

| Tầng | Entity | Vai trò | Vòng đời |
|---|---|---|---|
| **Tenant** | `workspaces` | Container gốc | Vĩnh viễn |
| **Strategy** | `onboard_*` | Bối cảnh công ty (7 chiều) | Update theo cadence |
| **Goal** | `goals` | Mục tiêu lồng nhau | 1 tuần - 5 năm |
| **Execution** | `objectives` | Outcome trong goal | Song song với goal |
| **Measurement** | `key_results` | Chỉ số đo objective | Song song với objective |
| **Action** | `projects` | Công việc thực thi | Ngày - vài tuần |

---

## 2. Sơ đồ quan hệ & phân tầng

### 2.1. Sơ đồ tổng thể

```
┌──────────────────────────────────────────────────────────┐
│  WORKSPACES (= Company = Tenant)                         │
│                                                          │
│  ┌──────────────────────┐    ┌───────────────────────┐  │
│  │ ONBOARD              │    │ GOALS (nested tree)   │  │
│  │  ├─ sessions         │    │  ├─ vision            │  │
│  │  ├─ 7 dimensions     │    │  ├─ strategic         │  │
│  │  │   (is_current)    │    │  ├─ tactical          │  │
│  │  ├─ snapshots        │    │  └─ sprint            │  │
│  │  └─ review_cadence   │    └───────────┬───────────┘  │
│  └──────────┬───────────┘                │              │
│             │ informs                    │ contains     │
│             ▼                            ▼              │
│                                    ┌──────────────────┐ │
│                                    │ OBJECTIVES       │ │
│                                    │  (owner per obj) │ │
│                                    └────────┬─────────┘ │
│                                             │ measures  │
│                                             ▼           │
│                                    ┌──────────────────┐ │
│                                    │ KEY RESULTS      │ │
│                                    └────────┬─────────┘ │
│                                             │ executes  │
│                                             ▼           │
│                                    ┌──────────────────┐ │
│                                    │ PROJECTS         │ │
│                                    └──────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 2.2. Quan hệ giữa các entity

| Từ | Đến | Kiểu | Ràng buộc |
|---|---|---|---|
| `workspaces` | `workspace_members` | 1-n | Cascade delete |
| `workspaces` | `goals` | 1-n | Cascade delete |
| `goals` | `goals` | self n-n | Qua `parent_id`, cascade |
| `goals` | `objectives` | 1-n | Cascade delete |
| `goals` | `onboard_snapshots` | n-1 | `onboard_snapshot_id` (nullable) |
| `objectives` | `key_results` | 1-n | Cascade delete |
| `objectives` | `projects` | 1-n | Set null khi xóa objective |
| `onboard_sessions` | `onboard_snapshots` | 1-n | Mỗi update tạo 1 snapshot |
| `onboard_sessions` | `onboard_*` (7 chiều) | 1-n | Mỗi session touch 1-n chiều |

---

## 3. Cây Goal — Ví dụ thực tế

```
Goal #1 (vision, 2026-2030)
│  "Trở thành #1 tool cho X"
│
├── Goal #2 (strategic, 12 tháng)
│   │  "Đạt $1M ARR"
│   │
│   ├── Goal #3 (tactical, 4 tuần)
│   │   │  "Launch MVP"
│   │   │
│   │   ├── Objective "Build core features"    (owner: A)
│   │   │     ├── KR: 3 features done
│   │   │     └── KR: coverage > 80%
│   │   │
│   │   ├── Objective "Acquire 100 beta users" (owner: B)
│   │   │     └── KR: 100 signups
│   │   │
│   │   └── Objective "Production infra"       (owner: C)
│   │         └── KR: uptime 99.9%
│   │
│   └── Goal #4 (sprint, 2 tuần)
│         "Validate pricing"
│         └── Objective "20 user interviews"
│
└── Goal #5 (strategic, 12 tháng)
      "Build brand awareness"
```

**Đặc điểm:**
- Depth không giới hạn (thường 2-4 tầng)
- Siblings có thể chạy song song (Goal #3 và #4 cùng parent #2)
- Mỗi goal có snapshot riêng — biết ngữ cảnh lúc lập

---

# PHẦN II — SCHEMA REFERENCE

> **Lưu ý:** DDL dưới đây dùng `BIGINT` cho ID (Snowflake), không dùng `UUID`.
> Snowflake ID được generate ở application layer trước khi INSERT.
> Phần này để tham khảo — đối chiếu với schema hiện có của bạn.

## 4. Workspace & Members

```sql
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =========================================================
-- WORKSPACES (= Company = Tenant)
-- =========================================================
CREATE TABLE workspaces (
    id              BIGINT PRIMARY KEY,              -- Snowflake ID
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    owner_user_id   BIGINT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workspace_members (
    workspace_id    BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         BIGINT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);
```

## 5. Goals (nested tree)

```sql
-- =========================================================
-- GOALS (nested, time-boxed)
-- =========================================================
CREATE TABLE goals (
    id                  BIGINT PRIMARY KEY,          -- Snowflake
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    parent_id           BIGINT REFERENCES goals(id) ON DELETE CASCADE,

    title               TEXT NOT NULL,
    description         TEXT,
    goal_type           TEXT NOT NULL CHECK (goal_type IN (
                            'vision',       -- 3-5 năm
                            'strategic',    -- 12 tháng
                            'tactical',     -- 4-12 tuần
                            'sprint'        -- 1-4 tuần
                        )),

    -- Time-box (vision có thể NULL)
    start_date          DATE,
    end_date            DATE,
    duration_weeks      NUMERIC(4,1),
    CONSTRAINT chk_goal_dates CHECK (
        (start_date IS NULL AND end_date IS NULL)
        OR (start_date IS NOT NULL AND end_date IS NOT NULL)
    ),

    status              TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('draft', 'active', 'completed', 'abandoned')),

    onboard_snapshot_id BIGINT REFERENCES onboard_snapshots(id),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX idx_goals_workspace_active ON goals(workspace_id, status) WHERE status = 'active';
CREATE INDEX idx_goals_parent           ON goals(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_goals_dates            ON goals(workspace_id, start_date, end_date);
CREATE INDEX idx_goals_type             ON goals(workspace_id, goal_type, status);
```

## 6. Objectives & Key Results

```sql
-- =========================================================
-- OBJECTIVES (nhiều objective trong 1 goal)
-- =========================================================
CREATE TABLE objectives (
    id                  BIGINT PRIMARY KEY,
    goal_id             BIGINT NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    title               TEXT NOT NULL,
    description         TEXT,
    owner_user_id       BIGINT,
    weight              NUMERIC(4,2) DEFAULT 1.0,
    display_order       INT DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'completed', 'abandoned')),
    progress_pct        NUMERIC(5,2) DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_objectives_goal      ON objectives(goal_id, display_order);
CREATE INDEX idx_objectives_workspace ON objectives(workspace_id, status);
CREATE INDEX idx_objectives_owner     ON objectives(owner_user_id) WHERE owner_user_id IS NOT NULL;

-- =========================================================
-- KEY RESULTS
-- =========================================================
CREATE TABLE key_results (
    id              BIGINT PRIMARY KEY,
    objective_id    BIGINT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    metric_name     TEXT NOT NULL,
    baseline        NUMERIC,
    target          NUMERIC NOT NULL,
    current_value   NUMERIC DEFAULT 0,
    unit            TEXT,
    status          TEXT DEFAULT 'active'
                        CHECK (status IN ('active', 'achieved', 'missed', 'archived')),
    display_order   INT DEFAULT 0
);

CREATE INDEX idx_kr_objective ON key_results(objective_id, display_order);
```

## 7. Projects

```sql
-- =========================================================
-- PROJECTS
-- =========================================================
CREATE TABLE projects (
    id              BIGINT PRIMARY KEY,
    workspace_id    BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    objective_id    BIGINT REFERENCES objectives(id) ON DELETE SET NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    owner_user_id   BIGINT,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'completed', 'archived', 'abandoned')),
    origin          TEXT CHECK (origin IN (
                        'okr_driven',      -- sinh từ objective (top-down)
                        'discovery',       -- khám phá, chưa map objective
                        'maintenance',     -- định kỳ
                        'reactive'         -- bug/incident
                    )),
    link_status     TEXT DEFAULT 'linked'
                        CHECK (link_status IN ('linked', 'pending_review', 'intentionally_unlinked')),
    started_at      DATE,
    due_at          DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_workspace  ON projects(workspace_id, status);
CREATE INDEX idx_projects_objective  ON projects(objective_id) WHERE objective_id IS NOT NULL;
CREATE INDEX idx_projects_pending    ON projects(workspace_id, link_status) WHERE link_status = 'pending_review';
```

## 8. Onboard — Sessions, Snapshots, Dimensions, Cadence

### 8.1. Sessions & Snapshots

```sql
-- =========================================================
-- ONBOARD SESSIONS
-- =========================================================
CREATE TABLE onboard_sessions (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_type        TEXT NOT NULL CHECK (session_type IN (
                            'initial',          -- /cs:setup lần đầu
                            'partial_update',   -- update 1 vài chiều
                            'event_driven'      -- pivot, funding,...
                        )),
    status              TEXT NOT NULL DEFAULT 'in_progress'
                            CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    duration_minutes    INT,
    dimensions_touched  TEXT[] DEFAULT '{}',
    summary             TEXT,
    transcript          JSONB,
    metadata            JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_workspace ON onboard_sessions(workspace_id, started_at DESC);

-- =========================================================
-- CONVERSATION TURNS (audit)
-- =========================================================
CREATE TABLE conversation_turns (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES onboard_sessions(id) ON DELETE CASCADE,
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

CREATE INDEX idx_turns_session   ON conversation_turns(session_id, turn_number);
CREATE INDEX idx_turns_dimension ON conversation_turns(session_id, dimension);
CREATE INDEX idx_turns_trgm      ON conversation_turns USING gin (content gin_trgm_ops);

-- =========================================================
-- ONBOARD SNAPSHOTS (version toàn bộ ngữ cảnh)
-- =========================================================
CREATE TABLE onboard_snapshots (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),
    full_context        JSONB NOT NULL,
    changed_dimensions  TEXT[] DEFAULT '{}',
    change_reason       TEXT,
    is_current          BOOLEAN NOT NULL DEFAULT false,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uniq_snapshot_current ON onboard_snapshots(workspace_id) WHERE is_current;
CREATE INDEX idx_snapshots_workspace      ON onboard_snapshots(workspace_id, captured_at DESC);
```

### 8.2. Bảy chiều Onboard

```sql
-- =========================================================
-- CHIỀU 1: IDENTITY
-- =========================================================
CREATE TABLE onboard_identity (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),

    what_they_do        TEXT,
    who_they_serve      TEXT,
    founding_why        TEXT,
    one_sentence_pitch  TEXT,
    not_captured        TEXT[] DEFAULT '{}',

    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE onboard_values (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    identity_id         BIGINT NOT NULL REFERENCES onboard_identity(id) ON DELETE CASCADE,
    value_text          TEXT NOT NULL,
    is_fire_worthy      BOOLEAN DEFAULT false,
    reality_status      TEXT CHECK (reality_status IN ('real', 'poster', 'unclear')),
    display_order       INT DEFAULT 0
);

-- =========================================================
-- CHIỀU 2: STAGE & SCALE
-- =========================================================
CREATE TABLE onboard_stage_scale (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),

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

-- =========================================================
-- CHIỀU 3: FOUNDERS
-- =========================================================
CREATE TABLE onboard_founders (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),

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

CREATE INDEX idx_founders_current ON onboard_founders(workspace_id, founder_name) WHERE is_current;

-- =========================================================
-- CHIỀU 4: TEAM & CULTURE
-- =========================================================
CREATE TABLE onboard_team_culture (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),

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

-- =========================================================
-- CHIỀU 5: MARKET & COMPETITION
-- =========================================================
CREATE TABLE onboard_market (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),

    market_description  TEXT,
    unfair_advantage    TEXT,
    competitive_threat  TEXT,
    has_real_competition BOOLEAN,
    not_captured        TEXT[] DEFAULT '{}',

    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE onboard_competitors (
    id                  BIGINT PRIMARY KEY,
    market_id           BIGINT NOT NULL REFERENCES onboard_market(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    why_winning         TEXT,
    threat_level        TEXT CHECK (threat_level IN ('low','medium','high','critical')),
    display_order       INT DEFAULT 0
);

-- =========================================================
-- CHIỀU 6: CHALLENGES
-- =========================================================
CREATE TABLE onboard_challenges (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),

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

-- =========================================================
-- CHIỀU 7: GOALS & AMBITION
-- Lưu ý: đây là text mô tả ambition. Goal thực nằm ở bảng `goals`.
-- =========================================================
CREATE TABLE onboard_goals_ambition (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    session_id          BIGINT NOT NULL REFERENCES onboard_sessions(id),

    goal_12_months_text TEXT,
    goal_36_months_text TEXT,
    exit_orientation    TEXT CHECK (exit_orientation IN ('exit', 'build_forever', 'undecided')),
    personal_success_definition TEXT,
    not_captured        TEXT[] DEFAULT '{}',

    is_current          BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- PARTIAL UNIQUE INDEXES cho is_current
-- =========================================================
CREATE UNIQUE INDEX uniq_identity_current    ON onboard_identity(workspace_id)       WHERE is_current;
CREATE UNIQUE INDEX uniq_stage_current       ON onboard_stage_scale(workspace_id)    WHERE is_current;
CREATE UNIQUE INDEX uniq_team_current        ON onboard_team_culture(workspace_id)   WHERE is_current;
CREATE UNIQUE INDEX uniq_market_current      ON onboard_market(workspace_id)         WHERE is_current;
CREATE UNIQUE INDEX uniq_challenges_current  ON onboard_challenges(workspace_id)     WHERE is_current;
CREATE UNIQUE INDEX uniq_ambition_current    ON onboard_goals_ambition(workspace_id) WHERE is_current;
```

### 8.3. Review Cadence (BSC-style)

```sql
CREATE TABLE onboard_review_cadence (
    id                  BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
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

-- Seed khi tạo workspace mới (application layer):
-- identity       slow    180 ngày
-- stage_scale    fast     14 ngày
-- founder        slow    180 ngày
-- team_culture   medium   60 ngày
-- market         medium   60 ngày
-- challenges     fast     14 ngày
-- goals_ambition medium   90 ngày
```

## 9. Views, Functions & Triggers

### 9.1. View: Current Company Context

```sql
CREATE OR REPLACE VIEW v_current_company_context AS
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
                    SELECT jsonb_agg(jsonb_build_object(
                        'value', ov.value_text,
                        'is_fire_worthy', ov.is_fire_worthy,
                        'reality', ov.reality_status
                    ) ORDER BY ov.display_order)
                    FROM onboard_values ov WHERE ov.identity_id = oi.id
                )
            )
            FROM onboard_identity oi
            WHERE oi.workspace_id = w.id AND oi.is_current LIMIT 1
        ),
        'stage_scale', (
            SELECT to_jsonb(oss.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM onboard_stage_scale oss
            WHERE oss.workspace_id = w.id AND oss.is_current LIMIT 1
        ),
        'founders', (
            SELECT jsonb_agg(to_jsonb(ofr.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current')
            FROM onboard_founders ofr
            WHERE ofr.workspace_id = w.id AND ofr.is_current
        ),
        'team_culture', (
            SELECT to_jsonb(otc.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM onboard_team_culture otc
            WHERE otc.workspace_id = w.id AND otc.is_current LIMIT 1
        ),
        'market', (
            SELECT jsonb_build_object(
                'description', om.market_description,
                'unfair_advantage', om.unfair_advantage,
                'threat', om.competitive_threat,
                'competitors', (
                    SELECT jsonb_agg(jsonb_build_object(
                        'name', oc.name, 'why_winning', oc.why_winning, 'threat', oc.threat_level
                    ))
                    FROM onboard_competitors oc WHERE oc.market_id = om.id
                )
            )
            FROM onboard_market om
            WHERE om.workspace_id = w.id AND om.is_current LIMIT 1
        ),
        'challenges', (
            SELECT to_jsonb(och.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM onboard_challenges och
            WHERE och.workspace_id = w.id AND och.is_current LIMIT 1
        ),
        'goals_ambition', (
            SELECT to_jsonb(oga.*) - 'id' - 'workspace_id' - 'session_id' - 'is_current' - 'created_at'
            FROM onboard_goals_ambition oga
            WHERE oga.workspace_id = w.id AND oga.is_current LIMIT 1
        )
    ) AS full_context,

    (SELECT captured_at FROM onboard_snapshots WHERE workspace_id = w.id AND is_current) AS snapshot_at

FROM workspaces w;
```

### 9.2. View: Goal Tree

```sql
CREATE OR REPLACE VIEW v_goal_tree AS
WITH RECURSIVE tree AS (
    SELECT 
        g.id, g.parent_id, g.workspace_id, g.title, g.goal_type, g.status,
        g.start_date, g.end_date, g.onboard_snapshot_id,
        0 AS depth,
        ARRAY[g.id] AS path,
        g.title::TEXT AS hierarchy
    FROM goals g
    WHERE g.parent_id IS NULL
    
    UNION ALL
    
    SELECT 
        g.id, g.parent_id, g.workspace_id, g.title, g.goal_type, g.status,
        g.start_date, g.end_date, g.onboard_snapshot_id,
        t.depth + 1,
        t.path || g.id,
        t.hierarchy || ' › ' || g.title
    FROM goals g
    JOIN tree t ON g.parent_id = t.id
)
SELECT 
    t.*,
    (SELECT COUNT(*) FROM objectives o WHERE o.goal_id = t.id) AS objective_count,
    (SELECT COUNT(*) FROM key_results kr
     JOIN objectives o ON o.id = kr.objective_id
     WHERE o.goal_id = t.id AND kr.current_value >= kr.target) AS kr_achieved,
    (SELECT COUNT(*) FROM key_results kr
     JOIN objectives o ON o.id = kr.objective_id
     WHERE o.goal_id = t.id) AS kr_total,
    (SELECT captured_at FROM onboard_snapshots os WHERE os.id = t.onboard_snapshot_id) AS snapshot_at
FROM tree t;
```

### 9.3. Function: Goals cần review

```sql
CREATE OR REPLACE FUNCTION fn_goals_needing_review(p_workspace_id BIGINT)
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
        END
    FROM goals g
    JOIN onboard_snapshots os ON os.id = g.onboard_snapshot_id
    WHERE g.workspace_id = p_workspace_id
      AND g.status = 'active'
      AND os.id != (SELECT id FROM onboard_snapshots 
                    WHERE workspace_id = p_workspace_id AND is_current)
    ORDER BY urgency;
END;
$$ LANGUAGE plpgsql;
```

### 9.4. Function: Dimensions cần review

```sql
CREATE OR REPLACE FUNCTION fn_suggest_dimension_review(p_workspace_id BIGINT)
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
        END
    FROM onboard_review_cadence rc
    WHERE rc.workspace_id = p_workspace_id
      AND rc.next_due_at <= now() + INTERVAL '7 days'
    ORDER BY 
        CASE rc.cadence WHEN 'fast' THEN 1 WHEN 'medium' THEN 2 WHEN 'slow' THEN 3 ELSE 4 END;
END;
$$ LANGUAGE plpgsql;
```

### 9.5. Triggers

```sql
-- =========================================================
-- DEMOTE is_current (generic)
-- =========================================================
CREATE OR REPLACE FUNCTION fn_demote_current()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current = true THEN
        EXECUTE format(
            'UPDATE %I SET is_current = false 
             WHERE workspace_id = $1 AND is_current = true AND id != $2',
            TG_TABLE_NAME
        ) USING NEW.workspace_id, NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_identity_current   BEFORE INSERT ON onboard_identity       FOR EACH ROW EXECUTE FUNCTION fn_demote_current();
CREATE TRIGGER trg_stage_current      BEFORE INSERT ON onboard_stage_scale    FOR EACH ROW EXECUTE FUNCTION fn_demote_current();
CREATE TRIGGER trg_team_current       BEFORE INSERT ON onboard_team_culture   FOR EACH ROW EXECUTE FUNCTION fn_demote_current();
CREATE TRIGGER trg_market_current     BEFORE INSERT ON onboard_market         FOR EACH ROW EXECUTE FUNCTION fn_demote_current();
CREATE TRIGGER trg_challenges_current BEFORE INSERT ON onboard_challenges     FOR EACH ROW EXECUTE FUNCTION fn_demote_current();
CREATE TRIGGER trg_ambition_current   BEFORE INSERT ON onboard_goals_ambition FOR EACH ROW EXECUTE FUNCTION fn_demote_current();
CREATE TRIGGER trg_snapshot_current   BEFORE INSERT ON onboard_snapshots      FOR EACH ROW EXECUTE FUNCTION fn_demote_current();

-- =========================================================
-- AUTO-LINK GOAL → CURRENT SNAPSHOT
-- =========================================================
CREATE OR REPLACE FUNCTION fn_link_goal_to_snapshot()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.onboard_snapshot_id IS NULL THEN
        SELECT id INTO NEW.onboard_snapshot_id
        FROM onboard_snapshots
        WHERE workspace_id = NEW.workspace_id AND is_current = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_goal_snapshot
    BEFORE INSERT ON goals
    FOR EACH ROW EXECUTE FUNCTION fn_link_goal_to_snapshot();

-- =========================================================
-- TOUCH updated_at
-- =========================================================
CREATE OR REPLACE FUNCTION fn_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_workspaces_touch
    BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();
```

---

# PHẦN III — FLOWS & VẬN HÀNH

## 10. State machines

### 10.1. Goal

```
[draft] ──▶ [active] ──▶ [completed]
              │
              └──▶ [abandoned]
```

| Transition | Trigger | Side effects |
|---|---|---|
| `draft → active` | User activate | Gán snapshot hiện tại (nếu chưa có) |
| `active → completed` | User đánh dấu xong | Cascade objectives; trigger review ambition |
| `active → abandoned` | User hủy | Objectives cascade sang `abandoned` |
| `completed → active` | User reopen | Chỉ cho phép nếu chưa qua cycle kế |

**Business rules:**
- Không thể `completed` nếu có objective con đang `active`
- Không thể tạo goal con nếu parent đã `completed`
- Goal type `vision` không có `end_date` bắt buộc

### 10.2. Objective

```
[active] ──▶ [completed]
    │
    └──▶ [abandoned]
```

**Business rules:**
- Khi goal cha `completed` → objective tự động `completed`
- Progress % tính từ KR con (trung bình có trọng số)
- Có thể reassign `owner_user_id` giữa chừng

### 10.3. Key Result

```
[active] ──▶ [achieved]  (current_value >= target)
    │
    ├──▶ [missed]        (đóng objective, KR chưa đạt)
    └──▶ [archived]      (không còn relevant)
```

### 10.4. Project

```
[active] ──▶ [completed]
    │
    ├──▶ [archived]
    └──▶ [abandoned]
```

**Phân loại theo `origin`:**

| Origin | `link_status` mặc định | Khi nào |
|---|---|---|
| `okr_driven` | `linked` | Sinh từ objective (top-down) |
| `discovery` | `pending_review` | Khám phá trong cycle |
| `maintenance` | `intentionally_unlinked` | Định kỳ |
| `reactive` | `pending_review` | Bug/incident |

### 10.5. Onboard Session

```
[in_progress] ──▶ [completed]
       │
       └──▶ [abandoned]
```

| Session type | Khi nào | Số chiều touch |
|---|---|---|
| `initial` | `/cs:setup` lần đầu | 7/7 |
| `partial_update` | Trigger bởi goal creation hoặc user chủ động | 1-3 |
| `event_driven` | Pivot, funding, exit | 3-7 |

---

## 11. Sáu luồng vận hành chính

### 11.1. Flow 1: Onboarding lần đầu

```
User tạo workspace
    │
    ▼
[/cs:setup] interview 7 chiều (45 phút)
    │
    ▼
[Tạo onboard_session] type = 'initial', status = 'in_progress'
    │
    ├── Lưu từng lượt hội thoại vào conversation_turns
    │
    ▼
[Hoàn thành] Tạo 7 bản ghi chiều với is_current = true
    │
    ▼
[Tạo snapshot] full_context = render 7 chiều
    │
    ▼
[Seed review cadence] Cho workspace mới
    │
    ▼
[Hoàn thành session] status = 'completed'
    │
    ▼
[Gợi ý] "Tạo Goal strategic 12 tháng đầu tiên?"
```

**Idempotency:** Nếu user chạy `/cs:setup` lần 2, tạo session mới với type = `initial` — snapshot mới, dimensions mới, bản ghi cũ giữ nguyên (không xóa).

### 11.2. Flow 2: Tạo Goal mới

```
User bấm "New Goal"
    │
    ▼
[Check review cadence]
    │
    ├── Nếu có dimension "critical" hoặc "recommended":
    │       │
    │       ▼
    │   "Cập nhật nhanh 2 chiều này trước? (~3 phút)"
    │       │
    │       ├── Yes → chạy partial update → snapshot mới
    │       └── No  → tiếp tục
    │
    ▼
[Insert goal]
    │
    ├── Trigger auto-gán onboard_snapshot_id = snapshot hiện tại
    │
    ▼
[Gợi ý contextual]
    │
    ├── stage = 'pre_pmf'   → duration 2-4 tuần, type = tactical
    ├── stage = 'scaling'   → duration 12 tuần, type = strategic
    ├── priority_growth = 1 → gợi ý objective liên quan growth
    └── value 'fire-worthy' → cảnh báo nếu goal vi phạm
    │
    ▼
[User confirm] Goal status = 'active'
```

**Quan trọng:** Goal **luôn** reference snapshot hiện tại. Khi snapshot thay đổi, hệ thống biết goal nào cần review.

### 11.3. Flow 3: Từ Goal → Execution

```
Goal #3 (tactical): "Launch MVP" (4 tuần)
    │
    ▼
[User tạo Objectives trong Goal]
    │
    ├── Objective 1: "Build core features"    (owner: A)
    ├── Objective 2: "Acquire 100 beta users" (owner: B)
    └── Objective 3: "Production infra"       (owner: C)
    │
    ▼
[Mỗi Objective có KRs]
    │
    ├── Obj 1: KR "3 features done", KR "coverage > 80%"
    ├── Obj 2: KR "100 signups"
    └── Obj 3: KR "uptime 99.9%"
    │
    ▼
[User tạo Projects]
    │
    ├── Project "Auth flow"      → link Objective 1
    ├── Project "Landing page"   → link Objective 2
    └── Project "K8s setup"      → link Objective 3
    │
    ▼
[Tracking hàng tuần]
    │
    ├── User update current_value của KRs
    ├── Progress objective tự tính từ KR
    └── Progress goal tự tính từ objectives
```

### 11.4. Flow 4: Khi onboard update

```
User chạy /cs:update
    │
    ▼
[Tạo onboard_session] type = 'partial_update'
    │
    ▼
[User chọn dimensions cần update]
    │
    ├── Nếu trigger bởi goal creation → auto-select stale dimensions
    ├── Nếu user tự chạy → hiển thị 7 chiều với freshness status
    │
    ▼
[Với mỗi dimension update]
    │
    ├── INSERT bản ghi mới với is_current = true
    ├── Trigger demote bản ghi cũ (is_current = false)
    │
    ▼
[Tạo onboard_snapshot mới]
    │
    ├── full_context = render 7 chiều is_current
    ├── changed_dimensions = array các chiều vừa update
    ├── Trigger demote snapshot cũ
    │
    ▼
[Gọi fn_goals_needing_review]
    │
    ├── Hiển thị: "3 goal active đang dựa trên snapshot cũ >14 ngày"
    ├── "Launch MVP (tactical, 18 ngày)"     — urgency: high
    ├── "Validate pricing (sprint, 21 ngày)" — urgency: high
    └── "Build brand (strategic, 45 ngày)"   — urgency: low
    │
    ▼
[User quyết định]
    │
    ├── Review goal ngay → tạo partial update cho goal đó
    ├── Snooze → nhắc lại sau 7 ngày
    └── Ignore → ghi log
```

**Nguyên tắc vàng:** Onboard update **không tự động sửa goal**. Nó chỉ **đánh dấu** goal nào cần review. User là người quyết định.

### 11.5. Flow 5: Hoàn thành Goal

```
User đánh dấu goal "Launch MVP" completed
    │
    ▼
[Validate]
    │
    ├── Còn objective active? → Cảnh báo "2 objectives chưa xong"
    │
    ▼
[Update goal] status = 'completed', completed_at = now()
    │
    ▼
[Cascade]
    │
    ├── Objectives con: active → completed
    ├── KRs con: nếu chưa đạt → 'missed', nếu đạt → 'achieved'
    └── Projects con: giữ nguyên status (user tự dọn)
    │
    ▼
[Review ambition]
    │
    ├── Query onboard_goals_ambition
    │    "goal_12_months_text = 'Đạt $1M ARR'"
    │    "Goal strategic #2 đã completed?"
    │    │
    │    ├── Yes → gợi ý update ambition lên mức cao hơn
    │    └── No  → giữ nguyên
    │
    ▼
[Đề xuất]
    │
    └── "Tạo goal tiếp theo trong program này?"
```

### 11.6. Flow 6: Xử lý Discovery Projects

```
Cuối sprint/tactical goal:
    │
    ▼
[Query projects có link_status = 'pending_review']
    │
    ├── Filter: origin IN ('discovery', 'reactive')
    ├── Filter: created_at trong khoảng thời gian của goal
    │
    ▼
[Hiển thị cho user]
    │
    ├── "5 project khám phá chưa map objective"
    ├── Với mỗi project: name, origin, tuổi, owner
    │
    ▼
[User quyết định cho mỗi project]
    │
    ├── Link với objective → link_status = 'linked'
    ├── Đánh dấu R&D       → link_status = 'intentionally_unlinked'
    ├── Archive            → status = 'archived'
    └── Roll vào goal mới  → tạo objective mới, link project
```

**Đây là double-loop learning:** Discovery projects ở sprint N có thể trở thành objectives trong goal strategic ở sprint N+1.

---

## 12. Review cadence — BSC-style

### 12.1. Phân loại 7 chiều

| Chiều | Cadence | Interval | Lý do |
|---|---|---|---|
| `identity` | slow | 180 ngày | Vision/mission ít thay đổi |
| `stage_scale` | fast | 14 ngày | Metrics, runway thay đổi liên tục |
| `founder` | slow | 180 ngày | Archetype, superpower ổn định |
| `team_culture` | medium | 60 ngày | Thay đổi khi có hire/fire |
| `market` | medium | 60 ngày | Competitive landscape thay đổi |
| `challenges` | fast | 14 ngày | Ưu tiên thay đổi theo cycle |
| `goals_ambition` | medium | 90 ngày | Review cùng strategic goal |

### 12.2. Cơ chế trigger

```
Khi user bắt đầu tương tác với hệ thống:
    │
    ▼
[System check onboard_review_cadence]
    │
    ├── Dimension nào next_due_at <= now() + 7 days?
    │
    ▼
[Phân loại urgency]
    │
    ├── critical: quá hạn >14 ngày
    ├── recommended: quá hạn 0-14 ngày
    └── optional: sắp đến hạn trong 7 ngày
    │
    ▼
[Hiển thị contextual]
    │
    ├── "Bạn có 3 dimensions cần review. Mất ~5 phút. Bắt đầu?"
    ├── "Challenges của bạn đã 18 ngày chưa update"
    └── "Stage & Scale đã 14 ngày chưa update"
    │
    ▼
[User chọn]
    │
    ├── Update ngay → partial session
    ├── Snooze 7 ngày
    └── Ignore → ghi log
```

### 12.3. Trigger tự động khi tạo Goal

Đây là cơ chế chính kết nối onboard với execution:

```
User bấm "New Goal"
    │
    ▼
[Check cadence của các dimension "fast"]
    │
    ├── stage_scale: last_reviewed 14 ngày trước → stale
    ├── challenges:  last_reviewed 10 ngày trước → ok
    │
    ▼
[Modal]
    │
    "Trước khi tạo goal mới:
     Stage & Scale đã 14 ngày chưa update.
     [Update nhanh (2 phút)] [Bỏ qua]"
    │
    ▼
[User chọn]
    │
    ├── Update → tạo snapshot mới → goal dùng snapshot này
    └── Bỏ qua → goal dùng snapshot hiện tại
```

---

## 13. Data flow & events

### 13.1. Data flow: Onboard → Goal

```
┌─────────────────────┐
│ onboard_*           │
│ (7 chiều is_current)│
└──────────┬──────────┘
           │ render
           ▼
┌─────────────────────┐
│ onboard_snapshots   │
│ (full_context JSONB)│
└──────────┬──────────┘
           │ auto-link (trigger)
           ▼
┌─────────────────────┐
│ goals               │
│ (onboard_snapshot_id)│
└─────────────────────┘
```

**Một chiều:** Onboard → Goal. Goal không bao giờ ghi ngược lại onboard.

### 13.2. Data flow: Goal → Objective → KR → Project

```
goals (parent_id self-ref)
    │ has many
    ▼
objectives (owner per obj)
    │ has many
    ▼
key_results (baseline → target)
    │ optionally drives
    ▼
projects (origin, link_status)
```

**Hai chiều mềm:**
- Top-down: Goal mới → gợi ý objectives → gợi ý projects
- Bottom-up: Project discovery → gợi ý objective mới (qua `pending_review`)

### 13.3. Events & Reactions

```
Event: Onboard snapshot thay đổi
    │
    ├── Reaction 1: Query goals_needing_review
    ├── Reaction 2: Hiển thị badge "N goals cần review"
    └── Reaction 3: Ghi log vào change_history

Event: Goal completed
    │
    ├── Reaction 1: Cascade objectives
    ├── Reaction 2: Review onboard_goals_ambition
    └── Reaction 3: Đề xuất goal kế tiếp

Event: Goal quá hạn (end_date < now)
    │
    ├── Reaction 1: Đánh dấu "overdue"
    ├── Reaction 2: Notify owner
    └── Reaction 3: Suggest retrospective
```

### 13.4. Trigger points

| Trigger | Nguồn | Đích | Hành động |
|---|---|---|---|
| Insert goal | `goals` | `onboard_snapshots` | Auto-gán `onboard_snapshot_id` |
| Insert dimension | 7 chiều onboard | cùng bảng | Demote `is_current` cũ |
| Insert snapshot | `onboard_snapshots` | cùng bảng | Demote `is_current` cũ |
| Complete goal | `goals` | `objectives` | Cascade status |
| Onboard update | `onboard_snapshots` | `goals` | Đánh dấu goal cần review |

---

# PHẦN IV — BEST PRACTICES

## 14. Nguyên tắc vàng

1. **Onboard inform, không control.** Onboard cung cấp ngữ cảnh, không tự động sửa goal. User là người quyết định.

2. **Snapshot không thay đổi.** Snapshot cũ giữ nguyên vĩnh viễn. Goal reference snapshot — không phải "latest snapshot". Điều này cho phép trace ngược: *"Goal này lập dựa trên giả định gì?"*

3. **Discovery có chỗ đứng.** Không ép mọi project phải link objective ngay. `pending_review` là trạng thái hợp lệ. Review ở cuối cycle, không phải lúc tạo.

### Khi nào onboard trigger?

| Sự kiện | Có trigger onboard không? |
|---|---|
| Tạo goal mới | ✅ Check cadence, gợi ý update chiều "fast" |
| Hoàn thành goal | ✅ Review `goals_ambition` |
| Cuối sprint/tactical | ✅ Review `challenges` |
| Cuối strategic goal | ✅ Review tất cả chiều |
| User tự chạy `/cs:update` | ✅ Bất kỳ lúc nào |
| Event bên ngoài (pivot, funding) | ✅ Event-driven session |

### Khi nào KHÔNG trigger?

- Update KR hàng ngày → không cần onboard
- Tạo project discovery → không cần onboard
- Reassign owner → không cần onboard
- Đổi tên objective → không cần onboard

**Nguyên tắc:** Onboard chỉ trigger khi có khả năng **thay đổi chiến lược**, không phải khi thực thi.

---

## 15. Anti-patterns

| Anti-pattern | Hậu quả | Cách tránh |
|---|---|---|
| Tạo bảng `companies` riêng | Trùng lặp với workspace | Workspace = Company |
| Tạo bảng `programs` | Over-engineering | Dùng `goals.parent_id` |
| Tạo bảng `cycles` riêng | Trùng với `goals` | Cycle = Goal với duration cụ thể |
| Goal tự động update khi onboard thay đổi | Mất quyết định của user | Chỉ đánh dấu "cần review" |
| Snapshot bị UPDATE | Mất lịch sử | Snapshot immutable, luôn INSERT mới |
| Update dimension trực tiếp | Mất trace | Luôn INSERT + `is_current` |
| Auto-link project với goal | Mất giá trị alignment review | Dùng `link_status = 'pending_review'` |
| Bắt mọi project phải link | Cứng nhắc | Dùng WARN, không ERROR |
| Cascade xóa goal → xóa project | Mất dữ liệu | Dùng `SET NULL` cho project |
| Goal `completed` khi objective chưa xong | Báo cáo sai | Validate trước khi cascade |
| Dùng `quarter` (Q1-Q4) làm key | Không linh hoạt với cycle 2-4 tuần | Dùng `start_date`, `end_date`, `duration_weeks` |

---

## 16. Migration path

Nếu workspace đã có dữ liệu OKR/cycle cũ:

| Bước | Hành động | Ghi chú |
|---|---|---|
| **1** | `pg_dump` backup toàn bộ | Trước khi chạy bất kỳ DDL nào |
| **2** | Tạo bảng mới | Chạy DDL ở Phần II |
| **3** | Migrate workspace | `INSERT INTO workspaces SELECT ... FROM old_workspaces` |
| **4** | Migrate goals từ old cycles | Map `duration_weeks` → `goal_type` (≤4: sprint, ≤12: tactical, ≤52: strategic, còn lại: vision) |
| **5** | Migrate objectives (nếu có) | Map old_cycles → goals, old_objectives → objectives |
| **6** | Chạy onboarding cho từng workspace | Thủ công qua `/cs:setup` |
| **7** | Gợi ý link goal cũ → snapshot | Keyword matching + **human review** (không auto-accept) |

**Quan trọng:** Không auto-link. Việc review thủ công chính là bước học hỏi — buộc bạn suy nghĩ lại về alignment của từng goal hiện có.

---

## 17. Checklist triển khai

### 17.1. Database

- [ ] Cài PostgreSQL 14+ và extensions `pg_trgm`
- [ ] Chạy DDL sections 4 → 9
- [ ] Tạo views (`v_current_company_context`, `v_goal_tree`)
- [ ] Tạo functions (`fn_goals_needing_review`, `fn_suggest_dimension_review`)
- [ ] Tạo triggers (`fn_demote_current`, `fn_link_goal_to_snapshot`)
- [ ] Bật RLS theo `workspace_id`
- [ ] Seed `onboard_review_cadence` khi tạo workspace mới

### 17.2. Application layer

- [ ] Hàm `render_current_context(workspace_id)`
- [ ] Hàm `check_cadence(workspace_id)`
- [ ] Hàm `create_goal(workspace_id, data)`
- [ ] Hàm `update_dimension(workspace_id, dimension, data)`
- [ ] Hàm `create_snapshot(workspace_id, session_id)`
- [ ] Hàm `goals_needing_review(workspace_id)`
- [ ] Hàm `complete_goal(goal_id)`
- [ ] Hàm `handle_pending_projects(workspace_id)`
- [ ] Snowflake ID generator (worker_id + sequence)
- [ ] Cron job: đánh dấu dimension stale hàng ngày
- [ ] Cron job: notify user khi có dimension overdue >14 ngày

### 17.3. UI

- [ ] Cây Goal (dùng `v_goal_tree`)
- [ ] Dashboard "Context Freshness" — tuổi từng chiều
- [ ] Modal "Update nhanh" khi tạo goal
- [ ] Badge "N goals cần review"
- [ ] Trang "Pending Projects" cuối cycle
- [ ] Modal "Review ambition" khi complete strategic goal

### 17.4. Operations

- [ ] Backup strategy: `pg_dump` hàng ngày
- [ ] Transcript JSONB > 1MB → đẩy lên S3/GCS, chỉ giữ reference
- [ ] Materialized view cho dashboard nếu >100 workspace
- [ ] Monitoring: query performance của `v_goal_tree` và `v_current_company_context`

---

## 18. Tóm tắt

**Cấu trúc:**
- Workspace = Company = Tenant (một bảng, Snowflake ID)
- Goal là container lồng nhau (vision → strategic → tactical → sprint)
- Objective trong Goal, KR trong Objective, Project trong Objective
- Onboard là tầng chiến lược, không phải tầng thực thi

**Flow:**
- Onboard inform, không control
- Snapshot immutable, goal reference snapshot tại thời điểm lập
- Multi-cadence review (BSC-style), trigger bởi goal creation
- Discovery có chỗ đứng (`pending_review`)
- Double-loop learning: discovery projects → objectives ở cycle sau

**Nguyên tắc:**
- User quyết định, hệ thống gợi ý
- Trace ngược được từ goal về ngữ cảnh
- Không auto-merge giữa strategy và execution
- Chỉ tách bảng khi có 2+ khách hàng yêu cầu

**ID strategy:**
- Snowflake ID (BIGINT) — sortable theo thời gian
- Generate ở application layer trước INSERT
- Không dùng UUID, không dùng `SERIAL`/`BIGSERIAL` cho business entity
- `conversation_turns.id` dùng `BIGSERIAL` vì là audit log, không cần distributed

---

*Hết tài liệu.*
```

File này gộp cả **schema reference** (Phần II) và **cấu trúc/flow** (Phần I, III, IV) vào một tài liệu duy nhất. Điểm khác biệt so với hai file riêng:

- **Snowflake ID** được ghi rõ ở header và trong mọi DDL (dùng `BIGINT` thay vì `UUID`)
- **Phần II** được đánh dấu rõ là "reference" — bạn đối chiếu với schema hiện có, không copy-paste
- **Mục lục** ở đầu để điều hướng nhanh trong file dài
- Bỏ phần "seed data" và ví dụ end-to-end dài dòng, giữ lại các ví dụ cốt lõi
- Ghi chú rõ `conversation_turns.id` dùng `BIGSERIAL` (không cần Snowflake vì là audit log nội bộ)

Bạn có thể đặt file này làm `docs/architecture.md` trong dự án.