# ADR-AI-COMPLIANCE-RUNTIME-001: Workspace-scoped ownership for AI compliance resources

## Status
ACCEPTED — implemented 2026-08-30 trong `services/company/finance-legal` (governance, snapshot, data-governance, incident-response). Xem `## Verification` để biết trạng thái test.

## Context
Audit bảo mật (2026-08-30, dẫn nhập từ `.superpowers/sdd/2026-08-30-ai-compliance-production-hardening-reconciled/task-1-brief.md`) xác nhận một lớp lỗ hổng cross-workspace IDOR có thật trong runtime AI compliance của `services/company/finance-legal`:

- `ai-compliance-governance.service.ts`: `submitAiAssessment`, `approveAiAssessment`, `suspendAiDeployment`, `resumeAiDeployment`, `getDeployment` chỉ lookup deployment bằng `WHERE id = :id`, không kèm `workspace_id`.
- `ai-compliance-snapshot.service.ts`: `verifySnapshotIntegrity` lookup snapshot chỉ bằng `id`; `captureComplianceSnapshot` khi nhận `deploymentIdInput` từ caller không kiểm tra deployment đó có thuộc `workspaceId` truyền vào hay không.
- `ai-incident-response.service.ts`: `resolveAiIncident` update incident chỉ bằng `id`, không lọc `workspace_id`; `openAiIncident` tự suy ra `workspaceId` từ deployment (nếu caller không truyền) mà không xác nhận quyền truy cập của caller trên deployment đó.
- `ai-data-governance.service.ts`: phần lớn hàm đã đúng (`and(eq(workspaceId, ...))`), ngoại lệ `withdrawProcessingAuthorization` chỉ lookup/update bằng `id`.

Hậu quả: một actor xác thực hợp lệ ở workspace B, biết (hoặc đoán/enumerate) snowflake ID của một resource ở workspace A, có thể đọc trạng thái, duyệt, tạm dừng/khôi phục deployment, xác minh snapshot, đóng incident, hoặc thu hồi authorization xử lý dữ liệu **của workspace khác** — vi phạm trực tiếp ranh giới tenant isolation mà toàn bộ Company Business Plane dựa vào (`requireWorkspaceAccess` chỉ xác thực caller thuộc *một* workspace hợp lệ nào đó, không tự động chặn caller đó thao tác id của workspace khác nếu service không tự lọc lại theo `workspaceId`).

Test hiện có trước khi vá (`ai-compliance-governance.test.ts:212-216`, `returns no deployment from another workspace`) chỉ kiểm chứng list view (`getComplianceCenterView`) — không gọi mutation trực tiếp theo `id`, nên không phát hiện được các lỗ hổng trên. Đây là bài học chính của ADR này: coverage theo "list view" không chứng minh gì về an toàn của "get/mutate theo id".

## Decision

### 1. Bất biến bắt buộc cho mọi resource thuộc AI compliance domain
Mọi đọc và mọi ghi (select initial lookup, update, delete) đối với một resource có `workspace_id` PHẢI dùng:

```ts
type WorkspaceScopedId = {
  workspaceId: string | bigint;
  id: string | bigint;
};
// WHERE id = :id AND workspace_id = :workspaceId — không có ngoại lệ.
```

Một ID hợp lệ nhưng thuộc workspace khác PHẢI trả về response public giống hệt trường hợp ID không tồn tại (`APIError.notFound`, HTTP 404) — không được lộ thông tin phân biệt "tồn tại nhưng không có quyền" so với "không tồn tại" (tránh oracle cho phép enumerate resource của workspace khác).

### 2. workspaceId luôn đến từ TenantContext đã xác thực, không từ request body
Handler public lấy `workspaceId` duy nhất từ `ctx.workspaceId` (kết quả của `requireWorkspaceAccess`), không bao giờ tin `workspaceId` do client gửi kèm trong body để cấp quyền cho một mutation. Tương tự, actor/member ID thực hiện hành động (approver, suspender, resolver...) lấy từ `ctx.workforceMemberId || ctx.userId`, không nhận từ request body khi context đã cung cấp.

### 3. Một điểm triển khai lookup dùng chung, không rải rác theo từng service
Các hàm scoped-lookup dùng chung đặt tại `services/company/finance-legal/services/ai-compliance-access.service.ts` (`getDeploymentInWorkspace`, `getAssessmentInWorkspace`, `getComplianceSnapshotInWorkspace`, `getIncidentInWorkspace`, `getProcessingAuthorizationInWorkspace`). Governance, snapshot, data-governance và incident-response service đều gọi qua đây thay vì tự viết lại điều kiện `and(eq(id), eq(workspaceId))` — tránh một service sau này "trôi" về id-only implementation.

### 4. Constraint lịch sử không tự nới lỏng theo scope mới
Việc thêm `workspaceId` vào input interface là bổ sung điều kiện chặt hơn (deny thêm trường hợp cross-workspace), không thay đổi bất kỳ business rule đã có (Founder approval, statutory block, evidence required, circuit breaker...). Các rule đó vẫn áp dụng nguyên vẹn sau khi resource đã được xác nhận thuộc đúng workspace.

### 5. Không sửa migration đã áp dụng
Các bảng liên quan (`workspace_ai_deployments`, `ai_risk_assessments`, `ai_compliance_snapshots`, `ai_incidents`, `data_processing_authorizations`) đã có sẵn cột `workspace_id` từ migration 27/28. ADR này không yêu cầu migration mới — đây thuần tuý là sửa lỗi logic tầng service/handler TypeScript.

### 6. (Bổ sung từ audit) `ai-incident-response.service.ts` nằm trong cùng đợt vá
Bản kế hoạch gốc chỉ liệt kê governance/snapshot/data-governance; audit xác nhận `resolveAiIncident` và `openAiIncident` có cùng lớp lỗ hổng nên được đưa vào cùng Task 1 thay vì tách task riêng — tách ra sẽ để lại một cửa sổ cross-workspace IDOR đang biết mà chưa vá.

### 7. (Bổ sung từ audit) `withdrawProcessingAuthorization` nằm trong cùng đợt vá
Đây là ngoại lệ duy nhất trong `ai-data-governance.service.ts` — phần còn lại của file đã tuân thủ đúng pattern `and(eq(workspaceId, ...))` từ trước; ADR này chỉ đưa hàm ngoại lệ này về cùng chuẩn, không viết lại các hàm đã đúng.

## Consequences
- Interface `ApproveAiAssessmentInput`, `SuspendAiDeploymentInput`, `ResumeAiDeploymentInput`, `ResolveAiIncidentInput`, `VerifySnapshotRequest`/`verifySnapshotIntegrity`, và `withdrawProcessingAuthorization` đổi chữ ký để nhận `workspaceId` bắt buộc — đây là breaking change nội bộ cho mọi call site (service, handler, test) trong `services/company/finance-legal`; toàn bộ call site đã được cập nhật cùng lúc trong Task 1.
- Không đổi hành vi quan sát được từ phía client hợp lệ (đúng workspace): mọi test hành vi cũ (Founder approval, lifecycle transition, circuit breaker, data governance decisions) phải tiếp tục pass nguyên vẹn.
- Client cố tình truy cập resource của workspace khác nhận `404 Not Found` giống hệt trường hợp ID không tồn tại — không có `403`/`permissionDenied` riêng biệt để tránh lộ oracle tồn tại.

## Verification
- Test mới: `services/company/finance-legal/tests/ai-compliance-workspace-access.test.ts` — hostile-workspace case cho `suspendAiDeployment`, `verifySnapshotIntegrity`, `resolveAiIncident`, `withdrawProcessingAuthorization`.
- Test hiện có: `ai-compliance-governance.test.ts`, `ai-compliance-snapshot.test.ts`, `ai-data-governance.test.ts`, `ai-incident-response.test.ts`, `ai-incident.test.ts` — cập nhật call site để truyền `workspaceId`, giữ nguyên assertion hành vi gốc.
- Chạy: `cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-governance.test.ts finance-legal/tests/ai-compliance-workspace-access.test.ts finance-legal/tests/ai-data-governance.test.ts finance-legal/tests/ai-compliance-snapshot.test.ts finance-legal/tests/ai-incident-response.test.ts finance-legal/tests/ai-incident.test.ts`.
- Kết quả chi tiết (pass/fail count, ngày chạy) ghi tại `task-1-report.md` cùng thư mục brief này, không lặp lại ở đây để tránh hai nguồn sự thật lệch nhau theo thời gian.
