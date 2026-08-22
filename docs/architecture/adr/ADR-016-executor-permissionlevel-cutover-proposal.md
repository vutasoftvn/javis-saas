# ADR-016 (Proposal): Cutover Executor/tool binding sang `PermissionLevel` (ADR-014 bước 2)

## Status

**Proposal — chờ quyết định.** Không phải quyết định đã chốt như ADR-013/014/015. Tài liệu này phân tích các phương án và đề xuất 1 hướng, nhưng việc gán `risk_level` cho từng tool thật là quyết định nghiệp vụ cuối cùng thuộc về người vận hành hệ thống (founder/admin), không phải Claude tự quyết.

## Context

ADR-014 đã port xong primitives (`PermissionLevel`, `ExecutionMode`, `evaluate_for_agent()`) vào `agentos/core/policy.py`, nhưng **chưa cutover** — `Executor` (`agentos/core/executor.py`) và `ApprovalGateStep` (`agentos/workflows/approval_step.py`) vẫn gọi `PolicyEngine.evaluate(PermissionClass)` (bảng tra cứu 1 chiều, không phân biệt agent nào gọi).

Hiện trạng cụ thể (2026-08-22, sau khi dọn 4 tool hỏng ở pilot mở rộng):

- **13 tool binding thật** còn hoạt động trong `agentos/tools/clusters/*.py`, mỗi tool chỉ có `permission_class: Optional[str]` (1 trong 11 tag phẳng).
- **0 Agent nào có `PermissionLevel` tường minh** — `Executor.__init__` không nhận tham số nào biểu diễn "agent này được tin tưởng tới mức nào".
- `PERMISSION_CLASS_RISK_MAPPING` (đã có trong `agentos/core/policy.py`) là bảng khởi đầu, tự suy ra từ `DEFAULT_POLICY_TABLE` đã duyệt — không phải đánh giá rủi ro mới.

## Vấn đề cốt lõi cần quyết định

`evaluate_for_agent()` là hàm quyết định 2 chiều: `(agent_permission_level, tool_risk_level, tool_permission)`. Cutover thật cần trả lời 2 câu hỏi độc lập:

1. **Mỗi tool có `risk_level`/`tool_permission` gì?** — có thể suy từ `PERMISSION_CLASS_RISK_MAPPING`, nhưng đây là suy diễn cơ học từ 11 tag cũ, KHÔNG phải review thật cho từng tool cụ thể (vd: `transaction_record` — ghi giao dịch tài chính bất kỳ số tiền nào — có nên luôn là "critical" bất kể số tiền, hay risk nên phụ thuộc `amount` trong `arguments`? Đây là câu hỏi nghiệp vụ).
2. **Mỗi Agent có `PermissionLevel` gì?** — hiện chưa có khái niệm này ở đâu trong `agentos/`. Cần quyết định: gán tĩnh theo cấu hình (mỗi agent_key một level cố định), hay động theo `WorkforceMember`/`ExecutionMode` (agent chạy trong context nào)?

## Phương án cho câu hỏi 1 (risk_level per tool)

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| **A. Dùng thẳng `PERMISSION_CLASS_RISK_MAPPING`** (đã có) | Không cần review gì thêm, cutover ngay | Mapping suy từ 11 tag cũ, độ chi tiết thấp hơn ý định gốc của `risk_level` (vd. mọi `FINANCIAL_ACTION` đều "critical" bất kể số tiền 10k hay 10 triệu) |
| **B. Review thủ công từng tool, gán `risk_level` field trực tiếp trên `ToolSpec`** | Chính xác nhất, đúng tinh thần L0-L3A-L3 | Cần người có thẩm quyền nghiệp vụ duyệt 13 tool, không phải việc code |
| **C. Risk động theo argument** (vd. `transaction_record` risk phụ thuộc `amount`) | Khớp thực tế nhất (giao dịch nhỏ ít rủi ro hơn giao dịch lớn) | Phức tạp hơn nhiều — `ToolSpec.risk_level` hiện là field tĩnh, cần đổi thành callable `risk_level(arguments) -> str`; đây là thay đổi kiến trúc, không chỉ điền dữ liệu |

**Đề xuất:** Bắt đầu bằng A (dùng `PERMISSION_CLASS_RISK_MAPPING` làm mặc định), rồi cho phép override thủ công per-tool khi người vận hành xác nhận (B) — không làm C ngay vì đó là mở rộng kiến trúc, nên tách thành 1 quyết định riêng sau khi đã có dữ liệu vận hành thật (giống nguyên tắc §95 blueprint "Eval Before Autonomy": tăng độ phức tạp sau khi có bằng chứng, không trước).

## Phương án cho câu hỏi 2 (PermissionLevel per Agent)

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| **A. 1 `PermissionLevel` mặc định toàn hệ thống** (config 1 giá trị, áp dụng mọi agent) | Đơn giản nhất, cutover nhanh | Không phân biệt được agent nghiên cứu (nên L1) với agent thực thi công việc đã duyệt (nên L3) |
| **B. `PermissionLevel` gắn theo `agent_key`** (map tĩnh: agent_key → level, giống cách `permission_profile` hoạt động ở `legacy/agent_runtime`) | Khớp mô hình đã có sẵn ở production (`legacy/agent_runtime` đã dùng `permission_profile` per agent) | Cần liệt kê agent_key nào ứng với level nào — vẫn là quyết định nghiệp vụ nhưng nhỏ hơn (số lượng agent_key ít hơn nhiều số lượng tool) |
| **C. `PermissionLevel` gắn theo `WorkforceMember`** (đúng tinh thần Hybrid Workforce identity — mỗi nhân sự AI/người có 1 mức tin cậy riêng, không phải theo agent_key cố định) | Đúng model tổ chức thật nhất, nhất quán với `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`'s "Hybrid Workforce identity" | `agentos/` hiện chưa có khái niệm `WorkforceMember` nào cả — đây là tích hợp lớn hơn nhiều, kéo theo câu hỏi RBAC (xem ADR-017) |

**Đề xuất:** B làm bước trung gian (khớp pattern `legacy/agent_runtime` đã dùng, triển khai nhanh, không chặn bởi câu hỏi RBAC), tiến tới C sau khi ADR-017 (RBAC) có quyết định — vì C và RBAC thực chất là cùng 1 câu hỏi ("ai/cái gì được cấp quyền gì") nhìn từ 2 góc khác nhau.

## Kế hoạch cutover đề xuất (chỉ thực hiện sau khi user chốt phương án ở trên)

1. Thêm `risk_level`/`tool_permission` (Optional, mặc định suy từ `PERMISSION_CLASS_RISK_MAPPING`) vào `agentos/tools/registry.py::ToolSpec`.
2. Thêm `default_agent_permission_level: PermissionLevel` vào `Executor.__init__` (mặc định `L2_DRAFT` — khớp tinh thần "auto-allow read/scoped-write rủi ro thấp, còn lại cần duyệt" mà `DEFAULT_POLICY_TABLE` hiện đang thể hiện).
3. `Executor.run()` gọi `self._policy_engine.evaluate_for_agent(...)` thay cho `evaluate(permission)` — giữ `evaluate(PermissionClass)` không xóa (vẫn cần cho `ApprovalGateStep` tới khi nó cũng cutover).
4. Test lại toàn bộ 13 tool binding với ít nhất 2 `PermissionLevel` khác nhau để xác nhận hành vi không thoái lui so với `DEFAULT_POLICY_TABLE` hiện tại (mỗi tool ALLOW/DENY/REQUIRE_APPROVAL trước/sau cutover phải được đối chiếu tường minh, không suy đoán).
5. Cập nhật `docs/architecture/specs/07-governance-policy-spec.md` sau khi xong.

## Câu hỏi cần user trả lời trước khi thực hiện

1. Dùng A (mapping suy sẵn) hay B (review thủ công per-tool) cho `risk_level`?
2. Dùng B (per agent_key) hay chờ C (per WorkforceMember, gắn với RBAC) cho `PermissionLevel` của agent?
3. `default_agent_permission_level` mặc định nên là gì nếu 1 agent chưa được gán tường minh — `L0_READ` (an toàn nhất, có thể làm gãy tool đang chạy) hay `L2_DRAFT` (khớp hành vi hiện tại nhiều nhất)?
