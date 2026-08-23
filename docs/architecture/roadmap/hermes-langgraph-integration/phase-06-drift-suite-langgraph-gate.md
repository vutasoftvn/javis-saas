# Phase 6 — Spec-Drift & Governance-Drift Test Suite (+ LangGraph Adoption Decision Gate)

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 6" (P0.10). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3 — **đây là gate duy nhất được phép quyết định adoption LangGraph.**

## Mục tiêu

9 case bắt buộc ở Master doc §41.1 đều có test độc lập, pass — và (mới) quyết định adoption LangGraph (Adopt / Reject / Defer) dựa trên bằng chứng đầy đủ từ Phase 3-5, không phải phỏng đoán.

## Điều kiện tiên quyết

Phase 1 (spec pinning), Phase 2 (durable run), Phase 5 (approval) đã xong — case này lắp ráp lại toàn bộ hệ thống đã build.

## Việc cụ thể (gốc) — 9 case, mỗi case 1 file test riêng, không gộp chung

- **A. Workflow spec drift:** v1 pause → publish v2 → restart → resume → phải chạy v1, không có node của v2.
- **B. AgentSpec privilege widening:** v1 autonomy thấp → pause → publish v2 autonomy cao → resume → Run cũ không kế thừa v2.
- **C. Current revocation:** Run được allow → pause → principal/connector bị revoke → resume → DENY thắng.
- **D. Risk increase:** approve ở MEDIUM → risk tăng lên CRITICAL trước khi resume → evidence cũ không đủ/stale.
- **E. Risk/policy relaxation:** approve ở CRITICAL/FounderApproval → policy sau đó nới lỏng xuống LOW/ALLOW → resume → constraint lịch sử vẫn giữ.
- **F. Orthogonal approval requirement:** request cần FounderApproval, hiện tại cần FinanceAdminApproval → resume → cần CẢ HAI trừ khi có role semantics chứng minh khác.
- **G. Same tool twice:** gọi `send_email` 2 lần → `tool_call_id` khác nhau, approval/evidence không cross.
- **H. Target drift:** cùng capability + payload nhưng connector/account/schema/credential thay đổi → approval cũ stale.
- **I. Side-effect committed before crash:** remote system commit thành công → process chết trước khi mark success → restart → không duplicate (tái sử dụng test từ Phase 4).

## Definition of Done — Phase 6 (gốc)

- 9 file test, mỗi file pass độc lập, không phụ thuộc thứ tự chạy lẫn nhau.
- CI (nếu có) chạy được cả 9 case trong một suite riêng "governance drift suite".

## Bổ sung Hermes/LangGraph — LangGraph Adoption Decision Gate

**Đây là gate duy nhất trong toàn bộ roadmap được phép quyết định adopt/reject/defer LangGraph.** Không quyết định sớm hơn (Phase 3 chỉ là technical spike; Phase 4/5 chỉ tích hợp thêm boundary thật vào spike).

**Điều kiện để chạy gate này:** branch `experiment/langgraph-spike` đã tích hợp qua Phase 3 (technical feasibility), Phase 4 (Capability Gateway + readiness thật), Phase 5 (approval thật + interrupt semantics) — nếu spike đã bị bỏ ở phase nào đó giữa chừng, ghi nhận **Reject** với lý do tại điểm dừng, không cần chạy hết acceptance matrix.

**Việc cụ thể:**

1. Chạy đầy đủ acceptance matrix HL-01 → HL-18 (định nghĩa nguyên văn từ supplement gốc §45, liệt kê lại dưới đây để tiện tham chiếu) trên branch spike, dùng baseline thật từ Phase 4/5:

   | ID | Tên | Điều kiện pass |
   |---|---|---|
   | HL-01 | Context lifetime | Stable fragments không đổi khi CURRENT/EPHEMERAL facts đổi (chỉ liên quan nếu Phase 7 context đã có; với LangGraph track có thể N/A) |
   | HL-02 | Business truth thắng stale memory | Business service result là authoritative |
   | HL-03 | Conversation tenant isolation | Không cross-tenant recall (N/A cho track LangGraph thuần) |
   | HL-06 | Child authority attenuation | N/A ở phase này (thuộc Phase 9 delegation) |
   | HL-11 | WorkflowSpec compiler | Cùng WorkflowSpec compile deterministic ra cùng StateGraph |
   | HL-12 | Workflow version pinning với LangGraph | v1 paused Run resume đúng v1 sau khi v2 publish (test case A tương tự, chạy lại trên LangGraph runtime) |
   | HL-13 | Parallel pending-write recovery | Sibling branch thành công sống sót qua crash/failure |
   | HL-14 | Approval resume | COSA exact invocation identity + temporal governance vẫn authoritative (đã test ở Phase 5) |
   | HL-15 | Side-effect crash window | Remote success trước local commit không tạo duplicate side effect sau replay |
   | HL-16 | Thread identity | 2 Run trong 1 Conversation không share graph execution state (`thread_id ≈ run_id`, không map tự động sang `conversation_id`) |
   | HL-17 | Run fork | Replay/fork tạo lineage rõ ràng, không mutate history gốc |
   | HL-18 | Checkpoint serialization security | Checkpoint serializer production reject/control unsafe arbitrary object reconstruction |

   (Các HL-04/05/07/08/09/10 thuộc track Hermes, không liên quan LangGraph — verify ở Phase 9, không lặp lại ở đây.)

2. Ghi kết quả pass/partial/fail từng item vào `docs/architecture/langgraph_spike_results.md` (tiếp tục từ Phase 3/5).
3. Quyết định 1 trong 3, ghi vào **ADR-LANGGRAPH** (`docs/architecture/adr/ADR-LANGGRAPH-adoption-decision.md`):
   - **Adopt** — merge `experiment/langgraph-spike` vào main, engineering đầy đủ tiếp tục ở Phase 9 (migrate các workflow usage hiện tại sang LangGraph một cách cẩn trọng, không big-bang).
   - **Reject** — đóng branch (không xóa — giữ lịch sử git để tham khảo), áp dụng ý tưởng supersteps/reducer/pending-writes/state-context-separation vào WorkflowEngine native ở Phase 9 (theo supplement gốc §47).
   - **Defer** — ADR mở, re-evaluate ở Phase 10 khi có trigger sản phẩm cụ thể; dùng WorkflowEngine native cho Phase 7-9.
4. Điều kiện complexity gate (từ supplement gốc §46, giữ nguyên tinh thần): chỉ Adopt nếu `custom code removed + failure semantics improved + tests simplified/strengthened` > `framework coupling + extra persistence + integration complexity`. Đây là đánh giá định tính cuối cùng do người quyết định (không phải agent) đưa ra dựa trên bằng chứng đã log.

## Test bắt buộc (bổ sung)

- Toàn bộ acceptance matrix HL-01, HL-02, HL-11 đến HL-18 (loại trừ HL-03/06 nếu N/A ở track LangGraph) chạy trên branch spike, log kết quả.

## Definition of Done — Phase 6 (bổ sung)

- ADR-LANGGRAPH đóng với quyết định rõ ràng (Adopt/Reject/Defer) + bằng chứng HL-01→HL-18 (hoặc lý do dừng sớm nếu Reject tại điểm dừng giữa chừng).

## Rủi ro/lưu ý

**Gốc:** Đây là nơi dễ phát hiện thiếu sót từ các phase trước (vd. `ExecutionTargetSnapshot` thiếu field cần cho case H) — chấp nhận quay lại phase trước bổ sung, không patch tắt case test.

**Bổ sung:** Rủi ro lớn nhất ở phần LangGraph gate là quyết định thiên vị theo sunk cost (đã đầu tư 3 phase vào spike nên miễn cưỡng Adopt dù bằng chứng yếu) — complexity gate ở mục 4 tồn tại chính xác để chống lại thiên kiến này; nếu HL-* có nhiều PARTIAL/FAIL, nghiêng về Reject/Defer thay vì Adopt "cho đỡ phí công".
