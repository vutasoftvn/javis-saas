-- services/company/finance-legal/migrations/29_ai_compliance_runtime_hardening.up.sql
-- Defense-in-depth ở tầng database cho quyền sở hữu theo workspace (Task 2,
-- kế thừa Task 1 — Task 1 đã sửa mọi lookup/mutation TS scope theo
-- and(eq(id), eq(workspaceId))). Trước migration này, mọi FK trong
-- legal.* chỉ tham chiếu PK đơn `id`: không gì ở tầng DB ngăn một row con
-- khai workspace_id = B nhưng deployment_id/assessment_id/incident_id/
-- recipient_provider_profile_id trỏ sang một parent thuộc workspace A.
--
-- Kỹ thuật: thêm composite UNIQUE (workspace_id, id) trên mỗi bảng cha thuộc
-- workspace, sau đó thêm composite FOREIGN KEY (workspace_id, <ref>)
-- REFERENCES parent(workspace_id, id) trên bảng con. PostgreSQL sẽ tự chặn
-- insert/update nếu workspace_id của con không khớp workspace_id thật của
-- parent — không cần thêm bất kỳ kiểm tra ứng dụng nào.
--
-- Phạm vi bảng: khảo sát toàn bộ legal.ts + migration 27, xác định các bảng
-- cha thuộc workspace được bảng con khác trỏ tới qua FK:
--   - legal.workspace_ai_deployments  (cha của: ai_risk_assessments,
--     ai_data_processing_profiles, ai_incidents, ai_compliance_snapshots;
--     đồng thời tự tham chiếu ai_risk_assessments qua current_assessment_id)
--   - legal.ai_risk_assessments       (cha của: ai_compliance_evidence,
--     ai_compliance_snapshots, và workspace_ai_deployments.current_assessment_id)
--   - legal.ai_provider_profiles      (cha của: ai_data_processing_profiles
--     qua recipient_provider_profile_id, nullable — composite FK cho phép NULL)
--   - legal.ai_incidents              (cha của: ai_incident_actions)
--
-- Không đưa vào phạm vi: ai_system_catalog, ai_system_versions,
-- ai_system_capability_bindings (catalog toàn cục, không có workspace_id —
-- không áp dụng composite ownership); data_processing_authorizations và
-- data_subject_requests (có workspace_id nhưng không có FK trỏ tới bảng cha
-- thuộc workspace khác trong legal.*, nên không có lỗ hổng IDOR loại này).
--
-- Backfill: đã kiểm tra dữ liệu hiện có trong DB dev bằng JOIN so
-- workspace_id giữa mỗi bảng con và bảng cha trước khi viết migration này.
-- Kết quả: với CẢ 9 quan hệ composite FK bên dưới, có ĐÚNG 1 row vi phạm mỗi
-- quan hệ (không hơn) — mẫu hình này khớp chính xác với hostile-workspace
-- test suite (finance-legal/tests/ai-compliance-workspace-access.test.ts):
-- mỗi "it" trong suite đó cố tạo đúng 1 row cross-workspace để assert bị từ
-- chối; các row hiện diện trong DB là kết quả của một lần chạy suite đó
-- TRƯỚC KHI Task 1 sửa lỗ hổng — ở thời điểm đó thao tác cross-workspace vẫn
-- thành công và bị ghi xuống DB, để lại đúng 1 artifact rác cho mỗi bảng.
-- Không row nào trong số này được tham chiếu bởi bảng con khác (đã verify:
-- evidence/snapshots/current_assessment_id trỏ tới các assessment/incident
-- rác đều = 0), và tất cả đều thuộc DB dev/test — không phải production
-- data.
--
-- Theo quy tắc "không tự ý xóa dữ liệu" (CLAUDE.md #10), migration này KHÔNG
-- tự xoá các row rác đó. Thay vào đó: mọi composite FOREIGN KEY dưới đây
-- được thêm bằng NOT VALID — PostgreSQL vẫn enforce đầy đủ constraint cho
-- MỌI insert/update mới kể từ thời điểm apply migration này (đây là mục
-- tiêu chính của Task 2 — chặn IDOR mới ở tầng DB), nhưng không validate
-- ngược lại dữ liệu cũ đã tồn tại nên không cần xoá/sửa gì để migration này
-- áp dụng thành công. Một khi người vận hành xác nhận có thể xoá các row
-- rác kể trên, hãy tạo migration theo dõi riêng chạy
-- `ALTER TABLE ... VALIDATE CONSTRAINT ...;` cho từng constraint để nâng từ
-- NOT VALID lên fully-validated — không tự ý quyết định thay ở migration
-- này.

-- 1. Composite unique key trên các bảng cha thuộc workspace.
ALTER TABLE legal.workspace_ai_deployments
  ADD CONSTRAINT workspace_ai_deployments_workspace_id_id_key UNIQUE (workspace_id, id);

ALTER TABLE legal.ai_risk_assessments
  ADD CONSTRAINT ai_risk_assessments_workspace_id_id_key UNIQUE (workspace_id, id);

ALTER TABLE legal.ai_provider_profiles
  ADD CONSTRAINT ai_provider_profiles_workspace_id_id_key UNIQUE (workspace_id, id);

ALTER TABLE legal.ai_incidents
  ADD CONSTRAINT ai_incidents_workspace_id_id_key UNIQUE (workspace_id, id);

-- 2. Composite foreign key trên bảng con → parent(workspace_id, id).
-- Tất cả dùng NOT VALID (xem ghi chú Backfill ở trên) — vẫn enforce đầy đủ
-- cho ghi mới, chỉ bỏ qua validate 1 row rác lịch sử mỗi bảng.

-- ai_risk_assessments.deployment_id phải cùng workspace với deployment cha.
ALTER TABLE legal.ai_risk_assessments
  ADD CONSTRAINT ai_risk_assessments_workspace_deployment_fk
  FOREIGN KEY (workspace_id, deployment_id)
  REFERENCES legal.workspace_ai_deployments (workspace_id, id)
  NOT VALID;

-- workspace_ai_deployments.current_assessment_id (nullable) phải cùng
-- workspace với assessment được gán làm "current".
ALTER TABLE legal.workspace_ai_deployments
  ADD CONSTRAINT workspace_ai_deployments_workspace_assessment_fk
  FOREIGN KEY (workspace_id, current_assessment_id)
  REFERENCES legal.ai_risk_assessments (workspace_id, id)
  NOT VALID;

-- ai_compliance_evidence.assessment_id phải cùng workspace với assessment cha.
ALTER TABLE legal.ai_compliance_evidence
  ADD CONSTRAINT ai_compliance_evidence_workspace_assessment_fk
  FOREIGN KEY (workspace_id, assessment_id)
  REFERENCES legal.ai_risk_assessments (workspace_id, id)
  NOT VALID;

-- ai_data_processing_profiles.deployment_id phải cùng workspace với deployment cha.
ALTER TABLE legal.ai_data_processing_profiles
  ADD CONSTRAINT ai_data_profiles_workspace_deployment_fk
  FOREIGN KEY (workspace_id, deployment_id)
  REFERENCES legal.workspace_ai_deployments (workspace_id, id)
  NOT VALID;

-- ai_data_processing_profiles.recipient_provider_profile_id (nullable) phải
-- cùng workspace với provider profile — MATCH SIMPLE (mặc định) cho phép
-- NULL bỏ qua kiểm tra, giữ đúng ngữ nghĩa optional hiện tại.
ALTER TABLE legal.ai_data_processing_profiles
  ADD CONSTRAINT ai_data_profiles_workspace_provider_fk
  FOREIGN KEY (workspace_id, recipient_provider_profile_id)
  REFERENCES legal.ai_provider_profiles (workspace_id, id)
  NOT VALID;

-- ai_incidents.deployment_id phải cùng workspace với deployment cha.
ALTER TABLE legal.ai_incidents
  ADD CONSTRAINT ai_incidents_workspace_deployment_fk
  FOREIGN KEY (workspace_id, deployment_id)
  REFERENCES legal.workspace_ai_deployments (workspace_id, id)
  NOT VALID;

-- ai_incident_actions.incident_id phải cùng workspace với incident cha.
ALTER TABLE legal.ai_incident_actions
  ADD CONSTRAINT ai_incident_actions_workspace_incident_fk
  FOREIGN KEY (workspace_id, incident_id)
  REFERENCES legal.ai_incidents (workspace_id, id)
  NOT VALID;

-- ai_compliance_snapshots.deployment_id / assessment_id phải cùng workspace
-- với deployment/assessment cha tương ứng.
ALTER TABLE legal.ai_compliance_snapshots
  ADD CONSTRAINT ai_compliance_snapshots_workspace_deployment_fk
  FOREIGN KEY (workspace_id, deployment_id)
  REFERENCES legal.workspace_ai_deployments (workspace_id, id)
  NOT VALID;

ALTER TABLE legal.ai_compliance_snapshots
  ADD CONSTRAINT ai_compliance_snapshots_workspace_assessment_fk
  FOREIGN KEY (workspace_id, assessment_id)
  REFERENCES legal.ai_risk_assessments (workspace_id, id)
  NOT VALID;

-- 3. Snapshot provenance columns (task-2-brief.md "Produces" + Step 3 — bổ
-- sung sau review, chưa có ở bản migration 29 đầu tiên).
--
-- ai_compliance_snapshots trước đây chỉ lưu providerProfileVersion/
-- dataProfileVersion (text) và legalVersionIds (đã có sẵn) — không lưu ID
-- thật của binding/evidence/provider profile/data profile đã dùng để tạo
-- snapshot, nên không ai verify lại được "snapshot này thực sự dựa trên
-- đúng những gì". Thêm 5 cột provenance:
--   - capability_binding_ids  JSONB — id của các ai_system_capability_bindings
--     thuộc system_version của deployment (bindings là catalog toàn cục,
--     không có workspace_id nên không cần composite FK).
--   - evidence_ids            JSONB — id của các ai_compliance_evidence
--     thuộc đúng (workspace_id, assessment_id) của snapshot.
--   - evidence_hashes         JSONB — content_hash tương ứng, cùng thứ tự.
--   - provider_profile_id     BIGINT NULL — id thật của ai_provider_profiles
--     đã dùng, composite FK (workspace_id, provider_profile_id) → tự chặn
--     cross-workspace giống các bảng khác.
--   - data_profile_id         BIGINT NULL — id thật của
--     ai_data_processing_profiles đã dùng, composite FK tương tự.
-- Cộng thêm cột provenance_complete (boolean) để Task 4's resolver biết
-- snapshot nào KHÔNG verify được đầy đủ provider/data profile — không được
-- coi các snapshot đó là hợp lệ ngầm định.
--
-- provider_profile_id/data_profile_id là composite FK NHƯNG KHÔNG NOT VALID
-- (khác với các FK ở mục 2): cột hoàn toàn mới (toàn NULL trước backfill) và
-- backfill bên dưới CHỈ set giá trị khi match được đúng 1 quan hệ verified
-- (workspace_id khớp theo JOIN) — nên không thể có row nào vi phạm composite
-- FK ngay từ đầu, validate ngay được, không cần trì hoãn.

ALTER TABLE legal.ai_data_processing_profiles
  ADD CONSTRAINT ai_data_processing_profiles_workspace_id_id_key UNIQUE (workspace_id, id);

ALTER TABLE legal.ai_compliance_snapshots
  ADD COLUMN capability_binding_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN evidence_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN provider_profile_id BIGINT,
  ADD COLUMN data_profile_id BIGINT,
  ADD COLUMN provenance_complete BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE legal.ai_compliance_snapshots
  ADD CONSTRAINT ai_compliance_snapshots_workspace_provider_fk
  FOREIGN KEY (workspace_id, provider_profile_id)
  REFERENCES legal.ai_provider_profiles (workspace_id, id);

ALTER TABLE legal.ai_compliance_snapshots
  ADD CONSTRAINT ai_compliance_snapshots_workspace_data_profile_fk
  FOREIGN KEY (workspace_id, data_profile_id)
  REFERENCES legal.ai_data_processing_profiles (workspace_id, id);

-- Backfill — CHỈ điền giá trị khi verify được quan hệ thật, không bịa ID/hash.
--
-- Mọi UPDATE bên dưới đều giới hạn ở snapshot có deployment_id/assessment_id
-- đã verify đúng workspace ("verified snapshot") — lý do kỹ thuật: 2 trong số
-- các row rác lịch sử mô tả ở mục Backfill phía trên (1 snapshot có
-- deployment_id trỏ sai workspace, 1 snapshot khác có assessment_id trỏ sai
-- workspace) sẽ bị composite FK NOT VALID ở mục 2 chặn lại NGAY LẬP TỨC nếu
-- UPDATE đụng tới bất kỳ cột nào của chính row đó (PostgreSQL re-check FK
-- trigger trên toàn bộ row khi UPDATE, không chỉ khi sửa đúng cột FK). Loại
-- các snapshot chưa verify được chính deployment/assessment của nó ra khỏi
-- backfill vừa tránh lỗi đó, vừa đúng về nghĩa: một snapshot có provenance
-- gốc (deployment/assessment) đã sai thì chắc chắn KHÔNG THỂ coi là có đầy đủ
-- provenance — giữ nguyên default ('[]', NULL, provenance_complete=false)
-- cho các snapshot đó là chính xác, không phải bỏ sót.
WITH verified_snapshots AS (
  SELECT s.id
  FROM legal.ai_compliance_snapshots s
  JOIN legal.workspace_ai_deployments d
    ON d.id = s.deployment_id AND d.workspace_id = s.workspace_id
  JOIN legal.ai_risk_assessments a
    ON a.id = s.assessment_id AND a.workspace_id = s.workspace_id
)

-- capability_binding_ids: bindings thuộc đúng system_version của deployment
-- (quan hệ trực tiếp, không mơ hồ — deployment.system_version_id là 1 giá
-- trị duy nhất).
UPDATE legal.ai_compliance_snapshots s
SET capability_binding_ids = COALESCE((
  SELECT jsonb_agg(b.id ORDER BY b.id)
  FROM legal.workspace_ai_deployments d
  JOIN legal.ai_system_capability_bindings b ON b.system_version_id = d.system_version_id
  WHERE d.id = s.deployment_id AND d.workspace_id = s.workspace_id
), '[]'::jsonb)
WHERE s.id IN (SELECT id FROM verified_snapshots);

-- evidence_ids / evidence_hashes: evidence thuộc đúng (workspace_id,
-- assessment_id) của snapshot — quan hệ trực tiếp, không mơ hồ.
WITH verified_snapshots AS (
  SELECT s.id
  FROM legal.ai_compliance_snapshots s
  JOIN legal.workspace_ai_deployments d
    ON d.id = s.deployment_id AND d.workspace_id = s.workspace_id
  JOIN legal.ai_risk_assessments a
    ON a.id = s.assessment_id AND a.workspace_id = s.workspace_id
)
UPDATE legal.ai_compliance_snapshots s
SET evidence_ids = COALESCE((
      SELECT jsonb_agg(e.id ORDER BY e.id)
      FROM legal.ai_compliance_evidence e
      WHERE e.assessment_id = s.assessment_id AND e.workspace_id = s.workspace_id
    ), '[]'::jsonb),
    evidence_hashes = COALESCE((
      SELECT jsonb_agg(e.content_hash ORDER BY e.id)
      FROM legal.ai_compliance_evidence e
      WHERE e.assessment_id = s.assessment_id AND e.workspace_id = s.workspace_id
    ), '[]'::jsonb)
WHERE s.id IN (SELECT id FROM verified_snapshots);

-- provider_profile_id: snapshot cũ chỉ lưu (workspace_id, version) dạng text,
-- KHÔNG lưu provider_key/model_key — nên match theo (workspace_id, version)
-- có thể mơ hồ nếu 2 provider profile khác nhau tình cờ trùng version string.
-- CHỈ set khi match ĐÚNG 1 hàng (match_count = 1); nếu 0 hoặc >1 hàng khớp,
-- để NULL — không đoán.
WITH verified_snapshots AS (
  SELECT s.id
  FROM legal.ai_compliance_snapshots s
  JOIN legal.workspace_ai_deployments d
    ON d.id = s.deployment_id AND d.workspace_id = s.workspace_id
  JOIN legal.ai_risk_assessments a
    ON a.id = s.assessment_id AND a.workspace_id = s.workspace_id
),
provider_match AS (
  SELECT s.id AS snapshot_id, p.id AS provider_id,
         COUNT(*) OVER (PARTITION BY s.id) AS match_count
  FROM legal.ai_compliance_snapshots s
  JOIN legal.ai_provider_profiles p
    ON p.workspace_id = s.workspace_id AND p.version = s.provider_profile_version
  WHERE s.id IN (SELECT id FROM verified_snapshots)
)
UPDATE legal.ai_compliance_snapshots s
SET provider_profile_id = pm.provider_id
FROM provider_match pm
WHERE pm.snapshot_id = s.id AND pm.match_count = 1;

-- data_profile_id: match theo (workspace_id, deployment_id, version) — chặt
-- hơn provider vì có thêm deployment_id, nhưng vẫn CHỈ set khi match đúng 1
-- hàng, cùng lý do.
WITH verified_snapshots AS (
  SELECT s.id
  FROM legal.ai_compliance_snapshots s
  JOIN legal.workspace_ai_deployments d
    ON d.id = s.deployment_id AND d.workspace_id = s.workspace_id
  JOIN legal.ai_risk_assessments a
    ON a.id = s.assessment_id AND a.workspace_id = s.workspace_id
),
data_profile_match AS (
  SELECT s.id AS snapshot_id, dp.id AS data_profile_id,
         COUNT(*) OVER (PARTITION BY s.id) AS match_count
  FROM legal.ai_compliance_snapshots s
  JOIN legal.ai_data_processing_profiles dp
    ON dp.workspace_id = s.workspace_id
   AND dp.deployment_id = s.deployment_id
   AND dp.version = s.data_profile_version
  WHERE s.id IN (SELECT id FROM verified_snapshots)
)
UPDATE legal.ai_compliance_snapshots s
SET data_profile_id = dpm.data_profile_id
FROM data_profile_match dpm
WHERE dpm.snapshot_id = s.id AND dpm.match_count = 1;

-- provenance_complete: TRUE chỉ khi snapshot đã verified (deployment/
-- assessment đúng workspace) VÀ cả provider_profile_id lẫn data_profile_id
-- đều verify được (không NULL). provider/data profile là 2 trường duy nhất
-- có rủi ro "không thể xác minh" từ backfill (do dữ liệu cũ thiếu cột ID
-- trực tiếp) — mảng capability_binding_ids/evidence_ids rỗng được coi là hợp
-- lệ (nghĩa là thật sự không có binding/evidence nào, không phải "không
-- verify được"). Task 4 resolver phải coi provenance_complete = false là
-- "unusable", không được tự suy diễn/lấp đầy.
WITH verified_snapshots AS (
  SELECT s.id
  FROM legal.ai_compliance_snapshots s
  JOIN legal.workspace_ai_deployments d
    ON d.id = s.deployment_id AND d.workspace_id = s.workspace_id
  JOIN legal.ai_risk_assessments a
    ON a.id = s.assessment_id AND a.workspace_id = s.workspace_id
)
UPDATE legal.ai_compliance_snapshots s
SET provenance_complete = (s.provider_profile_id IS NOT NULL AND s.data_profile_id IS NOT NULL)
WHERE s.id IN (SELECT id FROM verified_snapshots);
