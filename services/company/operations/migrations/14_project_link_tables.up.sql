-- Hai bảng liên kết many-to-many tùy chọn. Task/Objective workspace-wide
-- không có row nào; Task/Objective thuộc nhiều project có nhiều row. Không
-- có "shared project" tổng hợp. Composite FK (…, workspace_id) khiến liên
-- kết chéo workspace là bất khả thi ngay ở tầng DB (spec §5.4).

CREATE TABLE operating.task_projects (
    workspace_id BIGINT NOT NULL,
    task_id      BIGINT NOT NULL,
    project_id   BIGINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_id, project_id),
    CONSTRAINT fk_task_projects_task
      FOREIGN KEY (task_id, workspace_id)
      REFERENCES operating.tasks (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_task_projects_project
      FOREIGN KEY (project_id, workspace_id)
      REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_task_projects_workspace ON operating.task_projects(workspace_id);
CREATE INDEX idx_task_projects_project ON operating.task_projects(project_id);

CREATE TABLE strategy.okr_objective_projects (
    workspace_id BIGINT NOT NULL,
    objective_id BIGINT NOT NULL,
    project_id   BIGINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (objective_id, project_id),
    CONSTRAINT fk_okr_objective_projects_objective
      FOREIGN KEY (objective_id, workspace_id)
      REFERENCES strategy.okr_objectives (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_okr_objective_projects_project
      FOREIGN KEY (project_id, workspace_id)
      REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_okr_objective_projects_workspace ON strategy.okr_objective_projects(workspace_id);
CREATE INDEX idx_okr_objective_projects_project ON strategy.okr_objective_projects(project_id);
