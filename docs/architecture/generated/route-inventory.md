# Route inventory (GENERATED — `scripts/route_inventory.py`)

Nguồn intent: [M0 §3](../plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md).
Không sửa tay. Chạy `make route-inventory` để cập nhật; `make route-inventory-check` ở CI.

## 1. Encore handler routes (`services/company`, `services/cosa`)

| Method | Path | Service | expose | auth | File |
|---|---|---|---|---|---|
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
| POST | `/commercial/marketing-context/approve` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/customer-research` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/offer-architecture` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/product-marketing` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| POST | `/commercial/marketing-context/submit-review` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| PATCH | `/commercial/marketing-context/twelve-week-plan` | company | ✓ |  | services/company/commercial/handlers/marketing-context.handler.ts |
| POST | `/commercial/marketing-forms` | company | ✓ |  | services/company/commercial/handlers/marketing.handler.ts |
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
| GET | `/identity/me` | company | ✓ | ✓ | services/company/identity/handlers/auth.handler.ts |
| POST | `/identity/session/renew` | company | ✓ |  | services/company/identity/handlers/auth.handler.ts |
| POST | `/identity/sync-from-platform` | company | ✓ |  | services/company/identity/handlers/sync.handler.ts |
| POST | `/identity/tenant-context/resolve` | company | ✓ |  | services/company/identity/handlers/tenant-context.handler.ts |
| POST | `/identity/workforce-members` | company | ✓ |  | services/company/identity/handlers/workforce.handler.ts |
| GET | `/identity/workforce-members/:id` | company | ✓ |  | services/company/identity/handlers/workforce.handler.ts |
| POST | `/identity/workspaces` | company |  |  | services/company/identity/handlers/workspace.handler.ts |
| GET | `/identity/workspaces/:id` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| GET | `/identity/workspaces/:workspaceId/platform-company` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| GET | `/legal/applicable-obligations` | company | ✓ |  | services/company/finance-legal/handlers/legal-applicability.handler.ts |
| GET | `/legal/legal-entity-profiles` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles/:id/verify` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles/:id/verify/confirm` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| GET | `/legal/obligation-instances` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/legal/obligation-instances` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/operations/cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/executive-context` | company | ✓ |  | services/company/operations/handlers/executive-context.handler.ts |
| POST | `/operations/initiatives` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| GET | `/operations/initiatives/:id` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| POST | `/operations/key-results/:id/checkin` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:id/projects` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives/:id/projects` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| DELETE | `/operations/objectives/:id/projects/:projectId` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives/:objectiveId/key-results` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:objectiveId/progress` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/okr-cycles` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/portfolios` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| POST | `/operations/portfolios` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| GET | `/operations/projects` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| POST | `/operations/projects` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| GET | `/operations/projects/:id` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| GET | `/operations/strategy/action-context` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| GET | `/operations/strategy/action-proposals` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| POST | `/operations/strategy/action-proposals` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| POST | `/operations/strategy/action-proposals/:id/accept` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| GET | `/operations/strategy/assumptions` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| POST | `/operations/strategy/assumptions` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| DELETE | `/operations/strategy/assumptions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| GET | `/operations/strategy/assumptions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| PATCH | `/operations/strategy/assumptions/:id` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
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
| DELETE | `/operations/strategy/evidence/:id` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| GET | `/operations/strategy/evidence/:id` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| PATCH | `/operations/strategy/evidence/:id` | company | ✓ |  | services/company/operations/strategy/handlers/evidence.handler.ts |
| GET | `/operations/strategy/experiments` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| POST | `/operations/strategy/experiments` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| DELETE | `/operations/strategy/experiments/:id` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| GET | `/operations/strategy/experiments/:id` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| PATCH | `/operations/strategy/experiments/:id` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
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
| GET | `/operations/strategy/projects/:id/next-best-actions` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| POST | `/operations/strategy/projects/:id/stage` | company | ✓ |  | services/company/operations/strategy/handlers/project-stage.handler.ts |
| GET | `/operations/strategy/projects/:id/stage/transitions` | company | ✓ |  | services/company/operations/strategy/handlers/project-stage.handler.ts |
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
| GET | `/operations/tasks/:id/projects` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/projects` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| DELETE | `/operations/tasks/:id/projects/:projectId` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/status` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/:taskId/dependencies` | company | ✓ |  | services/company/operations/handlers/task-dependency.handler.ts |
| POST | `/operations/weekly-commitments` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/weekly-plans` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/workspaces/:workspaceId/cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/platform/auth/companies/create` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| POST | `/platform/auth/companies/join` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| GET | `/platform/auth/me` | cosa | ✓ | ✓ | services/cosa/handlers/auth.handler.ts |
| PATCH | `/platform/auth/me` | cosa | ✓ | ✓ | services/cosa/handlers/auth.handler.ts |
| GET | `/platform/auth/me/agent-policy-snapshot` | cosa | ✓ | ✓ | services/cosa/handlers/agent-policy.handler.ts |
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

### ⚠ `expose:true` không `auth` (rà M1)

- POST `/commercial/accounts` — services/company/commercial/handlers/account.handler.ts
- GET `/commercial/accounts/:id` — services/company/commercial/handlers/account.handler.ts
- POST `/commercial/campaign-assets` — services/company/commercial/handlers/marketing.handler.ts
- POST `/commercial/campaigns` — services/company/commercial/handlers/marketing.handler.ts
- POST `/commercial/contacts` — services/company/commercial/handlers/contact.handler.ts
- GET `/commercial/contacts/:id` — services/company/commercial/handlers/contact.handler.ts
- POST `/commercial/customers` — services/company/commercial/handlers/customer.handler.ts
- GET `/commercial/customers/:id` — services/company/commercial/handlers/customer.handler.ts
- GET `/commercial/engagement/automation/rules` — services/company/commercial/handlers/customer-engagement/automation.handler.ts
- POST `/commercial/engagement/automation/rules` — services/company/commercial/handlers/customer-engagement/automation.handler.ts
- POST `/commercial/engagement/automation/rules/:key/disable` — services/company/commercial/handlers/customer-engagement/automation.handler.ts
- POST `/commercial/engagement/automation/rules/:key/enable` — services/company/commercial/handlers/customer-engagement/automation.handler.ts
- POST `/commercial/engagement/autopilot/kill-switch` — services/company/commercial/handlers/customer-engagement/autopilot.handler.ts
- GET `/commercial/engagement/autopilot/settings` — services/company/commercial/handlers/customer-engagement/autopilot.handler.ts
- PUT `/commercial/engagement/autopilot/settings` — services/company/commercial/handlers/customer-engagement/autopilot.handler.ts
- POST `/commercial/engagement/autopilot/threshold-check` — services/company/commercial/handlers/customer-engagement/autopilot.handler.ts
- POST `/commercial/engagement/channels` — services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts
- POST `/commercial/engagement/channels/:id/activate` — services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts
- GET `/commercial/engagement/channels/:id/deliveries` — services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts
- POST `/commercial/engagement/channels/:id/pause` — services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts
- POST `/commercial/engagement/channels/zalo/webhook` — services/company/commercial/handlers/customer-engagement/channels/zalo.handler.ts
- GET `/commercial/engagement/contacts/:id/360` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- GET `/commercial/engagement/copilot-invocations/:id` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- POST `/commercial/engagement/copilot-invocations/:id/feedback` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- POST `/commercial/engagement/copilot-invocations/:runId/result` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- GET `/commercial/engagement/copilot/settings` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- PATCH `/commercial/engagement/copilot/settings` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- POST `/commercial/engagement/copilot/settings/disable` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- POST `/commercial/engagement/copilot/settings/enable` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- POST `/commercial/engagement/decision-authorities` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/decision-authorities/:authorityKey/grants` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/decision-requests` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/decision-requests/:id/approvals` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/decision-requests/:id/execute` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/decision-requests/:id/review` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/decision-requests/:id/submit` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/deliveries/:id/retry` — services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts
- PUT `/commercial/engagement/escalation-routes/:routeKey` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- GET `/commercial/engagement/threads` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/threads` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- GET `/commercial/engagement/threads/:id` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/threads/:id/assign` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- GET `/commercial/engagement/threads/:id/automation/applications` — services/company/commercial/handlers/customer-engagement/automation.handler.ts
- POST `/commercial/engagement/threads/:id/automation/dry-run` — services/company/commercial/handlers/customer-engagement/automation.handler.ts
- GET `/commercial/engagement/threads/:id/context` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- POST `/commercial/engagement/threads/:id/copilot` — services/company/commercial/handlers/customer-engagement/copilot.handler.ts
- POST `/commercial/engagement/threads/:id/hand-back` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/threads/:id/messages` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/threads/:id/notes` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/threads/:id/status` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/engagement/threads/:id/takeover` — services/company/commercial/handlers/customer-engagement/desk.handler.ts
- POST `/commercial/invoices` — services/company/commercial/handlers/billing.handler.ts
- GET `/commercial/leads` — services/company/commercial/handlers/lead.handler.ts
- POST `/commercial/leads` — services/company/commercial/handlers/lead.handler.ts
- GET `/commercial/leads/:id` — services/company/commercial/handlers/lead.handler.ts
- POST `/commercial/leads/:id/stage` — services/company/commercial/handlers/lead.handler.ts
- GET `/commercial/marketing-context` — services/company/commercial/handlers/marketing-context.handler.ts
- POST `/commercial/marketing-context/approve` — services/company/commercial/handlers/marketing-context.handler.ts
- PATCH `/commercial/marketing-context/customer-research` — services/company/commercial/handlers/marketing-context.handler.ts
- PATCH `/commercial/marketing-context/offer-architecture` — services/company/commercial/handlers/marketing-context.handler.ts
- PATCH `/commercial/marketing-context/product-marketing` — services/company/commercial/handlers/marketing-context.handler.ts
- POST `/commercial/marketing-context/submit-review` — services/company/commercial/handlers/marketing-context.handler.ts
- PATCH `/commercial/marketing-context/twelve-week-plan` — services/company/commercial/handlers/marketing-context.handler.ts
- POST `/commercial/marketing-forms` — services/company/commercial/handlers/marketing.handler.ts
- POST `/commercial/opportunities` — services/company/commercial/handlers/opportunity.handler.ts
- GET `/commercial/opportunities/:id` — services/company/commercial/handlers/opportunity.handler.ts
- POST `/commercial/opportunities/:id/stage` — services/company/commercial/handlers/opportunity.handler.ts
- POST `/commercial/subscriptions` — services/company/commercial/handlers/billing.handler.ts
- GET `/commercial/workspaces/:workspaceId/campaigns` — services/company/commercial/handlers/marketing.handler.ts
- GET `/commercial/workspaces/:workspaceId/invoices` — services/company/commercial/handlers/billing.handler.ts
- POST `/control-plane/internal/child-tasks` — services/cosa/handlers/control-plane.handler.ts
- GET `/control-plane/internal/child-tasks/:parentTaskId` — services/cosa/handlers/control-plane.handler.ts
- GET `/control-plane/internal/child-tasks/:parentTaskId/join` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/child-tasks/complete` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/cost-ledger` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/delivery-attempts` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/delivery-policies` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/leases/acquire` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/leases/release` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/leases/renew` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/missions` — services/cosa/handlers/control-plane.handler.ts
- GET `/control-plane/internal/missions/:id` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/scheduled-tasks` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/scheduled-tasks/:taskId/complete` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/scheduled-tasks/:taskId/heartbeat` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/scheduled-tasks/poll` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/scheduled-tasks/reclaim-stuck` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/signals` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/tasks` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/tasks/:taskId/checkout` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/watches` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/workers` — services/cosa/handlers/control-plane.handler.ts
- POST `/control-plane/internal/workers/:id/heartbeat` — services/cosa/handlers/control-plane.handler.ts
- POST `/cosa/connectors/assert` — services/cosa/handlers/workspace-connector.handler.ts
- POST `/cosa/connectors/authorize` — services/cosa/handlers/workspace-connector.handler.ts
- POST `/cosa/connectors/grant` — services/cosa/handlers/workspace-connector.handler.ts
- POST `/cosa/connectors/install` — services/cosa/handlers/workspace-connector.handler.ts
- POST `/cosa/connectors/revoke` — services/cosa/handlers/workspace-connector.handler.ts
- POST `/cosa/document-ingestions` — services/cosa/handlers/document-ingestion.handler.ts
- GET `/cosa/document-ingestions/:ingestionId` — services/cosa/handlers/document-ingestion.handler.ts
- POST `/cosa/document-ingestions/:ingestionId/complete` — services/cosa/handlers/document-ingestion.handler.ts
- POST `/cosa/document-ingestions/:ingestionId/review` — services/cosa/handlers/document-ingestion.handler.ts
- POST `/cosa/document-ingestions/:ingestionId/transition` — services/cosa/handlers/document-ingestion.handler.ts
- GET `/cosa/runtime/nodes` — services/cosa/handlers/runtime-node.handler.ts
- POST `/cosa/runtime/nodes/heartbeat` — services/cosa/handlers/runtime-node.handler.ts
- POST `/cosa/runtime/nodes/register` — services/cosa/handlers/runtime-node.handler.ts
- POST `/cosa/runtime/nodes/revoke` — services/cosa/handlers/runtime-node.handler.ts
- POST `/cosa/runtime/route` — services/cosa/handlers/runtime-node.handler.ts
- GET `/cosa/schedules` — services/cosa/handlers/workspace-schedule.handler.ts
- POST `/cosa/schedules` — services/cosa/handlers/workspace-schedule.handler.ts
- POST `/cosa/schedules/:scheduleId/run-now` — services/cosa/handlers/workspace-schedule.handler.ts
- GET `/cosa/schedules/executions/:executionId` — services/cosa/handlers/workspace-schedule.handler.ts
- POST `/cosa/schedules/executions/complete` — services/cosa/handlers/workspace-schedule.handler.ts
- POST `/cosa/workers/ingress` — services/cosa/handlers/worker-ingress.handler.ts
- POST `/events/internal/knowledge-published` — services/company/events/knowledge-published.api.ts
- GET `/events/metrics` — services/company/events/event-operations.api.ts
- GET `/events/outbox` — services/company/events/event-operations.api.ts
- POST `/events/outbox/:eventId/retry` — services/company/events/event-operations.api.ts
- POST `/finance-legal/accounting-periods` — services/company/finance-legal/handlers/accounting-period.handler.ts
- GET `/finance-legal/accounting-periods/:id` — services/company/finance-legal/handlers/accounting-period.handler.ts
- POST `/finance-legal/accounting-periods/:id/close` — services/company/finance-legal/handlers/accounting-period.handler.ts
- POST `/finance-legal/accounting-profiles` — services/company/finance-legal/handlers/accounting-profile.handler.ts
- GET `/finance-legal/accounting-profiles/by-workspace/:workspaceId` — services/company/finance-legal/handlers/accounting-profile.handler.ts
- POST `/finance-legal/ai-compliance/authorizations` — services/company/finance-legal/handlers/ai-data-governance.handler.ts
- POST `/finance-legal/ai-compliance/authorizations/:id/withdraw` — services/company/finance-legal/handlers/ai-data-governance.handler.ts
- GET `/finance-legal/ai-compliance/center` — services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- POST `/finance-legal/ai-compliance/data-profiles` — services/company/finance-legal/handlers/ai-data-governance.handler.ts
- POST `/finance-legal/ai-compliance/data-subject-requests` — services/company/finance-legal/handlers/ai-data-governance.handler.ts
- POST `/finance-legal/ai-compliance/deployments` — services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- POST `/finance-legal/ai-compliance/deployments/:deploymentId/approve` — services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- POST `/finance-legal/ai-compliance/deployments/:deploymentId/assessments` — services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- POST `/finance-legal/ai-compliance/deployments/:deploymentId/resume` — services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- POST `/finance-legal/ai-compliance/deployments/:deploymentId/suspend` — services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- POST `/finance-legal/ai-compliance/incidents` — services/company/finance-legal/handlers/ai-incident-response.handler.ts
- POST `/finance-legal/ai-compliance/incidents/:id/resolve` — services/company/finance-legal/handlers/ai-incident-response.handler.ts
- POST `/finance-legal/ai-compliance/provider-profiles` — services/company/finance-legal/handlers/ai-data-governance.handler.ts
- POST `/finance-legal/ai-compliance/resolve-data-use` — services/company/finance-legal/handlers/ai-data-governance.handler.ts
- GET `/finance-legal/ai-compliance/snapshots` — services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts
- POST `/finance-legal/ai-compliance/snapshots/:id/verify` — services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts
- POST `/finance-legal/cas/webhook` — services/company/finance-legal/handlers/cas-webhook.handler.ts
- POST `/finance-legal/checklist-items` — services/company/finance-legal/handlers/legal-checklist-item.handler.ts
- GET `/finance-legal/checklist-items/:id` — services/company/finance-legal/handlers/legal-checklist-item.handler.ts
- POST `/finance-legal/checklist-items/:id/complete` — services/company/finance-legal/handlers/legal-checklist-item.handler.ts
- POST `/finance-legal/exceptions` — services/company/finance-legal/handlers/finance-exception.handler.ts
- GET `/finance-legal/exceptions/:id` — services/company/finance-legal/handlers/finance-exception.handler.ts
- POST `/finance-legal/exceptions/:id/resolve` — services/company/finance-legal/handlers/finance-exception.handler.ts
- POST `/finance-legal/fiscal-profiles` — services/company/finance-legal/handlers/accounting-regime.handler.ts
- GET `/finance-legal/obligation-templates` — services/company/finance-legal/handlers/regulation-catalog.handler.ts
- POST `/finance-legal/obligations` — services/company/finance-legal/handlers/legal-obligation.handler.ts
- GET `/finance-legal/obligations/:id` — services/company/finance-legal/handlers/legal-obligation.handler.ts
- POST `/finance-legal/obligations/:id/fulfill` — services/company/finance-legal/handlers/legal-obligation.handler.ts
- GET `/finance-legal/regulation-sources` — services/company/finance-legal/handlers/regulation-catalog.handler.ts
- POST `/finance-legal/snapshots` — services/company/finance-legal/handlers/finance-snapshot.handler.ts
- GET `/finance-legal/snapshots/latest` — services/company/finance-legal/handlers/finance-snapshot.handler.ts
- GET `/finance-legal/transactions` — services/company/finance-legal/handlers/financial-transaction.handler.ts
- POST `/finance-legal/transactions` — services/company/finance-legal/handlers/financial-transaction.handler.ts
- GET `/finance-legal/transactions/:id` — services/company/finance-legal/handlers/financial-transaction.handler.ts
- POST `/finance-legal/transactions/:id/approve` — services/company/finance-legal/handlers/financial-transaction.handler.ts
- GET `/finance-legal/workspaces/:workspaceId/fiscal-profiles` — services/company/finance-legal/handlers/accounting-regime.handler.ts
- GET `/finance/accounting-documents` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- POST `/finance/accounting-documents` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- POST `/finance/accounting-documents/:id/confirm` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- GET `/finance/bank-connections` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- POST `/finance/bank-connections` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- GET `/finance/bank-transactions` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- GET `/finance/reconciliation-proposals` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- POST `/finance/reconciliation-proposals/:id/accept` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- GET `/finance/regime-policy` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- GET `/finance/snapshots` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- POST `/finance/snapshots/calculate` — services/company/finance-legal/handlers/finance-tt58.handler.ts
- GET `/healthz` — services/company/identity/handlers/health.handler.ts
- GET `/healthz` — services/cosa/handlers/health.handler.ts
- POST `/identity/session/renew` — services/company/identity/handlers/auth.handler.ts
- POST `/identity/sync-from-platform` — services/company/identity/handlers/sync.handler.ts
- POST `/identity/tenant-context/resolve` — services/company/identity/handlers/tenant-context.handler.ts
- POST `/identity/workforce-members` — services/company/identity/handlers/workforce.handler.ts
- GET `/identity/workforce-members/:id` — services/company/identity/handlers/workforce.handler.ts
- GET `/identity/workspaces/:id` — services/company/identity/handlers/workspace.handler.ts
- GET `/identity/workspaces/:workspaceId/platform-company` — services/company/identity/handlers/workspace.handler.ts
- GET `/legal/applicable-obligations` — services/company/finance-legal/handlers/legal-applicability.handler.ts
- GET `/legal/legal-entity-profiles` — services/company/finance-legal/handlers/legal-entity-profile.handler.ts
- POST `/legal/legal-entity-profiles` — services/company/finance-legal/handlers/legal-entity-profile.handler.ts
- POST `/legal/legal-entity-profiles/:id/verify` — services/company/finance-legal/handlers/legal-entity-profile.handler.ts
- POST `/legal/legal-entity-profiles/:id/verify/confirm` — services/company/finance-legal/handlers/legal-entity-profile.handler.ts
- GET `/legal/obligation-instances` — services/company/finance-legal/handlers/legal-obligation.handler.ts
- POST `/legal/obligation-instances` — services/company/finance-legal/handlers/legal-obligation.handler.ts
- POST `/operations/cycles` — services/company/operations/handlers/twelve-week-year.handler.ts
- GET `/operations/executive-context` — services/company/operations/handlers/executive-context.handler.ts
- POST `/operations/initiatives` — services/company/operations/handlers/initiative.handler.ts
- GET `/operations/initiatives/:id` — services/company/operations/handlers/initiative.handler.ts
- POST `/operations/key-results/:id/checkin` — services/company/operations/handlers/okr.handler.ts
- POST `/operations/objectives` — services/company/operations/handlers/okr.handler.ts
- GET `/operations/objectives/:id` — services/company/operations/handlers/okr.handler.ts
- GET `/operations/objectives/:id/projects` — services/company/operations/handlers/okr.handler.ts
- POST `/operations/objectives/:id/projects` — services/company/operations/handlers/okr.handler.ts
- DELETE `/operations/objectives/:id/projects/:projectId` — services/company/operations/handlers/okr.handler.ts
- POST `/operations/objectives/:objectiveId/key-results` — services/company/operations/handlers/okr.handler.ts
- GET `/operations/objectives/:objectiveId/progress` — services/company/operations/handlers/okr.handler.ts
- POST `/operations/okr-cycles` — services/company/operations/handlers/okr.handler.ts
- GET `/operations/portfolios` — services/company/operations/handlers/project.handler.ts
- POST `/operations/portfolios` — services/company/operations/handlers/project.handler.ts
- GET `/operations/projects` — services/company/operations/handlers/project.handler.ts
- POST `/operations/projects` — services/company/operations/handlers/project.handler.ts
- GET `/operations/projects/:id` — services/company/operations/handlers/project.handler.ts
- GET `/operations/strategy/action-context` — services/company/operations/strategy/handlers/next-best-action.handler.ts
- GET `/operations/strategy/action-proposals` — services/company/operations/strategy/handlers/next-best-action.handler.ts
- POST `/operations/strategy/action-proposals` — services/company/operations/strategy/handlers/next-best-action.handler.ts
- POST `/operations/strategy/action-proposals/:id/accept` — services/company/operations/strategy/handlers/next-best-action.handler.ts
- GET `/operations/strategy/assumptions` — services/company/operations/strategy/handlers/assumption.handler.ts
- POST `/operations/strategy/assumptions` — services/company/operations/strategy/handlers/assumption.handler.ts
- DELETE `/operations/strategy/assumptions/:id` — services/company/operations/strategy/handlers/assumption.handler.ts
- GET `/operations/strategy/assumptions/:id` — services/company/operations/strategy/handlers/assumption.handler.ts
- PATCH `/operations/strategy/assumptions/:id` — services/company/operations/strategy/handlers/assumption.handler.ts
- GET `/operations/strategy/decision-records` — services/company/operations/strategy/handlers/decision-record.handler.ts
- POST `/operations/strategy/decision-records` — services/company/operations/strategy/handlers/decision-record.handler.ts
- DELETE `/operations/strategy/decision-records/:id` — services/company/operations/strategy/handlers/decision-record.handler.ts
- GET `/operations/strategy/decision-records/:id` — services/company/operations/strategy/handlers/decision-record.handler.ts
- GET `/operations/strategy/discovery-signals` — services/company/operations/strategy/handlers/discovery-signal.handler.ts
- POST `/operations/strategy/discovery-signals` — services/company/operations/strategy/handlers/discovery-signal.handler.ts
- DELETE `/operations/strategy/discovery-signals/:id` — services/company/operations/strategy/handlers/discovery-signal.handler.ts
- GET `/operations/strategy/discovery-signals/:id` — services/company/operations/strategy/handlers/discovery-signal.handler.ts
- PATCH `/operations/strategy/discovery-signals/:id` — services/company/operations/strategy/handlers/discovery-signal.handler.ts
- GET `/operations/strategy/evidence` — services/company/operations/strategy/handlers/evidence.handler.ts
- POST `/operations/strategy/evidence` — services/company/operations/strategy/handlers/evidence.handler.ts
- DELETE `/operations/strategy/evidence/:id` — services/company/operations/strategy/handlers/evidence.handler.ts
- GET `/operations/strategy/evidence/:id` — services/company/operations/strategy/handlers/evidence.handler.ts
- PATCH `/operations/strategy/evidence/:id` — services/company/operations/strategy/handlers/evidence.handler.ts
- GET `/operations/strategy/experiments` — services/company/operations/strategy/handlers/experiment.handler.ts
- POST `/operations/strategy/experiments` — services/company/operations/strategy/handlers/experiment.handler.ts
- DELETE `/operations/strategy/experiments/:id` — services/company/operations/strategy/handlers/experiment.handler.ts
- GET `/operations/strategy/experiments/:id` — services/company/operations/strategy/handlers/experiment.handler.ts
- PATCH `/operations/strategy/experiments/:id` — services/company/operations/strategy/handlers/experiment.handler.ts
- GET `/operations/strategy/gate-evaluations` — services/company/operations/strategy/handlers/gate-evaluation.handler.ts
- POST `/operations/strategy/gate-evaluations` — services/company/operations/strategy/handlers/gate-evaluation.handler.ts
- DELETE `/operations/strategy/gate-evaluations/:id` — services/company/operations/strategy/handlers/gate-evaluation.handler.ts
- GET `/operations/strategy/gate-evaluations/:id` — services/company/operations/strategy/handlers/gate-evaluation.handler.ts
- PATCH `/operations/strategy/gate-evaluations/:id` — services/company/operations/strategy/handlers/gate-evaluation.handler.ts
- GET `/operations/strategy/interviews` — services/company/operations/strategy/handlers/interview.handler.ts
- POST `/operations/strategy/interviews` — services/company/operations/strategy/handlers/interview.handler.ts
- DELETE `/operations/strategy/interviews/:id` — services/company/operations/strategy/handlers/interview.handler.ts
- GET `/operations/strategy/interviews/:id` — services/company/operations/strategy/handlers/interview.handler.ts
- PATCH `/operations/strategy/interviews/:id` — services/company/operations/strategy/handlers/interview.handler.ts
- GET `/operations/strategy/projects/:id/next-best-actions` — services/company/operations/strategy/handlers/next-best-action.handler.ts
- POST `/operations/strategy/projects/:id/stage` — services/company/operations/strategy/handlers/project-stage.handler.ts
- GET `/operations/strategy/projects/:id/stage/transitions` — services/company/operations/strategy/handlers/project-stage.handler.ts
- GET `/operations/strategy/projects/:projectId/proposed-experiments` — services/company/operations/strategy/handlers/experiment.handler.ts
- GET `/operations/strategy/projects/:projectId/ranked-assumptions` — services/company/operations/strategy/handlers/assumption.handler.ts
- GET `/operations/strategy/stage-context` — services/company/operations/strategy/handlers/project-stage.handler.ts
- GET `/operations/strategy/stage-policies` — services/company/operations/strategy/handlers/stage-policy.handler.ts
- POST `/operations/strategy/stage-policies` — services/company/operations/strategy/handlers/stage-policy.handler.ts
- DELETE `/operations/strategy/stage-policies/:id` — services/company/operations/strategy/handlers/stage-policy.handler.ts
- GET `/operations/strategy/stage-policies/:id` — services/company/operations/strategy/handlers/stage-policy.handler.ts
- PATCH `/operations/strategy/stage-policies/:id` — services/company/operations/strategy/handlers/stage-policy.handler.ts
- GET `/operations/strategy/stage-transitions` — services/company/operations/strategy/handlers/stage-transition-config.handler.ts
- POST `/operations/strategy/stage-transitions` — services/company/operations/strategy/handlers/stage-transition-config.handler.ts
- DELETE `/operations/strategy/stage-transitions/:id` — services/company/operations/strategy/handlers/stage-transition-config.handler.ts
- GET `/operations/strategy/stage-transitions/:id` — services/company/operations/strategy/handlers/stage-transition-config.handler.ts
- GET `/operations/strategy/venture-profile` — services/company/operations/strategy/handlers/venture-profile.handler.ts
- PUT `/operations/strategy/venture-profile` — services/company/operations/strategy/handlers/venture-profile.handler.ts
- POST `/operations/strategy/venture-stage/assess` — services/company/operations/strategy/handlers/venture-stage.handler.ts
- POST `/operations/strategy/venture-stage/transition` — services/company/operations/strategy/handlers/venture-stage.handler.ts
- GET `/operations/strategy/venture-stage/transitions` — services/company/operations/strategy/handlers/venture-stage.handler.ts
- GET `/operations/strategy/weekly-reviews` — services/company/operations/strategy/handlers/weekly-review.handler.ts
- POST `/operations/strategy/weekly-reviews` — services/company/operations/strategy/handlers/weekly-review.handler.ts
- POST `/operations/strategy/weekly-reviews/:id/complete` — services/company/operations/strategy/handlers/weekly-review.handler.ts
- POST `/operations/task-dependencies` — services/company/operations/handlers/task-dependency.handler.ts
- POST `/operations/task-schedules` — services/company/operations/handlers/task-dependency.handler.ts
- GET `/operations/tasks` — services/company/operations/handlers/task.handler.ts
- POST `/operations/tasks` — services/company/operations/handlers/task.handler.ts
- GET `/operations/tasks/:id` — services/company/operations/handlers/task.handler.ts
- GET `/operations/tasks/:id/projects` — services/company/operations/handlers/task.handler.ts
- POST `/operations/tasks/:id/projects` — services/company/operations/handlers/task.handler.ts
- DELETE `/operations/tasks/:id/projects/:projectId` — services/company/operations/handlers/task.handler.ts
- POST `/operations/tasks/:id/status` — services/company/operations/handlers/task.handler.ts
- GET `/operations/tasks/:taskId/dependencies` — services/company/operations/handlers/task-dependency.handler.ts
- POST `/operations/weekly-commitments` — services/company/operations/handlers/twelve-week-year.handler.ts
- POST `/operations/weekly-plans` — services/company/operations/handlers/twelve-week-year.handler.ts
- GET `/operations/workspaces/:workspaceId/cycles` — services/company/operations/handlers/twelve-week-year.handler.ts
- POST `/platform/auth/register` — services/cosa/handlers/auth.handler.ts
- POST `/platform/auth/sessions` — services/cosa/handlers/auth.handler.ts
- POST `/platform/internal/list-workspace-memberships` — services/cosa/handlers/venture-workspace.handler.ts
- POST `/platform/internal/mark-workspace-synced` — services/cosa/handlers/venture-workspace.handler.ts
- POST `/platform/internal/validate-workspace-membership` — services/cosa/handlers/venture-workspace.handler.ts

## 2. Frontend company-bound call sites — trạng thái resolve

| Key (METHOD prefix) | Resolved | Owner (allowlist) | Call sites |
|---|---|---|---|
| `DELETE /execution/milestones` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:853 |
| `DELETE /execution/stages` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:781 |
| `DELETE /execution/weekly-commitments` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:478 |
| `DELETE /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:626 |
| `DELETE /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:276 |
| `DELETE /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:557 |
| `DELETE /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:518 |
| `DELETE /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:228 |
| `DELETE /okrs/key-results` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:320 |
| `DELETE /okrs/objectives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:255 |
| `DELETE /operations/objectives` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:99 |
| `DELETE /strategy/canvases` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:96, frontend/lib/modules/strategy/services/strategy_service.dart:107 |
| `DELETE /strategy/initiatives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:628 |
| `DELETE /strategy/projects` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:577 |
| `DELETE /workforce/agents` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:484 |
| `GET /admin` | ✗ GHOST |  | frontend/lib/modules/dashboard/services/hub_service.dart:39, frontend/lib/modules/settings/services/admin_service.dart:14 |
| `GET /business/packs` | ✗ GHOST |  | frontend/lib/modules/organization/services/business_pack_service.dart:17, frontend/lib/modules/organization/services/business_pack_service.dart:35, frontend/lib/modules/organization/services/business_pack_service.dart:52 … |
| `GET /channels` | ✗ GHOST |  | frontend/lib/modules/marketing/services/channels_service.dart:50 |
| `GET /channels/list` | ✗ GHOST |  | frontend/lib/modules/marketing/services/channels_service.dart:167 |
| `GET /commercial/leads` | ✓ |  | frontend/lib/modules/sales/services/sales_service.dart:62 |
| `GET /commercial/marketing-context` | ✓ |  | frontend/lib/modules/marketing/services/marketing_service.dart:150 |
| `GET /connectors` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:14 |
| `GET /connectors/zalo/sessions` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:141 |
| `GET /devices` | ✗ GHOST |  | frontend/lib/modules/settings/services/developer_service.dart:14 |
| `GET /devices/jobs` | ✗ GHOST |  | frontend/lib/modules/settings/services/developer_service.dart:41 |
| `GET /execution/gate-decisions` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:889 |
| `GET /execution/milestones` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:793 |
| `GET /execution/twelve-week-cycles` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:332, frontend/lib/modules/strategy/services/strategy_service.dart:716 |
| `GET /execution/weekly-commitments` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:432 |
| `GET /execution/weekly-plans` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:377 |
| `GET /finance-legal/accounting-profiles/by-workspace` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:80 |
| `GET /finance-legal/snapshots/latest` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:31 |
| `GET /finance-legal/transactions` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:46 |
| `GET /finance-legal/workspaces` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:144 |
| `GET /identity/me` | ✓ |  | frontend/lib/modules/auth/services/auth_service.dart:87, frontend/lib/modules/auth/services/auth_service.dart:357 |
| `GET /marketing/analytics/overview` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:132 |
| `GET /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:600 |
| `GET /marketing/assumptions/summary` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:608 |
| `GET /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:244, frontend/lib/modules/marketing/services/marketing_service.dart:254 |
| `GET /marketing/canvases/revisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:736 |
| `GET /marketing/canvases/status` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:654 |
| `GET /marketing/cockpit-summary` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:125 |
| `GET /marketing/crm/attributions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:708 |
| `GET /marketing/crm/interviews` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:699 |
| `GET /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:542 |
| `GET /marketing/evidence` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:634 |
| `GET /marketing/experiments` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:298 |
| `GET /marketing/funnel` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:140 |
| `GET /marketing/learnings` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:330 |
| `GET /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:503 |
| `GET /marketing/metrics` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:341, frontend/lib/modules/marketing/services/marketing_service.dart:351 |
| `GET /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:211 |
| `GET /marketing/recommendations` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:567 |
| `GET /marketing/skill-executions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:365 |
| `GET /marketing/skills` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:360 |
| `GET /okrs/cycles` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:182 |
| `GET /okrs/key-results` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:264 |
| `GET /okrs/objectives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:213 |
| `GET /operations/objectives` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:54, frontend/lib/modules/strategy/services/outcomes_service.dart:11, frontend/lib/modules/strategy/services/outcomes_service.dart:85 |
| `GET /operations/okr-cycles` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:12 |
| `GET /operations/strategy/assumptions` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:21, frontend/lib/modules/vault/services/evidence_service.dart:88 |
| `GET /operations/strategy/decision-records` | ✓ |  | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:89, frontend/lib/modules/vault/services/evidence_service.dart:118, frontend/lib/modules/vault/services/evidence_service.dart:152 |
| `GET /operations/strategy/evidence` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:60 |
| `GET /operations/strategy/gate-evaluations` | ✓ |  | frontend/lib/modules/strategy/services/stage_gate_service.dart:41, frontend/lib/modules/strategy/services/stage_gate_service.dart:59 |
| `GET /operations/strategy/projects` | ✓ | M4 | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:73 |
| `GET /operations/strategy/stage-context` | ✓ |  | frontend/lib/modules/strategy/services/stage_service.dart:85 |
| `GET /operations/strategy/stage-policies` | ✓ |  | frontend/lib/modules/strategy/services/stage_service.dart:14, frontend/lib/modules/strategy/services/stage_service.dart:98 |
| `GET /operations/strategy/stage-transitions` | ✓ |  | frontend/lib/modules/strategy/services/stage_service.dart:68 |
| `GET /operations/tasks` | ✓ |  | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:30, frontend/lib/modules/tasks/services/task_service.dart:18, frontend/lib/modules/tasks/services/task_service.dart:42 … |
| `GET /operations/workspaces` | ✓ |  | frontend/lib/modules/strategy/services/twelve_wy_service.dart:12, frontend/lib/modules/strategy/services/twelve_wy_service.dart:28 |
| `GET /org` | ✗ GHOST |  | frontend/lib/modules/organization/services/organization_service.dart:14, frontend/lib/modules/organization/services/organization_service.dart:25, frontend/lib/modules/organization/services/organization_service.dart:36 … |
| `GET /plugins` | ✗ GHOST |  | frontend/lib/modules/skills/services/plugins_service.dart:14 |
| `GET /policy-programs` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:172, frontend/lib/modules/finance/services/policy_funding_service.dart:202 |
| `GET /policy-programs/draft-watchlist` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:165 |
| `GET /projects` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:45, frontend/lib/modules/strategy/services/validation_service.dart:25, frontend/lib/modules/strategy/services/validation_service.dart:61 … |
| `GET /runtime/doctor` | ✗ GHOST |  | frontend/lib/core/services/diagnostics_service.dart:8 |
| `GET /strategy/canvases` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:57, frontend/lib/modules/strategy/services/canvas_service.dart:66, frontend/lib/modules/strategy/services/strategy_service.dart:68 … |
| `GET /strategy/founder-profile` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1447 |
| `GET /strategy/initiatives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:586 |
| `GET /strategy/lenses/bsc` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:210 |
| `GET /strategy/lenses/pestel` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:25 |
| `GET /strategy/lenses/summary` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:11 |
| `GET /strategy/lenses/swot` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:87 |
| `GET /strategy/lenses/tows` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_lens_service.dart:133 |
| `GET /strategy/portfolios` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1469 |
| `GET /strategy/projects` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:107, frontend/lib/modules/strategy/services/strategy_service.dart:515, frontend/lib/modules/strategy/services/strategy_service.dart:1666 |
| `GET /strategy/revisions` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:119, frontend/lib/modules/strategy/services/strategy_service.dart:130 |
| `GET /strategy/workspace-templates` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1636 |
| `GET /vault/documents` | ✗ GHOST |  | frontend/lib/modules/vault/services/vault_service.dart:17, frontend/lib/modules/vault/services/vault_service.dart:34 |
| `GET /vault/graph` | ✗ GHOST |  | frontend/lib/modules/vault/services/vault_service.dart:125 |
| `GET /vault/knowledge` | ✗ GHOST |  | frontend/lib/modules/vault/services/vault_service.dart:109 |
| `GET /workforce/agents` | ✗ GHOST | M7 | frontend/lib/modules/agents/services/agent_platform_service.dart:24, frontend/lib/modules/agents/services/agent_platform_service.dart:605, frontend/lib/modules/agents/services/agents_service.dart:34 |
| `GET /workforce/approvals` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:239 |
| `GET /workforce/budgets` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:360 |
| `GET /workforce/cost-ledger` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:399 |
| `GET /workforce/dashboard-summary` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:9, frontend/lib/modules/agents/services/agents_service.dart:13 |
| `GET /workforce/decisions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:333 |
| `GET /workforce/exceptions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:635 |
| `GET /workforce/heartbeats` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:414 |
| `GET /workforce/org-chart` | ✗ GHOST | M7 | frontend/lib/modules/agents/services/agent_platform_service.dart:226, frontend/lib/modules/agents/services/agents_service.dart:54 |
| `GET /workforce/packs` | ✗ GHOST | M7 | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:162 |
| `GET /workforce/prompts` | ✗ GHOST |  | frontend/lib/modules/skills/services/prompt_registry_service.dart:76, frontend/lib/modules/skills/services/prompt_registry_service.dart:85, frontend/lib/modules/skills/services/prompt_registry_service.dart:93 |
| `GET /workforce/routines` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:441 |
| `GET /workforce/runs` | ✗ GHOST |  | frontend/lib/modules/agents/services/agents_service.dart:113, frontend/lib/modules/agents/services/agents_service.dart:122 |
| `GET /workforce/runtimes` | ✗ GHOST |  | frontend/lib/modules/agents/services/agents_service.dart:86 |
| `GET /workforce/skills/physical` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:553 |
| `GET /workforce/stage-roster` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:591 |
| `GET /workforce/tools` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:200, frontend/lib/modules/agents/services/agent_platform_service.dart:525 |
| `GET /workforce/work-products` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:286 |
| `GET /workspace/file` | ✗ GHOST |  | frontend/lib/core/services/workspace_service.dart:21 |
| `GET /workspace/files` | ✗ GHOST |  | frontend/lib/core/services/workspace_service.dart:8 |
| `GET /workspaces` | ✗ GHOST |  | frontend/lib/modules/dashboard/services/hub_service.dart:136, frontend/lib/modules/sales/services/revenue_engine_service.dart:16, frontend/lib/modules/sales/services/revenue_engine_service.dart:70 … |
| `PATCH /commercial/marketing-context/product-marketing` | ✓ |  | frontend/lib/modules/marketing/services/marketing_service.dart:199 |
| `PATCH /identity/me` | ✓ |  | frontend/lib/modules/auth/services/auth_service.dart:344 |
| `PATCH /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:620 |
| `PATCH /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:260 |
| `PATCH /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:552 |
| `PATCH /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:513 |
| `PATCH /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:223 |
| `POST /connectors/zalo/sessions` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:151 |
| `POST /finance-legal/accounting-periods` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:127 |
| `POST /finance-legal/transactions` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:65 |
| `POST /marketing/ai/design-experiment` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:660 |
| `POST /marketing/ai/evaluate-learning-loop` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:714 |
| `POST /marketing/ai/extract-assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:646 |
| `POST /marketing/ai/extract-interview` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:684 |
| `POST /marketing/ai/propose-canvas-revision` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:726 |
| `POST /marketing/analytics/attribution` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:533 |
| `POST /marketing/assets` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:289 |
| `POST /marketing/assumptions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:614 |
| `POST /marketing/campaigns` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:249 |
| `POST /marketing/canvases/revisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:742, frontend/lib/modules/marketing/services/marketing_service.dart:748 |
| `POST /marketing/crm/interviews` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:690 |
| `POST /marketing/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:547 |
| `POST /marketing/evidence` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:640 |
| `POST /marketing/experiments` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:303 |
| `POST /marketing/learning-loop/decisions` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:720 |
| `POST /marketing/learnings` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:336 |
| `POST /marketing/loops` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:508, frontend/lib/modules/marketing/services/marketing_service.dart:523 |
| `POST /marketing/metrics` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:346 |
| `POST /marketing/objectives` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:218 |
| `POST /marketing/recommendations` | ✗ GHOST |  | frontend/lib/modules/marketing/services/marketing_service.dart:572 |
| `POST /operations/strategy/assumptions` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:36 |
| `POST /operations/strategy/decision-records` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:132 |
| `POST /operations/strategy/evidence` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:75 |
| `POST /operations/tasks` | ✓ |  | frontend/lib/modules/tasks/services/task_service.dart:77 |
| `POST /projects` | ✗ GHOST |  | frontend/lib/modules/strategy/services/validation_service.dart:219 |
| `POST /strategy/canvases` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:102, frontend/lib/modules/strategy/services/strategy_service.dart:113 |
| `POST /strategy/projects` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1690 |
| `POST /strategy/revisions` | ✗ GHOST |  | frontend/lib/modules/strategy/services/canvas_service.dart:125, frontend/lib/modules/strategy/services/strategy_service.dart:136 |
| `POST /strategy/stages` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1768 |
| `POST /strategy/workspace-templates` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1651 |
| `POST /strategy/workspace-templates:provision` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1645 |
| `POST /tech-radar/seed` | ✗ GHOST |  | frontend/lib/modules/skills/services/tech_radar_service.dart:116 |
| `POST /workforce/agents` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:470 |
| `POST /workforce/decisions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:347 |
| `POST /workforce/heartbeats/check-stalled` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:428 |
| `POST /workforce/routines` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:455 |
| `POST /workforce/routing/test` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:213 |
| `POST /workforce/tools/webhook` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:539 |
| `PUT /strategy/workspace-templates` | ✗ GHOST |  | frontend/lib/modules/strategy/services/strategy_service.dart:1660 |

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
| GET | `/approvals` | apps/cosa/api/routes.py |
| POST | `/approvals/{approval_id}/decision` | apps/cosa/api/routes.py |
| POST | `/candidates` | apps/cosa/api/skill_registry_routes.py |
| POST | `/connectors/authorize` | apps/cosa/api/routes.py |
| POST | `/connectors/grant` | apps/cosa/api/routes.py |
| POST | `/connectors/install` | apps/cosa/api/routes.py |
| POST | `/connectors/revoke` | apps/cosa/api/routes.py |
| GET | `/conversations` | apps/cosa/api/routes.py |
| POST | `/conversations` | apps/cosa/api/routes.py |
| GET | `/conversations/{conversation_id}` | apps/cosa/api/routes.py |
| PATCH | `/conversations/{conversation_id}` | apps/cosa/api/routes.py |
| GET | `/conversations/{conversation_id}/artifacts` | apps/cosa/api/routes.py |
| POST | `/conversations/{conversation_id}/messages` | apps/cosa/api/routes.py |
| GET | `/correlation/{correlation_id}` | apps/cosa/api/event_operations_routes.py |
| POST | `/customer-support` | apps/cosa/api/copilot_routes.py |
| GET | `/dead-letter` | apps/cosa/api/event_operations_routes.py |
| POST | `/events` | apps/cosa/api/event_intake_routes.py |
| GET | `/healthz` | apps/cosa/api/app.py |
| POST | `/knowledge/ingestions/{ingestion_id}/review` | apps/cosa/api/routes.py |
| POST | `/knowledge/uploads` | apps/cosa/api/routes.py |
| POST | `/knowledge/uploads/{ingestion_id}/complete` | apps/cosa/api/routes.py |
| GET | `/live` | apps/cosa/worker/health.py |
| GET | `/metrics` | apps/cosa/api/app.py |
| GET | `/metrics` | apps/cosa/api/autopilot_metrics_routes.py |
| GET | `/metrics` | apps/cosa/worker/health.py |
| GET | `/ready` | apps/cosa/worker/health.py |
| POST | `/runs/{run_id}/cancel` | apps/cosa/api/routes.py |
| GET | `/runs/{run_id}/events` | apps/cosa/api/routes.py |
| GET | `/schedules` | apps/cosa/api/routes.py |
| POST | `/schedules` | apps/cosa/api/routes.py |
| POST | `/schedules/{schedule_id}/run-now` | apps/cosa/api/routes.py |
| GET | `/sessions/{conversation_id}` | apps/cosa/api/routes.py |
| GET | `/sessions/{conversation_id}/artifacts` | apps/cosa/api/routes.py |
| GET | `/sessions/{conversation_id}/timeline` | apps/cosa/api/routes.py |
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

