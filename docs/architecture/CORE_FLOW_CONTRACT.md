# Supported core flow contract

| User step | API boundary | Required scope | Success | Navigation/error |
|---|---|---|---|---|
| Create workspace and brain | `/api/v1/auth/*`, `/api/v1/brains/*` | authenticated user, workspace | Snowflake IDs as strings | dashboard; membership error is 403 |
| Add company context | `/api/v1/vault/{brain_id}/*` | workspace + brain | revision/document IDs | Vault; inaccessible brain is 404 |
| Create or update strategy canvas | `/api/v1/strategy/*` | workspace + brain | canvas/revision IDs | Strategy; validation shown inline |
| Compile twelve-week plan | `/api/v1/execution/*` | workspace + brain | cycle/plan/task IDs | Execution; unavailable prerequisites are 400/404 |
| Create or assign task | `/api/v1/tasks/*` | workspace + brain where relevant | task ID | Tasks; cross-workspace references are rejected |
| Ask for context-aware help | `/api/v1/chat/*` | workspace + brain + chat session | message/session IDs | Chat; unconfigured provider is a visible error |

Modules outside this path are experimental until they have a complete tenant-scoped API,
coverage, and useful empty states.
