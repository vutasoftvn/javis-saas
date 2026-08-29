# Agent, COSA, Workspace Naming and Development Reset Design

## Goal

Replace the ambiguous development-era database names with three canonical data
planes: `agent`, `cosa`, and `workspace`; reset the development databases; and
integrate the usable Customer Engagement P0 service layer from `ce-p0` without
regressing the P1–P3 implementation already on `main`.

## Scope and Decisions

### Canonical names

| Concern | Canonical name | Retired development name |
| --- | --- | --- |
| Agent platform database, Python package, primary schema and environment variable | `agent`, `AGENT_DATABASE_URL`, `agent` | `javis`, `AGENT_DATABASE_URL`, `agent` |
| COSA control-plane database and environment variable | `cosa`, `COSA_DATABASE_URL` | `cosa_control_plane`, `COSA_DATABASE_URL` |
| Workspace business database and environment variable | `workspace`, `WORKSPACE_DATABASE_URL` | `company`, `WORKSPACE_DATABASE_URL` |
| Tenant identifier | `workspace_id` | `company_id` as a product tenant key |

`services/company` remains the name of the business-service source directory
and service boundary. It is not renamed: “Company” remains a business domain,
whereas `workspace` is the tenancy and database name.

Historical documents under `docs/archive/` retain their original vocabulary as
evidence. Active code, configuration, tests, operations documentation and
generated contracts use the canonical names.

### Database topology

One PostgreSQL cluster hosts three databases and least-privileged roles:

```text
agent      <- agent_app      (agent runtime, governance, memory, knowledge)
cosa       <- cosa_app       (control plane, licensing, connector policy)
workspace  <- workspace_app  (business data for workspace-scoped Company service)
```

Dedicated migration roles own the databases and schemas. Runtime roles receive
only the schema and DML privileges required by their service. Public database
connections are revoked. Development PostgreSQL ports are bound to loopback.

The system communicates across these database boundaries through service APIs
and authenticated events, never cross-database writes. `workspace_id` is the
tenant key on every product-side query and relationship.

### Development reset and cutover

The user has confirmed this is a development environment with no data to keep.
The implementation therefore creates fresh databases rather than copying the
mixed historical `javis`, `company`, and `cosa_control_plane` databases.

1. Replace bootstrap roles/databases with the canonical three-database layout.
2. Update migration runners, application configuration, Compose contracts and
   active documentation to use canonical URLs.
3. Rebuild the explicitly identified development PostgreSQL volumes only after
   the source migration suite succeeds on an empty cluster.
4. Verify exact schemas, service readiness and tenant isolation on the fresh
   environment.

The old containers and volumes are not removed until the new stack has passed
verification. They are not a source of data for this development reset.

### Agent package and schema rename

The reusable Python package moves from `packages/agent` to
`packages/agent`; its imports, migration module, tests, Make targets, Docker
build contexts and active documentation move with it. The primary PostgreSQL
schema moves from `agent` to `agent`; the companion `agent_*` schemas keep
their descriptive names. All new configuration uses `AGENT_DATABASE_URL`.

There is no runtime fallback to the retired variables or databases. This is an
intentional clean development reset, not a zero-downtime production migration.

### COSA and Workspace configuration rename

The COSA runner uses only `COSA_DATABASE_URL` and targets database `cosa`.
The Company runner and Company service use `WORKSPACE_DATABASE_URL` and target
database `workspace`. Database names, role names, Compose defaults, health
tests and deployment examples must agree exactly.

### Customer Engagement P0 integration

`ce-p0` is not merged. Its P0 migration is already identical to `main`, while
`main` contains newer P1–P3 migrations and services. The implementation ports
only the missing P0 business services and their tests into `main`:

- thread lifecycle and SLA snapshot;
- internal, public and inbound messages with idempotency;
- assignment, atomic takeover and queued-delivery cancellation;
- escalation route binding;
- decision authority, approval and execution guards;
- customer-360 and non-merging identity resolution where no P1–P3 equivalent
  exists.

The port adapts to the current P1–P3 schema and complements existing copilot,
channel, automation and autopilot services. It adds explicit Company handlers
for the P0 human-desk flows so that the service layer is not orphaned.

## Error Handling and Safety

- Missing canonical database URLs fail at startup without default credentials.
- Migration runners serialize execution with PostgreSQL advisory locks and
  reject checksum drift.
- Workspace mismatch returns an authorization/not-found style error without
  revealing another workspace’s data.
- The reset script validates exact container and volume targets before any
  destructive action; it never recursively removes paths.
- P0 handlers use existing `APIError` and workspace-auth patterns.

## Verification

- New database-url resolution tests prove that only canonical variables are
  accepted.
- Fresh-cluster migration test verifies the three databases, roles and schema
  ownership.
- Agent, COSA and Company typechecks; Python lint/mypy; existing route and
  contract gates remain applicable.
- Customer Engagement P0 tests are first ported as failing tests and then run
  together with P1–P3 tests.
- Smoke tests exercise Agent, COSA and Company health endpoints against the
  canonical configuration.

## Non-goals

- No production-data migration or deletion.
- No rename of the Company business service directory or its user-facing
  business semantics.
- No blind merge of `ce-p0`.
