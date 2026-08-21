# ADR-V13-2-003: Sales CRM Entity Model & Deduplication

## Context
Cross-function lead intake from Marketing can produce duplicate leads, accounts, and contacts.

## Decision
Enforce unique partial indexes:
- `(workspace_id, domain)` on `accounts` WHERE domain IS NOT NULL
- `(workspace_id, email)` on `contacts` WHERE email IS NOT NULL
- Lead intake dedupes against active open leads by `(workspace_id, contact_id)`.
