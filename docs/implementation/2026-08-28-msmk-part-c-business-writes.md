# PART C — Business writes và external integrations

**Ngày:** 2026-08-28
**Phần của:** [marketingskills-makerskills-program](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §5
**Nhánh đề xuất:** mỗi provider/capability một nhánh riêng (`msmk/part-c-<provider>`)
**Phụ thuộc:** PART B1/B2/B3 tương ứng · gate toàn cục như Part B

## Context

Part A–B chỉ tạo bản nháp / artifact / evidence read-only. Part C là nơi skill được phép có
**side effect thật**: ghi business data, gửi nội dung ra ngoài, chi tiêu, deploy. Theo CLAUDE.md
#1/#5/#8 và adoption-plan §"Phase C", mỗi nhóm action là **một sub-plan riêng theo
provider/capability**, không nằm trong adaptation prompt của skill. Không mở Part C như một khối.

Mỗi sub-plan phải định nghĩa capability handler thật với: workspace authorization, policy
evaluation, approval risk (bind `run_id + tool_call_id + checkpoint_ref`), connector grant,
idempotency key, audit event, và post-action verification. Đăng ký tường minh trong
`build_cosa_agent_plane()`; publish/pin SkillSpec sau khi capability integration test xanh.

## Ma trận sub-plan

| Sub-plan | Capability/contract cần | Connector | Approval tối thiểu | Skill tiêu thụ |
| --- | --- | --- | --- | --- |
| `part-c-marketing-write` | `commercial.marketing_context.write`, `commercial.campaign_asset.write`, `commercial.experiment.write` — Company Commercial API workspace-scoped (Part CTX mở rộng thêm write cho asset/experiment) + audit/event + idempotency key | — (nội bộ Company) | Review user trước publish / change business truth; optimistic `expectedRevision` | `marketing.copywriting`, `marketing.campaign-review`, `strategy.experiment-design` |
| `part-c-outbound-comms` | `comms.email.send`, `comms.sms.send`, `comms.social.post` — recipient scope, content preview, rate limit, idempotency key | Connector grant (email/SMS/social provider) qua `ConnectorGrantHttpClient` | **Approval bắt buộc theo từng send/batch**, bind `run_id + tool_call_id + checkpoint_ref`; content preview trong approval payload | (chưa pin skill nào — `cold-email`/`emails`/`sms`/`social` đã loại khỏi 18 pack; chỉ mở khi có pack mới được duyệt riêng) |
| `part-c-ads` | `ads.campaign.write`, `ads.budget.set` — budget cap, attribution source, rollback/pause path | Connector grant (ad platform) | Approval bắt buộc; **không** tự đặt ngân sách / launch; mọi thay đổi có rollback | `commercial.launch`, `commercial.pricing` (chỉ ở mức khuyến nghị — không tự thực thi) |
| `part-c-web-deploy` | `web.tracking.deploy`, `web.schema.deploy` — versioned deploy capability, change review, validation/rollback | Connector grant (hosting/CDN) | Approval deploy; staging trước production; validation gate | `marketing.seo-plan` |
| `part-c-finance-cfo` | Finance-Legal capability (reconciliation), connector grant (bank/accounting), reconciliation evidence, retention policy | Connector grant tài chính | **Quyền tài chính riêng** + approval theo policy Finance-Legal; **không** raw bank data vào prompt | `finance.cfo-review` (runbook Part A-C) |

## Template cho mỗi sub-plan

```
docs/implementation/2026-XX-XX-msmk-part-c-<name>.md
├── Context: action cụ thể, rủi ro, vì sao cần
├── Capability contract: id, risk class, approval_policy, idempotency_semantics,
│   connector_requirements, input/output schema
├── Handler: file apps/cosa/capabilities/<name>.py, đăng ký trong build_cosa_agent_plane()
├── Policy: rule trong CosaPolicyEngine (apps/cosa/policies/) — risk class, approval binding
├── Connector: grant flow, scope, revoke path
├── Skill pin: SkillSpec nào nhận required_capabilities mới, version bump
├── Test (gate production):
│   - capability integration test: plane expose đúng ID; denied connector grant; tenancy isolation
│   - approval bind + resume test: run_id+tool_call_id+checkpoint_ref; target drift → STALE
│   - idempotency: cùng key → không double-execute
│   - restart recovery E2E qua durable worker thật
│   - provider sandbox/fixture + rate-limit/retry + post-action verification
├── Verify: lệnh cụ thể
└── Definition of Done
```

## Nguyên tắc chặn (áp cho mọi sub-plan)

1. Không suy ra quyền gửi / chi tiêu từ nội dung skill (`marketingskills` AGENTS.md không phải grant).
2. Approval phải bind `run_id + tool_call_id + checkpoint_ref`, không lookup theo tên action
   (CLAUDE.md #5). Constraint đã `REQUIRE_APPROVAL` không tự mất khi policy sau nới lỏng.
3. Connector/integration chỉ qua connector grant đã kiểm (`ConnectorGrantHttpClient`), không
   adapter/API trực tiếp từ skill instruction.
4. Không secret/API key vào prompt / skillpack / frontend bundle / source control.
5. E2E cho workflow có scheduling/approval/restart phải qua process/durable worker thật.
6. Post-action verification bắt buộc cho provider ngoài (đọc lại trạng thái sau khi ghi/gửi).

## Definition of Done (Part C mức chương trình)

- [ ] Mỗi nhóm action có một sub-plan `docs/implementation/2026-XX-XX-msmk-part-c-*.md` riêng, theo template trên.
- [ ] Không sub-plan nào được thực thi trước khi capability integration test + approval bind/resume test + restart-recovery E2E của chính nó xanh.
- [ ] `part-c-marketing-write` là sub-plan đầu tiên (rủi ro thấp nhất, nội bộ Company); outbound/ads/deploy/finance sau.
