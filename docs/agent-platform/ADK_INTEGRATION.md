# Google ADK 2.0 Integration Guide for COSA OS

## Tổng quan (Overview)

Tài liệu này mô tả kiến trúc và cách thức tích hợp Google Agent Development Kit (ADK) 2.0 vào nền tảng COSA Agent Platform theo mô hình Strangler Pattern:
- **Không bypass hạ tầng**: Mọi node trong ADK graph bắt buộc gọi Model qua `ModelGateway` và gọi Tool qua `GovernanceKernel`.
- **An toàn theo Tenant**: Không cho phép client hay model tự ý cung cấp `workspace_id` hay `user_id`.
- **Feature Flag Gating**: Pilot từng domain qua cờ `FLAG_ADK_SALES_PILOT`.

---

## Kiến trúc Tích hợp (Integration Architecture)

```
┌────────────────────────────────────────────────────────┐
│               COSA Agent Platform Entry               │
│         (chat_execution_service / mission_router)      │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
  [Legacy Execution Engine]    [Google ADK 2.0 Graph Runtime]
                                (app.agents.adk_runtime)
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
         [AdkModelAdapter]                            [AdkToolAdapter]
                   │                                           │
                   ▼                                           ▼
          [ModelGateway]                               [GovernanceKernel]
   (Retries / CB / Fallbacks)                    (Policy / Approval / Audit)
```

---

## Mapping Thành phần COSA ↔ ADK

| Khái niệm Google ADK 2.0 | Thành phần tương ứng trong COSA OS | Ghi chú |
|---|---|---|
| Graph / State Graph | `SalesAdkPilotGraph` / `SalesPilotGraphState` | Quản lý state luồng nghiệp vụ theo Pydantic |
| Model Provider | `AdkModelAdapter` → `ModelGateway` | Tránh gọi trực tiếp LLM SDK trong node |
| Tool Node | `AdkToolAdapter` → `GovernanceKernel` | Ghi audit `AgentToolCall` và kiểm soát permission L0-L3 |
| Human in the Loop | `ApprovalService` / `AgentApproval` | Pauses graph khi gặp high-risk / mutating action |
| Tracing / Callbacks | `OpenTelemetry` + `AgentEventRecord` | Xuất traces và timeline realtime qua event bus |

---

## Cách chạy Pilot

1. Bật cờ `adk_sales_pilot` trong workspace:
   ```python
   from app.core.feature_flags import set_feature_flag, FLAG_ADK_SALES_PILOT
   set_feature_flag(db, FLAG_ADK_SALES_PILOT, enabled=True, workspace_id=ws_id)
   ```
2. Thực thi graph pilot:
   ```python
   from app.agents.adk_runtime.sales_graph import SalesAdkPilotGraph

   graph = SalesAdkPilotGraph()
   state = await graph.execute(
       db=db,
       workspace_id=ws_id,
       user_id=user_id,
       goal="Tăng tốc pipeline quý 3",
       run_id=mission_id,
   )
   ```
