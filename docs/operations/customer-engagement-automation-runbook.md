# Customer Engagement Automation Runbook

Tài liệu hướng dẫn vận hành, cấu hình luật tự động hoá xác định (**Deterministic Automation**) và kiểm tra giám sát trong phân hệ Customer Engagement.

---

## 1. Nguyên tắc cốt lõi (Core Invariants)

1. **Deterministic & No LLM**: Automation chạy hoàn toàn dựa trên Structured Facts (`AutomationFacts`) và cây Predicate thuần (`evaluatePredicate`). Không gọi mô hình ngôn ngữ lớn (LLM), không dùng `eval` hoặc dynamic code execution.
2. **Versioned & Immutable Rules**: Mọi thay đổi trên rule tạo một `version` mới với trạng thái mặc định là `enabled: false`.
3. **Idempotent Application**: Mọi hành động áp dụng đều được ghi vết vào ledger `engagement_automation_applications` với `dedupe_key` xác định. Không bao giờ tạo trùng hiệu ứng.
4. **Delayed Schedule Re-check**: Các hành động hẹn giờ (`schedule_delayed`) sẽ được worker Housekeeping kiểm tra lại toàn bộ:
   - Rule còn hiệu lực?
   - Condition còn đúng trên facts hiện tại?
   - Nhân viên đã tiếp quản (`human_assigned`)?
   Nếu không thoả mãn, hành động sẽ bị bỏ qua (`skipped`) và ghi rõ lý do.
5. **Fail-Closed Decision Request**: Nếu không tìm thấy thẩm quyền tương ứng ở trạng thái `enabled`, hệ thống không tạo Decision Request và ghi nhận `skipped_no_authority`.

---

## 2. Danh mục Trigger & Facts

### 2.1 Trigger Hỗ trợ
- `thread_opened`: Kích hoạt khi Thread mới được mở.
- `message_received`: Kích hoạt khi nhận tin nhắn inbound mới.
- `thread_status_changed`: Kích hoạt khi trạng thái thread thay đổi.
- `csat_recorded`: Kích hoạt khi khách hàng đánh giá điểm CSAT (1-5).
- `time_sweep`: Quét định kỳ mỗi tick của housekeeping.

### 2.2 Fact Keys (`FACT_KEYS`)
- `thread.status`, `thread.priority`, `thread.tier`, `thread.activeMode`, `thread.ownerMemberId`, `thread.escalationLevel`, `thread.ageMinutes`, `thread.minutesSinceLastCustomerMsg`, `thread.firstResponded`, `thread.hasOpenDecisionRequest`
- `inbox.channelType`, `inbox.locale`, `inbox.businessHoursOpen`
- `sla.firstResponseDueInMinutes`, `sla.resolutionDueInMinutes`, `sla.firstResponseBreached`, `sla.resolutionBreached`, `sla.pctToFirstResponseBreach`
- `contact.present`, `contact.doNotContact`
- `account.present`
- `customer.present`, `customer.healthStatus`, `customer.tier`
- `lastMessage.direction`, `lastMessage.visibility`
- `csat.latestScore`, `csat.latestRecordedMinutesAgo`
- `labels` (Array)

---

## 3. Danh mục Actions & Idempotency Key

| Action Type | Payload | Dedupe Key | Mô tả |
| --- | --- | --- | --- |
| `route_to_team` | `{ teamId }` | `team:<teamId>` | Phân phối thread về hàng đợi nhóm |
| `route_to_member` | `{ memberId }` | `member:<memberId>` | Gán trực tiếp thread cho nhân viên |
| `set_priority` | `{ priority }` | `priority:<priority>` | Cập nhật độ ưu tiên của thread |
| `apply_label` | `{ labelKey, taxonomyVersion? }` | `label:<labelKey>` | Gắn nhãn phân loại vào thread |
| `create_follow_up_task` | `{ title, dueInHours }` | `task:<title>` | Tạo tác vụ follow-up |
| `snooze` | `{ minutes }` | `snooze:<minutes>` | Tạm ẩn thread trong N phút |
| `reopen` | `{}` | `reopen` | Mở lại thread đã giải quyết |
| `escalate` | `{}` | `escalate` | Tăng `escalation_level` và kích hoạt route |
| `create_decision_request` | `{ decisionKind }` | `dr:<decisionKind>` | Tạo yêu cầu phê duyệt có thẩm quyền |
| `schedule_delayed` | `{ delayMinutes, action, requireStillTrue }` | `sched:<delay>:<action>` | Hẹn giờ thực hiện action có kiểm tra lại facts |

---

## 4. Hướng dẫn Quản trị Rule

### 4.1 Tạo / Cập nhật Rule
```bash
POST /commercial/engagement/automation/rules
{
  "ruleKey": "escalate_vip_sla_breach",
  "name": "Escalate VIP on SLA Breach",
  "trigger": "time_sweep",
  "priority": 10,
  "condition": {
    "all": [
      { "fact": "thread.tier", "op": "eq", "value": "vip" },
      { "fact": "sla.firstResponseBreached", "op": "eq", "value": true }
    ]
  },
  "actions": [
    { "type": "escalate" },
    { "type": "apply_label", "labelKey": "vip_breached" }
  ]
}
```

### 4.2 Kiểm thử Khô (Dry-Run) trước khi Bật
```bash
POST /commercial/engagement/threads/<THREAD_ID>/automation/dry-run
{
  "trigger": "time_sweep"
}
```
Trả về kết quả khớp (`matched`) và facts trích xuất được mà **không thực hiện bất kỳ thay đổi nào**.

### 4.3 Kích hoạt Rule
```bash
POST /commercial/engagement/automation/rules/escalate_vip_sla_breach/enable
```

### 4.4 Tắt Rule
```bash
POST /commercial/engagement/automation/rules/escalate_vip_sla_breach/disable
```
Sau khi disable, toàn bộ trigger mới và schedule pending của rule sẽ bị bỏ qua với `skip_reason: "rule_disabled"`.
