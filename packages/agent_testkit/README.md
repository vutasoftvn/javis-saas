# packages/agent_testkit

Conformance test suite dùng chung cho mọi runtime adapter, model provider, workflow runtime, capability gateway, persistence backend, và protocol adapter mới. Bất kỳ implementation mới trong `packages/agent_integrations/` **phải pass** bộ test tương ứng ở đây trước khi được chọn làm default trong `apps/cosa/composition/agent_plane.py` (xem Blueprint V2 §46).

## Cấu trúc

```text
agent_testkit/
├── kernel_conformance/       # ExecutionKernel: response, streaming, structured output, parallel tool,
│                              # cancellation, provider failure, timeout, resume, exact (run_id, tool_call_id)
├── model_conformance/        # ModelProvider: capabilities(), generate(), stream()
├── workflow_conformance/     # WorkflowRuntime: parallel snapshot/reducer semantics, checkpoint/replay
├── gateway_conformance/      # CapabilityGateway pipeline: readiness→governance→approval→idempotency→execute→audit
├── persistence_conformance/  # crash/restart, cross-process resume, no-duplicate-side-effect (Scenario A/B, Blueprint V2 §82)
├── protocol_conformance/     # MCP mapping, A2A authority attenuation, AG-UI event mapping
└── fixtures/                 # shared test data/factories dùng chung giữa các conformance suite trên
```

## Quan hệ với `tests/agent/`

`tests/agent/{p1,p2,drift}/` hiện đã có nhiều test theo hình dạng conformance (theo phase promotion cũ). Theo `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần B.2: **di chuyển dần theo từng batch nhỏ khi có liên quan trực tiếp tới Wave đang làm**, không bulk-move trong 1 PR để tránh vỡ CI hiện có. `tests/agent/` vẫn là nơi chứa unit/integration test theo module; `agent_testkit/` chỉ chứa test **conformance chéo runtime** (cùng 1 bộ test chạy lại cho nhiều implementation khác nhau của cùng 1 Protocol).

## Trạng thái hiện tại (2026-08-24)

Vừa scaffold ở Wave 0.2 — các thư mục con hiện rỗng. Sẽ điền dần bắt đầu từ Wave 1 (persistence_conformance cho Scenario A/B) và Wave 4 (kernel_conformance cho `LangChainKernel`).
