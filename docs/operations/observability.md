# COSA Observability & Monitoring Guide

Tài liệu chuẩn hóa hệ thống giám sát, cảnh báo và chỉ số vận hành (Observability & Monitoring) cho toàn bộ hệ thống COSA Multi-Agent Platform & Encore Business Services theo kế hoạch **TPR Part 2B**.

---

## 1. Kiến trúc Tổng quan

Hệ thống Observability bao gồm 3 trụ cột (Pillars of Observability):

```mermaid
flowchart TB
    subgraph ExecutionPlane [COSA Execution Plane]
        API[COSA API :8000]
        Worker[COSA Worker :8090]
        OTelSDK[OpenTelemetry SDK]
        PromClient[Prometheus Client]
        JSONLog[Structured JSON Logs]
    end

    subgraph BusinessPlane [Encore Business Services]
        CompanyAPI[Company Services :4000]
        OutboxDB[(Postgres Outbox)]
        EventMetricsAPI[/events/metrics]
    end

    subgraph ObservabilityCollector [Telemetry Backend]
        OTelCollector[OpenTelemetry Collector]
        Prometheus[Prometheus / VictoriaMetrics]
        LogAggregator[Loki / FluentBit / CloudWatch]
    end

    API -->|W3C traceparent| CompanyAPI
    API -->|OTLP Traces| OTelCollector
    Worker -->|OTLP Traces| OTelCollector
    API -->|/metrics| Prometheus
    Worker -->|/metrics :8090| Prometheus
    CompanyAPI -->|Event Metrics| Prometheus
    JSONLog --> LogAggregator
```

- **Distributed Tracing**: OpenTelemetry SDK trong Python (`apps/cosa/observability/otel.py`) instrument FastAPI, HTTPX client, kernel reasoning loops (`kernel.run`, `kernel.resume`), tool executions (`capability.execute`), và scheduler task claim/lease management. Propagate context qua chuẩn W3C `traceparent` sang Encore (`services/company`).
- **Runtime Metrics**: Prometheus metrics registry (`apps/cosa/observability/metrics.py`) xuất bản endpoint `GET /metrics` trên cả API Gateway (`:8000/metrics`) và Worker Health Server (`:8090/metrics`).
- **Event Backbone Metrics**: Endpoint `GET /events/metrics` trên Encore (`services/company/events/event-operations.api.ts`) giám sát backlog, DLQ, relay lag và event throughput theo từng workspace.
- **Structured JSON Logging**: Format JSON nhất quán (`ts`, `level`, `msg`, `service`, `run_id`, `workspace_id`, `trace_id`, `span_id`) kèm bộ lọc tự động che giấu (redact) API keys, DSNs và credentials.

---

## 2. Danh mục Runtime Metrics

### 2.1 COSA Python Runtime Metrics (`/metrics`)

| Tên Metric | Kiểu | Nhãn (Labels) | Ý nghĩa & Đơn vị |
| :--- | :--- | :--- | :--- |
| `cosa_runs_total` | Counter | `outcome` (`completed`, `failed`, `waiting_approval`, `cancelled`) | Tổng số lượt thực thi agent run. |
| `cosa_run_duration_seconds` | Histogram | *None* (Buckets: 0.1s – 300s) | Thời gian hoàn tất 1 lượt run của agent. |
| `cosa_tool_calls_total` | Counter | `capability`, `outcome` (`success`, `failed`, `waiting_approval`, `denied`) | Tổng số lần gọi capability tool. |
| `cosa_tool_call_duration_seconds` | Histogram | *None* (Buckets: 0.05s – 30s) | Thời lượng thực thi mỗi tool call. |
| `cosa_model_tokens_total` | Counter | `direction` (`input`, `output`), `model` | Số token LLM tiêu thụ qua model API. |
| `cosa_model_cost_usd_total` | Counter | `model` | Ước tính chi phí USD dựa trên bảng giá model. |
| `cosa_approvals_total` | Counter | `decision` (`approved`, `rejected`, `expired`, `timeout`) | Số quyết định phê duyệt hành động từ con người. |
| `cosa_approval_wait_seconds` | Histogram | *None* (Buckets: 1s – 3600s) | Thời gian chờ từ khi yêu cầu approval đến khi quyết định. |
| `cosa_worker_active_leases` | Gauge | *None* | Số lượng lease đang được worker nắm giữ đồng thời. |
| `cosa_scheduler_queue_depth` | Gauge | *None* | Số lượng task đang chờ hoặc đang xử lý trong scheduler queue. |

### 2.2 Encore Event Backbone Metrics (`/events/metrics`)

| Trường | Kiểu | Ý nghĩa |
| :--- | :--- | :--- |
| `outboxBacklog` | number | Số lượng event đang ở trạng thái `pending` chưa relay. |
| `outboxOldestPendingAgeSec` | number \| null | Tuổi (giây) của event pending cũ nhất trong hàng đợi. |
| `outboxClaimed` | number | Số lượng event đang được relay worker xử lý. |
| `outboxRetrying` | number | Số lượng event đang trong quá trình thử lại (`attempt_count > 0`). |
| `outboxDeadLetter` | number | Số lượng event bị chuyển vào Dead Letter Queue (`status = 'dead'`). |
| `outboxDeadLetterOldestAgeSec`| number \| null | Tuổi (giây) của message cũ nhất kẹt trong DLQ. |
| `outboxRelayLagSec` | number \| null | Độ trễ relay (tuổi của event pending/claimed cũ nhất). |
| `deliveredLast24h` | number | Số lượng event đã giao thành công trong 24 giờ qua. |
| `eventTypesActive` | number | Số lượng distinct `event_type` đang có trong outbox. |

---

## 3. Ngưỡng Cảnh báo Đề xuất (Alert Thresholds & SLOs)

| Cảnh báo (Alert Name) | Mức độ | Điều kiện kích hoạt (Threshold) | Ý nghĩa / Hành động khắc phục |
| :--- | :--- | :--- | :--- |
| **`OutboxDeadLetterDetected`** | `CRITICAL` | `outboxDeadLetter > 0` | Có event không thể phân phối sau max retries. Cần kiểm tra lý do (`dead_letter_reason`) và gọi `/events/outbox/:id/retry` sau khi sửa lỗi. |
| **`OutboxRelayLagHigh`** | `WARNING` | `outboxRelayLagSec > 60` trong 5 phút | Relay worker bị chậm hoặc tắc nghẽn outbox. Kiểm tra DB connection pool và outbox relay process. |
| **`HighAgentRunErrorRate`** | `CRITICAL` | `rate(cosa_runs_total{outcome="failed"}[5m]) / rate(cosa_runs_total[5m]) > 0.05` | Tỷ lệ lỗi run > 5% trong 5 phút. Kiểm tra log exception, provider upstream (DeepSeek/OpenAI), hoặc schema validation. |
| **`WorkerLeaseStallWithQueue`** | `CRITICAL` | `cosa_worker_active_leases == 0 and cosa_scheduler_queue_depth > 0` trong 2 phút | Có task trong queue nhưng không worker nào acquire lease để xử lý. Kiểm tra worker liveness và DB lock. |
| **`SchedulerQueueAccumulating`** | `WARNING` | `deriv(cosa_scheduler_queue_depth[10m]) > 0.5` | Hàng đợi scheduler tăng liên tục (inflow > outflow). Cần scale thêm worker instances. |
| **`ApprovalWaitTimeHigh`** | `INFO` / `WARNING` | `histogram_quantile(0.95, sum(rate(cosa_approval_wait_seconds_bucket[15m])) by (le)) > 1800` | p95 thời gian chờ duyệt > 30 phút. Cần nhắc nhở người phụ trách duyệt qua Slack/Email. |

---

## 4. Cấu hình Scrape Mẫu (Prometheus Scrape Config)

File `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'cosa-api'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['cosa-api:8000']
        labels:
          service: 'cosa-api'
          env: 'production'

  - job_name: 'cosa-worker'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['cosa-worker-1:8090', 'cosa-worker-2:8090']
        labels:
          service: 'cosa-worker'
          env: 'production'
```

---

## 5. Truy vấn PromQL Mẫu cho Dashboards

### 5.1 Run Throughput & Error Rate
- **Tổng số runs mỗi giây:**
  ```promql
  sum(rate(cosa_runs_total[5m])) by (outcome)
  ```
- **Tỷ lệ lỗi Runs (%):**
  ```promql
  (sum(rate(cosa_runs_total{outcome="failed"}[5m])) / sum(rate(cosa_runs_total[5m]))) * 100
  ```

### 5.2 Latency Percentiles
- **Run Latency p50, p95, p99:**
  ```promql
  histogram_quantile(0.95, sum(rate(cosa_run_duration_seconds_bucket[5m])) by (le))
  ```
- **Tool Call Latency p95:**
  ```promql
  histogram_quantile(0.95, sum(rate(cosa_tool_call_duration_seconds_bucket[5m])) by (le, capability))
  ```

### 5.3 Token Consumption & Cost Estimation
- **Token rate theo Model (tokens/giây):**
  ```promql
  sum(rate(cosa_model_tokens_total[5m])) by (model, direction)
  ```
- **Ước tính chi phí tiêu thụ lũy kế (USD/giờ):**
  ```promql
  sum(increase(cosa_model_cost_usd_total[1h])) by (model)
  ```

### 5.4 Queue & Lease Concurrency
- **Số lease active:**
  ```promql
  cosa_worker_active_leases
  ```
- **Độ sâu hàng đợi scheduler:**
  ```promql
  cosa_scheduler_queue_depth
  ```

---

## 6. Tiêu chuẩn Structured Logging & Tracing Correlation

Mọi log từ Python backend được xuất bản theo định dạng JSON với schema sau:

```json
{
  "ts": "2026-08-28T10:15:30.123456Z",
  "level": "INFO",
  "msg": "Executing run task",
  "service": "cosa-api",
  "logger": "cosa.api.routes",
  "run_id": "run_0191837f48a1",
  "workspace_id": "ws_enterprise_01",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

### Quy tắc Bảo mật & Redaction
1. **Không log raw secrets**: Mọi token dạng `sk-...`, `Bearer eyJ...`, hoặc password trong chuỗi kết nối DB (`postgres://user:pass@host...`) được filter tự động thay thế bằng `[REDACTED]`.
2. **Correlation xuyên suốt**: Khi nhận request, correlation context (`run_id`, `workspace_id`) được bind qua `log_context()` và tự động đính kèm vào tất cả các log records phát sinh trong luồng xử lý đó.
