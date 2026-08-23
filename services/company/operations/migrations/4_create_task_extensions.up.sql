CREATE TABLE operating.task_dependencies (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
    depends_on_task_id BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) DEFAULT 'BLOCKS',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_task_dependencies_task_id ON operating.task_dependencies(task_id);
CREATE INDEX idx_task_dependencies_depends_on ON operating.task_dependencies(depends_on_task_id);

CREATE TABLE operating.task_schedules (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
    schedule_type VARCHAR(50) NOT NULL DEFAULT 'once',
    cron_expr VARCHAR(100),
    next_run_at TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_task_schedules_task_id ON operating.task_schedules(task_id);
