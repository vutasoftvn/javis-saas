# Tenant Isolation Matrix Design

## Goal

Establish database-backed regression coverage proving that workspace and brain boundaries reject cross-tenant access without a side effect.

## Scope

Test the existing router/service guards for Chat, Tasks, Realtime, Vault, and Strategy with two persisted workspaces. The tests run only with `RUN_DB_INTEGRATION=1` against the dedicated test database.

## Constraints

- Preserve current public API responses: foreign resources are not found (`404`) after a valid workspace membership check.
- Do not create a second tenancy implementation.
- Use Snowflake-backed models and serialize identifiers as strings at API boundaries.
- Roll back all integration data at test end.

## Test matrix

| Domain | Foreign operation | Expected result | Side effect |
|---|---|---|---|
| Chat | list/create against foreign brain | 404 | no session/message |
| Tasks | read/update foreign task | 404 | unchanged task |
| Realtime | end foreign session | 404 | no usage record/status change |
| Vault | resolve foreign brain repository | 404 | no object/database write |
| Strategy | scoped project lookup | 404 | unchanged project |
