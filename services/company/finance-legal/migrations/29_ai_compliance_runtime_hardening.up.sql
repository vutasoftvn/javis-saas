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
