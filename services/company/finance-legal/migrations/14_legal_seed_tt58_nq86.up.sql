-- services/company/finance-legal/migrations/14_legal_seed_tt58_nq86.up.sql
-- Seed initial regulation catalog entries: TT58/2026 (CURRENT_LAW) and NQ86 (POLICY_WATCH)

-- Source 1: 58/2026/TT-BTC
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  1,
  'Thông tư hướng dẫn chế độ kế toán cho doanh nghiệp siêu nhỏ',
  'Bộ Tài chính',
  '58/2026/TT-BTC',
  'https://congbao.chinhphu.vn/58-2026-tt-btc',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'CURRENT_LAW',
  now(),
  now()
) ON CONFLICT (number) DO NOTHING;

-- Version 1 of Source 1
INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  101,
  1,
  '2026',
  '2026-07-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- Obligation Template for TT58
INSERT INTO legal.legal_obligation_templates (id, regulation_version_id, title, description, typical_due_offset_days, created_at)
VALUES (
  201,
  101,
  'Nộp báo cáo tài chính năm theo TT58',
  'Lập và nộp BCTC theo biểu mẫu rút gọn cho doanh nghiệp siêu nhỏ',
  90,
  now()
) ON CONFLICT DO NOTHING;

-- Applicability rule for TT58 obligation
INSERT INTO legal.applicability_rules (id, regulation_version_id, predicate, obligation_template_id, created_at)
VALUES (
  301,
  101,
  '{"entity_status": "REGISTERED_VERIFIED", "condition_field": "accounting_regime", "condition_value": "TT58_2026"}'::jsonb,
  201,
  now()
) ON CONFLICT DO NOTHING;

-- Source 2: 86/NQ-CP (POLICY_WATCH - không kèm obligation template)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  2,
  'Nghị quyết phiên họp Chính phủ chuyên đề về xây dựng pháp luật',
  'Chính phủ',
  '86/NQ-CP',
  'https://vanban.chinhphu.vn/?pageid=27160&docid=217558',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'POLICY_WATCH',
  now(),
  now()
) ON CONFLICT (number) DO NOTHING;

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  102,
  2,
  '2026',
  '2026-04-05',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;
