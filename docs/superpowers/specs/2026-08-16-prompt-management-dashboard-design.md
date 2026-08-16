# Prompt Management Dashboard (Spec 1 / 5)

## Goal

Cho Founder (role `owner`) xem, sửa và đặt lại về mặc định các system prompt của COSA OS qua dashboard, với audit đầy đủ. Đây là spec đầu tiên trong chuỗi 5 spec độc lập hướng tới việc mọi domain AI (chat, sales, finance, legal, quality) đều có prompt quản lý được qua dashboard này; các spec sau (Sales AI, Finance AI, Legal AI, Quality/Judge AI) sẽ nối tiếp domain thật vào catalog mà spec này dựng nền.

## Bối cảnh đã xác minh (quan trọng cho quyết định thiết kế)

- `backend/app/prompts/**/*.md` (23 file, 6 domain: cosa, sales, marketing, finance, legal, quality) hiện **không được bất kỳ code path nào load** — `PromptRegistry` (backend/app/ai/prompt_registry.py) tồn tại nhưng không có nơi nào gọi `get_instance()/render()/get()`. Sửa các file này hôm nay không đổi hành vi AI.
- Prompt LLM thật đang chạy nằm hardcode rải rác: `chat_execution_service.py` (6 hằng số), `chief_of_staff.py::_build_synthesis_prompt`, `deepseek_harness.py` (tool-usage header), `coding_agent_provider.py::MODULAR_LANDING_SYSTEM_PROMPT`.
- `sales/finance/legal/quality` domain hiện **chưa có LLM call nào** — `action.py`, `sales_tools.py`, `revenue_engine_service.py`, các `Capability` class của finance/legal/quality đều là logic tất định (deterministic), dispatch qua bảng cố định. Prompt của các domain này không "chưa nối dây" mà là "chưa có tính năng để nối vào" — việc xây tính năng AI thật cho các domain này là phạm vi của Spec 2–5.
- Hạ tầng "sửa + reset về mặc định + audit" đã có sẵn và đang chạy cho một đối tượng khác: `Agent.system_prompt` (agent do người dùng workspace tự tạo, bảng `agents` trong `modules/tasks/models.py`) — qua `app/core/protected_resources/service.py` (`create_revision`, `reset_to_default`, `get_effective`, `list_revisions`) và `app/core/authz.py` (`PROTECTED_ACTIONS` đã có sẵn `prompt.read/update/reset`, hiện gate ở role `admin` trở lên). `agents_router.py` đã dùng đúng cơ chế này nhưng chưa có UI Flutter nào gọi.
- 3 prompt sau đây là **hợp đồng kỹ thuật/guardrail chống bịa dữ liệu**, không phải văn phong, và bị loại khỏi phạm vi sửa qua dashboard (giữ code cứng, đổi phải qua code review): `GROUNDING_PROMPT`, `NO_TOOLS_PROMPT`, `UNGROUNDED_ACTION_PROMPT` (chat_execution_service.py — comment trong code ghi rõ đây là sửa lỗi model tự bịa số liệu OKR/tài chính), `MODULAR_LANDING_SYSTEM_PROMPT` (rule bắt buộc dùng COSA Public API), `deepseek_harness` tool-usage header (JSON tool-call contract mà chính code đó parse ngược), `chief_of_staff` synthesis prompt (có dòng "Do not invent numbers not present in the snapshots above").

## Scope and Decisions

- **Wiring thật** (sửa trên dashboard đổi ngay hành vi AI): 3 prompt văn phong/persona trong `chat_execution_service.py` — `SYSTEM_PROMPT_VI` (ngôn ngữ trả lời), `CONVERSATION_PROMPT` (giọng điệu hội thoại thường), `STRUCTURED_ONESHOT_PROMPT` (chuẩn định dạng output one-shot).
- **Catalog-only** (sửa/reset được, lưu DB, nhưng chưa có call site nào đọc — badge "Chưa có tính năng AI dùng"): 20 file `.md` còn lại (toàn bộ finance/legal/quality/sales, phần lớn cosa/marketing bao gồm `cosa/system.md`, `cosa/mission_planner.md`, `cosa/founder_brief.md`...).
- **Không đưa vào dashboard** (giữ code cứng, không tạo `domain_prompt` entry): `GROUNDING_PROMPT`, `NO_TOOLS_PROMPT`, `UNGROUNDED_ACTION_PROMPT`, `MODULAR_LANDING_SYSTEM_PROMPT`, `deepseek_harness` tool header, `chief_of_staff` synthesis prompt.
- **RBAC**: xem (`prompt.read`) — role `admin` trở lên (owner, admin). Sửa và reset (`prompt.update`, `prompt.reset`) — **chỉ role `owner`** (founder), admin thường bị chặn. Áp dụng đồng nhất cho cả `domain_prompt` (mới) lẫn `Agent.system_prompt` (đã có sẵn, đang gate ở admin, spec này siết lên owner).
- **Đa tenant**: mỗi workspace override độc lập qua `resource_key = f"{domain}/{name}"` scoped theo `workspace_id` sẵn có trong `protected_resources`. Không override thì mọi workspace dùng chung nội dung file mặc định trên đĩa.
- **Cutover trung tính hành vi**: nội dung mặc định của 3 file mới tạo cho prompt đã wiring phải giống hệt string hardcode hiện tại — bật tính năng không đổi hành vi AI cho tenant nào chưa từng chỉnh sửa.
- Không hỗ trợ tạo prompt key mới từ UI — chỉ sửa/xem/reset trong đúng danh mục cố định 23 file (không phát sinh domain/name tuỳ ý).

## Architecture

### Backend: mở rộng `protected_resources` cho domain prompt

Không cần migration schema mới — bảng `ProtectedResource`/`ProtectedResourceRevision` đã generic theo `resource_type` + `resource_key` (JSONB content). Domain prompt dùng:
- `resource_type = "domain_prompt"`
- `resource_key = f"{domain}/{name}"` (vd. `"cosa/chat_language"`)
- `default_content = {"content": <nội dung file .md hiện tại>}`

### `PromptRegistry` — thêm resolver có DB override

Giữ nguyên `reload()`/`get()` hiện có (cache file trong bộ nhớ). Thêm method mới:

```
render_effective(db: Session, workspace_id: int, domain: str, name: str, variables: dict | None) -> str
```

Thứ tự resolve: gọi `protected_resources.get_effective(db, workspace_id, "domain_prompt", f"{domain}/{name}", default_content={"content": template.content})` → lấy `content` từ kết quả (override nếu có, mặc định nếu không) → áp `${var}` substitution như `render()` hiện tại.

### Refactor 3 call site trong `chat_execution_service.py`

Thay `SYSTEM_PROMPT_VI`, `CONVERSATION_PROMPT`, `STRUCTURED_ONESHOT_PROMPT` (hằng số module-level) bằng lời gọi `PromptRegistry.get_instance().render_effective(db, workspace_id, "cosa", <name>, None)` tại nơi đang nối chuỗi prompt (dòng ~427-431). Tạo 3 file mới:
- `backend/app/prompts/cosa/chat_language.md` — nội dung = `SYSTEM_PROMPT_VI` hiện tại.
- `backend/app/prompts/cosa/chat_conversation.md` — nội dung = `CONVERSATION_PROMPT` hiện tại.
- `backend/app/prompts/cosa/chat_structured_oneshot.md` — nội dung = `STRUCTURED_ONESHOT_PROMPT` hiện tại.

`GROUNDING_PROMPT`, `NO_TOOLS_PROMPT`, `UNGROUNDED_ACTION_PROMPT` giữ nguyên hardcode, không đổi.

### RBAC — `authz.py`

Đổi `authorize()` từ 1 mức chung cho mọi `PROTECTED_ACTIONS` sang map theo action:

```python
ACTION_REQUIRED_LEVEL = {
    "prompt.update": "owner",
    "prompt.reset": "owner",
}
# các action khác trong PROTECTED_ACTIONS giữ nguyên mức "admin" như hiện tại
```

`authorize()` tra `ACTION_REQUIRED_LEVEL.get(action, "admin")` thay vì hardcode `"admin"`. Không đổi hành vi của `spec.*`, `skill.*`, `policy.*`, `employee.*`, `agent.configure`, `tool.configure`, `approval_policy.configure`.

### API mới — `backend/app/modules/platform/prompts_router.py`

Mount `/api/v1/platform/prompts` (theo mẫu `feature_flags_router.py`, cùng include trong `main.py`):

- `GET /` — liệt kê 23 domain prompt: `domain`, `name`, `is_overridden`, `is_wired` (true chỉ cho 3 prompt chat), `updated_at`. Yêu cầu `prompt.read`.
- `GET /{domain}/{name}` — nội dung hiệu lực + `default_content` + lịch sử revision (`list_revisions`). Yêu cầu `prompt.read`.
- `PATCH /{domain}/{name}` body `{content}` — `create_revision`. Yêu cầu `prompt.update` (owner-only).
- `POST /{domain}/{name}:reset` — `reset_to_default`. Yêu cầu `prompt.reset` (owner-only).

`Agent.system_prompt` tiếp tục dùng `agents_router.py` hiện có (update/reset đã implement) — chỉ cần đổi hành vi qua thay đổi chung ở `authz.py`, không sửa router đó.

### Frontend (Flutter)

Màn hình mới "Prompt Management" trong `frontend/lib/modules/dashboard`:
- Danh sách nhóm theo domain (cosa, sales, marketing, finance, legal, quality) + tab riêng "Custom Agents" cho `Agent.system_prompt`. Mỗi dòng: tên, badge "Đã tuỳ chỉnh" (nếu `is_overridden`), badge "Chưa có tính năng AI dùng" (nếu `!is_wired`).
- Màn chi tiết: textarea markdown, nút "Lưu" và "Đặt lại mặc định" (ẩn/disable nếu role hiện tại không phải `owner`, kèm tooltip giải thích), danh sách lịch sử revision (read-only, hiển thị `revision_no`, `created_by`, `created_at`, `checksum`).
- Gọi API qua `/api/v1/platform/prompts` (giống pattern `feature_flags_controller.dart`).

## Error Handling

- Reset khi chưa có override: idempotent, trả về nội dung mặc định hiện tại (hành vi có sẵn của `reset_to_default`, không lỗi).
- Sửa/reset domain/name không nằm trong danh mục 23 file cố định: 404 — không cho phát sinh key tuỳ ý từ UI.
- Ghi đè đồng thời (2 owner sửa cùng lúc): last-write-wins, không cần locking (tần suất thao tác thấp, không cần over-engineer).
- Biến `${var}` bị xoá khi sửa: không chặn lưu; UI hiển thị cảnh báo mềm nếu tập biến trong nội dung mới khác tập biến của bản mặc định (so khớp bằng regex `\$\{([a-zA-Z0-9_]+)\}` — logic đã có sẵn trong `PromptRegistry.reload()`).

## Testing

- Backend pytest: RBAC 403 khi admin thường gọi `PATCH`/`:reset` (chỉ owner pass); cách ly tenant (override ở workspace A không lộ sang workspace B); mặc định = nội dung file khi chưa override; cutover trung tính — response render của 3 prompt chat khi chưa override phải khớp bit-for-bit với hardcode string cũ (regression test trên `test_compose_contract.py` hoặc file test chat execution liên quan).
- Flutter: widget test ẩn/hiện nút Lưu/Reset theo role; controller test gọi đúng endpoint.

## Out of Scope (Spec 2–5, làm sau lần lượt)

- Spec 2 — Sales AI: xây LLM reasoning thật cho `sales/outbound.md`, `proposal.md`, `prospect.md`, `qualify.md`, nối vào `domains/sales/action.py`/`sales_tools.py`.
- Spec 3 — Finance AI: `finance/analyze.md`, `finance_brief.md` nối vào `revenue_engine_service.py`.
- Spec 4 — Legal AI: `legal/contract_review.md`, `review.md`.
- Spec 5 — Quality/Judge AI: `quality/judge.md`, `cosa/judge.md` — làm cuối vì cần domain khác có output thật để chấm.

Mỗi spec trên brainstorm riêng, bao gồm câu hỏi lấy dữ liệu thật ở đâu, tool gì, và guardrail chống bịa tương ứng — theo đúng cách đã làm cho chat ở spec này.
