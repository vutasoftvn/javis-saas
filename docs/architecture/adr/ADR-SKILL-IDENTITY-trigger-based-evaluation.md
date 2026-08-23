# ADR-SKILL-IDENTITY: Đánh Giá Kiến Trúc Định Danh Skill (Trigger-Based Evaluation)

- **Trạng thái:** PENDING TRIGGER / DEFERRED UNTIL FIRST RUNTIME EXECUTION USE CASE
- **Ngày quyết định:** 2026-08-23
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `docs/architecture/roadmap/hermes-langgraph-integration/phase-10-p2-trigger-based.md` §8
  - `docs/architecture/roadmap/hermes-langgraph-integration/phase-11-archive.md` §6
  - `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3, §4

---

## 1. Bối cảnh & Nguyên tắc Trigger-Based

Tại Phase 9 (Track 9D), hệ thống đã thiết lập lifecycle publication bất biến cho `SkillSpec` (`packages/agent_core/skills/`). Tuy nhiên, để ngăn chặn **floating runtime references** (rủi ro một Run đang thực thi nạp động phiên bản skill mới không xác định qua tên chuỗi không version), quyền tiêu thụ skill trong runtime execution bị cố tình **khóa** cho đến khi có use case sản phẩm thực tế kích hoạt.

Kỷ luật của Phase 10: **Không prebuild trước khi có trigger thật.**

---

## 2. Ba Phương Án Kiến Trúc Khi Trigger Xảy Ra

Khi có use case sản phẩm đầu tiên cần một Skill tham gia vào execution loop của Agent:

### Phương án A: AgentSpec tham chiếu exact `SkillSpec` version & `definition_hash`
- `AgentSpec` chứa danh sách `pinned_skills: list[PinnedSkillRef] = [{"id": "finance-close", "version": "1.2.0", "hash": "..."}]`.
- **Ưu điểm:** Tách bạch lifecycle giữa Agent và Skill; Skill có thể cập nhật version độc lập.
- **Nhược điểm:** Cần resolver kiểm tra hash tại thời điểm nạp.

### Phương án B: Nội dung Skill được compile trực tiếp vào `AgentSpec.definition_hash`
- Toàn bộ instructions của Skill được nối trực tiếp vào prompt của `AgentSpec` và hash chung.
- **Ưu điểm:** Tính tất định tuyệt đối 100%, không cần runtime skill resolver.
- **Nhược điểm:** Mọi thay đổi nhỏ trong Skill đều tạo ra AgentSpec version mới.

### Phương án C: Skill trở thành một `spec_kind` mới trong `PinnedSpecIdentity`
- Mở rộng `spec_kind: Literal["agent", "workflow", "skill"]`.
- Thêm `SpecResolutionManifest` tracking cho Skill tương tự như Agent và Workflow.
- **Ưu điểm:** Nhất quán mô hình quản trị temporal governance toàn diện của COSA.
- **Nhược điểm:** Tăng độ phức tạp của `SpecResolutionManifest`.

---

## 3. Quyết định Tạm thời & Enforcement Invariant

1. **Trạng thái:** Giữ ADR này ở trạng thái **PENDING TRIGGER**.
2. **Quy tắc thực thi:**
   - Trường `skill_refs` trong `AgentSpec` (khởi tạo từ Phase 1) tiếp tục **giữ rỗng và không ảnh hưởng đến execution** của `OpenAIAgentsKernel`.
   - Mọi skill mới chỉ được publish và lập chỉ mục (L0 index), không được nạp tự do qua floating reference trong runtime execution.
3. Khi có yêu cầu nghiệp vụ thực tế đầu tiên cần Agent sử dụng Skill động, ADR này sẽ được kích hoạt để đánh giá thực nghiệm cả 3 phương án và chốt lựa chọn tối ưu.
