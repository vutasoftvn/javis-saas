-- Migration 026: cho phép event lifecycle "khai báo baseline lần đầu" khác
-- với "transition thật" — 2026-09-14 foundation correctness remediation.
-- Founder onboard một Project đã tồn tại ngoài đời cần được phép khai báo
-- đúng stage hiện tại (P0..P6) mà KHÔNG bịa ra một chuỗi P0->P1->...->Pn giả.
-- from_stage NULL chỉ hợp lệ cho event_type = 'PROJECT_INITIALIZED'; mọi
-- 'TRANSITION' (transitionProjectLifecycle) vẫn luôn có from_stage NOT NULL ở
-- tầng ứng dụng dù ràng buộc DB đã nới.
ALTER TABLE strategy.project_lifecycle_events
  ALTER COLUMN from_stage DROP NOT NULL,
  ADD COLUMN event_type varchar(32) NOT NULL DEFAULT 'TRANSITION',
  ADD COLUMN initialization_source varchar(64);
