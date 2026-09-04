# Route inventory (GENERATED — `scripts/route_inventory.py`)

Nguồn intent: [M0 §3](../plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md).
Không sửa tay. Chạy `make route-inventory` để cập nhật; `make route-inventory-check` ở CI.

## 1. Encore handler routes (`services/company`, `services/cosa`)

| Method | Path | Service | expose | auth | File |
|---|---|---|---|---|---|
| POST | `/academy/enrollments` | company | ✓ |  | services/company/academy/handlers/program.handler.ts |
| POST | `/academy/enrollments/:enrollmentId/complete-lesson` | company | ✓ |  | services/company/academy/handlers/program.handler.ts |
| GET | `/academy/enrollments/:id` | company | ✓ |  | services/company/academy/handlers/program.handler.ts |
| GET | `/academy/programs` | company | ✓ |  | services/company/academy/handlers/program.handler.ts |
| GET | `/academy/programs/:id` | company | ✓ |  | services/company/academy/handlers/program.handler.ts |
| POST | `/academy/template-exports` | company | ✓ |  | services/company/academy/handlers/template-export.handler.ts |
| GET | `/academy/template-exports/:id` | company | ✓ |  | services/company/academy/handlers/template-export.handler.ts |
| POST | `/commercial/accounts` | company | ✓ |  | services/company/commercial/handlers/account.handler.ts |
| GET | `/commercial/accounts/:id` | company | ✓ |  | services/company/commercial/handlers/account.handler.ts |
| POST | `/commercial/campaign-assets` | company | ✓ |  | services/company/commercial/handlers/marketing.handler.ts |
| POST | `/commercial/campaigns` | company | ✓ |  | services/company/commercial/handlers/marketing.handler.ts |
| POST | `/commercial/contacts` | company | ✓ |  | services/company/commercial/handlers/contact.handler.ts |
| GET | `/commercial/contacts/:id` | company | ✓ |  | services/company/commercial/handlers/contact.handler.ts |
| POST | `/commercial/customers` | company | ✓ |  | services/company/commercial/handlers/customer.handler.ts |
| GET | `/commercial/customers/:id` | company | ✓ |  | services/company/commercial/handlers/customer.handler.ts |
| GET | `/commercial/engagement/automation/rules` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/automation.handler.ts |
| POST | `/commercial/engagement/automation/rules` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/automation.handler.ts |
| POST | `/commercial/engagement/automation/rules/:key/disable` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/automation.handler.ts |
| POST | `/commercial/engagement/automation/rules/:key/enable` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/automation.handler.ts |
| POST | `/commercial/engagement/autopilot/kill-switch` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/autopilot.handler.ts |
| GET | `/commercial/engagement/autopilot/settings` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/autopilot.handler.ts |
| PUT | `/commercial/engagement/autopilot/settings` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/autopilot.handler.ts |
| POST | `/commercial/engagement/autopilot/threshold-check` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/autopilot.handler.ts |
| POST | `/commercial/engagement/channels` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts |
| POST | `/commercial/engagement/channels/:id/activate` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts |
| GET | `/commercial/engagement/channels/:id/deliveries` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts |
| POST | `/commercial/engagement/channels/:id/pause` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts |
| POST | `/commercial/engagement/channels/zalo/webhook` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/channels/zalo.handler.ts |
| GET | `/commercial/engagement/contacts/:id/360` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| GET | `/commercial/engagement/copilot-invocations/:id` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| POST | `/commercial/engagement/copilot-invocations/:id/feedback` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| POST | `/commercial/engagement/copilot-invocations/:runId/result` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| GET | `/commercial/engagement/copilot/settings` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| PATCH | `/commercial/engagement/copilot/settings` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| POST | `/commercial/engagement/copilot/settings/disable` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| POST | `/commercial/engagement/copilot/settings/enable` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| POST | `/commercial/engagement/decision-authorities` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/decision-authorities/:authorityKey/grants` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/decision-requests` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/decision-requests/:id/approvals` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/decision-requests/:id/execute` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/decision-requests/:id/review` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/decision-requests/:id/submit` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/deliveries/:id/retry` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts |
| POST | `/commercial/engagement/delivery-relay/tick` | company |  |  | services/company/commercial/services/customer-engagement/delivery-relay.cron.ts |
| PUT | `/commercial/engagement/escalation-routes/:routeKey` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| GET | `/commercial/engagement/threads` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/threads` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| GET | `/commercial/engagement/threads/:id` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/threads/:id/assign` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| GET | `/commercial/engagement/threads/:id/automation/applications` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/automation.handler.ts |
| POST | `/commercial/engagement/threads/:id/automation/dry-run` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/automation.handler.ts |
| GET | `/commercial/engagement/threads/:id/context` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| POST | `/commercial/engagement/threads/:id/copilot` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/copilot.handler.ts |
| POST | `/commercial/engagement/threads/:id/hand-back` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/threads/:id/messages` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/threads/:id/notes` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/threads/:id/status` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/engagement/threads/:id/takeover` | company | ✓ |  | services/company/commercial/handlers/customer-engagement/desk.handler.ts |
| POST | `/commercial/invoices` | company | ✓ |  | services/company/commercial/handlers/billing.handler.ts |
| GET | `/commercial/leads` | company | ✓ |  | services/company/commercial/handlers/lead.handler.ts |
| POST | `/commercial/leads` | company | ✓ |  | services/company/commercial/handlers/lead.handler.ts |
| GET | `/commercial/leads/:id` | company | ✓ |  | services/company/commercial/handlers/lead.handler.ts |
| POST | `/commercial/leads/:id/stage` | company | ✓ |  | services/company/commercial/handlers/lead.handler.ts |
| GET | `/commercial/marketing-context` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PUT | `/commercial/marketing-context` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| POST | `/commercial/marketing-context/approve` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/customer-research` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/offer-architecture` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/product-marketing` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| POST | `/commercial/marketing-context/submit-review` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/twelve-week-plan` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| POST | `/commercial/marketing-forms` | company | ✓ |  | services/company/commercial/handlers/marketing.handler.ts |
| GET | `/commercial/marketing/assets` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| GET | `/commercial/marketing/campaigns` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| POST | `/commercial/marketing/campaigns` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| GET | `/commercial/marketing/experiments` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| POST | `/commercial/marketing/experiments` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| GET | `/commercial/marketing/metrics/observed` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| GET | `/commercial/marketing/objectives` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| POST | `/commercial/marketing/objectives` | company | ✓ |  | services/company/commercial/handlers/marketing-mvp.handler.ts |
| POST | `/commercial/opportunities` | company | ✓ |  | services/company/commercial/handlers/opportunity.handler.ts |
| GET | `/commercial/opportunities/:id` | company | ✓ |  | services/company/commercial/handlers/opportunity.handler.ts |
| POST | `/commercial/opportunities/:id/stage` | company | ✓ |  | services/company/commercial/handlers/opportunity.handler.ts |
| POST | `/commercial/subscriptions` | company | ✓ |  | services/company/commercial/handlers/billing.handler.ts |
| GET | `/commercial/workspaces/:workspaceId/campaigns` | company | ✓ |  | services/company/commercial/handlers/marketing.handler.ts |
| GET | `/commercial/workspaces/:workspaceId/invoices` | company | ✓ |  | services/company/commercial/handlers/billing.handler.ts |
| POST | `/control-plane/internal/child-tasks` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| GET | `/control-plane/internal/child-tasks/:parentTaskId` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| GET | `/control-plane/internal/child-tasks/:parentTaskId/join` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/child-tasks/complete` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/cost-ledger` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/delivery-attempts` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/delivery-policies` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/leases/acquire` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/leases/release` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/leases/renew` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/missions` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| GET | `/control-plane/internal/missions/:id` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/scheduled-tasks` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/scheduled-tasks/:taskId/complete` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/scheduled-tasks/:taskId/heartbeat` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/scheduled-tasks/poll` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/scheduled-tasks/reclaim-stuck` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/signals` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/tasks` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/tasks/:taskId/checkout` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/watches` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/workers` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/workers/:id/heartbeat` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/cosa/connectors/assert` | cosa | ✓ |  | services/cosa/handlers/workspace-connector.handler.ts |
| POST | `/cosa/connectors/authorize` | cosa | ✓ |  | services/cosa/handlers/workspace-connector.handler.ts |
| POST | `/cosa/connectors/grant` | cosa | ✓ |  | services/cosa/handlers/workspace-connector.handler.ts |
| POST | `/cosa/connectors/install` | cosa | ✓ |  | services/cosa/handlers/workspace-connector.handler.ts |
| POST | `/cosa/connectors/revoke` | cosa | ✓ |  | services/cosa/handlers/workspace-connector.handler.ts |
| POST | `/cosa/document-ingestions` | cosa | ✓ |  | services/cosa/handlers/document-ingestion.handler.ts |
| GET | `/cosa/document-ingestions/:ingestionId` | cosa | ✓ |  | services/cosa/handlers/document-ingestion.handler.ts |
| POST | `/cosa/document-ingestions/:ingestionId/complete` | cosa | ✓ |  | services/cosa/handlers/document-ingestion.handler.ts |
| POST | `/cosa/document-ingestions/:ingestionId/review` | cosa | ✓ |  | services/cosa/handlers/document-ingestion.handler.ts |
| POST | `/cosa/document-ingestions/:ingestionId/transition` | cosa | ✓ |  | services/cosa/handlers/document-ingestion.handler.ts |
| GET | `/cosa/runtime/nodes` | cosa | ✓ |  | services/cosa/handlers/runtime-node.handler.ts |
| POST | `/cosa/runtime/nodes/heartbeat` | cosa | ✓ |  | services/cosa/handlers/runtime-node.handler.ts |
| POST | `/cosa/runtime/nodes/register` | cosa | ✓ |  | services/cosa/handlers/runtime-node.handler.ts |
| POST | `/cosa/runtime/nodes/revoke` | cosa | ✓ |  | services/cosa/handlers/runtime-node.handler.ts |
| POST | `/cosa/runtime/route` | cosa | ✓ |  | services/cosa/handlers/runtime-node.handler.ts |
| GET | `/cosa/schedules` | cosa | ✓ |  | services/cosa/handlers/workspace-schedule.handler.ts |
| POST | `/cosa/schedules` | cosa | ✓ |  | services/cosa/handlers/workspace-schedule.handler.ts |
| POST | `/cosa/schedules/:scheduleId/run-now` | cosa | ✓ |  | services/cosa/handlers/workspace-schedule.handler.ts |
| GET | `/cosa/schedules/executions/:executionId` | cosa | ✓ |  | services/cosa/handlers/workspace-schedule.handler.ts |
| POST | `/cosa/schedules/executions/complete` | cosa | ✓ |  | services/cosa/handlers/workspace-schedule.handler.ts |
| POST | `/cosa/workers/ingress` | cosa | ✓ |  | services/cosa/handlers/worker-ingress.handler.ts |
| POST | `/events/internal/agent-runtime-signal` | company | ✓ |  | services/company/events/handlers/agent-runtime-signal.handler.ts |
| POST | `/events/internal/knowledge-published` | company | ✓ |  | services/company/events/knowledge-published.api.ts |
| GET | `/events/metrics` | company | ✓ |  | services/company/events/event-operations.api.ts |
| GET | `/events/outbox` | company | ✓ |  | services/company/events/event-operations.api.ts |
| POST | `/events/outbox/:eventId/retry` | company | ✓ |  | services/company/events/event-operations.api.ts |
| POST | `/events/prune/tick` | company |  |  | services/company/events/outbox-prune.cron.ts |
| POST | `/events/relay/tick` | company |  |  | services/company/events/outbox-relay.cron.ts |
| POST | `/finance-legal/accounting-periods` | company | ✓ |  | services/company/finance-legal/handlers/accounting-period.handler.ts |
| GET | `/finance-legal/accounting-periods/:id` | company | ✓ |  | services/company/finance-legal/handlers/accounting-period.handler.ts |
| POST | `/finance-legal/accounting-periods/:id/close` | company | ✓ |  | services/company/finance-legal/handlers/accounting-period.handler.ts |
| POST | `/finance-legal/accounting-profiles` | company | ✓ |  | services/company/finance-legal/handlers/accounting-profile.handler.ts |
| GET | `/finance-legal/accounting-profiles/by-workspace/:workspaceId` | company | ✓ |  | services/company/finance-legal/handlers/accounting-profile.handler.ts |
| POST | `/finance-legal/ai-compliance/_e2e/seed` | company |  |  | services/company/finance-legal/handlers/ai-compliance-e2e-seed.handler.ts |
| POST | `/finance-legal/ai-compliance/authorizations` | company | ✓ |  | services/company/finance-legal/handlers/ai-data-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/authorizations/:id/withdraw` | company | ✓ |  | services/company/finance-legal/handlers/ai-data-governance.handler.ts |
| GET | `/finance-legal/ai-compliance/center` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/data-profiles` | company | ✓ |  | services/company/finance-legal/handlers/ai-data-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/data-subject-requests` | company | ✓ |  | services/company/finance-legal/handlers/ai-data-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/deployments` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/deployments/:deploymentId/approve` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/deployments/:deploymentId/assessments` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/deployments/:deploymentId/resume` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/deployments/:deploymentId/suspend` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/incidents` | company | ✓ |  | services/company/finance-legal/handlers/ai-incident-response.handler.ts |
| POST | `/finance-legal/ai-compliance/incidents/:id/resolve` | company | ✓ |  | services/company/finance-legal/handlers/ai-incident-response.handler.ts |
| POST | `/finance-legal/ai-compliance/provider-profiles` | company | ✓ |  | services/company/finance-legal/handlers/ai-data-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/resolve-data-use` | company | ✓ |  | services/company/finance-legal/handlers/ai-data-governance.handler.ts |
| POST | `/finance-legal/ai-compliance/runtime/snapshots/resolve` | company |  |  | services/company/finance-legal/handlers/ai-compliance-runtime.handler.ts |
| GET | `/finance-legal/ai-compliance/snapshots` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts |
| POST | `/finance-legal/ai-compliance/snapshots` | company |  |  | services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts |
| POST | `/finance-legal/ai-compliance/snapshots/:id/verify` | company | ✓ |  | services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts |
| POST | `/finance-legal/cas/webhook` | company | ✓ |  | services/company/finance-legal/handlers/cas-webhook.handler.ts |
| POST | `/finance-legal/cas/webhook/reprocess/:id` | company |  |  | services/company/finance-legal/handlers/cas-webhook.handler.ts |
| POST | `/finance-legal/checklist-items` | company | ✓ |  | services/company/finance-legal/handlers/legal-checklist-item.handler.ts |
| GET | `/finance-legal/checklist-items/:id` | company | ✓ |  | services/company/finance-legal/handlers/legal-checklist-item.handler.ts |
| POST | `/finance-legal/checklist-items/:id/complete` | company | ✓ |  | services/company/finance-legal/handlers/legal-checklist-item.handler.ts |
| POST | `/finance-legal/coa-mappings` | company |  |  | services/company/finance-legal/handlers/accounting-regime.handler.ts |
| POST | `/finance-legal/exceptions` | company | ✓ |  | services/company/finance-legal/handlers/finance-exception.handler.ts |
| GET | `/finance-legal/exceptions/:id` | company | ✓ |  | services/company/finance-legal/handlers/finance-exception.handler.ts |
| POST | `/finance-legal/exceptions/:id/resolve` | company | ✓ |  | services/company/finance-legal/handlers/finance-exception.handler.ts |
| POST | `/finance-legal/fiscal-profiles` | company | ✓ |  | services/company/finance-legal/handlers/accounting-regime.handler.ts |
| GET | `/finance-legal/obligation-templates` | company | ✓ |  | services/company/finance-legal/handlers/regulation-catalog.handler.ts |
| POST | `/finance-legal/obligations` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| GET | `/finance-legal/obligations/:id` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/finance-legal/obligations/:id/fulfill` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| GET | `/finance-legal/regulation-sources` | company | ✓ |  | services/company/finance-legal/handlers/regulation-catalog.handler.ts |
| POST | `/finance-legal/regulation-versions` | company |  |  | services/company/finance-legal/handlers/regulation-catalog.handler.ts |
| POST | `/finance-legal/snapshots` | company | ✓ |  | services/company/finance-legal/handlers/finance-snapshot.handler.ts |
| GET | `/finance-legal/snapshots/latest` | company | ✓ |  | services/company/finance-legal/handlers/finance-snapshot.handler.ts |
| GET | `/finance-legal/transactions` | company | ✓ |  | services/company/finance-legal/handlers/financial-transaction.handler.ts |
| POST | `/finance-legal/transactions` | company | ✓ |  | services/company/finance-legal/handlers/financial-transaction.handler.ts |
| GET | `/finance-legal/transactions/:id` | company | ✓ |  | services/company/finance-legal/handlers/financial-transaction.handler.ts |
| POST | `/finance-legal/transactions/:id/approve` | company | ✓ |  | services/company/finance-legal/handlers/financial-transaction.handler.ts |
| GET | `/finance-legal/workspaces/:workspaceId/fiscal-profiles` | company | ✓ |  | services/company/finance-legal/handlers/accounting-regime.handler.ts |
| GET | `/finance/accounting-documents` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/accounting-documents` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/accounting-documents/:id/confirm` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/bank-connections` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/bank-connections` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/bank-transactions` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/reconciliation-proposals` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/reconciliation-proposals/:id/accept` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/regime-policy` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/snapshots` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/snapshots/calculate` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/healthz` | company | ✓ |  | services/company/identity/handlers/health.handler.ts |
| GET | `/healthz` | cosa | ✓ |  | services/cosa/handlers/health.handler.ts |
| POST | `/identity/_e2e/session` | company |  |  | services/company/identity/handlers/e2e-session.handler.ts |
| GET | `/identity/me` | company | ✓ | ✓ | services/company/identity/handlers/auth.handler.ts |
| POST | `/identity/session/renew` | company | ✓ |  | services/company/identity/handlers/auth.handler.ts |
| POST | `/identity/sync-from-platform` | company | ✓ |  | services/company/identity/handlers/sync.handler.ts |
| POST | `/identity/tenant-context/resolve` | company | ✓ |  | services/company/identity/handlers/tenant-context.handler.ts |
| POST | `/identity/workforce-members` | company | ✓ |  | services/company/identity/handlers/workforce.handler.ts |
| GET | `/identity/workforce-members/:id` | company | ✓ |  | services/company/identity/handlers/workforce.handler.ts |
| POST | `/identity/workspaces` | company |  |  | services/company/identity/handlers/workspace.handler.ts |
| GET | `/identity/workspaces/:id` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| PATCH | `/identity/workspaces/:id/company-identity` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| GET | `/identity/workspaces/:workspaceId/platform-company` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| GET | `/legal/applicable-obligations` | company | ✓ |  | services/company/finance-legal/handlers/legal-applicability.handler.ts |
| GET | `/legal/legal-entity-profiles` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles/:id/verify` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles/:id/verify/confirm` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| GET | `/legal/obligation-instances` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/legal/obligation-instances` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/operations/cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/execution-plans` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/execution-plans` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| GET | `/operations/execution-plans/:id` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/execution-plans/:id/accept` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| PATCH | `/operations/execution-plans/:id/items/:itemId` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/execution-plans/:id/reject` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| GET | `/operations/executive-context` | company | ✓ |  | services/company/operations/handlers/executive-context.handler.ts |
| POST | `/operations/initiatives` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| GET | `/operations/initiatives/:id` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| POST | `/operations/key-results/:id/checkin` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| DELETE | `/operations/objectives/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:id/progress` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:id/projects` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives/:id/projects` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| DELETE | `/operations/objectives/:id/projects/:projectId` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives/:objectiveId/key-results` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/okr-cycles` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/okr-cycles` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/portfolios` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| POST | `/operations/portfolios` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| GET | `/operations/projects` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| POST | `/operations/projects` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| GET | `/operations/projects/:id` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| GET | `/operations/projects/:id/operating-setup` | company | ✓ |  | services/company/operations/strategy/handlers/project-operating-setup.handler.ts |
| PUT | `/operations/projects/:id/operating-setup` | company | ✓ |  | services/company/operations/strategy/handlers/project-operating-setup.handler.ts |
| POST | `/operations/projects/:id/operating-setup/activate` | company | ✓ |  | services/company/operations/strategy/handlers/project-operating-setup.handler.ts |
| GET | `/operations/strategy/action-context` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| GET | `/operations/strategy/action-proposals` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| POST | `/operations/strategy/action-proposals` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| POST | `/operations/strategy/action-proposals/:id/accept` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| GET | `/operations/strategy/assumptions` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| POST | `/operations/strategy/assumptions` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| DELETE | `/operations/strategy/assumptions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| GET | `/operations/strategy/assumptions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| PATCH | `/operations/strategy/assumptions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| GET | `/operations/strategy/canvas-revisions/:id` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| POST | `/operations/strategy/canvas-revisions/:id/approve` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| POST | `/operations/strategy/canvas-revisions/:id/reject` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| POST | `/operations/strategy/canvas-revisions/:id/submit-review` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| GET | `/operations/strategy/canvases` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| POST | `/operations/strategy/canvases` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| DELETE | `/operations/strategy/canvases/:id` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| GET | `/operations/strategy/canvases/:id` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| PUT | `/operations/strategy/canvases/:id` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| POST | `/operations/strategy/canvases/:id/revisions` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| GET | `/operations/strategy/decision-records` | company | ✓ |  | services/company/operations/strategy/handlers/decision-record.handler.ts |
| POST | `/operations/strategy/decision-records` | company | ✓ |  | services/company/operations/strategy/handlers/decision-record.handler.ts |
| DELETE | `/operations/strategy/decision-records/:id` | company | ✓ |  | services/company/operations/strategy/handlers/decision-record.handler.ts |
| GET | `/operations/strategy/decision-records/:id` | company | ✓ |  | services/company/operations/strategy/handlers/decision-record.handler.ts |
| GET | `/operations/strategy/discovery-signals` | company | ✓ |  | services/company/operations/strategy/handlers/discovery-signal.handler.ts |
| POST | `/operations/strategy/discovery-signals` | company | ✓ |  | services/company/operations/strategy/handlers/discovery-signal.handler.ts |
| DELETE | `/operations/strategy/discovery-signals/:id` | company | ✓ |  | services/company/operations/strategy/handlers/discovery-signal.handler.ts |
| GET | `/operations/strategy/discovery-signals/:id` | company | ✓ |  | services/company/operations/strategy/handlers/discovery-signal.handler.ts |
| PATCH | `/operations/strategy/discovery-signals/:id` | company | ✓ |  | services/company/operations/strategy/handlers/discovery-signal.handler.ts |
| GET | `/operations/strategy/evidence` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| POST | `/operations/strategy/evidence` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| GET | `/operations/strategy/evidence-ingestions` | company | ✓ |  | services/company/operations/strategy/handlers/evidence-ingestion.handler.ts |
| POST | `/operations/strategy/evidence-ingestions` | company | ✓ |  | services/company/operations/strategy/handlers/evidence-ingestion.handler.ts |
| DELETE | `/operations/strategy/evidence/:id` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| GET | `/operations/strategy/evidence/:id` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| PATCH | `/operations/strategy/evidence/:id` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| POST | `/operations/strategy/evidence/:id/review` | company | ✓ |  | services/company/operations/strategy/handlers/evidence-review.handler.ts |
| GET | `/operations/strategy/experiments` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| POST | `/operations/strategy/experiments` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| DELETE | `/operations/strategy/experiments/:id` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| GET | `/operations/strategy/experiments/:id` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| PATCH | `/operations/strategy/experiments/:id` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| GET | `/operations/strategy/funding-matches` | company | ✓ |  | services/company/operations/handlers/canvas.handler.ts |
| GET | `/operations/strategy/gate-evaluations` | company | ✓ |  | services/company/operations/strategy/handlers/gate-evaluation.handler.ts |
| POST | `/operations/strategy/gate-evaluations` | company | ✓ |  | services/company/operations/strategy/handlers/gate-evaluation.handler.ts |
| DELETE | `/operations/strategy/gate-evaluations/:id` | company | ✓ |  | services/company/operations/strategy/handlers/gate-evaluation.handler.ts |
| GET | `/operations/strategy/gate-evaluations/:id` | company | ✓ |  | services/company/operations/strategy/handlers/gate-evaluation.handler.ts |
| PATCH | `/operations/strategy/gate-evaluations/:id` | company | ✓ |  | services/company/operations/strategy/handlers/gate-evaluation.handler.ts |
| GET | `/operations/strategy/interviews` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| POST | `/operations/strategy/interviews` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| DELETE | `/operations/strategy/interviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| GET | `/operations/strategy/interviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| PATCH | `/operations/strategy/interviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| GET | `/operations/strategy/maturity-assessments` | company | ✓ |  | services/company/operations/strategy/handlers/maturity-assessment.handler.ts |
| POST | `/operations/strategy/maturity-assessments` | company | ✓ |  | services/company/operations/strategy/handlers/maturity-assessment.handler.ts |
| GET | `/operations/strategy/maturity-assessments/:id` | company | ✓ |  | services/company/operations/strategy/handlers/maturity-assessment.handler.ts |
| GET | `/operations/strategy/metric-contracts` | company | ✓ |  | services/company/operations/strategy/handlers/metric-contract.handler.ts |
| POST | `/operations/strategy/metric-contracts` | company | ✓ |  | services/company/operations/strategy/handlers/metric-contract.handler.ts |
| GET | `/operations/strategy/metric-contracts/:id` | company | ✓ |  | services/company/operations/strategy/handlers/metric-contract.handler.ts |
| PATCH | `/operations/strategy/metric-contracts/:id` | company | ✓ |  | services/company/operations/strategy/handlers/metric-contract.handler.ts |
| POST | `/operations/strategy/metric-contracts/:id/publish` | company | ✓ |  | services/company/operations/strategy/handlers/metric-contract.handler.ts |
| POST | `/operations/strategy/metric-contracts/:id/revise` | company | ✓ |  | services/company/operations/strategy/handlers/metric-contract.handler.ts |
| GET | `/operations/strategy/metric-snapshots` | company | ✓ |  | services/company/operations/strategy/handlers/metric-snapshot.handler.ts |
| POST | `/operations/strategy/metric-snapshots` | company | ✓ |  | services/company/operations/strategy/handlers/metric-snapshot.handler.ts |
| GET | `/operations/strategy/metric-snapshots/:id` | company | ✓ |  | services/company/operations/strategy/handlers/metric-snapshot.handler.ts |
| GET | `/operations/strategy/pilots` | company | ✓ |  | services/company/operations/strategy/handlers/pilot-run.handler.ts |
| POST | `/operations/strategy/pilots` | company | ✓ |  | services/company/operations/strategy/handlers/pilot-run.handler.ts |
| GET | `/operations/strategy/pilots/:id` | company | ✓ |  | services/company/operations/strategy/handlers/pilot-run.handler.ts |
| POST | `/operations/strategy/pilots/:id/activate` | company | ✓ |  | services/company/operations/strategy/handlers/pilot-run.handler.ts |
| POST | `/operations/strategy/pilots/:id/approve` | company | ✓ |  | services/company/operations/strategy/handlers/pilot-run.handler.ts |
| POST | `/operations/strategy/pilots/:id/close` | company | ✓ |  | services/company/operations/strategy/handlers/pilot-run.handler.ts |
| GET | `/operations/strategy/pmf-scoreboards` | company | ✓ |  | services/company/operations/strategy/handlers/pmf-scoreboard.handler.ts |
| GET | `/operations/strategy/pmf-scoreboards/:id` | company | ✓ |  | services/company/operations/strategy/handlers/pmf-scoreboard.handler.ts |
| POST | `/operations/strategy/pmf-scoreboards/calculate` | company | ✓ |  | services/company/operations/strategy/handlers/pmf-scoreboard.handler.ts |
| GET | `/operations/strategy/projects/:id/next-best-actions` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| POST | `/operations/strategy/projects/:id/stage` | company | ✓ |  | services/company/operations/strategy/handlers/project-stage.handler.ts |
| GET | `/operations/strategy/projects/:id/stage/transitions` | company | ✓ |  | services/company/operations/strategy/handlers/project-stage.handler.ts |
| POST | `/operations/strategy/projects/:id/weekly-goal` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-goal.handler.ts |
| GET | `/operations/strategy/projects/:projectId/proposed-experiments` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| GET | `/operations/strategy/projects/:projectId/ranked-assumptions` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| GET | `/operations/strategy/stage-context` | company | ✓ |  | services/company/operations/strategy/handlers/project-stage.handler.ts |
| GET | `/operations/strategy/stage-policies` | company | ✓ |  | services/company/operations/strategy/handlers/stage-policy.handler.ts |
| POST | `/operations/strategy/stage-policies` | company | ✓ |  | services/company/operations/strategy/handlers/stage-policy.handler.ts |
| DELETE | `/operations/strategy/stage-policies/:id` | company | ✓ |  | services/company/operations/strategy/handlers/stage-policy.handler.ts |
| GET | `/operations/strategy/stage-policies/:id` | company | ✓ |  | services/company/operations/strategy/handlers/stage-policy.handler.ts |
| PATCH | `/operations/strategy/stage-policies/:id` | company | ✓ |  | services/company/operations/strategy/handlers/stage-policy.handler.ts |
| GET | `/operations/strategy/stage-transitions` | company | ✓ |  | services/company/operations/strategy/handlers/stage-transition-config.handler.ts |
| POST | `/operations/strategy/stage-transitions` | company | ✓ |  | services/company/operations/strategy/handlers/stage-transition-config.handler.ts |
| DELETE | `/operations/strategy/stage-transitions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/stage-transition-config.handler.ts |
| GET | `/operations/strategy/stage-transitions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/stage-transition-config.handler.ts |
| GET | `/operations/strategy/venture-profile` | company | ✓ |  | services/company/operations/strategy/handlers/venture-profile.handler.ts |
| PUT | `/operations/strategy/venture-profile` | company | ✓ |  | services/company/operations/strategy/handlers/venture-profile.handler.ts |
| POST | `/operations/strategy/venture-stage/assess` | company | ✓ |  | services/company/operations/strategy/handlers/venture-stage.handler.ts |
| POST | `/operations/strategy/venture-stage/transition` | company | ✓ |  | services/company/operations/strategy/handlers/venture-stage.handler.ts |
| GET | `/operations/strategy/venture-stage/transitions` | company | ✓ |  | services/company/operations/strategy/handlers/venture-stage.handler.ts |
| GET | `/operations/strategy/weekly-reviews` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-review.handler.ts |
| POST | `/operations/strategy/weekly-reviews` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-review.handler.ts |
| POST | `/operations/strategy/weekly-reviews/:id/complete` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-review.handler.ts |
| POST | `/operations/task-dependencies` | company | ✓ |  | services/company/operations/handlers/task-dependency.handler.ts |
| POST | `/operations/task-schedules` | company | ✓ |  | services/company/operations/handlers/task-dependency.handler.ts |
| GET | `/operations/tasks` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/:id` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/advance` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/:id/projects` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/projects` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| DELETE | `/operations/tasks/:id/projects/:projectId` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/schedule` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/status` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/:taskId/dependencies` | company | ✓ |  | services/company/operations/handlers/task-dependency.handler.ts |
| GET | `/operations/tasks/agent-claimable` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/twelve-week-commitments` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/twelve-week-cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/twelve-week-plans` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| PATCH | `/operations/twelve-week-plans/:id` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/weekly-commitments` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/weekly-plans` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/workspace-runtime/blockers` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspace-runtime/items/:sourceKind/:sourceId` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| POST | `/operations/workspace-runtime/items/:sourceKind/:sourceId/snooze` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspace-runtime/needs-you` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspace-runtime/source-status` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspaces/:workspaceId/cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/platform/auth/companies/create` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| POST | `/platform/auth/companies/join` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| GET | `/platform/auth/me` | cosa | ✓ | ✓ | services/cosa/handlers/auth.handler.ts |
| PATCH | `/platform/auth/me` | cosa | ✓ | ✓ | services/cosa/handlers/auth.handler.ts |
| GET | `/platform/auth/me/agent-policy-snapshot` | cosa | ✓ |  | services/cosa/handlers/agent-policy.handler.ts |
| GET | `/platform/auth/me/companies` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| POST | `/platform/auth/register` | cosa | ✓ |  | services/cosa/handlers/auth.handler.ts |
| POST | `/platform/auth/sessions` | cosa | ✓ |  | services/cosa/handlers/auth.handler.ts |
| GET | `/platform/internal/agent-policy` | cosa |  |  | services/cosa/handlers/agent-policy.handler.ts |
| POST | `/platform/internal/agent-policy` | cosa |  |  | services/cosa/handlers/agent-policy.handler.ts |
| POST | `/platform/internal/list-workspace-memberships` | cosa | ✓ |  | services/cosa/handlers/venture-workspace.handler.ts |
| POST | `/platform/internal/mark-workspace-synced` | cosa | ✓ |  | services/cosa/handlers/venture-workspace.handler.ts |
| POST | `/platform/internal/validate-membership` | cosa |  |  | services/cosa/handlers/company.handler.ts |
| POST | `/platform/internal/validate-workspace-membership` | cosa | ✓ |  | services/cosa/handlers/venture-workspace.handler.ts |
| GET | `/platform/workspaces/:id/entitlement` | cosa | ✓ | ✓ | services/cosa/handlers/venture-workspace.handler.ts |
| GET | `/platform/workspaces/:workspaceId/audit-events` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/workspaces/:workspaceId/connectors` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| POST | `/platform/workspaces/:workspaceId/connectors/:connectorKey/install` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| POST | `/platform/workspaces/:workspaceId/connectors/:connectorKey/revoke` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/workspaces/:workspaceId/members` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/workspaces/:workspaceId/runtime-nodes` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| POST | `/platform/workspaces/:workspaceId/runtime-nodes/:nodeId/revoke` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/workspaces/:workspaceId/session-context` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/workspaces/:workspaceId/skill-policies` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| PUT | `/platform/workspaces/:workspaceId/skill-policies/:skillKey` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |

### ⚠ `expose:true` không `auth` (rà M1)

- GET `/healthz` — services/company/identity/handlers/health.handler.ts
- GET `/healthz` — services/cosa/handlers/health.handler.ts
- POST `/identity/session/renew` — services/company/identity/handlers/auth.handler.ts
- POST `/identity/sync-from-platform` — services/company/identity/handlers/sync.handler.ts
- GET `/platform/auth/me/agent-policy-snapshot` — services/cosa/handlers/agent-policy.handler.ts
- POST `/platform/auth/register` — services/cosa/handlers/auth.handler.ts
- POST `/platform/auth/sessions` — services/cosa/handlers/auth.handler.ts
- POST `/platform/internal/list-workspace-memberships` — services/cosa/handlers/venture-workspace.handler.ts
- POST `/platform/internal/mark-workspace-synced` — services/cosa/handlers/venture-workspace.handler.ts
- POST `/platform/internal/validate-workspace-membership` — services/cosa/handlers/venture-workspace.handler.ts

## 2. Frontend company-bound call sites — trạng thái resolve

| Key (METHOD prefix) | Resolved | Owner (allowlist) | Call sites |
|---|---|---|---|
| `DELETE /execution/milestones` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:324 |
| `DELETE /execution/stages` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:250 |
| `DELETE /execution/weekly-commitments` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:167 |
| `DELETE /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:628 |
| `DELETE /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:278 |
| `DELETE /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:559 |
| `DELETE /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:520 |
| `DELETE /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:230 |
| `DELETE /okrs/key-results` | ✗ GHOST |  | frontend/lib/modules/strategy/services/okr_service.dart:155 |
| `DELETE /okrs/objectives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/okr_service.dart:88 |
| `DELETE /strategy/canvases` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:52 |
| `DELETE /workforce/agents` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:523 |
| `GET /admin` | ✗ GHOST |  | frontend/lib/modules/dashboard/services/hub_service.dart:39, frontend/lib/modules/settings/services/admin_service.dart:14 |
| `GET /business/packs` | ✗ GHOST |  | frontend/lib/modules/organization/services/business_pack_service.dart:17, frontend/lib/modules/organization/services/business_pack_service.dart:35, frontend/lib/modules/organization/services/business_pack_service.dart:52 … |
| `GET /channels` | ✗ GHOST |  | frontend/lib/modules/marketing/services/channels_service.dart:50 |
| `GET /channels/list` | ✗ GHOST |  | frontend/lib/modules/marketing/services/channels_service.dart:167 |
| `GET /commercial/leads` | ✓ |  | frontend/lib/modules/sales/services/sales_service.dart:62 |
| `GET /commercial/marketing-context` | ✓ |  | frontend/lib/modules/marketing/services/marketing_service.dart:152 |
| `GET /connectors` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:14 |
| `GET /connectors/zalo/sessions` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:141 |
| `GET /devices` | ✗ GHOST |  | frontend/lib/modules/settings/services/developer_service.dart:14 |
| `GET /devices/jobs` | ✗ GHOST |  | frontend/lib/modules/settings/services/developer_service.dart:41 |
| `GET /execution/gate-decisions` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:362 |
| `GET /execution/milestones` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:264 |
| `GET /execution/twelve-week-cycles` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:17, frontend/lib/modules/strategy/services/twelve_week_service.dart:181 |
| `GET /execution/weekly-commitments` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:121 |
| `GET /execution/weekly-plans` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:64 |
| `GET /finance-legal/accounting-profiles/by-workspace` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:101 |
| `GET /finance-legal/snapshots/latest` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:52 |
| `GET /finance-legal/transactions` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:67 |
| `GET /finance-legal/workspaces` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:170 |
| `GET /identity/me` | ✓ |  | frontend/lib/modules/auth/services/auth_service.dart:100, frontend/lib/modules/auth/services/auth_service.dart:519 |
| `GET /identity/workspaces` | ✓ |  | frontend/lib/modules/settings/services/workspace_orientation_service.dart:16 |
| `GET /marketing/analytics/overview` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:134 |
| `GET /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:602 |
| `GET /marketing/assumptions/summary` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:610 |
| `GET /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:246, frontend/lib/modules/marketing/services/marketing_service.dart:256 |
| `GET /marketing/canvases/revisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:738 |
| `GET /marketing/canvases/status` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:656 |
| `GET /marketing/cockpit-summary` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:127 |
| `GET /marketing/crm/attributions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:710 |
| `GET /marketing/crm/interviews` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:701 |
| `GET /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:544 |
| `GET /marketing/evidence` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:636 |
| `GET /marketing/experiments` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:300 |
| `GET /marketing/funnel` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:142 |
| `GET /marketing/learnings` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:332 |
| `GET /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:505 |
| `GET /marketing/metrics` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:343, frontend/lib/modules/marketing/services/marketing_service.dart:353 |
| `GET /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:213 |
| `GET /marketing/recommendations` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:569 |
| `GET /marketing/skill-executions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:367 |
| `GET /marketing/skills` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:362 |
| `GET /okrs/cycles` | ✗ GHOST |  | frontend/lib/modules/strategy/services/okr_service.dart:13 |
| `GET /okrs/key-results` | ✗ GHOST |  | frontend/lib/modules/strategy/services/okr_service.dart:99 |
| `GET /okrs/objectives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/okr_service.dart:46 |
| `GET /operations/objectives` | ✓ |  | frontend/lib/modules/strategy/services/outcomes_service.dart:11, frontend/lib/modules/strategy/services/outcomes_service.dart:85 |
| `GET /operations/projects` | ✓ |  | frontend/lib/modules/marketing/services/marketing_service.dart:109 |
| `GET /operations/strategy/assumptions` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:21, frontend/lib/modules/vault/services/evidence_service.dart:88 |
| `GET /operations/strategy/decision-records` | ✓ |  | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:104, frontend/lib/modules/vault/services/evidence_service.dart:118, frontend/lib/modules/vault/services/evidence_service.dart:152 |
| `GET /operations/strategy/evidence` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:60 |
| `GET /operations/strategy/gate-evaluations` | ✓ |  | frontend/lib/modules/strategy/services/stage_gate_service.dart:40, frontend/lib/modules/strategy/services/stage_gate_service.dart:58 |
| `GET /operations/strategy/maturity-assessments` | ✓ |  | frontend/lib/modules/strategy/services/pmf_scoreboard_service.dart:153 |
| `GET /operations/strategy/metric-contracts` | ✓ |  | frontend/lib/modules/strategy/services/pmf_scoreboard_service.dart:17 |
| `GET /operations/strategy/metric-snapshots` | ✓ |  | frontend/lib/modules/strategy/services/pmf_scoreboard_service.dart:42 |
| `GET /operations/strategy/pilots` | ✓ |  | frontend/lib/modules/strategy/services/pilot_run_service.dart:15, frontend/lib/modules/strategy/services/pilot_run_service.dart:31 |
| `GET /operations/strategy/pmf-scoreboards` | ✓ |  | frontend/lib/modules/strategy/services/pmf_scoreboard_service.dart:89, frontend/lib/modules/strategy/services/pmf_scoreboard_service.dart:110 |
| `GET /operations/strategy/projects` | ✓ | M4 | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:84 |
| `GET /operations/strategy/stage-context` | ✓ |  | frontend/lib/modules/strategy/services/stage_service.dart:85 |
| `GET /operations/strategy/stage-policies` | ✓ |  | frontend/lib/modules/strategy/services/stage_service.dart:14, frontend/lib/modules/strategy/services/stage_service.dart:98 |
| `GET /operations/strategy/stage-transitions` | ✓ |  | frontend/lib/modules/strategy/services/stage_service.dart:68 |
| `GET /operations/tasks` | ✓ |  | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:32, frontend/lib/modules/tasks/services/task_service.dart:18, frontend/lib/modules/tasks/services/task_service.dart:42 … |
| `GET /org` | ✗ GHOST |  | frontend/lib/modules/organization/services/organization_service.dart:14, frontend/lib/modules/organization/services/organization_service.dart:25, frontend/lib/modules/organization/services/organization_service.dart:36 … |
| `GET /plugins` | ✗ GHOST |  | frontend/lib/modules/skills/services/plugins_service.dart:14 |
| `GET /policy-programs` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:172, frontend/lib/modules/finance/services/policy_funding_service.dart:202 |
| `GET /policy-programs/draft-watchlist` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:165 |
| `GET /projects` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:45, frontend/lib/modules/strategy/services/validation_service.dart:25, frontend/lib/modules/strategy/services/validation_service.dart:61 … |
| `GET /runtime/doctor` | ✗ GHOST |  | frontend/lib/core/services/diagnostics_service.dart:8 |
| `GET /strategy/canvases` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:13, frontend/lib/modules/strategy/services/canvas_service.dart:22 |
| `GET /strategy/founder-profile` | ✗ GHOST |  | frontend/lib/modules/strategy/services/founder_service.dart:13 |
| `GET /strategy/initiatives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/project_service.dart:124 |
| `GET /strategy/lenses/bsc` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:210 |
| `GET /strategy/lenses/pestel` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:25 |
| `GET /strategy/lenses/summary` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:11 |
| `GET /strategy/lenses/swot` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:87 |
| `GET /strategy/lenses/tows` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:133 |
| `GET /strategy/portfolios` | ✗ GHOST |  | frontend/lib/modules/strategy/services/portfolio_service.dart:323 |
| `GET /strategy/revisions` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:75 |
| `GET /workforce/agents` | ✗ GHOST | M7 | frontend/lib/modules/agents/services/agent_platform_service.dart:49, frontend/lib/modules/agents/services/agent_platform_service.dart:644, frontend/lib/modules/agents/services/agents_service.dart:50 |
| `GET /workforce/budgets` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:399 |
| `GET /workforce/cost-ledger` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:438 |
| `GET /workforce/dashboard-summary` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:34, frontend/lib/modules/agents/services/agents_service.dart:29 |
| `GET /workforce/decisions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:372 |
| `GET /workforce/exceptions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:674 |
| `GET /workforce/heartbeats` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:453 |
| `GET /workforce/prompts` | ✗ GHOST |  | frontend/lib/modules/skills/services/prompt_registry_service.dart:76, frontend/lib/modules/skills/services/prompt_registry_service.dart:85, frontend/lib/modules/skills/services/prompt_registry_service.dart:93 |
| `GET /workforce/routines` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:480 |
| `GET /workforce/runs` | ✗ GHOST |  | frontend/lib/modules/agents/services/agents_service.dart:148 |
| `GET /workforce/runtimes` | ✗ GHOST |  | frontend/lib/modules/agents/services/agents_service.dart:96 |
| `GET /workforce/skills/physical` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:592 |
| `GET /workforce/stage-roster` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:630 |
| `GET /workforce/tools` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:225, frontend/lib/modules/agents/services/agent_platform_service.dart:564 |
| `GET /workforce/work-products` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:325 |
| `GET /workspace/file` | ✗ GHOST |  | frontend/lib/core/services/workspace_service.dart:21 |
| `GET /workspace/files` | ✗ GHOST |  | frontend/lib/core/services/workspace_service.dart:8 |
| `GET /workspaces` | ✗ GHOST |  | frontend/lib/modules/dashboard/services/hub_service.dart:136, frontend/lib/modules/sales/services/revenue_engine_service.dart:16, frontend/lib/modules/sales/services/revenue_engine_service.dart:70 … |
| `PATCH /commercial/marketing-context/product-marketing` | ✓ |  | frontend/lib/modules/marketing/services/marketing_service.dart:201 |
| `PATCH /identity/me` | ✓ |  | frontend/lib/modules/auth/services/auth_service.dart:506 |
| `PATCH /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:622 |
| `PATCH /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:262 |
| `PATCH /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:554 |
| `PATCH /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:515 |
| `PATCH /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:225 |
| `POST /connectors/zalo/sessions` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:151 |
| `POST /finance-legal/accounting-periods` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:153 |
| `POST /finance-legal/transactions` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:86 |
| `POST /marketing/ai/design-experiment` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:662 |
| `POST /marketing/ai/evaluate-learning-loop` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:716 |
| `POST /marketing/ai/extract-assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:648 |
| `POST /marketing/ai/extract-interview` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:686 |
| `POST /marketing/ai/propose-canvas-revision` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:728 |
| `POST /marketing/analytics/attribution` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:535 |
| `POST /marketing/assets` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:291 |
| `POST /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:616 |
| `POST /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:251 |
| `POST /marketing/canvases/revisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:744, frontend/lib/modules/marketing/services/marketing_service.dart:750 |
| `POST /marketing/crm/interviews` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:692 |
| `POST /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:549 |
| `POST /marketing/evidence` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:642 |
| `POST /marketing/experiments` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:305 |
| `POST /marketing/learning-loop/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:722 |
| `POST /marketing/learnings` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:338 |
| `POST /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:510, frontend/lib/modules/marketing/services/marketing_service.dart:525 |
| `POST /marketing/metrics` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:348 |
| `POST /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:220 |
| `POST /marketing/recommendations` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:574 |
| `POST /operations/execution-plans` | ✓ |  | frontend/lib/modules/strategy/services/execution_plan_service.dart:59, frontend/lib/modules/strategy/services/execution_plan_service.dart:66 |
| `POST /operations/strategy/assumptions` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:36 |
| `POST /operations/strategy/decision-records` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:132 |
| `POST /operations/strategy/evidence` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:75 |
| `POST /operations/tasks` | ✓ |  | frontend/lib/modules/tasks/services/task_service.dart:77 |
| `POST /projects` | ✗ GHOST |  | frontend/lib/modules/strategy/services/validation_service.dart:219 |
| `POST /strategy/canvases` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:58 |
| `POST /strategy/revisions` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:81 |
| `POST /tech-radar/seed` | ✗ GHOST |  | frontend/lib/modules/skills/services/tech_radar_service.dart:116 |
| `POST /workforce/agents` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:509 |
| `POST /workforce/decisions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:386 |
| `POST /workforce/heartbeats/check-stalled` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:467 |
| `POST /workforce/routines` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:494 |
| `POST /workforce/routing/test` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:238 |
| `POST /workforce/tools/webhook` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:578 |

## 3. Known-broken allowlist (route ma đã biết — owned by M4/M7)

| Key | Owner milestone |
|---|---|
| `GET /operations/strategy/projects` | M4 |
| `GET /workforce/agents` | M7 |
| `GET /workforce/org-chart` | M7 |
| `GET /workforce/packs` | M7 |

## 4. AgentOS FastAPI routes (`apps/cosa`) — tham chiếu, không thuộc drift lint

| Method | Path | File |
|---|---|---|
| GET | `/approvals` | apps/cosa/api/workforce_routes.py |
| POST | `/approvals/{approval_id}/decision` | apps/cosa/api/workforce_routes.py |
| GET | `/assignments` | apps/cosa/api/workforce_routes.py |
| POST | `/assignments` | apps/cosa/api/workforce_routes.py |
| POST | `/assignments/{assignment_id}/retire` | apps/cosa/api/workforce_routes.py |
| POST | `/candidates` | apps/cosa/api/skill_registry_routes.py |
| GET | `/capabilities` | apps/cosa/api/workforce_routes.py |
| GET | `/composition` | apps/cosa/api/workforce_routes.py |
| POST | `/connectors/authorize` | apps/cosa/api/connector_routes.py |
| POST | `/connectors/grant` | apps/cosa/api/connector_routes.py |
| POST | `/connectors/install` | apps/cosa/api/connector_routes.py |
| POST | `/connectors/revoke` | apps/cosa/api/connector_routes.py |
| GET | `/conversations` | apps/cosa/api/conversation_routes.py |
| POST | `/conversations` | apps/cosa/api/conversation_routes.py |
| GET | `/conversations/{conversation_id}` | apps/cosa/api/conversation_routes.py |
| PATCH | `/conversations/{conversation_id}` | apps/cosa/api/conversation_routes.py |
| GET | `/conversations/{conversation_id}/artifacts` | apps/cosa/api/conversation_routes.py |
| POST | `/conversations/{conversation_id}/messages` | apps/cosa/api/conversation_routes.py |
| GET | `/correlation/{correlation_id}` | apps/cosa/api/event_operations_routes.py |
| GET | `/cost-observations` | apps/cosa/api/workforce_routes.py |
| POST | `/customer-support` | apps/cosa/api/copilot_routes.py |
| GET | `/dead-letter` | apps/cosa/api/event_operations_routes.py |
| GET | `/documents` | apps/cosa/api/vault_routes.py |
| POST | `/documents/upload-ticket` | apps/cosa/api/vault_routes.py |
| DELETE | `/documents/{document_id}` | apps/cosa/api/vault_routes.py |
| GET | `/documents/{document_id}` | apps/cosa/api/vault_routes.py |
| POST | `/documents/{document_id}/confirm` | apps/cosa/api/vault_routes.py |
| POST | `/events` | apps/cosa/api/event_intake_routes.py |
| GET | `/health` | apps/cosa/api/workforce_routes.py |
| GET | `/healthz` | apps/cosa/api/app.py |
| GET | `/knowledge/graph` | apps/cosa/api/vault_routes.py |
| POST | `/knowledge/ingestions/{ingestion_id}/review` | apps/cosa/api/knowledge_routes.py |
| GET | `/knowledge/sources` | apps/cosa/api/vault_routes.py |
| POST | `/knowledge/uploads` | apps/cosa/api/knowledge_routes.py |
| POST | `/knowledge/uploads/{ingestion_id}/complete` | apps/cosa/api/knowledge_routes.py |
| GET | `/live` | apps/cosa/api/app.py |
| GET | `/live` | apps/cosa/worker/health.py |
| GET | `/metrics` | apps/cosa/api/app.py |
| GET | `/metrics` | apps/cosa/api/autopilot_metrics_routes.py |
| GET | `/metrics` | apps/cosa/worker/health.py |
| GET | `/org-chart` | apps/cosa/api/workforce_routes.py |
| GET | `/ready` | apps/cosa/api/app.py |
| GET | `/ready` | apps/cosa/worker/health.py |
| POST | `/retrieval/query` | apps/cosa/api/vault_routes.py |
| GET | `/runs` | apps/cosa/api/workforce_routes.py |
| GET | `/runs/{run_id}` | apps/cosa/api/workforce_routes.py |
| GET | `/runs/{run_id}/artifacts` | apps/cosa/api/workforce_routes.py |
| POST | `/runs/{run_id}/cancel` | apps/cosa/api/routes.py |
| GET | `/runs/{run_id}/events` | apps/cosa/api/workforce_routes.py |
| GET | `/runs/{run_id}/events` | apps/cosa/api/routes.py |
| GET | `/schedules` | apps/cosa/api/schedule_routes.py |
| GET | `/schedules` | apps/cosa/api/workforce_routes.py |
| POST | `/schedules` | apps/cosa/api/schedule_routes.py |
| POST | `/schedules` | apps/cosa/api/workforce_routes.py |
| POST | `/schedules/{schedule_id}/run-now` | apps/cosa/api/schedule_routes.py |
| POST | `/schedules/{schedule_id}/run-now` | apps/cosa/api/workforce_routes.py |
| GET | `/sessions/{conversation_id}` | apps/cosa/api/conversation_routes.py |
| GET | `/sessions/{conversation_id}/artifacts` | apps/cosa/api/conversation_routes.py |
| GET | `/sessions/{conversation_id}/timeline` | apps/cosa/api/conversation_routes.py |
| GET | `/skills` | apps/cosa/api/settings_routes.py |
| PUT | `/skills/{skill_key}` | apps/cosa/api/settings_routes.py |
| POST | `/sync-built-in` | apps/cosa/api/skill_registry_routes.py |
| POST | `/{event_id}/retry` | apps/cosa/api/event_operations_routes.py |
| POST | `/{rule_id}/enable` | apps/cosa/api/event_rule_routes.py |
| GET | `/{skill_id}` | apps/cosa/api/skill_registry_routes.py |
| PUT | `/{skill_id}` | apps/cosa/api/skill_registry_routes.py |
| POST | `/{skill_id}/deprecate` | apps/cosa/api/skill_registry_routes.py |
| POST | `/{skill_id}/evaluate` | apps/cosa/api/skill_registry_routes.py |
| POST | `/{skill_id}/feedback` | apps/cosa/api/skill_registry_routes.py |
| POST | `/{skill_id}/promote` | apps/cosa/api/skill_registry_routes.py |

## 5. `normalizeEndpoint` rewrites gây route drift (M7 gỡ dần)

- `/api/v1/auth/*` → `/identity/*`
- `/auth/*` → `/identity/*`
- `/api/v1/tasks*` → `/operations/tasks*`
- `/tasks*` → `/operations/tasks*`
- `/api/v1/sales/*` → `/commercial/*`
- `/sales/*` → `/commercial/*`
- `/api/v1/finance/*` → `/finance-legal/*`
- `/finance/*` → `/finance-legal/*`
- `/api/v1/legal/*` → `/finance-legal/*`
- `/legal/*` → `/finance-legal/*`
- `/api/v1/marketing/context*` → `/commercial/marketing-context*`
- `/marketing/context*` → `/commercial/marketing-context*`
- `/api/v1/skills*` → `/agent/skills*`
- `/skills*` → `/agent/skills*`

