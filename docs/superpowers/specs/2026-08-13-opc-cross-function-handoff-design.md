# OPC Cross-Function Handoff Design

## Goal

Connect Marketing, Sales, Finance and Learning through a tenant-scoped, durable handoff record so Week 13 can review the evidence without direct cross-domain writes.

## Scope

The initial implementation covers two business facts already represented in the runtime:

1. A sales opportunity is won and requires a Finance handoff.
2. A completed handoff can produce a Learning lesson for the same workspace.

It does not create accounting transactions automatically. Finance remains the system of record for accounting documents and transactions; a handoff is an auditable request for a Finance user or workflow to process.

## Architecture

Extend the existing `handoffs` table and `Company Runtime HandoffService`. A record contains its source domain/entity, target function, workspace, normalized payload, lifecycle status and an idempotency key. A unique `(workspace_id, idempotency_key)` constraint makes retried opportunity-win calls safe.

Sales creates the Finance handoff through a small service injected into the existing opportunity transition service. The service never imports Finance models. Finance resolves a handoff through its own API, which records the resolver and resolution notes. The Learning endpoint can create a lesson from a resolved handoff after verifying workspace ownership.

The existing platform event broker is used only for best-effort UI notification after commit. The new table is the durable source of truth.

## Data Contract

`CrossFunctionHandoff` fields:

- `workspace_id`: owner and tenant boundary.
- `source_function`: `sales` for this increment.
- `source_entity_type`: `opportunity` for this increment.
- `source_entity_id`: Snowflake ID of the source entity.
- `target_function`: `finance` for this increment.
- `title`, `payload`: business context, including customer and expected amount.
- `status`: `pending`, `accepted`, `resolved`, `rejected`.
- `idempotency_key`: `sales-opportunity-won:<opportunity-id>`.
- `resolved_by`, `resolved_at`, `resolution_notes`: Finance decision audit.

## API

- `GET /api/v1/handoffs?workspace_id=&target_function=&status=` lists tenant-scoped handoffs.
- `POST /api/v1/handoffs/{handoff_id}/accept` accepts a pending handoff.
- `POST /api/v1/handoffs/{handoff_id}/resolve` resolves an accepted handoff.
- `POST /api/v1/learning/from-handoff/{handoff_id}` creates a lesson only from a resolved handoff in the caller's workspace.

All endpoints authenticate a user and validate workspace membership. Finance actions additionally use the existing Finance access dependency.

## Error Handling

- Cross-workspace and absent IDs return the same 404 response.
- Invalid lifecycle changes return 409.
- A missing source opportunity prevents handoff creation and rolls back the win transition.
- Duplicate opportunity-win requests return the existing handoff without creating a second record.

## Testing

Unit tests cover idempotent creation, lifecycle transitions and tenant rejection. Router tests cover Finance authorization and lesson creation from resolved handoffs. The full backend suite and Flutter suite remain the regression gate.
