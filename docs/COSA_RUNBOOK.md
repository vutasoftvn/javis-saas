# COSA Production Operations Runbook (§12c)

Hướng dẫn vận hành, triển khai, giám sát và xử lý sự cố cho nền tảng JAVIS / COSA.

---

## 1. Khởi Động & Triển Khai Các Thành Phần (Deployment)

### 1.1. Hạ Tầng Dữ Liệu (PostgreSQL & PgVector)
```bash
# Khởi động PostgreSQL với pgvector extension
docker compose up -d postgres

# Chạy migrations cơ sở dữ liệu
cd agentos && python -m alembic upgrade head
```

### 1.2. Business Services Clusters (Encore TypeScript)
```bash
cd services
encore run
# Server lắng nghe tại http://localhost:4000
```

### 1.3. AgentOS Core & API Server (Python FastAPI)
```bash
cd agentos
uvicorn agentos.api.chat.routes:router --host 0.0.0.0 --port 8000
```

### 1.4. Frontend Client (Flutter)
```bash
cd frontend
flutter run -d chrome
```

---

## 2. Giám Sát & Vận Hành (Monitoring & Observability)

1. **Distributed Tracing (OpenTelemetry)**:
   - Tất cả requests và tool calls được gắn `correlation_id` và phát ra spans qua `OtelTracer` (`agentos/observability/otel.py`).
   - Có thể kết nối OTLP Exporter tới Grafana Tempo hoặc Jaeger.
2. **Audit Trail & Governance Logs**:
   - Mọi quyết định chính sách và sự kiện phê duyệt được lưu trữ trong `var/agentos/audit_log.sqlite3` (`SqliteAuditSink`).
   - Log đã được làm sạch 100% không chứa secrets/tokens (`redact_payload`).
3. **Operational Trace Events**:
   - Các sự kiện vận hành (run started, tool requested, tool completed, run completed) lưu trong `var/agentos/traces.sqlite3` (`SqliteTraceSink`).

---

## 3. Quy Trình Xử Lý Sự Cố (Incident Response & Troubleshooting)

### 3.1. Sự Cố: Run Bị Kẹt Ở Trạng Thái `PAUSED` / Chờ Duyệt (Approval Stuck)
- **Nguyên nhân**: Tool có `risk_level=HIGH` hoặc `approval_policy=always` đã tạo approval record nhưng chưa có phản hồi từ người duyệt.
- **Xử lý**:
  1. Kiểm tra danh sách approvals đang pending:
     ```python
     from agentos.core.approval import ApprovalService
     svc = ApprovalService()
     pending = svc.find_pending(run_id="<stuck_run_id>")
     ```
  2. Quyết định phê duyệt hoặc từ chối:
     ```bash
     curl -X POST http://localhost:8000/agent/approvals/<approval_id>/decision \
       -H "Content-Type: application/json" \
       -d '{"approved": true, "reason": "Manually verified by admin"}'
     ```

### 3.2. Sự Cố: File SQLite Trace / Audit Quá Lớn
- **Nguyên nhân**: Số lượng tool calls và event runs tăng cao sau thời gian dài vận hành.
- **Xử lý**:
  - Chạy vacuum hoặc lưu trữ định kỳ các runs đã hoàn thành:
    ```bash
    sqlite3 var/agentos/traces.sqlite3 "VACUUM;"
    ```

### 3.3. Sự Cố: Lỗi Kết Nối Đến External Connector (Slack / Notion)
- **Nguyên nhân**: Token trong Vault bị hết hạn hoặc network gián đoạn.
- **Xử lý**:
  1. Kiểm tra secret store `InMemoryVaultStore` hoặc Vault backend.
  2. Cập nhật lại token mới cho `slack_bot_token` tương ứng với `workspace_id`.
  3. Connector tự động retry với exponential backoff khi gặp lỗi 5xx/429.
