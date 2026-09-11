export interface PermissionDefinition {
  permissionKey: string;
  domain: string;
  description: string;
}

export type StrategyGovernancePermission =
  | "strategy.framework.manage"
  | "strategy.okr.publish"
  | "strategy.initiative.approve"
  | "strategy.review.close"
  | "strategy.agent.configure";

export const PERMISSION_CATALOG: readonly PermissionDefinition[] = [
  { permissionKey: "permissions.read", domain: "identity", description: "Xem danh mục và phân quyền" },
  { permissionKey: "permissions.manage", domain: "identity", description: "Cấu hình vai trò và gán quyền" },
  { permissionKey: "agent.policy.manage", domain: "agent", description: "Quản lý chính sách và giới hạn của agent" },
  { permissionKey: "agent.sweep.manage", domain: "agent", description: "Bật tắt và cấu hình task sweep của agent" },
  { permissionKey: "execution.plan.approve", domain: "operations", description: "Duyệt execution plan thành task" },
  { permissionKey: "operations.task.read", domain: "operations", description: "Xem thông tin và danh sách nhiệm vụ" },
  { permissionKey: "strategy.read", domain: "operations", description: "Xem thông tin chiến lược và OKR" },
  { permissionKey: "strategy.write", domain: "operations", description: "Tạo và cập nhật sáng kiến chiến lược" },
  { permissionKey: "strategy.target.manage", domain: "operations", description: "Quản lý chỉ tiêu mục tiêu tuần và quý" },
  { permissionKey: "strategy.transition", domain: "operations", description: "Chuyển đổi stage và trạng thái chiến lược" },
  { permissionKey: "strategy.framework.manage", domain: "operations", description: "Cấu hình khung chiến lược và policy workspace" },
  { permissionKey: "strategy.okr.publish", domain: "operations", description: "Công bố mục tiêu chiến lược và OKRs" },
  { permissionKey: "strategy.initiative.approve", domain: "operations", description: "Phê duyệt sáng kiến chiến lược" },
  { permissionKey: "strategy.review.close", domain: "operations", description: "Chốt đánh giá chu kỳ và review chiến lược" },
  { permissionKey: "strategy.agent.configure", domain: "operations", description: "Cấu hình và phân quyền agent chiến lược" },
  { permissionKey: "finance.read", domain: "finance", description: "Xem dữ liệu sổ sách tài chính" },
  { permissionKey: "finance.transaction.record", domain: "finance", description: "Ghi nhận giao dịch tài chính (thu/chi) vào sổ sách" },
  { permissionKey: "finance.request.create", domain: "finance", description: "Tạo đề nghị chi / thanh toán" },
  { permissionKey: "finance.request.approve", domain: "finance", description: "Phê duyệt đề nghị chi / thanh toán" },
  { permissionKey: "finance.reconcile", domain: "finance", description: "Đối soát giao dịch ngân hàng" },
  { permissionKey: "finance.period.close", domain: "finance", description: "Đóng kỳ kế toán" },
  { permissionKey: "finance.report.read", domain: "finance", description: "Xem báo cáo tài chính và snapshot" },
  { permissionKey: "legal.read", domain: "legal", description: "Xem danh mục pháp lý và nghĩa vụ" },
  { permissionKey: "legal.obligation.manage", domain: "legal", description: "Cập nhật và xử lý nghĩa vụ pháp lý" },
  { permissionKey: "ai.deployment.create", domain: "ai", description: "Khởi tạo AI deployment" },
  { permissionKey: "ai.deployment.review", domain: "ai", description: "Đánh giá rủi ro AI deployment" },
  { permissionKey: "ai.deployment.approve", domain: "ai", description: "Phê duyệt kích hoạt AI deployment" },
];

export const VALID_PERMISSION_KEYS = new Set(PERMISSION_CATALOG.map((p) => p.permissionKey));

export function isKnownPermission(key: string): boolean {
  return VALID_PERMISSION_KEYS.has(key);
}
