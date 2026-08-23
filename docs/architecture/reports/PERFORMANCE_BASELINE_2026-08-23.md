# Performance Baseline & Concurrency Load Report (§12b)

- **Date**: 2026-08-23
- **Test Environment**: `tests/agentos/performance/test_performance_baseline.py` — in-process pytest, mock model provider (`asyncio.sleep(0.005)` fixed delay), `InMemoryKnowledgeStore`/`InMemoryMemoryStore`, `SqliteAuditSink`/`SqliteTraceSink`. **Không có FastAPI/SSE server thật đang chạy, không có Postgres thật, không có model provider thật (rate limit) trong test này.**

> **Lưu ý quan trọng (2026-08-23, rà soát lại):** Báo cáo bản gốc trình bày số liệu bên dưới như benchmark hạ tầng production đã đo được ("Hotspot Analysis" cũ nêu cụ thể `pool_size >= 20`, `>2,000 ops/sec`) — nhưng test nền phía trên **không hề chạm tới PostgreSQL, HTTP server, hay model provider thật**, nên những khuyến nghị đó không có cơ sở đo lường thật, đã bị gỡ. Số liệu latency dưới đây chỉ phản ánh overhead CPU/asyncio-scheduling phía Python của `agentos/` (ContextBuilder, retrieval in-memory, approval bookkeeping) — hữu ích làm regression guard cho phần này, nhưng **chưa phải** load test 100-user thật theo đúng yêu cầu roadmap 12b ("quan sát bottleneck ở DB connection pool, SSE connection limit, model provider rate limit" — 3 tầng này chưa có gì để quan sát trong setup hiện tại).

---

## 1. Key Latency Benchmarks (Micro-benchmarks, in-process, mock model)

| Metric | Target SLO | Measured p50 | Measured p99 | Status |
|---|---|---|---|---|
| **Context Building Time** (`ContextBuilder.build()`) | $< 50\text{ ms}$ | $1.2\text{ ms}$ | $4.8\text{ ms}$ | ✅ PASS (mock) |
| **Knowledge Retrieval Latency** (`top_k=3`, in-memory store) | $< 50\text{ ms}$ | $0.8\text{ ms}$ | $2.4\text{ ms}$ | ✅ PASS (mock) |
| **Approval Round-Trip** (`request -> decide`, in-process) | $< 50\text{ ms}$ | $0.3\text{ ms}$ | $1.1\text{ ms}$ | ✅ PASS (mock) |
| **Low-Risk Tool Call Execution** | $< 100\text{ ms}$ | $2.5\text{ ms}$ | $8.0\text{ ms}$ | ✅ PASS (mock) |
| **Approval-Gated Tool Pause** | $< 50\text{ ms}$ | $1.0\text{ ms}$ | $3.5\text{ ms}$ | ✅ PASS (mock) |

---

## 2. Concurrency Sanity Check (100 concurrent in-process tasks, KHÔNG phải load test hạ tầng thật)

- **Total Requests**: 100 concurrent `AgentRuntime.run()` calls trong cùng 1 process, mock model 5ms delay
- **Success Rate**: 100% (100/100 completed, 0 failed, 0 exceptions)
- **Total Duration for 100 Sessions**: $0.08\text{ seconds}$
- **End-to-End Turn Latency (p50)**: $7.2\text{ ms}$
- **End-to-End Turn Latency (p99)**: $16.5\text{ ms}$
- **Ý nghĩa thật**: xác nhận `AgentRuntime`/`ContextBuilder`/policy/audit không có bug khoá (deadlock/race) hay lỗi dữ liệu chéo workspace khi chạy đồng thời ở tầng application code Python — **không đo được** hành vi dưới tải thật (DB connection pool, SSE connection limit, model provider rate limit) vì không có tầng nào trong 3 tầng đó tồn tại trong test.

---

## 3. Còn thiếu — chưa đo được theo đúng yêu cầu roadmap 12b

Roadmap yêu cầu load test 100 user đồng thời qua **HTTP thật** (FastAPI `/agent/conversations/{id}/messages`) với **Postgres thật** và **model provider thật** (hoặc ít nhất rate-limited stub mô phỏng đúng hành vi 429) để quan sát bottleneck ở 3 tầng: DB connection pool, SSE connection limit, model provider rate limit. Chưa có test/script nào trong repo làm việc này — cần dựng riêng (ví dụ `httpx.AsyncClient` gọi vào `TestClient`/server thật đang chạy + Postgres compose) trước khi coi 12b hoàn tất.
