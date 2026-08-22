# AI Agent OS — Audit Notes (Giai đoạn 0)

**Ngày:** 2026-08-22
**Loại:** Audit read-only, không có thay đổi code
**Liên quan:** `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md`

5 câu hỏi còn treo trong gap analysis, trả lời bằng bằng chứng file cụ thể.

## 0.1 — Workflow engine: `agentos/workflows/` vs `legacy/backend/integrations/workflows`

| Tính năng | `agentos/workflows/` | `legacy/backend/integrations/workflows` |
|---|---|---|
| Retry logic | ❌ | ❌ |
| Compensation/Rollback | ❌ | ❌ |
| Parallel branch/fork-join | ❌ (linear only) | ❌ |
| Approval step | ✅ `ApprovalGateStep` — `agentos/workflows/approval_step.py:10-58` | ✅ `WorkflowApproval` model — `legacy/backend/integrations/workflows/models.py:83-94`, bảng `workflow_approvals` |
| Version history | ❌ | ✅ `WorkflowVersion` — `legacy/backend/integrations/workflows/models.py:54-69` (`version_no`, `current_version_id`) |

**Kết luận:** không bên nào có retry/compensation/parallel — cả 2 đều thiếu ngang nhau (khác với giả định ban đầu trong gap analysis rằng "backend/integrations/workflows có thể tốt hơn"). Điểm khác biệt thật duy nhất: `legacy/backend/integrations/workflows` có version history cho workflow definition, `agentos/workflows/` thì không. → cập nhật Phần A7/Phần B: workflow gap (retry/compensation/parallel) là gap chung cho CẢ HAI hệ, không riêng agentos/.

## 0.2 — Eval harness

✅ **Tồn tại thật, không phải chỉ field:**
- `agentos/evals/agent_eval.py` — `evaluate_agent_run()` (dòng 17-36): tính goal_completion, tool_calls_made, latency_seconds.
- `agentos/evals/workflow_eval.py` — `evaluate_workflow()` (dòng 16-31): tính completed, failed_step_name, time_to_completion_seconds, reached_approval_gate.
- Có test tham chiếu trong `legacy/backend/tests/test_agent_platform_conformance.py`, `test_skills_lifecycle_p5.py`.

**Kết luận:** gap analysis Phần A9 ghi "không tìm thấy eval harness" — **cần sửa**: eval harness cơ bản (Agent Eval, Workflow Eval) đã có trong `agentos/evals/`, chỉ thiếu Skill Eval / Business Outcome Eval / Model Eval theo đúng phân loại §51 của blueprint.

## 0.3 — Knowledge Layer (ingest→parse→chunk→embed→index)

❌ **Chưa có, chỉ có placeholder gần đúng:**
- `agentos/memory/retrieval.py:10-32` có `MemoryQuery` + `score_relevance()` nhưng là **term-overlap thuần túy**, không gọi embedding, không có vector DB.
- Không tìm thấy bảng `knowledge_sources` trong `legacy/backend/alembic/` hay `legacy/backend/db/models.py`.

**Kết luận:** blueprint §66 (Knowledge Layer) **chưa được implement** ở đâu trong repo — xác nhận dứt khoát, không phải "chưa tìm thấy do search chưa đủ".

## 0.4 — `skillpacks/*` có qua supply_chain pipeline thật không

❌ **Không — static filesystem read, supply_chain chưa được wire vào SkillRegistry.**
- `agentos/skills/registry.py:1-71`: `discover()` đọc trực tiếp `**/manifest.yaml` → `load_skill_manifest()` → lưu status=ACTIVE ngay, **không** import `supply_chain/pipeline.py`.
- `agentos/skills/supply_chain/pipeline.py:21-70` tồn tại và hoạt động (import_candidate→scan→stage→promote_to_active) nhưng **chỉ dành cho EXTERNAL skill**, chưa từng được gọi từ registry cho skill nội bộ (`skillpacks/*`).

**Kết luận:** mọi skill trong `skillpacks/` hiện được registry coi là ACTIVE ngay lập tức, bỏ qua toàn bộ pipeline scan/eval/approval mà blueprint Phụ lục A §13 mô tả là bắt buộc cho production — đây là gap an toàn cần lưu ý, không chỉ là "thiếu tính năng".

## 0.5 — MCP adapter trong `agentos/`

❌ **Không tồn tại.**
- `grep -rn "mcp\|MCP" agentos/` → rỗng.
- Production có sẵn: `legacy/agent_runtime/workforce/tools/transports/mcp_adapter.py` — `MCPToolAdapter` (dòng 7-60), JSON-RPC qua httpx tới MCP server.

**Kết luận:** không phải duplicate (agentos/ đơn giản chưa có), nhưng là gap thật nếu muốn `agentos/tools/` hỗ trợ MCP tool theo blueprint §17.

---

## Cập nhật vào Gap Analysis (Phần A/B) sau audit này

1. **A7 (Event & Workflow):** sửa "thiếu retry, compensation, parallel branch" từ riêng `agentos/workflows/` → gap **chung cho cả 2 workflow engine**. Điểm khác biệt thật là version history (chỉ `legacy/backend/integrations/workflows` có).
2. **A9 (Evaluation):** sửa "không tìm thấy eval harness" → **đã có** Agent Eval + Workflow Eval cơ bản trong `agentos/evals/`; còn thiếu Skill Eval, Business Outcome Eval, Model Eval.
3. **A3 (Knowledge Layer):** xác nhận dứt khoát **chưa có**, không còn là "chưa xác nhận".
4. **A5 (Skill Supply Chain):** xác nhận dứt khoát **chưa wire** — nâng mức độ ưu tiên gap này vì đây là lỗ hổng an toàn (skill nội bộ bỏ qua scan/eval/approval), không chỉ thiếu tính năng tiện lợi.
5. **A4 (Tool/MCP):** xác nhận `agentos/tools/` chưa có MCP adapter — không phải duplicate risk, là feature gap thuần túy.

Điều kiện Giai đoạn 0 đã đạt: cả 5 câu hỏi treo đều có câu trả lời dứt khoát bằng bằng chứng file. Sẵn sàng sang Giai đoạn 1 (ADR).
