-- services/company/finance-legal/migrations/30_ai_legal_source_corrections.up.sql
-- Migration 30: AI Legal Source Corrections and Decision-Grade Provenance

-- 1. Thêm các cột thẩm định và provenance vào legal.regulation_versions
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'ACTIVE',
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS correction_reason text,
  ADD COLUMN IF NOT EXISTS artifact_path text,
  ADD COLUMN IF NOT EXISTS reviewer_member_id bigint,
  ADD COLUMN IF NOT EXISTS reviewed_at timestamp with time zone;

-- 2. Thêm các cột kết luận và nguồn vào legal.ai_compliance_evidence
ALTER TABLE legal.ai_compliance_evidence
  ADD COLUMN IF NOT EXISTS conclusion text NOT NULL DEFAULT 'COMPLIANT',
  ADD COLUMN IF NOT EXISTS source_version_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS rule_ids jsonb NOT NULL DEFAULT '[]'::jsonb;

-- 3. Tạo bảng quy tắc áp dụng AI chính quy gắn với nguồn luật đã thẩm định (ai_applicability_rules)
CREATE TABLE IF NOT EXISTS legal.ai_applicability_rules (
  id bigint PRIMARY KEY,
  rule_id text NOT NULL UNIQUE,
  rule_version text NOT NULL DEFAULT '1.0.0',
  regulation_source_id bigint NOT NULL REFERENCES legal.regulation_sources(id) ON DELETE CASCADE,
  regulation_version_id bigint NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  source_content_hash text NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  review_status text NOT NULL DEFAULT 'REVIEWED',
  layer text NOT NULL,
  effect text NOT NULL,
  reason_code text NOT NULL,
  description text,
  predicate jsonb NOT NULL,
  mandatory_evidence_type text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 4. Bất hoạt các bản ghi seed sai / placeholder empty hash tại Migration 28 (IDs 110-117)
UPDATE legal.regulation_versions
SET status = 'INACTIVE_CORRECTION',
    correction_reason = 'Placeholder empty hash and unverified metadata from seed 28; superseded by migration 30 certified gazette artifacts'
WHERE id IN (110, 111, 112, 113, 114, 115, 116, 117);

-- 5. Cập nhật thông tin chính xác và SHA-256 thật cho legal.regulation_sources
UPDATE legal.regulation_sources
SET source_name = 'Luật Trí tuệ nhân tạo',
    content_hash = '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69',
    updated_at = now()
WHERE id = 10;

UPDATE legal.regulation_sources
SET source_name = 'Nghị định quy định chi tiết một số điều và biện pháp thi hành Luật Trí tuệ nhân tạo',
    content_hash = '988fa7091b9f70615b8ae984e7e43b15293eb31398a113c86cc34f26666d5e40',
    updated_at = now()
WHERE id = 11;

UPDATE legal.regulation_sources
SET source_name = 'Quyết định ban hành Danh mục hệ thống trí tuệ nhân tạo có rủi ro cao',
    content_hash = 'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b',
    updated_at = now()
WHERE id = 12;

UPDATE legal.regulation_sources
SET source_name = 'Luật Bảo vệ dữ liệu cá nhân',
    content_hash = 'c3b87f994cedcedb69d38c590dcca2bb7700aab65e518a2a3a5ffbf22048b9ee',
    updated_at = now()
WHERE id = 13;

UPDATE legal.regulation_sources
SET source_name = 'Thông tư ban hành Khung đạo đức trí tuệ nhân tạo quốc gia',
    content_hash = '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220',
    updated_at = now()
WHERE id = 14;

UPDATE legal.regulation_sources
SET source_name = 'Quyết định ban hành Danh mục bộ dữ liệu phục vụ phát triển trí tuệ nhân tạo trong các lĩnh vực thiết yếu',
    content_hash = '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c',
    updated_at = now()
WHERE id = 15;

UPDATE legal.regulation_sources
SET source_name = 'Quyết định ban hành Kế hoạch triển khai thi hành Luật Trí tuệ nhân tạo',
    content_hash = '5cc8e35e58807295dae65fd46abc624334391b8bcf2fd35be9357256439c37af',
    updated_at = now()
WHERE id = 16;

UPDATE legal.regulation_sources
SET source_name = 'Quyết định phê duyệt Chương trình quốc gia phát triển nhân lực trí tuệ nhân tạo đến năm 2030, định hướng đến năm 2035',
    content_hash = '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f',
    updated_at = now()
WHERE id = 17;

UPDATE legal.regulation_sources
SET source_name = 'Nghị quyết ban hành Chiến lược quốc gia về khởi nghiệp sáng tạo',
    content_hash = '1e5208ca0a51c9ac7169c05a5186933a732204efd155f3ec66c1d8766b2bd476',
    updated_at = now()
WHERE id = 2;

-- 6. Chèn các phiên bản quy phạm pháp luật VERIFIED mới (IDs 210-218)
INSERT INTO legal.regulation_versions (
  id, regulation_source_id, version, effective_from, effective_to, superseded_by_id,
  status, content_hash, artifact_path, reviewer_member_id, reviewed_at, created_at
) VALUES
  (210, 10, '2026-verified', '2026-03-01', NULL, NULL, 'ACTIVE', '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69', 'vb-ai/luat134.signed.pdf', 1, now(), now()),
  (211, 11, '2026-verified', '2026-05-01', NULL, NULL, 'ACTIVE', '988fa7091b9f70615b8ae984e7e43b15293eb31398a113c86cc34f26666d5e40', 'vb-ai/142-2026-ndcp.signed.pdf', 1, now(), now()),
  (212, 12, '2026-verified', '2026-08-15', NULL, NULL, 'ACTIVE', 'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b', 'vb-ai/33-qdttg.signed.pdf', 1, now(), now()),
  (213, 13, '2025-verified', '2026-01-01', NULL, NULL, 'ACTIVE', 'c3b87f994cedcedb69d38c590dcca2bb7700aab65e518a2a3a5ffbf22048b9ee', 'vb-ai/91qh.signed.pdf', 1, now(), now()),
  (214, 14, '2026-verified', '2026-03-10', NULL, NULL, 'ACTIVE', '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220', 'vb-ai/05-bkhcn.pdf', 1, now(), now()),
  (215, 15, '2026-verified', '2026-05-06', NULL, NULL, 'ACTIVE', '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c', 'vb-ai/804-ttg.signed.pdf', 1, now(), now()),
  (216, 16, '2026-verified', '2026-02-28', NULL, NULL, 'ACTIVE', '5cc8e35e58807295dae65fd46abc624334391b8bcf2fd35be9357256439c37af', 'vb-ai/367-ttg.signed.pdf', 1, now(), now()),
  (217, 17, '2026-verified', '2026-08-11', NULL, NULL, 'ACTIVE', '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f', 'vb-ai/1528_qd-ttg_11082026-signed.signed.pdf', 1, now(), now()),
  (218, 2,  '2026-verified', '2026-04-05', NULL, NULL, 'ACTIVE', '1e5208ca0a51c9ac7169c05a5186933a732204efd155f3ec66c1d8766b2bd476', 'vb-ai/86-nqcp.signed.pdf', 1, now(), now())
ON CONFLICT (regulation_source_id, version) DO UPDATE SET
  effective_from = EXCLUDED.effective_from,
  content_hash = EXCLUDED.content_hash,
  artifact_path = EXCLUDED.artifact_path,
  status = EXCLUDED.status,
  reviewer_member_id = EXCLUDED.reviewer_member_id,
  reviewed_at = EXCLUDED.reviewed_at;

-- 7. Seed các quy tắc áp dụng AI khả thi (ai_applicability_rules) gắn chặt với nguồn đã thẩm định
INSERT INTO legal.ai_applicability_rules (
  id, rule_id, rule_version, regulation_source_id, regulation_version_id, source_content_hash,
  effective_from, effective_to, review_status, layer, effect, reason_code, description,
  predicate, mandatory_evidence_type, created_at, updated_at
) VALUES
  (
    301,
    'STATUTORY_MODE_ADVISORY',
    '1.0.0',
    10,
    210,
    '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69',
    '2026-03-01',
    NULL,
    'REVIEWED',
    'CURRENT_LAW',
    'BLOCK',
    'NON_ADVISORY_MODE',
    'COSA chỉ cho phép triển khai chế độ ADVISORY_ONLY phục vụ doanh nghiệp tư nhân theo Luật AI 134/2025/QH15',
    '{"deploymentModeNotEquals": "ADVISORY_ONLY"}'::jsonb,
    'LEGAL_ASSESSMENT',
    now(),
    now()
  ),
  (
    302,
    'STATUTORY_PROHIBITED_DOMAINS',
    '1.0.0',
    12,
    212,
    'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b',
    '2026-08-15',
    NULL,
    'REVIEWED',
    'CURRENT_LAW',
    'BLOCK',
    'PROHIBITED_DECISION_DOMAIN',
    'Cấm quyết định tự động không có con người giám sát trong các lĩnh vực có rủi ro cao theo Quyết định 33/2026/QĐ-TTg',
    '{"isProhibitedDomain": true}'::jsonb,
    'HIGH_RISK_CONFORMITY_CERTIFICATE',
    now(),
    now()
  ),
  (
    303,
    'STATUTORY_PROVIDER_APPROVED',
    '1.0.0',
    14,
    214,
    '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220',
    '2026-03-10',
    NULL,
    'REVIEWED',
    'CURRENT_LAW',
    'BLOCK',
    'PROVIDER_NOT_APPROVED',
    'Nhà cung cấp mô hình phải có hồ sơ APPROVED tuân thủ Khung đạo đức AI quốc gia theo Thông tư 05/2026/TT-BKHCN',
    '{"providerProfileStatusNotEquals": "APPROVED"}'::jsonb,
    'PROVIDER_COMPLIANCE_REVIEW',
    now(),
    now()
  ),
  (
    304,
    'STATUTORY_LEGAL_PROFESSIONAL_REVIEW',
    '1.0.0',
    10,
    210,
    '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69',
    '2026-03-01',
    NULL,
    'REVIEWED',
    'PROFESSIONAL_REVIEW',
    'REVIEW',
    'PROFESSIONAL_LEGAL_REVIEW_REQUIRED',
    'Nghiệp vụ tư vấn pháp lý có tranh chấp, tố tụng cần luật sư/chuyên gia rà soát',
    '{"decisionDomain": "LEGAL", "purposeKeywords": ["litigation", "dispute", "tranh chấp", "khởi kiện", "tố tụng"]}'::jsonb,
    NULL,
    now(),
    now()
  ),
  (
    305,
    'POLICY_WATCH_QD804',
    '1.0.0',
    15,
    215,
    '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c',
    '2026-05-06',
    NULL,
    'REVIEWED',
    'POLICY_WATCH',
    'NOTICE',
    'POLICY_WATCH_AI_DATA_CATALOG_804',
    'Theo dõi Danh mục bộ dữ liệu phục vụ phát triển AI thiết yếu theo Quyết định 804/QĐ-TTg',
    '{"alwaysNotice": true}'::jsonb,
    NULL,
    now(),
    now()
  ),
  (
    306,
    'POLICY_WATCH_QD1528',
    '1.0.0',
    17,
    217,
    '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f',
    '2026-08-11',
    NULL,
    'REVIEWED',
    'POLICY_WATCH',
    'NOTICE',
    'POLICY_WATCH_AI_HUMAN_RESOURCES_1528',
    'Theo dõi Chương trình quốc gia phát triển nhân lực AI theo Quyết định 1528/QĐ-TTg',
    '{"alwaysNotice": true}'::jsonb,
    NULL,
    now(),
    now()
  )
ON CONFLICT (rule_id) DO UPDATE SET
  regulation_version_id = EXCLUDED.regulation_version_id,
  source_content_hash = EXCLUDED.source_content_hash,
  effective_from = EXCLUDED.effective_from,
  review_status = EXCLUDED.review_status,
  predicate = EXCLUDED.predicate,
  mandatory_evidence_type = EXCLUDED.mandatory_evidence_type,
  updated_at = now();
