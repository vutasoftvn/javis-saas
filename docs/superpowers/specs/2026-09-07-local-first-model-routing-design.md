# Thiết kế Model Routing Local-first cho COSA

## Mục tiêu

Cho phép agent có model mặc định an toàn nhưng founder/co-founder/admin được cấu
hình provider, model chính và fallback theo workspace hoặc agent profile qua UI.
Mọi credential, usage chi tiết và prompt ở lại Workspace Runtime Node.

## Quy tắc kiến trúc

- Precedence: pinned run policy → agent-profile override → workspace default →
  system default. Mỗi run pin `profile_id`, provider, model và policy version.
- Fallback chỉ đi theo ordered allowlist do founder cấu hình. Không có fallback
  implicit khi quota lỗi, provider offline hay policy dữ liệu deny.
- Provider `local_openai_compatible`, `anthropic_api`, `openai_api`,
  `openrouter_api`, `deepseek_api`, `claude_cli`, `codex_cli`, `gemini_cli` có adapter riêng.
- `claude_cli`/`codex_cli`/`gemini_cli` là experimental local bridge, không phải shell tool;
  chỉ gọi executable tuyệt đối trong allowlist, arguments cố định, stdin prompt,
  timeout/cancellation/concurrency cứng.
- API key được encrypted bằng key local node; response/UI chỉ biết configured,
  status và key version. Không lưu key trong Flutter, log, scheduler, run event
  hay Platform Control Plane.
- Model routing luôn qua compliance snapshot. Data policy cấm provider/model/
  purpose/retention thì không gửi prompt, kể cả founder đã cấu hình provider.

## Provider entitlement

`openai_api` là credential API riêng. Không xem subscription ChatGPT là API key
hoặc tự động có API quota. `codex_cli` là route local-session riêng, dùng flow
đăng nhập ChatGPT của Codex CLI nếu provider cho phép. Claude API/Claude CLI và
Gemini API/Gemini CLI cũng là các credential/runtime khác nhau. `deepseek_api`
không còn là singleton env bắt buộc mà là một profile API bình thường. UI phải
thực hiện health check server-side và chỉ hiển thị provider usable sau khi check
thành công.

## UI và REST commands

Founder-only commands: tạo/test/rotate/revoke profile credential, đặt workspace
default, đặt agent override, đặt fallback, budget và concurrency. Member chỉ đọc
status nếu policy cho phép, không xem hoặc thay secret. Command write có audit;
agent không thể gọi chúng qua tool.

## Phát hành

Không phát hành trước khi prove: precedence, tenant isolation, secret redaction,
approved-only fallback, compliance deny trước egress, quota behavior, CLI timeout
kill, local provider availability và no-raw-prompt telemetry.
