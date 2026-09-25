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
| POST | `/commercial/lead-capture/:formKey/ingest` | company | ✓ |  | services/company/commercial/handlers/lead-capture.handler.ts |
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
| POST | `/commercial/projects/:projectId/crm/field-definitions` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| PATCH | `/commercial/projects/:projectId/crm/field-definitions/:fieldId` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| POST | `/commercial/projects/:projectId/crm/field-definitions/:fieldId/retire` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| GET | `/commercial/projects/:projectId/crm/lead-sources` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| POST | `/commercial/projects/:projectId/crm/lead-sources` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| GET | `/commercial/projects/:projectId/crm/leads` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| POST | `/commercial/projects/:projectId/crm/leads` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| GET | `/commercial/projects/:projectId/crm/schema` | company | ✓ |  | services/company/commercial/handlers/project-crm.handler.ts |
| POST | `/commercial/subscriptions` | company | ✓ |  | services/company/commercial/handlers/billing.handler.ts |
| GET | `/commercial/workspaces/:workspaceId/campaigns` | company | ✓ |  | services/company/commercial/handlers/marketing.handler.ts |
| GET | `/commercial/workspaces/:workspaceId/invoices` | company | ✓ |  | services/company/commercial/handlers/billing.handler.ts |
| POST | `/control-plane/internal/automation-dispatches` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| GET | `/control-plane/internal/automation-dispatches/:invocationId` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
| POST | `/control-plane/internal/automation-dispatches/:invocationId/complete` | cosa | ✓ |  | services/cosa/handlers/control-plane.handler.ts |
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
| POST | `/cosa/ai-governance/snapshot` | cosa | ✓ |  | services/cosa/handlers/ai-governance-snapshot.handler.ts |
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
| GET | `/finance-legal/accounting-periods` | company | ✓ |  | services/company/finance-legal/handlers/accounting-period.handler.ts |
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
| POST | `/finance-legal/cas/inbox-worker/tick` | company |  |  | services/company/finance-legal/cas-inbox-worker.cron.ts |
| POST | `/finance-legal/cas/sync/tick` | company |  |  | services/company/finance-legal/cas-sync.cron.ts |
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
| GET | `/finance-legal/payment-allocations` | company | ✓ |  | services/company/finance-legal/handlers/payment-allocation.handler.ts |
| POST | `/finance-legal/payment-allocations` | company | ✓ |  | services/company/finance-legal/handlers/payment-allocation.handler.ts |
| POST | `/finance-legal/payment-allocations/:id/reverse` | company | ✓ |  | services/company/finance-legal/handlers/payment-allocation.handler.ts |
| GET | `/finance-legal/payment-requests` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| POST | `/finance-legal/payment-requests` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| GET | `/finance-legal/payment-requests/:id` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| PATCH | `/finance-legal/payment-requests/:id` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| POST | `/finance-legal/payment-requests/:id/approve` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| POST | `/finance-legal/payment-requests/:id/cancel` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| POST | `/finance-legal/payment-requests/:id/reject` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| POST | `/finance-legal/payment-requests/:id/report-transfer` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
| POST | `/finance-legal/payment-requests/:id/submit` | company | ✓ |  | services/company/finance-legal/handlers/payment-request.handler.ts |
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
| POST | `/finance/accounting-documents/:id/void` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/accounting-mapping/:regimeCode/:mappingVersion/confirm` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/accounting-policies` | company | ✓ |  | services/company/finance-legal/handlers/accounting-policy.handler.ts |
| POST | `/finance/accounting-policies` | company | ✓ |  | services/company/finance-legal/handlers/accounting-policy.handler.ts |
| GET | `/finance/bank-connections` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/bank-connections` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/bank-connections/:id/reauthorize` | company | ✓ |  | services/company/finance-legal/handlers/cas-link.handler.ts |
| POST | `/finance/bank-connections/:id/revoke` | company | ✓ |  | services/company/finance-legal/handlers/cas-link.handler.ts |
| GET | `/finance/bank-transactions` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/books` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/books` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/budget-envelopes` | company | ✓ |  | services/company/finance-legal/handlers/budget-summary.handler.ts |
| GET | `/finance/budget-summary` | company | ✓ |  | services/company/finance-legal/handlers/budget-summary.handler.ts |
| POST | `/finance/cas/link-sessions` | company | ✓ |  | services/company/finance-legal/handlers/cas-link.handler.ts |
| POST | `/finance/cas/link-sessions/:sessionId/exchange` | company | ✓ |  | services/company/finance-legal/handlers/cas-link.handler.ts |
| GET | `/finance/reconciliation-proposals` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/reconciliation-proposals/:id/accept` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/regime-policy` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/reports` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/reports/generate` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/snapshots` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| POST | `/finance/snapshots/calculate` | company | ✓ |  | services/company/finance-legal/handlers/finance-tt58.handler.ts |
| GET | `/finance/tax-obligations` | company | ✓ |  | services/company/finance-legal/handlers/tax-obligation.handler.ts |
| POST | `/finance/tax-obligations` | company | ✓ |  | services/company/finance-legal/handlers/tax-obligation.handler.ts |
| POST | `/finance/tax-obligations/sync` | company | ✓ |  | services/company/finance-legal/handlers/tax-obligation.handler.ts |
| GET | `/healthz` | company | ✓ |  | services/company/identity/handlers/health.handler.ts |
| GET | `/healthz` | cosa | ✓ |  | services/cosa/handlers/health.handler.ts |
| POST | `/identity/_e2e/session` | company |  |  | services/company/identity/handlers/e2e-session.handler.ts |
| POST | `/identity/agent-authorization/tickets` | company | ✓ |  | services/company/identity/handlers/agent-authorization.handler.ts |
| POST | `/identity/agent-capability-grants` | company | ✓ |  | services/company/identity/handlers/agent-authorization.handler.ts |
| POST | `/identity/agent-capability-grants/:grantId/revoke` | company | ✓ |  | services/company/identity/handlers/agent-authorization.handler.ts |
| POST | `/identity/authorization/mode` | company | ✓ |  | services/company/identity/handlers/agent-authorization.handler.ts |
| GET | `/identity/authorization/overview` | company | ✓ |  | services/company/identity/handlers/agent-authorization.handler.ts |
| POST | `/identity/authorization/simulate` | company | ✓ |  | services/company/identity/handlers/agent-authorization.handler.ts |
| POST | `/identity/business-policy/evaluate` | company | ✓ |  | services/company/identity/handlers/business-policy.handler.ts |
| GET | `/identity/business-policy/rules` | company | ✓ |  | services/company/identity/handlers/business-policy.handler.ts |
| GET | `/identity/me` | company | ✓ | ✓ | services/company/identity/handlers/auth.handler.ts |
| GET | `/identity/permissions` | company | ✓ |  | services/company/identity/handlers/permissions.handler.ts |
| PUT | `/identity/permissions` | company | ✓ |  | services/company/identity/handlers/permissions.handler.ts |
| POST | `/identity/permissions/simulate` | company | ✓ |  | services/company/identity/handlers/permissions.handler.ts |
| POST | `/identity/session/renew` | company | ✓ |  | services/company/identity/handlers/auth.handler.ts |
| POST | `/identity/sync-from-platform` | company | ✓ |  | services/company/identity/handlers/sync.handler.ts |
| POST | `/identity/tenant-context/resolve` | company | ✓ |  | services/company/identity/handlers/tenant-context.handler.ts |
| POST | `/identity/workforce-members` | company | ✓ |  | services/company/identity/handlers/workforce.handler.ts |
| GET | `/identity/workforce-members/:id` | company | ✓ |  | services/company/identity/handlers/workforce.handler.ts |
| POST | `/identity/workspaces` | company |  |  | services/company/identity/handlers/workspace.handler.ts |
| GET | `/identity/workspaces/:id` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| PATCH | `/identity/workspaces/:id/company-identity` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| PATCH | `/identity/workspaces/:workspaceId/lifecycle` | company | ✓ |  | services/company/identity/handlers/workspace-lifecycle.handler.ts |
| GET | `/identity/workspaces/:workspaceId/lifecycle/events` | company | ✓ |  | services/company/identity/handlers/workspace-lifecycle.handler.ts |
| GET | `/identity/workspaces/:workspaceId/platform-company` | company | ✓ |  | services/company/identity/handlers/workspace.handler.ts |
| POST | `/internal/identity/membership-events` | company | ✓ |  | services/company/identity/handlers/membership-event.handler.ts |
| POST | `/internal/operations/founder/assets/status-callback` | company | ✓ |  | services/company/operations/handlers/founder-asset-authoring.handler.ts |
| GET | `/internal/operations/projects/:projectId/agent-deployments/:projectAgentDeploymentId/deployment-authority` | company | ✓ |  | services/company/operations/handlers/founder-asset-deployment.handler.ts |
| GET | `/internal/operations/projects/:projectId/agents/:workspaceAgentId/deployment-authority` | company | ✓ |  | services/company/operations/handlers/founder-asset-deployment.handler.ts |
| GET | `/internal/operations/projects/:projectId/deliberations/:deliberationId/authority` | company | ✓ |  | services/company/operations/handlers/executive-deliberation-internal.handler.ts |
| POST | `/internal/operations/projects/:projectId/deliberations/:deliberationId/callback` | company | ✓ |  | services/company/operations/handlers/executive-deliberation-internal.handler.ts |
| GET | `/internal/operations/projects/:projectId/startup-team/:profileKey/run-authority` | company | ✓ |  | services/company/operations/handlers/project-startup-team.handler.ts |
| GET | `/legal/applicable-obligations` | company | ✓ |  | services/company/finance-legal/handlers/legal-applicability.handler.ts |
| GET | `/legal/legal-entity-profiles` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles/:id/verify` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| POST | `/legal/legal-entity-profiles/:id/verify/confirm` | company | ✓ |  | services/company/finance-legal/handlers/legal-entity-profile.handler.ts |
| GET | `/legal/obligation-instances` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/legal/obligation-instances` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/legal/obligation-instances/:id/transition` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| GET | `/legal/obligation-instances/:id/transitions` | company | ✓ |  | services/company/finance-legal/handlers/legal-obligation.handler.ts |
| POST | `/operations/ai-governance-dossiers` | company | ✓ |  | services/company/operations/handlers/ai-governance-dossier.handler.ts |
| POST | `/operations/ai-governance-dossiers/:id/revisions` | company | ✓ |  | services/company/operations/handlers/ai-governance-dossier.handler.ts |
| GET | `/operations/automation/definitions` | company | ✓ |  | services/company/operations/handlers/automation-definition.handler.ts |
| GET | `/operations/automation/definitions/:definitionId` | company | ✓ |  | services/company/operations/handlers/automation-definition.handler.ts |
| PATCH | `/operations/automation/definitions/:definitionId/configuration` | company | ✓ |  | services/company/operations/handlers/automation-definition.handler.ts |
| POST | `/operations/automation/definitions/:definitionId/invocations` | company | ✓ |  | services/company/operations/handlers/automation-invocation.handler.ts |
| POST | `/operations/automation/definitions/:definitionId/revisions` | company | ✓ |  | services/company/operations/handlers/automation-definition.handler.ts |
| POST | `/operations/automation/definitions/:definitionId/suspension` | company | ✓ |  | services/company/operations/handlers/automation-definition.handler.ts |
| POST | `/operations/automation/internal/outcome` | company | ✓ |  | services/company/operations/handlers/automation-outcome.handler.ts |
| GET | `/operations/automation/invocations/:invocationId` | company | ✓ |  | services/company/operations/handlers/automation-invocation.handler.ts |
| POST | `/operations/automation/invocations/:invocationId/cancellation` | company | ✓ |  | services/company/operations/handlers/automation-invocation.handler.ts |
| GET | `/operations/automation/invocations/:invocationId/inspector` | company | ✓ |  | services/company/operations/handlers/automation-inspector.handler.ts |
| GET | `/operations/automation/needs-you` | company | ✓ |  | services/company/operations/handlers/automation-inspector.handler.ts |
| GET | `/operations/capability-policy` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/capability-policy` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/cosa/key-results/:id/checkin` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| POST | `/operations/cosa/objectives` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| POST | `/operations/cosa/objectives/:id/key-results` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| GET | `/operations/cycle-reviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/cycle-review.handler.ts |
| PATCH | `/operations/cycle-reviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/cycle-review.handler.ts |
| POST | `/operations/cycle-reviews/:id/close` | company | ✓ |  | services/company/operations/strategy/handlers/cycle-review.handler.ts |
| POST | `/operations/cycle-reviews/:id/start` | company | ✓ |  | services/company/operations/strategy/handlers/cycle-review.handler.ts |
| POST | `/operations/cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/cycles/:cycleId/reviews` | company | ✓ |  | services/company/operations/strategy/handlers/cycle-review.handler.ts |
| POST | `/operations/cycles/:cycleId/reviews/custom-mid-cycle` | company | ✓ |  | services/company/operations/strategy/handlers/cycle-review.handler.ts |
| PATCH | `/operations/cycles/:id` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/data-governance-dossiers` | company | ✓ |  | services/company/operations/handlers/data-governance-dossier.handler.ts |
| POST | `/operations/data-governance-dossiers/:id/revisions` | company | ✓ |  | services/company/operations/handlers/data-governance-dossier.handler.ts |
| GET | `/operations/execution-cycle-view` | company | ✓ |  | services/company/operations/handlers/execution-cycle-view.handler.ts |
| GET | `/operations/execution-plans` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/execution-plans` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| GET | `/operations/execution-plans/:id` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/execution-plans/:id/accept` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| PATCH | `/operations/execution-plans/:id/items/:itemId` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| POST | `/operations/execution-plans/:id/reject` | company | ✓ |  | services/company/operations/handlers/execution-plan.handler.ts |
| GET | `/operations/execution-settings` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/execution-settings` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/executive-context` | company | ✓ |  | services/company/operations/handlers/executive-context.handler.ts |
| GET | `/operations/founder-assets` | company | ✓ |  | services/company/operations/handlers/founder-asset-query.handler.ts |
| POST | `/operations/founder/assets/commands` | company | ✓ |  | services/company/operations/handlers/founder-asset-authoring.handler.ts |
| GET | `/operations/founder/assets/events` | company | ✓ |  | services/company/operations/handlers/founder-asset-authoring.handler.ts |
| POST | `/operations/goals` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| POST | `/operations/goals/:id/complete` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| GET | `/operations/goals/needing-review` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| GET | `/operations/goals/tree` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| GET | `/operations/initiatives` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| POST | `/operations/initiatives` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| GET | `/operations/initiatives/:id` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| PUT | `/operations/initiatives/:id` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| POST | `/operations/initiatives/:id/approve` | company | ✓ |  | services/company/operations/handlers/initiative.handler.ts |
| GET | `/operations/key-results` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| DELETE | `/operations/key-results/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| PUT | `/operations/key-results/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/key-results/:id/checkin` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/kr-contributions/:id/verify` | company | ✓ |  | services/company/operations/handlers/task-outcome-review.handler.ts |
| POST | `/operations/legal-issue-dossiers` | company | ✓ |  | services/company/operations/handlers/legal-issue-dossier.handler.ts |
| POST | `/operations/legal-issue-dossiers/:id/revisions` | company | ✓ |  | services/company/operations/handlers/legal-issue-dossier.handler.ts |
| GET | `/operations/objectives` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| DELETE | `/operations/objectives/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| PUT | `/operations/objectives/:id` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/objectives/:id/progress` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives/:id/publish` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/objectives/:objectiveId/generate-weekly-cycle` | company | ✓ |  | services/company/operations/handlers/okr-weekly-generator.handler.ts |
| POST | `/operations/objectives/:objectiveId/key-results` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| GET | `/operations/okr-cycles` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/okr-cycles` | company | ✓ |  | services/company/operations/handlers/okr.handler.ts |
| POST | `/operations/onboard/cadence/seed` | company | ✓ |  | services/company/operations/handlers/onboard.handler.ts |
| GET | `/operations/onboard/cadence/status` | company | ✓ |  | services/company/operations/handlers/onboard.handler.ts |
| GET | `/operations/onboard/context/current` | company | ✓ |  | services/company/operations/handlers/onboard.handler.ts |
| POST | `/operations/onboard/dimensions/:dimension` | company | ✓ |  | services/company/operations/handlers/onboard.handler.ts |
| POST | `/operations/onboard/sessions` | company | ✓ |  | services/company/operations/handlers/onboard.handler.ts |
| POST | `/operations/onboard/snapshots` | company | ✓ |  | services/company/operations/handlers/onboard.handler.ts |
| POST | `/operations/onboard/turns` | company | ✓ |  | services/company/operations/handlers/onboard.handler.ts |
| POST | `/operations/organizations/:organizationId/ai-workforce` | company | ✓ |  | services/company/operations/handlers/ai-workforce.handler.ts |
| GET | `/operations/organizations/:organizationId/overview` | company | ✓ |  | services/company/operations/handlers/organization-overview.handler.ts |
| GET | `/operations/organizations/:organizationId/workforce` | company | ✓ |  | services/company/operations/handlers/organization-overview.handler.ts |
| POST | `/operations/outcome-assessments` | company | ✓ |  | services/company/operations/handlers/task-outcome-analysis.handler.ts |
| POST | `/operations/people-risk-dossiers` | company | ✓ |  | services/company/operations/handlers/people-risk-dossier.handler.ts |
| POST | `/operations/people-risk-dossiers/:id/revisions` | company | ✓ |  | services/company/operations/handlers/people-risk-dossier.handler.ts |
| POST | `/operations/product-decision-dossiers` | company | ✓ |  | services/company/operations/handlers/product-decision-dossier.handler.ts |
| POST | `/operations/product-decision-dossiers/:id/revisions` | company | ✓ |  | services/company/operations/handlers/product-decision-dossier.handler.ts |
| GET | `/operations/projects` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| POST | `/operations/projects` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| GET | `/operations/projects/:id` | company | ✓ |  | services/company/operations/handlers/project.handler.ts |
| POST | `/operations/projects/:projectId/agent-deployments` | company | ✓ |  | services/company/operations/handlers/founder-asset-deployment.handler.ts |
| GET | `/operations/projects/:projectId/agent-timeline` | company | ✓ |  | services/company/operations/handlers/founder-asset-query.handler.ts |
| GET | `/operations/projects/:projectId/ai-governance-dossier` | company | ✓ |  | services/company/operations/handlers/ai-governance-dossier.handler.ts |
| GET | `/operations/projects/:projectId/data-governance-dossier` | company | ✓ |  | services/company/operations/handlers/data-governance-dossier.handler.ts |
| GET | `/operations/projects/:projectId/deliberations/:deliberationId` | company | ✓ |  | services/company/operations/handlers/executive-deliberation.handler.ts |
| POST | `/operations/projects/:projectId/deliberations/:deliberationId/cancel` | company | ✓ |  | services/company/operations/handlers/executive-deliberation.handler.ts |
| POST | `/operations/projects/:projectId/deliberations/:deliberationId/decision` | company | ✓ |  | services/company/operations/handlers/executive-deliberation.handler.ts |
| POST | `/operations/projects/:projectId/deliberations/:deliberationId/frame` | company | ✓ |  | services/company/operations/handlers/executive-deliberation.handler.ts |
| POST | `/operations/projects/:projectId/deliberations/draft` | company | ✓ |  | services/company/operations/handlers/executive-deliberation.handler.ts |
| POST | `/operations/projects/:projectId/executive-board/bootstrap-p0-core` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| GET | `/operations/projects/:projectId/executive-board/stage-suggestion` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| POST | `/operations/projects/:projectId/executive-preset` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| GET | `/operations/projects/:projectId/executive-roles` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| POST | `/operations/projects/:projectId/executive-roles/:roleKey/activate` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| POST | `/operations/projects/:projectId/executive-roles/:roleKey/disable` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| GET | `/operations/projects/:projectId/founder-deployments` | company | ✓ |  | services/company/operations/handlers/founder-asset-query.handler.ts |
| POST | `/operations/projects/:projectId/founder-deployments` | company | ✓ |  | services/company/operations/handlers/founder-asset-query.handler.ts |
| POST | `/operations/projects/:projectId/founder-trial/experiments` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| GET | `/operations/projects/:projectId/legal-issue-dossier` | company | ✓ |  | services/company/operations/handlers/legal-issue-dossier.handler.ts |
| PATCH | `/operations/projects/:projectId/lifecycle` | company | ✓ |  | services/company/operations/handlers/project-lifecycle.handler.ts |
| GET | `/operations/projects/:projectId/lifecycle/events` | company | ✓ |  | services/company/operations/handlers/project-lifecycle.handler.ts |
| GET | `/operations/projects/:projectId/operating-loop` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| POST | `/operations/projects/:projectId/operating-loop/commitments` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| POST | `/operations/projects/:projectId/operating-loop/cycles` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| PATCH | `/operations/projects/:projectId/operating-loop/cycles/:cycleId/week` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| POST | `/operations/projects/:projectId/operating-loop/initiatives` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| POST | `/operations/projects/:projectId/operating-loop/key-results` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| POST | `/operations/projects/:projectId/operating-loop/objectives` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| POST | `/operations/projects/:projectId/operating-loop/tasks` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| PATCH | `/operations/projects/:projectId/operating-loop/tasks/:taskId/status` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| POST | `/operations/projects/:projectId/operating-loop/weeks` | company | ✓ |  | services/company/operations/handlers/project-operating-loop.handler.ts |
| GET | `/operations/projects/:projectId/people-risk-dossier` | company | ✓ |  | services/company/operations/handlers/people-risk-dossier.handler.ts |
| GET | `/operations/projects/:projectId/product-decision-dossier` | company | ✓ |  | services/company/operations/handlers/product-decision-dossier.handler.ts |
| GET | `/operations/projects/:projectId/security-posture-dossier` | company | ✓ |  | services/company/operations/handlers/security-posture.handler.ts |
| GET | `/operations/projects/:projectId/startup-team` | company | ✓ |  | services/company/operations/handlers/project-startup-team.handler.ts |
| POST | `/operations/projects/:projectId/startup-team/:profileKey/activate` | company | ✓ |  | services/company/operations/handlers/project-startup-team.handler.ts |
| POST | `/operations/projects/:projectId/startup-team/:profileKey/pause` | company | ✓ |  | services/company/operations/handlers/project-startup-team.handler.ts |
| POST | `/operations/projects/:projectId/workflow-bindings/:bindingId/runs` | company | ✓ |  | services/company/operations/handlers/founder-asset-query.handler.ts |
| GET | `/operations/projects/pending-review` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| POST | `/operations/projects/triage` | company | ✓ |  | services/company/operations/handlers/goals.handler.ts |
| POST | `/operations/security-posture-dossiers` | company | ✓ |  | services/company/operations/handlers/security-posture.handler.ts |
| POST | `/operations/security-posture-dossiers/:id/revisions` | company | ✓ |  | services/company/operations/handlers/security-posture.handler.ts |
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
| GET | `/operations/strategy/interviews` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| POST | `/operations/strategy/interviews` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| DELETE | `/operations/strategy/interviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| GET | `/operations/strategy/interviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| PATCH | `/operations/strategy/interviews/:id` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
| POST | `/operations/strategy/interviews/:id/submit-evidence` | company | ✓ |  | services/company/operations/strategy/handlers/interview.handler.ts |
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
| GET | `/operations/strategy/projects/:id/action-context` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| GET | `/operations/strategy/projects/:id/next-best-actions` | company | ✓ |  | services/company/operations/strategy/handlers/next-best-action.handler.ts |
| POST | `/operations/strategy/projects/:id/weekly-goal` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-goal.handler.ts |
| GET | `/operations/strategy/projects/:projectId/proposed-experiments` | company | ✓ |  | services/company/operations/strategy/handlers/experiment.handler.ts |
| GET | `/operations/strategy/projects/:projectId/ranked-assumptions` | company | ✓ |  | services/company/operations/strategy/handlers/assumption.handler.ts |
| GET | `/operations/strategy/settings` | company | ✓ |  | services/company/operations/strategy/handlers/workspace-strategy-settings.handler.ts |
| PUT | `/operations/strategy/settings` | company | ✓ |  | services/company/operations/strategy/handlers/workspace-strategy-settings.handler.ts |
| GET | `/operations/strategy/weekly-reviews` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-review.handler.ts |
| POST | `/operations/strategy/weekly-reviews` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-review.handler.ts |
| POST | `/operations/strategy/weekly-reviews/:id/complete` | company | ✓ |  | services/company/operations/strategy/handlers/weekly-review.handler.ts |
| POST | `/operations/task-dependencies` | company | ✓ |  | services/company/operations/handlers/task-dependency.handler.ts |
| POST | `/operations/task-outcome-reviews` | company | ✓ |  | services/company/operations/handlers/task-outcome-review.handler.ts |
| POST | `/operations/task-results` | company | ✓ |  | services/company/operations/handlers/task-result.handler.ts |
| GET | `/operations/task-results/:taskResultId/analysis-requests` | company | ✓ |  | services/company/operations/handlers/task-result.handler.ts |
| POST | `/operations/task-schedules` | company | ✓ |  | services/company/operations/handlers/task-dependency.handler.ts |
| GET | `/operations/tasks` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| DELETE | `/operations/tasks/:id` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/:id` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/advance` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/schedule` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| POST | `/operations/tasks/:id/status` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/:taskId/dependencies` | company | ✓ |  | services/company/operations/handlers/task-dependency.handler.ts |
| GET | `/operations/tasks/agent-claimable` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/founder-inbox` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/tasks/stage-roster/:stageCode` | company | ✓ |  | services/company/operations/handlers/task.handler.ts |
| GET | `/operations/twelve-week-commitments` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/twelve-week-cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| GET | `/operations/twelve-week-plans` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| PATCH | `/operations/twelve-week-plans/:id` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/weekly-commitments` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/weekly-plans` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/work-packages` | company | ✓ |  | services/company/operations/handlers/work-package.handler.ts |
| GET | `/operations/work-packages/:id` | company | ✓ |  | services/company/operations/handlers/work-package.handler.ts |
| POST | `/operations/work-packages/:id/priority` | company | ✓ |  | services/company/operations/handlers/task-outcome-review.handler.ts |
| POST | `/operations/work-packages/:id/reassign` | company | ✓ |  | services/company/operations/handlers/work-package.handler.ts |
| POST | `/operations/work-packages/:id/review` | company | ✓ |  | services/company/operations/handlers/task-outcome-review.handler.ts |
| POST | `/operations/work-packages/confirm-proposal` | company | ✓ |  | services/company/operations/handlers/work-package.handler.ts |
| POST | `/operations/work-packages/confirmed-task` | company | ✓ |  | services/company/operations/handlers/work-package.handler.ts |
| GET | `/operations/workspace-runtime/blockers` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspace-runtime/items/:sourceKind/:sourceId` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| POST | `/operations/workspace-runtime/items/:sourceKind/:sourceId/snooze` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspace-runtime/needs-you` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspace-runtime/source-status` | company | ✓ |  | services/company/operations/handlers/workspace-runtime.handler.ts |
| GET | `/operations/workspaces/:workspaceId/cycles` | company | ✓ |  | services/company/operations/handlers/twelve-week-year.handler.ts |
| POST | `/operations/workspaces/:workspaceId/executive-roles/:roleKey/activate` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| POST | `/operations/workspaces/:workspaceId/executive-roles/:roleKey/disable` | company | ✓ |  | services/company/operations/handlers/executive-role-activation.handler.ts |
| POST | `/platform/auth/companies/create` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| POST | `/platform/auth/companies/invitations` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| POST | `/platform/auth/companies/invitations/accept` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| GET | `/platform/auth/me` | cosa | ✓ | ✓ | services/cosa/handlers/auth.handler.ts |
| PATCH | `/platform/auth/me` | cosa | ✓ | ✓ | services/cosa/handlers/auth.handler.ts |
| GET | `/platform/auth/me/agent-policy-snapshot` | cosa | ✓ |  | services/cosa/handlers/agent-policy.handler.ts |
| GET | `/platform/auth/me/companies` | cosa | ✓ | ✓ | services/cosa/handlers/company.handler.ts |
| GET | `/platform/auth/me/locale-snapshot` | cosa | ✓ |  | services/cosa/handlers/auth.handler.ts |
| GET | `/platform/internal/agent-policy` | cosa |  |  | services/cosa/handlers/agent-policy.handler.ts |
| POST | `/platform/internal/agent-policy` | cosa |  |  | services/cosa/handlers/agent-policy.handler.ts |
| GET | `/platform/internal/executive-advisor-overlay` | cosa | ✓ |  | services/cosa/handlers/advisor-overlay.handler.ts |
| POST | `/platform/internal/list-workspace-memberships` | cosa | ✓ |  | services/cosa/handlers/venture-workspace.handler.ts |
| POST | `/platform/internal/mark-workspace-synced` | cosa | ✓ |  | services/cosa/handlers/venture-workspace.handler.ts |
| POST | `/platform/internal/resolve-identity` | cosa | ✓ |  | services/cosa/handlers/venture-workspace.handler.ts |
| POST | `/platform/internal/validate-membership` | cosa |  |  | services/cosa/handlers/company.handler.ts |
| POST | `/platform/internal/validate-workspace-membership` | cosa | ✓ |  | services/cosa/handlers/venture-workspace.handler.ts |
| GET | `/platform/organizations/:organizationId/audit-events` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/organizations/:organizationId/capability-manifest` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| PUT | `/platform/organizations/:organizationId/capability-manifest/:surfaceKey` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/organizations/:organizationId/connectors` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| POST | `/platform/organizations/:organizationId/connectors/:connectorKey/install` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| POST | `/platform/organizations/:organizationId/connectors/:connectorKey/revoke` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/organizations/:organizationId/entitlement` | cosa | ✓ | ✓ | services/cosa/handlers/venture-workspace.handler.ts |
| GET | `/platform/organizations/:organizationId/members` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/organizations/:organizationId/module-visibility` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| PUT | `/platform/organizations/:organizationId/module-visibility/:moduleKey` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| PUT | `/platform/organizations/:organizationId/module-visibility/:moduleKey/preference` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/organizations/:organizationId/runtime-nodes` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| POST | `/platform/organizations/:organizationId/runtime-nodes/:nodeId/revoke` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/organizations/:organizationId/session-context` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| GET | `/platform/organizations/:organizationId/skill-policies` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |
| PUT | `/platform/organizations/:organizationId/skill-policies/:skillKey` | cosa | ✓ |  | services/cosa/handlers/workspace-settings.handler.ts |

### ⚠ `expose:true` không `auth` (rà M1)

- POST `/cosa/ai-governance/snapshot` — services/cosa/handlers/ai-governance-snapshot.handler.ts
- GET `/healthz` — services/company/identity/handlers/health.handler.ts
- GET `/healthz` — services/cosa/handlers/health.handler.ts
- POST `/identity/session/renew` — services/company/identity/handlers/auth.handler.ts
- POST `/identity/sync-from-platform` — services/company/identity/handlers/sync.handler.ts
- GET `/platform/auth/me/agent-policy-snapshot` — services/cosa/handlers/agent-policy.handler.ts
- GET `/platform/auth/me/locale-snapshot` — services/cosa/handlers/auth.handler.ts
- GET `/platform/internal/executive-advisor-overlay` — services/cosa/handlers/advisor-overlay.handler.ts
- POST `/platform/internal/list-workspace-memberships` — services/cosa/handlers/venture-workspace.handler.ts
- POST `/platform/internal/mark-workspace-synced` — services/cosa/handlers/venture-workspace.handler.ts
- POST `/platform/internal/resolve-identity` — services/cosa/handlers/venture-workspace.handler.ts
- POST `/platform/internal/validate-workspace-membership` — services/cosa/handlers/venture-workspace.handler.ts

## 2. Frontend company-bound call sites — trạng thái resolve

| Key (METHOD prefix) | Resolved | Owner (allowlist) | Call sites |
|---|---|---|---|
| `DELETE /execution/milestones` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:332 |
| `DELETE /execution/stages` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:258 |
| `DELETE /execution/weekly-commitments` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:175 |
| `DELETE /operations/key-results` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:240 |
| `DELETE /operations/objectives` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:162 |
| `DELETE /operations/tasks` | ✓ |  | frontend/lib/modules/tasks/services/task_service.dart:160 |
| `DELETE /workforce/agents` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:390 |
| `GET /admin` | ✗ GHOST |  | frontend/lib/modules/dashboard/services/hub_service.dart:39, frontend/lib/modules/settings/services/admin_service.dart:14 |
| `GET /channels` | ✗ GHOST |  | frontend/lib/modules/marketing/services/channels_service.dart:50 |
| `GET /channels/list` | ✗ GHOST |  | frontend/lib/modules/marketing/services/channels_service.dart:167 |
| `GET /commercial/leads` | ✓ |  | frontend/lib/modules/sales/services/sales_service.dart:69 |
| `GET /connectors` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:14 |
| `GET /connectors/zalo/sessions` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:141 |
| `GET /devices` | ✗ GHOST |  | frontend/lib/modules/settings/services/developer_service.dart:14 |
| `GET /devices/jobs` | ✗ GHOST |  | frontend/lib/modules/settings/services/developer_service.dart:41 |
| `GET /execution/gate-decisions` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:370 |
| `GET /execution/milestones` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:272 |
| `GET /execution/twelve-week-cycles` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:189 |
| `GET /execution/weekly-commitments` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:129 |
| `GET /execution/weekly-plans` | ✗ GHOST |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:72 |
| `GET /finance-legal/accounting-profiles/by-workspace` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:105 |
| `GET /finance-legal/snapshots/latest` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:52 |
| `GET /finance-legal/transactions` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:68 |
| `GET /finance-legal/workspaces` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:174 |
| `GET /identity/me` | ✓ |  | frontend/lib/modules/auth/services/auth_service.dart:110, frontend/lib/modules/auth/services/auth_service.dart:533 |
| `GET /identity/workspaces` | ✓ |  | frontend/lib/modules/settings/services/workspace_orientation_service.dart:16, frontend/lib/modules/settings/views/settings_view.dart:117 |
| `GET /operations/execution-settings` | ✓ |  | frontend/lib/modules/strategy/services/execution_plan_service.dart:60 |
| `GET /operations/key-results` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:177 |
| `GET /operations/objectives` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:104 |
| `GET /operations/okr-cycles` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:68 |
| `GET /operations/strategy/assumptions` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:21, frontend/lib/modules/vault/services/evidence_service.dart:88 |
| `GET /operations/strategy/decision-records` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:118, frontend/lib/modules/vault/services/evidence_service.dart:152 |
| `GET /operations/strategy/evidence` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:60 |
| `GET /operations/tasks` | ✓ |  | frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:46, frontend/lib/modules/tasks/services/task_service.dart:18, frontend/lib/modules/tasks/services/task_service.dart:42 … |
| `GET /operations/tasks/founder-inbox` | ✓ |  | frontend/lib/modules/strategy/services/execution_plan_service.dart:81 |
| `GET /operations/workspaces` | ✓ |  | frontend/lib/modules/strategy/services/twelve_week_service.dart:21 |
| `GET /plugins` | ✗ GHOST |  | frontend/lib/modules/skills/services/plugins_service.dart:14 |
| `GET /policy-programs` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:174, frontend/lib/modules/finance/services/policy_funding_service.dart:204 |
| `GET /policy-programs/draft-watchlist` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:167 |
| `GET /projects` | ✗ GHOST |  | frontend/lib/modules/finance/services/policy_funding_service.dart:47 |
| `GET /runtime/doctor` | ✗ GHOST |  | frontend/lib/core/services/diagnostics_service.dart:8 |
| `GET /strategy/initiatives` | ✗ GHOST |  | frontend/lib/modules/strategy/services/project_service.dart:124 |
| `GET /workforce/agents` | ✗ GHOST | M7 | frontend/lib/modules/agents/services/agent_platform_service.dart:521 |
| `GET /workforce/budgets` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:266 |
| `GET /workforce/cost-ledger` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:305 |
| `GET /workforce/decisions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:239 |
| `GET /workforce/heartbeats` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:320 |
| `GET /workforce/prompts` | ✗ GHOST |  | frontend/lib/modules/skills/services/prompt_registry_service.dart:76, frontend/lib/modules/skills/services/prompt_registry_service.dart:85, frontend/lib/modules/skills/services/prompt_registry_service.dart:93 |
| `GET /workforce/routines` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:347 |
| `GET /workforce/runs` | ✗ GHOST |  | frontend/lib/modules/agents/services/agents_service.dart:174 |
| `GET /workforce/runtimes` | ✗ GHOST |  | frontend/lib/modules/agents/services/agents_service.dart:122 |
| `GET /workforce/skills/physical` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:459 |
| `GET /workforce/tools` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:86, frontend/lib/modules/agents/services/agent_platform_service.dart:431 |
| `GET /workspace/file` | ✗ GHOST |  | frontend/lib/core/services/workspace_service.dart:21 |
| `GET /workspace/files` | ✗ GHOST |  | frontend/lib/core/services/workspace_service.dart:8 |
| `GET /workspaces` | ✗ GHOST |  | frontend/lib/modules/dashboard/services/hub_service.dart:136 |
| `POST /connectors/zalo/sessions` | ✗ GHOST |  | frontend/lib/modules/settings/services/connectors_service.dart:151 |
| `POST /finance-legal/accounting-periods` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:157 |
| `POST /finance-legal/transactions` | ✓ |  | frontend/lib/modules/finance/services/finance_service.dart:90 |
| `POST /operations/execution-plans` | ✓ |  | frontend/lib/modules/strategy/services/execution_plan_service.dart:95, frontend/lib/modules/strategy/services/execution_plan_service.dart:102 |
| `POST /operations/key-results` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:213 |
| `POST /operations/objectives` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:130, frontend/lib/modules/strategy/services/okr_service.dart:141, frontend/lib/modules/strategy/services/okr_service.dart:196 |
| `POST /operations/okr-cycles` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:82 |
| `POST /operations/strategy/assumptions` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:36 |
| `POST /operations/strategy/decision-records` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:132 |
| `POST /operations/strategy/evidence` | ✓ |  | frontend/lib/modules/vault/services/evidence_service.dart:75 |
| `POST /operations/tasks` | ✓ |  | frontend/lib/modules/tasks/services/task_service.dart:83 |
| `POST /tech-radar/seed` | ✗ GHOST |  | frontend/lib/modules/skills/services/tech_radar_service.dart:116 |
| `POST /workforce/agents` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:376 |
| `POST /workforce/decisions` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:253 |
| `POST /workforce/heartbeats/check-stalled` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:334 |
| `POST /workforce/routines` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:361 |
| `POST /workforce/routing/test` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:99 |
| `POST /workforce/tools/webhook` | ✗ GHOST |  | frontend/lib/modules/agents/services/agent_platform_service.dart:445 |
| `PUT /operations/key-results` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:229 |
| `PUT /operations/objectives` | ✓ |  | frontend/lib/modules/strategy/services/okr_service.dart:153 |

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
| GET | `/artifacts` | apps/cosa/api/workforce_routes.py |
| GET | `/assignments` | apps/cosa/api/workforce_routes.py |
| POST | `/assignments` | apps/cosa/api/workforce_routes.py |
| POST | `/assignments/{assignment_id}/retire` | apps/cosa/api/workforce_routes.py |
| POST | `/candidates` | apps/cosa/api/skill_registry_routes.py |
| GET | `/capabilities` | apps/cosa/api/workforce_routes.py |
| POST | `/commands` | apps/cosa/assets/internal_routes.py |
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
| GET | `/dashboard-summary` | apps/cosa/api/workforce_routes.py |
| GET | `/dead-letter` | apps/cosa/api/event_operations_routes.py |
| GET | `/documents` | apps/cosa/api/vault_routes.py |
| POST | `/documents` | apps/cosa/api/vault_routes.py |
| DELETE | `/documents/{document_id}` | apps/cosa/api/vault_routes.py |
| GET | `/documents/{document_id}` | apps/cosa/api/vault_routes.py |
| POST | `/documents/{document_id}/legal-hold` | apps/cosa/api/vault_routes.py |
| POST | `/documents/{document_id}/publish` | apps/cosa/api/vault_routes.py |
| POST | `/documents/{document_id}/purge` | apps/cosa/api/vault_routes.py |
| POST | `/documents/{document_id}/review` | apps/cosa/api/vault_routes.py |
| POST | `/documents/{document_id}/revoke` | apps/cosa/api/vault_routes.py |
| POST | `/eligibility` | apps/cosa/api/workforce_internal_routes.py |
| POST | `/events` | apps/cosa/api/event_intake_routes.py |
| GET | `/exceptions` | apps/cosa/api/workforce_routes.py |
| POST | `/first-week-suggestion` | apps/cosa/api/kickoff_suggestion_routes.py |
| GET | `/health` | apps/cosa/api/workforce_routes.py |
| GET | `/healthz` | apps/cosa/api/app.py |
| GET | `/knowledge/graph` | apps/cosa/api/vault_routes.py |
| POST | `/knowledge/ingestions/{ingestion_id}/review` | apps/cosa/api/knowledge_routes.py |
| POST | `/knowledge/projects/{project_id}/search` | apps/cosa/api/project_knowledge_routes.py |
| GET | `/knowledge/sources` | apps/cosa/api/vault_routes.py |
| POST | `/knowledge/uploads` | apps/cosa/api/knowledge_routes.py |
| POST | `/knowledge/uploads/{ingestion_id}/complete` | apps/cosa/api/knowledge_routes.py |
| GET | `/live` | apps/cosa/worker/health.py |
| GET | `/live` | apps/cosa/api/app.py |
| GET | `/metrics` | apps/cosa/worker/health.py |
| GET | `/metrics` | apps/cosa/api/autopilot_metrics_routes.py |
| GET | `/metrics` | apps/cosa/api/app.py |
| GET | `/model-policies/{agent_profile}` | apps/cosa/api/model_policy_routes.py |
| PUT | `/model-policies/{agent_profile}` | apps/cosa/api/model_policy_routes.py |
| GET | `/model-providers` | apps/cosa/api/model_policy_routes.py |
| POST | `/model-providers` | apps/cosa/api/model_policy_routes.py |
| POST | `/model-providers/{profile_id}/test` | apps/cosa/api/model_policy_routes.py |
| GET | `/org-chart` | apps/cosa/api/workforce_routes.py |
| GET | `/projects/{project_id}/activity` | apps/cosa/api/project_activity_routes.py |
| GET | `/projects/{project_id}/activity/stream` | apps/cosa/api/project_activity_routes.py |
| GET | `/projects/{project_id}/activity/{event_id}` | apps/cosa/api/project_activity_routes.py |
| GET | `/ready` | apps/cosa/worker/health.py |
| GET | `/ready` | apps/cosa/api/app.py |
| POST | `/retrieval/query` | apps/cosa/api/vault_routes.py |
| GET | `/roster` | apps/cosa/api/workforce_routes.py |
| GET | `/runs` | apps/cosa/api/workforce_routes.py |
| GET | `/runs/{run_id}` | apps/cosa/api/workforce_routes.py |
| GET | `/runs/{run_id}/artifacts` | apps/cosa/api/workforce_routes.py |
| POST | `/runs/{run_id}/cancel` | apps/cosa/api/routes.py |
| GET | `/runs/{run_id}/events` | apps/cosa/api/workforce_routes.py |
| GET | `/runs/{run_id}/events` | apps/cosa/api/routes.py |
| GET | `/runs/{run_id}/investigation` | apps/cosa/api/workforce_internal_routes.py |
| GET | `/schedules` | apps/cosa/api/workforce_routes.py |
| GET | `/schedules` | apps/cosa/api/schedule_routes.py |
| POST | `/schedules` | apps/cosa/api/workforce_routes.py |
| POST | `/schedules` | apps/cosa/api/schedule_routes.py |
| POST | `/schedules/{schedule_id}/run-now` | apps/cosa/api/workforce_routes.py |
| POST | `/schedules/{schedule_id}/run-now` | apps/cosa/api/schedule_routes.py |
| GET | `/sessions/{conversation_id}` | apps/cosa/api/conversation_routes.py |
| GET | `/sessions/{conversation_id}/artifacts` | apps/cosa/api/conversation_routes.py |
| GET | `/sessions/{conversation_id}/timeline` | apps/cosa/api/conversation_routes.py |
| GET | `/skills` | apps/cosa/api/settings_routes.py |
| PUT | `/skills/{skill_key}` | apps/cosa/api/settings_routes.py |
| GET | `/stage-roster/{stage_code}` | apps/cosa/api/workforce_routes.py |
| POST | `/sync-built-in` | apps/cosa/api/skill_registry_routes.py |
| POST | `/uploads/{upload_id}/complete` | apps/cosa/api/vault_routes.py |
| PUT | `/uploads/{upload_id}/content` | apps/cosa/api/vault_routes.py |
| GET | `/{asset_id}/status` | apps/cosa/assets/internal_routes.py |
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

