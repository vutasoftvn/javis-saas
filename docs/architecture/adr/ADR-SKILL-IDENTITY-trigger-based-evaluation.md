# ADR-SKILL-IDENTITY: Đánh Giá Kiến Trúc Định Danh Skill (Trigger-Based Evaluation)

- **Trạng thái:** ACTIVATED (2026-08-24) — xem "Cập nhật kích hoạt" §4. Lịch sử PENDING TRIGGER (2026-08-23) giữ nguyên bên dưới để không xoá bối cảnh quyết định gốc.
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

---

## 4. Cập nhật kích hoạt (2026-08-24)

**Trigger:** `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` Wave 5-6 (Skill Optimization Lab, Executor→Analyst→Mutator) yêu cầu trực tiếp khả năng agent thực thi với skill candidate để chấm điểm — đây là use case runtime execution đầu tiên chạm đúng ranh giới đã khoá. Người dùng xác nhận coi đây là trigger thật, chọn kích hoạt ADR này thay vì tiếp tục deferred.

**Quyết định: Phương án A** (`AgentSpec` tham chiếu exact `SkillSpec` version & `definition_hash`), theo đúng khuyến nghị ban đầu — giữ tách bạch lifecycle giữa Agent và Skill, cho phép Skill cập nhật version độc lập mà không bắt buộc AgentSpec đổi version.

**Không chọn Phương án B** (compile skill vào `AgentSpec.definition_hash`) vì mọi thay đổi nhỏ trong skill sẽ ép AgentSpec phải version mới — không phù hợp mô hình skill lifecycle (Draft→Candidate→...→Published) độc lập đã có ở `packages/agent_core/skills/contracts.py`.

**Không chọn Phương án C** (mở rộng `spec_kind` của `PinnedSpecIdentity`/`SpecResolutionManifest`) trong đợt này — mở rộng temporal governance model đầy đủ cho skill là thay đổi lớn hơn phạm vi trigger hiện tại (chỉ cần Skill Optimization Lab đọc được skill khi resolve prompt, chưa cần track trong `SpecResolutionManifest` như Agent/Workflow). Có thể mở lại nếu skill cần tham gia governance temporal đầy đủ sau này.

**Cài đặt cụ thể** (khác 1 điểm so với sketch gốc trong §2 Phương án A — dùng registry đã có thay vì tạo mới):

- `AgentSpec.pinned_skills: list[PinnedSkillRef] = []` — field mới, mỗi entry có `skill_id`, `version`, `definition_hash`.
- Skill publish qua **cùng bảng** `agent_registry.published_specs` (đã tạo ở migration 007, Wave 3) với `spec_kind="skill"` — không tạo registry riêng cho skill. `packages/agent_core/registry/publisher.py::publish_skill_spec()`.
- `packages/agent_core/skills/resolver.py::SkillResolver` — resolve từng `PinnedSkillRef` qua `SpecRegistryRepository`, **verify `definition_hash` khớp tuyệt đối** trước khi dùng (đây chính là invariant chống floating reference mà ADR gốc lo ngại) — mismatch raise `AgentRuntimeError(SKILL_RESOLUTION_ERROR)`, không âm thầm dùng version khác.
- Skill instructions resolve được inject vào `PromptBundle` (Wave 3) như 1 section riêng, đúng vị trí "selected SkillSpec" trong Blueprint V2 §68.2.
- `packages/agent_core/skills/registry.py::SkillRegistry` (in-memory, Phase 9D) **giữ nguyên không đổi** — vẫn dùng cho L0/L1 progressive disclosure index nội bộ process, không phải đường publish durable. 2 tầng khác nhau, không trùng nhau (giống agent_registry vs registry/ filesystem đã phân biệt ở Wave 3).

Xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần G (Wave 5-6) cho chi tiết triển khai.
