-- services/company/finance-legal/migrations/28_ai_compliance_legal_sources.up.sql
-- Seed official AI and personal data regulation sources and versions

-- 1. Luật Trí tuệ nhân tạo 134/2025/QH15 (CURRENT_LAW)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  10,
  'Luật Trí tuệ nhân tạo',
  'Quốc hội',
  '134/2025/QH15',
  'https://vanban.chinhphu.vn/?docid=216334&pageid=27160&typegroupid=3',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'CURRENT_LAW',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  110,
  10,
  '2026',
  '2026-03-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 2. Nghị định 142/2026/NĐ-CP (CURRENT_LAW)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  11,
  'Nghị định quy định chi tiết một số điều của Luật Trí tuệ nhân tạo về quản lý rủi ro',
  'Chính phủ',
  '142/2026/NĐ-CP',
  'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/142-2026-ndcp.signed.pdf',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'CURRENT_LAW',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  111,
  11,
  '2026',
  '2026-04-15',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 3. Quyết định 33/2026/QĐ-TTg (CURRENT_LAW)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  12,
  'Quyết định ban hành Danh mục hệ thống trí tuệ nhân tạo có độ rủi ro cao',
  'Thủ tướng Chính phủ',
  '33/2026/QĐ-TTg',
  'https://congbao.chinhphu.vn/van-ban/quyet-dinh-so-33-2026-qd-ttg-469951.htm',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'CURRENT_LAW',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  112,
  12,
  '2026',
  '2026-05-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 4. Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 (CURRENT_LAW)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  13,
  'Luật Bảo vệ dữ liệu cá nhân',
  'Quốc hội',
  '91/2025/QH15',
  'https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'CURRENT_LAW',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  113,
  13,
  '2025',
  '2026-01-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 5. Thông tư 05/2026/TT-BKHCN (CURRENT_LAW)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  14,
  'Thông tư quy định về các nguyên tắc, chuẩn mực đạo đức trong nghiên cứu, phát triển và sử dụng trí tuệ nhân tạo',
  'Bộ Khoa học và Công nghệ',
  '05/2026/TT-BKHCN',
  'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/05-bkhcn.pdf',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'CURRENT_LAW',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  114,
  14,
  '2026',
  '2026-04-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 6. Quyết định 804/QĐ-TTg (POLICY_WATCH)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  15,
  'Quyết định phê duyệt Chiến lược quốc gia về nghiên cứu, phát triển và ứng dụng Trí tuệ nhân tạo',
  'Thủ tướng Chính phủ',
  '804/QĐ-TTg',
  'https://vanban.chinhphu.vn/?pageid=27160&docid=208123',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'POLICY_WATCH',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  115,
  15,
  '2025',
  '2025-06-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 7. Quyết định 367/QĐ-TTg (POLICY_WATCH)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  16,
  'Quyết định về định hướng chuyển đổi số và ứng dụng công nghệ mới',
  'Thủ tướng Chính phủ',
  '367/QĐ-TTg',
  'https://vanban.chinhphu.vn/?pageid=27160&docid=209456',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'POLICY_WATCH',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  116,
  16,
  '2025',
  '2025-04-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 8. Quyết định 1528/QĐ-TTg (POLICY_WATCH)
INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES (
  17,
  'Quyết định ban hành Kế hoạch hành động triển khai chiến lược quốc gia về dữ liệu',
  'Thủ tướng Chính phủ',
  '1528/QĐ-TTg',
  'https://vanban.chinhphu.vn/?pageid=27160&docid=210789',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  'POLICY_WATCH',
  now(),
  now()
) ON CONFLICT (number) DO UPDATE SET
  layer = EXCLUDED.layer,
  url = EXCLUDED.url,
  updated_at = now();

INSERT INTO legal.regulation_versions (id, regulation_source_id, version, effective_from, effective_to, superseded_by_id, created_at)
VALUES (
  117,
  17,
  '2025',
  '2025-10-01',
  NULL,
  NULL,
  now()
) ON CONFLICT (regulation_source_id, version) DO NOTHING;

-- 9. Nghị quyết 86/NQ-CP (POLICY_WATCH - đã có thể được insert ở migration 14, đảm bảo đúng layer)
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
) ON CONFLICT (number) DO UPDATE SET
  layer = 'POLICY_WATCH',
  updated_at = now();
