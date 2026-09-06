-- Migration 10: Strategy governance permission definitions

INSERT INTO core.permission_definitions (permission_key, domain, description) VALUES
  ('strategy.framework.manage', 'operations', 'Cấu hình khung chiến lược và policy workspace'),
  ('strategy.analysis.write', 'operations', 'Tạo và cập nhật phân tích PESTEL, nguồn lực và SWOT'),
  ('strategy.option.select', 'operations', 'Đánh giá và chọn chiến lược TOWS'),
  ('strategy.okr.publish', 'operations', 'Công bố mục tiêu chiến lược và OKRs'),
  ('strategy.initiative.approve', 'operations', 'Phê duyệt sáng kiến chiến lược'),
  ('strategy.review.close', 'operations', 'Chốt đánh giá chu kỳ và review chiến lược'),
  ('strategy.agent.configure', 'operations', 'Cấu hình và phân quyền agent chiến lược')
ON CONFLICT (permission_key) DO NOTHING;
