# Vòng đời thực thi (Execution Lifecycle)

## Run lifecycle

```
PENDING → RUNNING → { COMPLETED | FAILED | CANCELLED | WAITING_APPROVAL }
                          WAITING_APPROVAL → (resume) → RUNNING → ...
```

`RunStatus` enum: `agent_core.contracts.run.RunStatus`.

## Trình tự 1 Run điển hình (có approval)

```
1. kernel.run(request, spec)
2. publish_agent_spec() — bất biến, version+hash pin (agent_registry.published_specs)
3. resolve pinned_skills (nếu có) — raise TRƯỚC khi tạo RunRecord nếu lỗi
4. RunRepository.create_run() — status=RUNNING
5. PromptBundle compose system message
6. Vòng lặp reasoning:
   a. model call → AgentRuntimeError nếu provider fail (KHÔNG convert thành assistant content)
   b. có tool_calls?
      - không → COMPLETED, update_run_status
      - có → cho từng tool call: CapabilityGateway.execute() [10 bước]
        → REQUIRE_APPROVAL? → save_checkpoint, create_approval, status=WAITING_APPROVAL, return
        → ALLOW → execute, tiếp vòng lặp
7. Reviewer POST /agent/approvals/{id}/decision → DurableApprovalService.submit_decision() [CAS]
8. kernel.resume(run_id, checkpoint_ref, updates={"approved": True})
   → verify_and_prepare_resume(): fresh governance + target drift check
   → load checkpoint → tiếp vòng lặp reasoning từ đúng state đã lưu
```

## Invariant xuyên suốt

- `(run_id, tool_call_id)` không đổi từ lúc phát sinh tới lúc side effect thật (kể cả qua resume).
- Governance accumulator monotonic — observation mới không làm yếu constraint đã tích luỹ, và durable qua restart (`GovernanceStateStore`).
- Idempotency claim atomic — 2 request race chỉ 1 thắng.
- Approval CAS — 2 quyết định race chỉ 1 thắng (`decision_version`).

## Event ledger (cho SSE/AG-UI)

Mọi bước trên ghi event vào `agent_core.run_events` (append-only). `map_run_event_to_ag_ui()` (`docs/integrations/ag-ui.md`) normalize cho client UI, giữ nguyên `sequence_no` để client resume qua Last-Event-ID.

## Khác biệt LangChainKernel vs OpenAIAgentsKernel

Cùng lifecycle, khác cách gọi model (LangChain `BaseChatModel.ainvoke()` thay vì raw OpenAI client) và khác kiểu message state (`langchain_core.messages` thay vì dict thô) — checkpoint serialize qua `messages_to_dict`/`messages_from_dict` thay vì JSON dict trực tiếp.
