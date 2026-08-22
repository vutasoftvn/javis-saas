# ADR-017 (Proposal): RBAC (Role-Based Access Control)

## Status

**Proposal — chờ quyết định, phân tích sâu theo yêu cầu.** Đây là thiết kế mới hoàn toàn (không hệ thống nào trong repo có RBAC thật), nên đề xuất ở đây có phạm vi rộng hơn ADR-016 — cần user chọn hướng trước khi viết bất kỳ dòng code nào.

## 1. Xác nhận hiện trạng: KHÔNG có RBAC ở đâu trong repo

Đã tìm 2 cơ chế permission thật, cả 2 đều **không phải RBAC**:

### 1.1 `PermissionLevel` (agentos/, ADR-014) — Trust-tier model
5 mức (L0_READ...L3_EXECUTE) áp cho **1 agent tại 1 thời điểm**, không phân biệt agent đó "là ai" về mặt tổ chức — chỉ trả lời "agent này được tin tưởng thực thi tới mức nào", không trả lời "agent này thuộc phòng ban/vai trò nào nên được làm gì".

### 1.2 `UnifiedPermission` (`legacy/agent_runtime/cosa_core/models.py:126-144`) — ABAC/ACL kiểu allow-list
```python
class UnifiedPermission(Base, SnowflakeIDMixin):
    """Permission Engine hợp nhất cho cả Human User và AI Agent (Principal-based)."""
    principal_type: str   # 'USER' hoặc 'AGENT'
    principal_id: int
    resource_type: str    # 'TOOL', 'DATA', 'MODULE', 'BUDGET'
    resource_key: str     # vd: 'crm.update', 'finance.read', '*'
    action: str            # 'READ', 'WRITE', 'EXECUTE', 'APPROVE', 'ADMIN'
    is_allowed: bool
    requires_approval: bool
```
Đây là **attribute/access-control-list per principal per resource** — mỗi (principal, resource, action) là 1 dòng grant riêng. Không có khái niệm "Role" nào đứng giữa principal và permission — nếu 50 nhân sự cùng cần quyền như nhau, phải tạo 50 dòng grant giống hệt nhau (không có 1 "Role" để gán chung rồi sửa 1 chỗ).

### 1.3 `WorkforceMember.role_title` — chỉ là nhãn HR, không phải access-control role
`role_title: str` (`legacy/agent_runtime/cosa_core/identity/models.py:51`) là chuỗi tự do như "Ops", "Sales Manager" — dùng cho org-chart/hiển thị, **không** được `UnifiedPermission` hay `PolicyEngine` nào đọc để suy ra quyền. Không có bảng ánh xạ `role_title -> permissions` ở đâu.

**Kết luận:** thêm RBAC là xây 1 lớp hoàn toàn mới, không phải mở rộng cái gì có sẵn.

## 2. Ba câu hỏi thiết kế cốt lõi

### Câu hỏi A — RBAC thay thế hay xếp lớp lên trên `UnifiedPermission`/`PermissionLevel`?

| Phương án | Mô tả | Đánh giá |
|---|---|---|
| **A1. Thay thế `UnifiedPermission`** | Xóa ACL per-principal, mọi permission đi qua Role | Rủi ro cao: `UnifiedPermission` đang là bảng thật trong `agent_runtime` schema, có thể đã có data — "thay thế" đụng vào dữ liệu production, không phải quyết định kỹ thuật đơn thuần |
| **A2. Role là 1 tầng TRUNG GIAN sinh ra `UnifiedPermission` rows** | `Role` = tập hợp `(resource_type, resource_key, action, is_allowed)` đặt tên sẵn; gán `Role` cho `principal` thì hệ thống tự sinh/resolve ra các dòng `UnifiedPermission` tương ứng (hoặc resolve tại thời điểm evaluate, không cần vật chất hóa) | An toàn hơn — không đụng schema hiện có, `UnifiedPermission` vẫn là nguồn sự thật cuối cùng, `Role` chỉ là cách gán hàng loạt tiện lợi |
| **A3. RBAC hoàn toàn độc lập, song song `UnifiedPermission`** | 2 hệ thống permission riêng biệt, PolicyEngine hỏi cả 2 | Nguy cơ **trùng lặp kiến trúc** — đúng loại rủi ro CLAUDE.md §14 cảnh báo (lịch sử 4 model Agent/AgentDefinition/AgentProfile/WorkforceMember phân mảnh) |

**Đề xuất: A2.** Role là lớp "convenience" đặt tên cho 1 nhóm quyền, resolve ra đúng shape `UnifiedPermission` đã có — không tạo nguồn sự thật permission thứ 2.

### Câu hỏi B — Role gán cho ai: `principal` (User/Agent) hay `WorkforceMember`?

`UnifiedPermission.principal_type` hiện là `'USER'`/`'AGENT'` — tách biệt 2 loại định danh. Nhưng `COSA_CANONICAL_OWNERSHIP_MAP.md` đã ghi rõ hướng dài hạn (chưa implement, "documented future direction"):

> `UnifiedPermission.principal` hiện là `USER`/`AGENT`... nên dần chuyển sang `WORKFORCE_MEMBER`/`SERVICE`/`DEVICE`, theo dõi đúng instance nhân sự thay vì template hay login identity.

Nếu RBAC gán Role theo `principal_type=USER`/`AGENT` như hiện tại, nó sẽ **kế thừa luôn vấn đề đã biết** (không phân biệt được 2 `WorkforceMember` cùng dùng chung 1 `AgentDefinition` template nhưng nên có quyền khác nhau ở 2 workspace khác nhau). Gán Role theo `WorkforceMember` giải quyết đúng vấn đề này nhưng **phải làm trước/cùng lúc** với migration `principal` đã ghi trong ownership map — nếu không sẽ tạo ra Role gắn với `WorkforceMember` trong khi enforcement thật (`UnifiedPermission`) vẫn còn gắn `USER`/`AGENT`, 2 tầng lệch nhau.

**Đề xuất:** RBAC nên là lý do thực hiện luôn migration `principal -> WORKFORCE_MEMBER` đã ghi nhận từ trước — làm RBAC mà không làm migration này sẽ phải quay lại sửa ngay sau đó.

### Câu hỏi C — Role liên hệ thế nào với `PermissionLevel` (trust tier)?

2 khái niệm khác trục, không thay thế nhau:
- **Role** (RBAC) = "Sales Manager được sửa CRM, xem báo cáo doanh thu" — permission theo **domain nghiệp vụ**.
- **PermissionLevel** (ADR-014) = "agent này được tin tưởng tự thực thi tới đâu trước khi cần người duyệt" — permission theo **mức độ tự chủ**.

Một Sales Manager (Role) vẫn có thể ở `PermissionLevel = L1_SUGGEST` (agent AI đóng vai Sales Manager mới triển khai, chưa được tin tưởng tự chạy) hoặc `L3_EXECUTE` (agent đã chứng minh độ tin cậy). 2 trục độc lập, quyết định cuối = giao của cả 2: `final_decision = min(role_allows, permission_level_allows)` theo hướng an toàn nhất (Role nói được phép, nhưng PermissionLevel vẫn có thể yêu cầu duyệt thêm).

## 3. Đề xuất phạm vi MVP (nếu user chọn tiến hành)

Tránh lặp lại rủi ro over-engineering mà blueprint chính đã cảnh báo (§53 "MVP Scope... Do not start with a full marketplace"):

1. `Role` model tối giản: `id`, `name`, `grants: list[(resource_type, resource_key, action, is_allowed, requires_approval)]` — đúng shape các field `UnifiedPermission` đã có, không thêm field mới.
2. `RoleAssignment`: `(workspace_id, principal_type, principal_id, role_id)` — tạm giữ `principal_type` USER/AGENT như hiện tại (không chặn RBAC MVP bởi migration WorkforceMember lớn), nhưng **ghi rõ trong code là nợ kỹ thuật đã biết**, có kế hoạch migrate sang `WORKFORCE_MEMBER` sau.
3. Resolve: khi cần biết principal có quyền gì, UNION các `UnifiedPermission` trực tiếp + các quyền suy ra từ mọi `Role` đã gán — không vật chất hóa (không insert hàng loạt `UnifiedPermission` rows khi gán Role, tránh out-of-sync khi sửa Role sau).
4. 3-5 Role mẫu tối thiểu để chứng minh cơ chế hoạt động (không cần đủ mọi phòng ban ngay): `Founder` (mọi quyền), `Ops` (task/OKR), `ReadOnly` (chỉ đọc) — **danh sách Role thật và quyền cụ thể của từng Role là quyết định nghiệp vụ của user, không phải Claude tự đặt**.

## 4. Câu hỏi cần user trả lời trước khi bắt đầu

1. Đồng ý hướng A2 (Role là lớp resolve ra `UnifiedPermission`, không thay thế) không?
2. RBAC có nên là lý do để làm luôn migration `principal: USER/AGENT -> WORKFORCE_MEMBER` đã ghi trong ownership map, hay tạm chấp nhận nợ kỹ thuật này ở MVP?
3. Danh sách Role thật đầu tiên cần có là gì (Founder/Ops/Sales/Finance/ReadOnly...) và quyền cụ thể của từng Role?
4. RBAC nên sống ở đâu — `agentos/` (Python, theo hướng target ADR-013) hay `legacy/agent_runtime` (nơi `UnifiedPermission` đang thật sự tồn tại như 1 bảng SQLAlchemy)? Nếu ở `agentos/`, cần quyết định thêm: đọc/ghi `UnifiedPermission` qua kết nối DB trực tiếp hay qua 1 adapter — đây lại là câu hỏi tương tự "agentos/ dùng DB nào" đang treo ở ADR-012/spec 02 (Knowledge Layer, Memory).
