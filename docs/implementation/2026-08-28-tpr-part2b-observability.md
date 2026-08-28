# Part 2B — Observability

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Milestone 1; trước go-live
**Ước lượng:** 2–3 ngày
**Nhánh:** `tpr/part2b-observability`

## Mục tiêu

Trước prod, phải "nhìn thấy" hệ thống: distributed trace, runtime metrics (token/cost/approval/lease/run outcome), structured log có correlation. Ưu tiên debug bằng số đo thật, không đoán (theo memory `debugging-preferences`).

## Trạng thái hiện tại (verify bằng code)

- OpenTelemetry SDK có trong Python requirements **nhưng chưa init** ở `apps/cosa/api/main.py` / `apps/cosa/worker/main.py` — không có tracer provider, không exporter.
- Metrics hiện có: **event backbone** — `services/company/events/services/event-metrics.service.ts` (outbox backlog/claimed/retrying/DLQ/delivered-24h). Handler cho `GET /events/metrics`: **chưa xác nhận đăng ký + authed** (Part 0 mục 5).
- Chưa có metric cho: token usage, model cost, approval latency, run outcome distribution, worker lease churn, scheduler queue depth.
- Log: stdout/stderr, không JSON có cấu trúc, không `run_id`/`workspace_id` correlation nhất quán giữa Python và Encore.
- Health: `/healthz` (api + 2 encore), worker `/live`+`/ready` (thêm ở Part 1E).

## Thay đổi cụ thể

### 2B.1 OpenTelemetry tracing

- `apps/cosa/observability/otel.py` (mới): `init_tracing(service_name)` — cấu hình `TracerProvider`, `OTLPSpanExporter` (endpoint qua `OTEL_EXPORTER_OTLP_ENDPOINT`, tắt khi không set → no-op), resource attrs (`service.name`, `service.version`, `deployment.environment`).
- Gọi trong lifespan của `apps/cosa/api/main.py` và đầu `apps/cosa/worker/main.py`.
- Instrument: FastAPI (auto), httpx client (auto), + span thủ công quanh: kernel `run`/`resume` (attrs `run_id`, `agent_spec_id`, `workspace_id`), mỗi tool call (`tool_call_id`, `capability`, `require_approval`), scheduler claim, lease acquire/renew.
- Encore side: dùng Encore built-in tracing (đã có), bảo đảm propagate `traceparent` header từ Python → Encore (thêm vào `CompanyServiceClient` / control-plane client).

### 2B.2 Runtime metrics

- `apps/cosa/observability/metrics.py` (mới): Prometheus client (`prometheus_client`), registry chung.
  - Counter: `cosa_runs_total{outcome}`, `cosa_tool_calls_total{capability,outcome}`, `cosa_model_tokens_total{direction,model}`, `cosa_approvals_total{decision}`.
  - Histogram: `cosa_run_duration_seconds`, `cosa_approval_wait_seconds`, `cosa_tool_call_duration_seconds`.
  - Gauge: `cosa_worker_active_leases`, `cosa_scheduler_queue_depth` (worker poll query), `cosa_model_cost_usd_total` (Counter thực ra — tính từ token × bảng giá `DEEPSEEK_PRICE_*`).
- Endpoint `GET /metrics` (Prometheus text) trên api. Worker: expose trên cùng health server (Part 1E) port 8090 `/metrics`.
- Cập nhật kernel + capability gateway + approval service để bơm số vào metrics (hook tại nơi đã có event emit, không thêm đường dữ liệu mới).

### 2B.3 `/events/metrics` — xác nhận + mở rộng

- Xác nhận handler đăng ký + yêu cầu workspace auth (nếu thiếu → thêm handler theo pattern `services/company/*/handlers/`).
- Mở rộng số liệu: thêm event-types active, DLQ oldest age, relay lag.

### 2B.4 Structured logging

- `apps/cosa/observability/logging.py`: cấu hình `structlog` (hoặc stdlib + JSON formatter) — mọi log dòng JSON: `ts`, `level`, `msg`, `service`, `run_id`, `workspace_id`, `trace_id`. Contextvars để tự đính `run_id`/`workspace_id` trong scope xử lý.
- Encore services: bật JSON log (Encore hỗ trợ), thống nhất field name `run_id`/`workspace_id`.
- **Không** log payload nhạy cảm/secret/DSN (rà lại các log hiện có).

### 2B.5 Dashboard + alert (doc)

- `docs/operations/observability.md`: liệt kê metric + ý nghĩa + ngưỡng cảnh báo đề xuất (DLQ > 0, approval_wait p95 > X, run outcome error rate > Y%, worker leases = 0 khi có queue depth > 0, scheduler queue depth tăng đơn điệu).
- Không bắt buộc dựng Grafana trong phạm vi này; cung cấp scrape config mẫu + PromQL.

## Reuse

- `services/company/events/services/event-metrics.service.ts` — pattern query trạng thái, không tính lại.
- Event vocabulary hiện có (`run.started`, `tool.called`, …) — bơm metric tại điểm emit.
- Encore built-in tracing/logging.
- `apps/cosa/worker/health.py` (Part 1E) — thêm `/metrics` vào cùng server.

## Test / verify

- `curl api/metrics` → text Prometheus hợp lệ, có các metric name ở trên; chạy 1 run → counter tăng.
- `OTEL_EXPORTER_OTLP_ENDPOINT` set tới 1 collector local → thấy trace `run` có span con `tool.call`, `trace_id` xuyên sang Encore.
- Không set OTLP → app chạy bình thường (no-op exporter).
- `grep` log output test → dòng JSON có `run_id`, không có `DEEPSEEK_API_KEY`/DSN.
- Unit test: `test_metrics.py` (counter tăng đúng theo outcome), `test_logging.py` (redaction).

## Definition of Done

- [ ] OTel init ở api + worker; span kernel/tool/scheduler/lease; propagate sang Encore.
- [ ] `/metrics` trên api + worker với bộ metric runtime; kernel/gateway/approval bơm số.
- [ ] `/events/metrics` xác nhận authed + mở rộng.
- [ ] Structured JSON log + correlation + redaction, xuyên Python↔Encore.
- [ ] `docs/operations/observability.md` (metric, ngưỡng, PromQL, scrape mẫu).

## Rủi ro

- Thêm instrument vào hot path (mỗi tool call) → giữ nhẹ (counter/histogram in-process, không blocking I/O).
- Bảng giá model để tính cost có thể lỗi thời → đặt trong env/config, ghi rõ "ước lượng".
- structlog thay logging hiện có → làm dần theo module, giữ tương thích handler cũ.
