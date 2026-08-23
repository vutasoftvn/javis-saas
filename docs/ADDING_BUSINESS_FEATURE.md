# Hướng Dẫn Thêm Tính Năng Nghiệp Vụ Mới (Adding Business Feature)

Tài liệu hướng dẫn kỹ sư phát triển tính năng mới cho hệ sinh thái JAVIS / COSA.

---

## 1. Quy Trình Bắt Buộc

Trước khi viết bất kỳ dòng code nào, kỹ sư **BẮT BUỘC** phải rà soát qua cây quyết định tại:
👉 [`docs/architecture/COSA_FEATURE_IMPLEMENTATION_TREE.md`](file:///Volumes/SSD/javis-saas/docs/architecture/COSA_FEATURE_IMPLEMENTATION_TREE.md)

### Các nguyên tắc cốt lõi:
1. **Không viết logic nghiệp vụ vào Agent / Tool / Chat Handler**: Logic nghiệp vụ tất định phải nằm trong `services/` (Encore TypeScript).
2. **Tool chỉ là Adapter**: `ToolSpecV2` chỉ gọi qua `EncoreClient` để tương tác với `services/`.
3. **Skill là Hướng Dẫn Cách Làm**: `SKILL.md` hướng dẫn agent khi nào dùng tool nào và theo trình tự nào, không tự ý bịa đặt kết quả.
4. **Quy trình nhiều bước**: Dùng `WorkflowSpec` (Phase 8b) thay vì để agent tự do gọi tool không kiểm soát.

---

## 2. Case Study Mẫu: Thêm Tính Năng Strategy Domain (Phase 2)

Dưới đây là ví dụ về cách triển khai đúng chuẩn:

### Bước 1: Schema & Migration trong `services/`
Tạo bảng dữ liệu trong `services/operations/strategy/migrations/`:
```sql
CREATE TABLE strategy_assumptions (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'untested'
);
```

### Bước 2: Endpoint Service Logic trong `services/operations/strategy/`
Viết API handler và hàm tính toán logic:
```typescript
export const createAssumption = api(
  { expose: true, method: "POST", path: "/operations/strategy/assumptions" },
  async (req: CreateAssumptionReq): Promise<Assumption> => {
    // Validate và lưu trữ database
  }
);
```

### Bước 3: Đăng Ký Tool trong `agentos/tools/clusters/strategy_tools.py`
Wrap endpoint thành `ToolSpecV2`:
```python
ToolSpecV2(
    name="strategy.assumption.create",
    description="Tạo mới giả định chiến lược",
    input_schema={...},
    handler=assumption_create,
    risk_level=ToolRiskLevel.MEDIUM,
    tool_permission=ToolPermission.SCOPED_WRITE,
)
```

### Bước 4: Viết Hướng Dẫn Skill trong `skillpacks/strategy/`
Tạo file `SKILL.md` và `manifest.yaml` hướng dẫn cách agent phân tích bài toán và gọi tool.

### Bước 5: Viết Test Smoke & Integration
Bổ sung test trong `tests/agentos/` kiểm tra toàn bộ luồng từ Agent $\rightarrow$ Tool $\rightarrow$ Database.
