-- Migration 17: Typed project ↔ record links (Founder Trial R1 — Node B/C)
--
-- Bỏ ý tưởng `project_record_links` polymorphic. Dùng liên kết typed per-entity
-- theo pattern `services/company/operations/services/project-link.service.ts`:
--   - contact ↔ project: bảng join N:M (một người có thể là evidence cho nhiều
--     project).
--   - lead / marketing_campaign / marketing_experiment: cột project_id nullable
--     FK (một record thuộc tối đa một project ở R1).
-- Tất cả expand-only. Record legacy chưa link vẫn đọc được (cột nullable, không
-- backfill).

-- 1. contact ↔ project (N:M)
CREATE TABLE IF NOT EXISTS sales.contact_projects (
  id                BIGINT NOT NULL PRIMARY KEY,
  workspace_id      BIGINT NOT NULL,
  contact_id        BIGINT NOT NULL REFERENCES sales.contacts(id) ON DELETE CASCADE,
  project_id        BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
  linked_by_member_id BIGINT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_contact_projects_pair
  ON sales.contact_projects (workspace_id, contact_id, project_id);
CREATE INDEX IF NOT EXISTS idx_contact_projects_project
  ON sales.contact_projects (workspace_id, project_id);

-- 2. lead → project (0..1)
ALTER TABLE sales.sales_leads
  ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES strategy.projects(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_sales_leads_project
  ON sales.sales_leads (workspace_id, project_id);

-- 3. marketing_campaign → project (0..1)
ALTER TABLE commercial.marketing_campaigns
  ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES strategy.projects(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_project
  ON commercial.marketing_campaigns (workspace_id, project_id);

-- 4. marketing_experiment → project (0..1)
ALTER TABLE commercial.marketing_experiments
  ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES strategy.projects(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_marketing_experiments_project
  ON commercial.marketing_experiments (workspace_id, project_id);
