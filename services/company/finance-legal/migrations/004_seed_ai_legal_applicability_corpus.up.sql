-- services/company/finance-legal/migrations/004_seed_ai_legal_applicability_corpus.up.sql
--
-- Baseline gap (Task 5F, epic 2026-09-10-baseline-completeness-harness-health):
-- squash R1 `001` giữ lại CẤU TRÚC `legal.regulation_sources` /
-- `legal.regulation_versions` / `legal.ai_applicability_rules` (đã khôi phục ở
-- `002_restore_baseline_gaps`), nhưng KHÔNG giữ lại NỘI DUNG corpus pháp lý mà
-- các migration tiền-squash 28 → 30 → 31 đã seed.
--
-- Hệ quả thật (fail-closed, không phải fail-open): `fetchActiveExecutableRules()`
-- trả mảng rỗng → `assessAiApplicability()` đi vào nhánh `rules.length === 0`
-- → luôn phát `PROFESSIONAL_REVIEW_REQUIRED` → `ai-compliance-snapshot.service.ts`
-- fail mọi `resolve-snapshot` với `LEGAL_REVIEW_PENDING`. Nghĩa là KHÔNG agent run
-- nào có thể tới model trên một DB baseline sạch.
--
-- Test buộc phải có migration này:
--   tests/e2e/test_ai_compliance_company_http.py::test_approved_run_reaches_company_then_model_once
--     (assert `RunStatus.COMPLETED`; trước seed này nhận `FAILED` kèm
--      "Deployment requires human legal review before runtime approval:
--       PROFESSIONAL_REVIEW_REQUIRED")
--
-- Nội dung dưới đây là TRẠNG THÁI CUỐI của corpus tiền-squash, chép nguyên văn
-- (không bịa thêm dữ liệu mới):
--   - `28_ai_compliance_legal_sources.up.sql` — 9 nguồn luật + version
--   - `30_ai_legal_source_corrections.up.sql` — SHA-256 THẬT của bản PDF công báo,
--     9 version "verified" (id 210-218, status ACTIVE) + 6 rule (id 301-306)
--   - `31_ai_legal_review_pending_correction.up.sql` — hạ 6 rule về
--     `review_status = 'PENDING_REVIEW'` và `legal_review_confirmed = false`,
--     vì migration 30 đã tự gán reviewer giả (`reviewer_member_id = 1`) mà không
--     có luật sư thật xác nhận. Trạng thái PENDING_REVIEW được giữ nguyên ở đây —
--     KHÔNG nâng lên 'REVIEWED' để test xanh; rule engine đọc đúng trạng thái này
--     và vẫn phát PROFESSIONAL_REVIEW_REQUIRED khi predicate khớp.
--   - Các row placeholder empty-hash id 110-117 (migration 28) mà migration 30 đã
--     đánh `INACTIVE_CORRECTION` thì KHÔNG seed lại — chúng chỉ là dấu vết sửa lỗi
--     của corpus cũ, không phải dữ liệu pháp lý.
--
-- Seed = dữ liệu, không phải cấu trúc → migration riêng, không gộp vào
-- `restore_baseline_gaps`. Expand-only + idempotent (upsert theo khoá tự nhiên).

-- ─── 1. Nguồn quy phạm pháp luật (content_hash = SHA-256 thật của PDF công báo) ───

INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES
  (10, 'Luật Trí tuệ nhân tạo', 'Quốc hội', '134/2025/QH15',
   'https://vanban.chinhphu.vn/?docid=216334&pageid=27160&typegroupid=3',
   '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69', 'CURRENT_LAW', now(), now()),
  (11, 'Nghị định quy định chi tiết một số điều và biện pháp thi hành Luật Trí tuệ nhân tạo', 'Chính phủ', '142/2026/NĐ-CP',
   'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/142-2026-ndcp.signed.pdf',
   '988fa7091b9f70615b8ae984e7e43b15293eb31398a113c86cc34f26666d5e40', 'CURRENT_LAW', now(), now()),
  (12, 'Quyết định ban hành Danh mục hệ thống trí tuệ nhân tạo có rủi ro cao', 'Thủ tướng Chính phủ', '33/2026/QĐ-TTg',
   'https://congbao.chinhphu.vn/van-ban/quyet-dinh-so-33-2026-qd-ttg-469951.htm',
   'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b', 'CURRENT_LAW', now(), now()),
  (13, 'Luật Bảo vệ dữ liệu cá nhân', 'Quốc hội', '91/2025/QH15',
   'https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=',
   'c3b87f994cedcedb69d38c590dcca2bb7700aab65e518a2a3a5ffbf22048b9ee', 'CURRENT_LAW', now(), now()),
  (14, 'Thông tư ban hành Khung đạo đức trí tuệ nhân tạo quốc gia', 'Bộ Khoa học và Công nghệ', '05/2026/TT-BKHCN',
   'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/05-bkhcn.pdf',
   '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220', 'CURRENT_LAW', now(), now()),
  (15, 'Quyết định ban hành Danh mục bộ dữ liệu phục vụ phát triển trí tuệ nhân tạo trong các lĩnh vực thiết yếu', 'Thủ tướng Chính phủ', '804/QĐ-TTg',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=208123',
   '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c', 'POLICY_WATCH', now(), now()),
  (16, 'Quyết định ban hành Kế hoạch triển khai thi hành Luật Trí tuệ nhân tạo', 'Thủ tướng Chính phủ', '367/QĐ-TTg',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=209456',
   '5cc8e35e58807295dae65fd46abc624334391b8bcf2fd35be9357256439c37af', 'POLICY_WATCH', now(), now()),
  (17, 'Quyết định phê duyệt Chương trình quốc gia phát triển nhân lực trí tuệ nhân tạo đến năm 2030, định hướng đến năm 2035', 'Thủ tướng Chính phủ', '1528/QĐ-TTg',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=210789',
   '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f', 'POLICY_WATCH', now(), now()),
  (2,  'Nghị quyết ban hành Chiến lược quốc gia về khởi nghiệp sáng tạo', 'Chính phủ', '86/NQ-CP',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=217558',
   '1e5208ca0a51c9ac7169c05a5186933a732204efd155f3ec66c1d8766b2bd476', 'POLICY_WATCH', now(), now())
ON CONFLICT (number) DO UPDATE SET
  source_name = EXCLUDED.source_name,
  issuer = EXCLUDED.issuer,
  url = EXCLUDED.url,
  content_hash = EXCLUDED.content_hash,
  layer = EXCLUDED.layer,
  updated_at = now();

-- ─── 2. Phiên bản đã xác minh document identity (SHA-256 + artifact ký số) ───
-- `legal_review_confirmed = false`: document identity là thật, nhưng CHƯA có
-- luật sư/founder xác nhận đã đọc và duyệt predicate (migration 31).

INSERT INTO legal.regulation_versions (
  id, regulation_source_id, version, effective_from, effective_to, superseded_by_id,
  status, content_hash, artifact_path, reviewer_member_id, reviewed_at,
  legal_review_confirmed, created_at
) VALUES
  (210, 10, '2026-verified', '2026-03-01', NULL, NULL, 'ACTIVE', '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69', 'vb-ai/luat134.signed.pdf', NULL, NULL, false, now()),
  (211, 11, '2026-verified', '2026-05-01', NULL, NULL, 'ACTIVE', '988fa7091b9f70615b8ae984e7e43b15293eb31398a113c86cc34f26666d5e40', 'vb-ai/142-2026-ndcp.signed.pdf', NULL, NULL, false, now()),
  (212, 12, '2026-verified', '2026-08-15', NULL, NULL, 'ACTIVE', 'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b', 'vb-ai/33-qdttg.signed.pdf', NULL, NULL, false, now()),
  (213, 13, '2025-verified', '2026-01-01', NULL, NULL, 'ACTIVE', 'c3b87f994cedcedb69d38c590dcca2bb7700aab65e518a2a3a5ffbf22048b9ee', 'vb-ai/91qh.signed.pdf', NULL, NULL, false, now()),
  (214, 14, '2026-verified', '2026-03-10', NULL, NULL, 'ACTIVE', '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220', 'vb-ai/05-bkhcn.pdf', NULL, NULL, false, now()),
  (215, 15, '2026-verified', '2026-05-06', NULL, NULL, 'ACTIVE', '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c', 'vb-ai/804-ttg.signed.pdf', NULL, NULL, false, now()),
  (216, 16, '2026-verified', '2026-02-28', NULL, NULL, 'ACTIVE', '5cc8e35e58807295dae65fd46abc624334391b8bcf2fd35be9357256439c37af', 'vb-ai/367-ttg.signed.pdf', NULL, NULL, false, now()),
  (217, 17, '2026-verified', '2026-08-11', NULL, NULL, 'ACTIVE', '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f', 'vb-ai/1528_qd-ttg_11082026-signed.signed.pdf', NULL, NULL, false, now()),
  (218, 2,  '2026-verified', '2026-04-05', NULL, NULL, 'ACTIVE', '1e5208ca0a51c9ac7169c05a5186933a732204efd155f3ec66c1d8766b2bd476', 'vb-ai/86-nqcp.signed.pdf', NULL, NULL, false, now())
ON CONFLICT (regulation_source_id, version) DO UPDATE SET
  effective_from = EXCLUDED.effective_from,
  status = EXCLUDED.status,
  content_hash = EXCLUDED.content_hash,
  artifact_path = EXCLUDED.artifact_path,
  legal_review_confirmed = EXCLUDED.legal_review_confirmed;

-- ─── 3. Quy tắc áp dụng AI (review_status = 'PENDING_REVIEW' theo migration 31) ───

INSERT INTO legal.ai_applicability_rules (
  id, rule_id, rule_version, regulation_source_id, regulation_version_id, source_content_hash,
  effective_from, effective_to, review_status, layer, effect, reason_code, description,
  predicate, mandatory_evidence_type, created_at, updated_at
) VALUES
  (301, 'STATUTORY_MODE_ADVISORY', '1.0.0', 10, 210,
   '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69',
   '2026-03-01', NULL, 'PENDING_REVIEW', 'CURRENT_LAW', 'BLOCK', 'NON_ADVISORY_MODE',
   'COSA chỉ cho phép triển khai chế độ ADVISORY_ONLY phục vụ doanh nghiệp tư nhân theo Luật AI 134/2025/QH15',
   '{"deploymentModeNotEquals": "ADVISORY_ONLY"}'::jsonb, 'LEGAL_ASSESSMENT', now(), now()),
  (302, 'STATUTORY_PROHIBITED_DOMAINS', '1.0.0', 12, 212,
   'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b',
   '2026-08-15', NULL, 'PENDING_REVIEW', 'CURRENT_LAW', 'BLOCK', 'PROHIBITED_DECISION_DOMAIN',
   'Cấm quyết định tự động không có con người giám sát trong các lĩnh vực có rủi ro cao theo Quyết định 33/2026/QĐ-TTg',
   '{"isProhibitedDomain": true}'::jsonb, 'HIGH_RISK_CONFORMITY_CERTIFICATE', now(), now()),
  (303, 'STATUTORY_PROVIDER_APPROVED', '1.0.0', 14, 214,
   '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220',
   '2026-03-10', NULL, 'PENDING_REVIEW', 'CURRENT_LAW', 'BLOCK', 'PROVIDER_NOT_APPROVED',
   'Nhà cung cấp mô hình phải có hồ sơ APPROVED tuân thủ Khung đạo đức AI quốc gia theo Thông tư 05/2026/TT-BKHCN',
   '{"providerProfileStatusNotEquals": "APPROVED"}'::jsonb, 'PROVIDER_COMPLIANCE_REVIEW', now(), now()),
  (304, 'STATUTORY_LEGAL_PROFESSIONAL_REVIEW', '1.0.0', 10, 210,
   '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69',
   '2026-03-01', NULL, 'PENDING_REVIEW', 'PROFESSIONAL_REVIEW', 'REVIEW', 'PROFESSIONAL_LEGAL_REVIEW_REQUIRED',
   'Nghiệp vụ tư vấn pháp lý có tranh chấp, tố tụng cần luật sư/chuyên gia rà soát',
   '{"decisionDomain": "LEGAL", "purposeKeywords": ["litigation", "dispute", "tranh chấp", "khởi kiện", "tố tụng"]}'::jsonb, NULL, now(), now()),
  (305, 'POLICY_WATCH_QD804', '1.0.0', 15, 215,
   '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c',
   '2026-05-06', NULL, 'PENDING_REVIEW', 'POLICY_WATCH', 'NOTICE', 'POLICY_WATCH_AI_DATA_CATALOG_804',
   'Theo dõi Danh mục bộ dữ liệu phục vụ phát triển AI thiết yếu theo Quyết định 804/QĐ-TTg',
   '{"alwaysNotice": true}'::jsonb, NULL, now(), now()),
  (306, 'POLICY_WATCH_QD1528', '1.0.0', 17, 217,
   '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f',
   '2026-08-11', NULL, 'PENDING_REVIEW', 'POLICY_WATCH', 'NOTICE', 'POLICY_WATCH_AI_HUMAN_RESOURCES_1528',
   'Theo dõi Chương trình quốc gia phát triển nhân lực AI theo Quyết định 1528/QĐ-TTg',
   '{"alwaysNotice": true}'::jsonb, NULL, now(), now())
ON CONFLICT (rule_id) DO UPDATE SET
  regulation_source_id = EXCLUDED.regulation_source_id,
  regulation_version_id = EXCLUDED.regulation_version_id,
  source_content_hash = EXCLUDED.source_content_hash,
  effective_from = EXCLUDED.effective_from,
  review_status = EXCLUDED.review_status,
  layer = EXCLUDED.layer,
  effect = EXCLUDED.effect,
  reason_code = EXCLUDED.reason_code,
  description = EXCLUDED.description,
  predicate = EXCLUDED.predicate,
  mandatory_evidence_type = EXCLUDED.mandatory_evidence_type,
  updated_at = now();
