-- services/company/finance-legal/migrations/31_ai_legal_review_pending_correction.up.sql
-- Migration 31: Sửa lỗi audit Critical — Migration 30 tự gán reviewer_member_id = 1
-- và review_status = 'REVIEWED' cho 9 nguồn luật + 6 rule mà KHÔNG có workforce
-- member thật nào mang ID 1 với vai trò "Chief Legal & Compliance Officer", và
-- KHÔNG có xác nhận thật từ người có thẩm quyền pháp lý rằng các rule/predicate
-- cụ thể đã được review đúng. Vi phạm rule 5 CLAUDE.md ("Governance là code xác
-- định, không phải LLM tự quyết") — AI không được tự gán reviewer giả.
--
-- QUAN TRỌNG: Migration này KHÔNG đụng tới content_hash / artifact_path / tên
-- văn bản / ngày hiệu lực của 9 nguồn luật — phần "document identity" đó đã
-- được người dùng tự tay verify SHA-256 + ngày ký số khớp 100% với PDF gốc, là
-- SỰ THẬT, giữ nguyên. Chỉ hạ phần "đã được luật sư duyệt" (claim của session
-- trước, chưa có xác nhận thật) xuống "chờ luật sư/founder duyệt".

-- 1. Thêm cột đánh dấu rõ ràng "đã có xác nhận review pháp lý THẬT hay chưa",
--    tách biệt khỏi reviewer_member_id/reviewed_at (giữ 2 cột cũ làm audit
--    trail lịch sử "ai/khi nào đã CLAIM review" — không xoá, vì xoá sẽ làm mất
--    dấu vết audit rằng migration 30 đã tự gán reviewer sai).
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS legal_review_confirmed boolean NOT NULL DEFAULT false;

-- 2. Hạ cờ xác nhận review pháp lý về false cho đúng các row do migration 30
--    tạo (IDs 210-218) — các row này có content_hash/artifact_path thật, nhưng
--    chưa có luật sư/founder nào xác nhận đã đọc và duyệt đúng predicate.
UPDATE legal.regulation_versions
SET legal_review_confirmed = false
WHERE id IN (210, 211, 212, 213, 214, 215, 216, 217, 218);

-- 3. Hạ review_status của 6 rule do migration 30 tạo từ 'REVIEWED' (claim giả)
--    xuống 'PENDING_REVIEW' — rule engine (Bước 3 sửa cùng migration này) sẽ
--    trả PROFESSIONAL_REVIEW_REQUIRED thay vì tự động BLOCK/CURRENT_LAW cho
--    các rule ở trạng thái này, cho tới khi có review thật.
UPDATE legal.ai_applicability_rules
SET review_status = 'PENDING_REVIEW',
    updated_at = now()
WHERE id IN (301, 302, 303, 304, 305, 306);
