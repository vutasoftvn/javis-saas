# Prompt Language Strategy

## Quyết định

**English là ngôn ngữ chỉ dẫn canonical; vi-VN là locale mặc định cho output người dùng.** Không dịch toàn bộ prompt hệ thống sang tiếng Việt — thay vào đó English prompt chứa locale directive rõ ràng.

## Implementation (Wave 3, `packages/agent_core/prompts/`)

```
PromptBundle.render():
  platform_policy (English, bất biến, mọi agent)
  + agent_instructions (từ AgentSpec.instructions — hiện đa số viết tiếng Việt trong `apps/cosa/agents/specs.py`)
  + skill_instructions (từ pinned_skills đã resolve, nếu có)
  + locale_policy (English, template cố định — xem dưới)
```

Locale policy template (`agent_core.prompts.locale.render_locale_policy()`):

```
The user's preferred locale is {locale}.
Respond in that locale unless the user explicitly requests another language.
Preserve official product names, code identifiers, API names, schema fields,
and technical terms when translation would reduce precision.
```

`RunRequest.locale: str = "vi-VN"` — mặc định vi-VN, đổi được per-request.

## Glossary (tĩnh, chưa có consumer)

`packages/agent_core/prompts/glossary/{core.en.yaml,vi-VN.yaml}` — ánh xạ cách hiển thị thuật ngữ (vd `run` → "lượt chạy"), KHÔNG đổi internal identifier. Hiện là dữ liệu tham chiếu, chưa có code load/substitute (chưa cần vì chưa có consumer thật — tránh xây plumbing thừa).

## Khác biệt với AgentSpec.instructions hiện có

`apps/cosa/agents/specs.py` viết `instructions` trực tiếp bằng tiếng Việt (không phải English canonical như chiến lược này đề xuất) — đây là NỘI DUNG NGHIỆP VỤ cụ thể của 2 agent spec production hiện có, khác với `platform_policy`/`locale_policy` (canonical, luôn English). Chiến lược "English canonical" áp dụng cho phần HẠ TẦNG (platform policy, locale directive), không bắt buộc rewrite mọi `AgentSpec.instructions` đã viết tiếng Việt sang tiếng Anh.

## Việc chưa làm

- Chưa có eval 2 track (EN reasoning/contract compliance, VI user-facing quality) như Blueprint V2 §83 đề xuất.
- Chưa có override locale-specific cho skill prompt (`skill_prompt.vi-VN.md`).
