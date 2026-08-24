# Hướng dẫn: Testing & Conformance suites

## Cấu trúc `packages/agent_testkit/`

```
agent_testkit/
├── kernel_conformance/       # ExecutionKernel Protocol — mọi kernel mới phải pass
├── model_conformance/        # ModelProvider/ModelClient Protocol
├── workflow_conformance/     # WorkflowEngine Protocol
├── gateway_conformance/      # CapabilityGateway pipeline behavior
├── persistence_conformance/  # Repository Protocol implementations (InMemory vs Postgres phải cùng hành vi)
├── protocol_conformance/     # MCP/A2A/AG-UI adapter format
└── fixtures/                 # shared test fixtures
```

Nguyên tắc: conformance test viết chống lại CONTRACT (Protocol trong `packages/agent_core/contracts/`), không chống lại 1 implementation cụ thể — để cùng 1 test suite chạy được cho `OpenAIAgentsKernel` VÀ `LangChainKernel`.

## Chạy test trong môi trường dev (không có Postgres/Encore CLI thật)

Môi trường phát triển hiện tại (2026-08-24) KHÔNG có: Postgres/pg_ctl/initdb, Homebrew, pyenv, Encore CLI. Python hệ thống là 3.9.6 (không đủ cho 1 số cú pháp pydantic v2 union type mặc định — dùng thêm package `eval_type_backport`).

Cách đã dùng trong phiên này: venv scratchpad riêng, KHÔNG phải venv trong repo:
```bash
PYTHONPATH=. "$PYVENV" -m pytest tests/agent_core tests/apps packages/agent_testkit -q
```
Kết quả xác nhận cuối phiên: 256 passed, 15 skipped (skip là các test cần Postgres/Encore CLI/API key thật, không tồn tại trong môi trường này).

## Test yêu cầu hạ tầng thật — CHƯA chạy được ở đây

- Migration Postgres thật (mọi file `.sql` trong `packages/agent_core/migrations/` và `services/cosa/migrations/`) — chỉ review bằng mắt, chưa `psql` thật.
- Encore CLI (`encore test`, `encore run`) cho `services/cosa` — chỉ verify bằng `npx tsc --noEmit` (type-check, không phải runtime test).
- `LangChainKernel`/`LiteLLMModelClient` với API key DeepSeek/OpenAI thật.
- Wave 7 control-plane latency benchmark (H.4) — cần Encore chạy thật để đo.

**Không được báo "đã test" cho các mục trên chỉ vì code compile/type-check — phải phân biệt rõ "verified" vs "chưa verify" trong mọi doc/PR** (CLAUDE.md #11).

## Quy trình khi thêm test mới

1. Xác định đây là conformance test (chống Protocol, tái dùng nhiều implementation) hay unit test riêng cho 1 module — conformance đặt trong `agent_testkit/`, unit test đặt cạnh module (`tests/agent_core/...`).
2. Test "resume sau restart" phải qua process/instance MỚI hoàn toàn, không chỉ tạo object thứ 2 trong cùng process (CLAUDE.md #6 — gap đã phát hiện và fix trong `test_governance_accumulator_survives_gateway_restart`).
3. Chạy full suite trước khi báo hoàn thành bất kỳ thay đổi hành vi nào (CLAUDE.md #11).
