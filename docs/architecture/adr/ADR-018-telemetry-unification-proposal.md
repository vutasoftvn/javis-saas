# ADR-018 (Proposal): Hợp nhất OpenTelemetry (production) và TraceRecorder (agentos/)

## Status

**Proposal — chờ quyết định, phân tích sâu theo yêu cầu.**

## 1. Hiện trạng: 2 cơ chế trace độc lập, không tương thích

### 1.1 Production — OpenTelemetry (`legacy/agent_runtime/cosa_core/telemetry.py`)

```python
tracer = trace.get_tracer("cosa.agent_platform", "1.0.0")

@contextmanager
def trace_span(name, attributes=None):
    safe_attrs = filter_attributes(attributes or {})   # lọc SENSITIVE_KEYS (api_key, secret, password, token, ...)
    with tracer.start_as_current_span(name, attributes=safe_attrs) as span:
        ...

def configure_telemetry(service_name="cosa-brain-api"):
    provider = TracerProvider(...)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))  # xuất ra console, CHƯA nối OTLP collector thật
    trace.set_tracer_provider(provider)
```

Đặc điểm:
- Chuẩn công nghiệp (W3C Trace Context, span nesting tự động qua `contextvars`, tương thích Jaeger/Tempo/Datadog/... nếu nối exporter thật).
- **Chỉ xuất ra Console hiện tại** (`ConsoleSpanExporter`) — chưa nối collector thật, nên dù dùng chuẩn OTel, hiện KHÔNG có nơi lưu trữ/truy vấn trace lâu dài nào đang chạy thật (khác với agentos/'s SQLite, vốn ít nhất persist được).
- Có filter tự động chặn secret/token lộ vào trace — cơ chế bảo mật cụ thể, đáng giữ lại.
- Có sẵn nhưng **graceful fallback**: nếu SDK không cài, `trace_span` vẫn chạy (no-op), không crash.

### 1.2 agentos/ — TraceRecorder tự chế (`agentos/core/trace.py`, `trace_sink.py`)

```python
class TraceRecorder:
    def record(self, name, *, parent_span_id=None, **payload) -> str:
        span = {"span_id": uuid4(), "parent_span_id": parent_span_id, "name": name, "run_id": self.run_id, **payload}
        self.spans.append(span)
        self._event_bus.publish(EventEnvelope(name=name, run_id=self.run_id, payload=payload))
        return span_id

class SqliteTraceSink:
    def attach(self, event_bus): event_bus.subscribe(self._on_event)
    def _on_event(self, event): ...INSERT INTO agent_trace_events...
```

Đặc điểm:
- Tự chế hoàn toàn (không dùng OTel SDK), format riêng (`dict` với `span_id`/`parent_span_id`/`name`/`run_id`).
- **Persist thật** qua SQLite (`var/agentos/traces.sqlite3`) — đúng CLAUDE.md §10 ("SQLite → sessions, traces, cache").
- **Không có span nesting tự động** — mọi caller hiện tại (`Executor`) ghi span phẳng (`parent_span_id=None` luôn), tự nhận là "honest limitation" trong chính docstring.
- Không có filter chặn secret tự động như bản OTel — nếu 1 caller vô tình `record(..., api_key="...")`, nó sẽ được ghi thẳng vào SQLite. **Đây là khoảng trống bảo mật cụ thể so với bản OTel.**
- Không tương thích công cụ observability chuẩn (Jaeger/Tempo/Grafana) — chỉ đọc được qua `export_run()` tự viết.

## 2. Vì sao 2 hệ thống này khác nhau ngay từ đầu

Không phải trùng lặp ngẫu nhiên — mỗi bên tối ưu cho mục tiêu khác nhau tại thời điểm viết:
- OTel (production): tối ưu cho **observability vận hành** (dashboard, alerting, phân tích latency phân tán) — nhưng hiện chưa nối exporter thật nên giá trị đó *chưa hiện thực hóa*.
- TraceRecorder (agentos/): tối ưu cho **audit trail per-run truy vấn lại được** (blueprint §12, §55) — ưu tiên "chạy được ngay, persist thật, không cần hạ tầng ngoài" hơn là tương thích chuẩn ngành, đúng tinh thần MVP của `agentos/`.

## 3. Các phương án hợp nhất

| # | Phương án | Mô tả | Ưu điểm | Nhược điểm |
|---|---|---|---|---|
| **1** | **Giữ nguyên 2 hệ, không hợp nhất** | Không làm gì thêm | Không tốn công, không rủi ro breaking | Duy trì mãi 2 cơ chế trace khác nhau cho 2 phần của cùng 1 sản phẩm — vi phạm tinh thần CLAUDE.md §14; khi `agentos/` cutover production (ADR-013), sẽ phải làm lại từ đầu lúc đó thay vì bây giờ |
| **2** | **agentos/ chuyển hẳn sang OTel SDK, bỏ `TraceRecorder`/`SqliteTraceSink`** | `Executor` gọi `tracer.start_as_current_span()` trực tiếp thay vì `self._trace.record()` | Nesting tự động (giải quyết luôn "honest limitation" về flat span), tương thích chuẩn ngành, filter secret có sẵn | Mất khả năng persist SQLite ngay lập tức trừ khi tự viết 1 `SpanExporter` ghi SQLite (khối lượng việc tương đương viết lại `SqliteTraceSink` nhưng theo API OTel); `EventEnvelope`/`InMemoryEventBus` (dùng cho cả trace lẫn domain event khác — `agent_run.*`, `tool_call.*`) cũng cần tách trace ra khỏi event bus, đổi khá nhiều chỗ đang dùng `trace.export()` |
| **3** | **Bridge: `TraceRecorder.record()` gọi thêm OTel `trace_span()` song song, giữ SQLite làm nguồn sự thật chính** | Mỗi lần `record()`, mở thêm 1 OTel span (best-effort, không raise nếu OTel chưa cấu hình — theo đúng graceful-fallback đã có ở bản `legacy`) | Giữ nguyên toàn bộ `Executor`/test hiện tại, không breaking change; có được cả 2: SQLite persist + khả năng xuất OTel khi có collector thật; là bước trung gian tốt trước khi cutover thật (ADR-013) | Vẫn duy trì 2 định dạng trace song song (dù không xung đột) — cần đảm bảo `run_id`/`span_id` map nhất quán giữa 2 bên để không gây nhầm lẫn khi debug |
| **4** | **Chỉ thêm secret-filter vào `TraceRecorder`, không đụng OTel** | Port `filter_attributes()`/`SENSITIVE_KEYS` từ bản `legacy` vào `TraceRecorder.record()` | Vá đúng khoảng trống bảo mật cụ thể đã tìm thấy (mục 1.2), việc nhỏ, không rủi ro | Không giải quyết vấn đề "2 hệ song song" — chỉ vá 1 triệu chứng |

## 4. Đề xuất

**Ngắn hạn (nên làm ngay, rủi ro thấp, không cần quyết định lớn):** Phương án 4 — port `SENSITIVE_KEYS`/`filter_attributes()` vào `TraceRecorder.record()`. Đây là vá lỗ hổng bảo mật cụ thể, không phụ thuộc quyết định kiến trúc nào khác, nên có thể làm độc lập với phần còn lại của ADR này nếu user đồng ý riêng phần này.

**Trung hạn (sau khi user chọn hướng):** Phương án 3 (bridge) — lý do:
- Không breaking `Executor`/26+ test đang pass.
- Cho phép **đo thử** giá trị thật của OTel (nối 1 collector dev như Jaeger local) mà không cam kết viết lại toàn bộ trace layer trước khi biết có đáng không — đúng nguyên tắc blueprint §95 "Eval Before Autonomy": tăng đầu tư sau khi có bằng chứng.
- Là bước dọn đường tự nhiên cho Phương án 2 khi ADR-013 tới lượt cutover `agentos/` thay `legacy/agent_runtime` thật — lúc đó bỏ hẳn `SqliteTraceSink`, giữ lại OTel làm chuẩn duy nhất, không phải quyết định vội bây giờ.

**Không đề xuất Phương án 2 ngay** — khối lượng việc lớn (viết `SpanExporter` tùy chỉnh + tách trace khỏi event bus) trong khi `agentos/` còn chưa vào production (ADR-013 hướng đi, chưa cutover) — làm bây giờ có rủi ro phải sửa lại lần 2 khi biết thêm yêu cầu thật từ production traffic.

## 5. Câu hỏi cần user trả lời trước khi thực hiện

1. Đồng ý làm ngay phần vá bảo mật (secret filter, Phương án 4) độc lập, không chờ quyết định phần còn lại?
2. Đồng ý hướng trung hạn là Phương án 3 (bridge, không breaking), hay muốn nhảy thẳng lên Phương án 2 (OTel là duy nhất, chấp nhận viết lại nhiều hơn)?
3. Nếu làm bridge (Phương án 3): có sẵn OTel collector nào để nối exporter thật chưa (Jaeger/Tempo/Datadog/khác), hay vẫn tạm dùng `ConsoleSpanExporter` như bản `legacy` hiện tại?
