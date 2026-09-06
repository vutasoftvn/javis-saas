-- services/company/finance-legal/migrations/39_legal_predicate_tt58_status_correction.up.sql
--
-- IA19 (audit 2026-09-06) — predicate của rule TT58 seed tại migration 14
-- (legal.applicability_rules id=301) dùng literal "entity_status":
-- "REGISTERED_VERIFIED", nhưng cột legal_entity_profiles.status KHÔNG BAO
-- GIỜ có giá trị đó — enum thật (xem comment tại
-- shared/db/schema/legal.ts::legalEntityProfiles) là:
-- DRAFT | REGISTRATION_PREPARATION | REGISTERED_UNVERIFIED | VERIFIED |
-- SUSPENDED | DISSOLVED. Nguồn xác nhận: hàm chuyển trạng thái founder-verify
-- thật (legal-entity-profile.service.ts, transition sang status="VERIFIED"
-- kèm verifiedByMemberId/verifiedAt) — đây chính là trạng thái "đã được xác
-- minh hợp lệ" mà rule này cần kiểm tra.
--
-- Vì literal cũ không khớp bất kỳ giá trị enum thật nào, rule TT58/NQ86 này
-- (nghĩa vụ "Nộp báo cáo tài chính năm theo TT58") KHÔNG BAO GIỜ có thể
-- APPLIES cho bất kỳ pháp nhân nào — kể cả pháp nhân đã verify thật —
-- evaluateLegalPredicateWithDetails trả NOT_APPLIES ngay ở bước so khớp
-- entity_status (services/legal-predicate.ts), khiến obligation bị "ẩn"
-- vĩnh viễn thay vì thực sự không áp dụng.
--
-- Đồng thời predicate dùng 2 field vestigial "condition_field"/
-- "condition_value" thay vì field chuẩn evaluator nhận diện được
-- (KNOWN_PREDICATE_FIELDS ở legal-predicate.ts có "accounting_regime" —
-- không có "condition_field"/"condition_value"), bị flag
-- unknown_predicate_field (không chặn kết quả nhưng là dữ liệu sai hình
-- dạng). Giá trị "TT58_2026" vẫn đúng — khớp regulationCode mặc định của
-- accounting_fiscal_profiles (shared/db/schema/finance-legal.ts) và toàn
-- bộ code base dùng cùng literal này (accounting-regime.service.ts) — chỉ
-- đổi TÊN field, không đổi giá trị.
--
-- Sửa tại chỗ (UPDATE, không đổi schema — Expand-only) vì applicability_rules
-- chưa có cột versioning/supersedes (audit cũng ghi nhận đây là tính năng
-- CHƯA XÂY, không phải bug có thể vá bằng cách bịa cột mới); các bản ghi
-- applicability_evaluations lịch sử là log độc lập, không đọc lại predicate
-- hiện tại của rule nên không bị ảnh hưởng bởi UPDATE này.
UPDATE legal.applicability_rules
SET predicate = '{"entity_status": "VERIFIED", "accounting_regime": "TT58_2026"}'::jsonb
WHERE id = 301
  AND predicate = '{"entity_status": "REGISTERED_VERIFIED", "condition_field": "accounting_regime", "condition_value": "TT58_2026"}'::jsonb;
