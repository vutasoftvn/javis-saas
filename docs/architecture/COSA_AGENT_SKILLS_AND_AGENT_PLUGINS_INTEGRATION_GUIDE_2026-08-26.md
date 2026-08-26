# Hướng dẫn tích hợp Agent Skills và Agent Plugins cho COSA

**Ngày:** 2026-08-26
**Trạng thái:** Thiết kế tích hợp cho test pilot; chưa cho phép marketplace hoặc plugin bên thứ ba.
**Phạm vi:** `packages/agent_core`, `apps/cosa`, `services/cosa`, Flutter và vận hành.

## 1. Quyết định kiến trúc

| Lớp | Chuẩn/owner | Mục đích |
|---|---|---|
| Nội dung workflow | [Agent Skills](https://agentskills.io/specification) | `SKILL.md`, instructions, references, assets và optional scripts. |
| Phân phối | [Agent Plugins v1.0.0](https://agent-plugins.org/specification) | Một directory portable chứa Skills và optional MCP configuration. |
| Governance | COSA | Catalog, source review, tenant install, credential, approval, quota, audit, run snapshot. |

Agent Plugins v1 chỉ giải quyết discovery/packaging. Distribution, installation, permissions, credential và UX là trách nhiệm của client; do đó COSA phải giữ mọi quyết định quyền trong control plane. [Agent Plugins overview](https://agent-plugins.org/)

Các quyết định v1:

1. Chỉ nhận package **first-party, source-controlled**.
2. Chỉ cho `streamable-http` MCP qua origin allowlist; chặn `stdio`, SSE và package script execution trong pilot.
3. Import mỗi skill hợp lệ thành `SkillSpec` immutable và publish vào registry hiện có; AgentSpec chỉ dùng pin `(skill_id, version, definition_hash)`.
4. `SKILL.md`, `mcp.json`, `extensions` và `allowed-tools` không bao giờ tự cấp quyền thực thi.
5. Credentials tiếp tục nằm ở `connector_authorizations.secret_ref` và secret manager; không chứa token trong package, log hoặc API response.

## 2. Baseline code base cần giữ nguyên

### 2.1 Skill runtime

`packages/agent_core/skills/contracts.py` đã có progressive disclosure:

- L0: `SkillIndexEntry` (`id`, `version`, `name`, `description`, `definition_hash`).
- L1: `SkillSpec` có instructions, required capabilities/references và lifecycle status.
- `packages/agent_core/skills/resolver.py::SkillResolver` reject missing/drifted `PinnedSkillRef` theo exact version/hash.
- `packages/agent_core/kernel/openai_agents_kernel.py` resolve pinned skills trước execution.

**Không tạo skill registry mới.** Package import phải gọi `publish_skill_spec()` trong `packages/agent_core/registry/publisher.py`, và runtime tiếp tục resolve bằng `SkillResolver`.

### 2.2 Plugin manifest hiện có

`packages/agent_core/plugins/manifest.py` có `PluginManifest`, `PluginCapabilityGrant` và `PluginRegistry` in-memory. Đây là internal format với `capabilities`/`permissions`, khác Agent Plugins v1 với `plugin.json`, `skills/` và `mcp.json`.

**Không deserialize trực tiếp `plugin.json` vào `PluginManifest`.** Tạo reader riêng cho standard v1, sau đó một adapter chuyển package đã review thành catalog/component inventory của COSA. Giữ legacy manifest cho consumer hiện tại đến khi migration có coverage đầy đủ.

### 2.3 Connector boundary hiện có

`services/cosa/storage/control-plane-schema.ts` đã map:

- `workspaceConnectorInstallations`;
- `connectorAuthorizations` với `secretRef`, scope, state và expiry;
- `sessionConnectorGrants` scoped theo company/workspace/conversation.

MCP server là connector descriptor, không phải credential source. Package installation, account authorization và session grant đều phải usable trước khi tool được gọi.

## 3. Target architecture

```text
First-party source directory
  → offline validation + deterministic SHA-256
  → human review + control-plane catalog
  → Agent Skills import → published immutable SkillSpec
  → workspace plugin installation
  → session plugin grant + connector authorization
  → Run metadata snapshots IDs/hashes
  → CapabilityGateway + tenant policy + approval
  → MCP invocation / artifact lineage / redacted audit
```

| Concern | Owner | Source of truth |
|---|---|---|
| Portable manifest and skill syntax | Vendored Agent Plugins/Agent Skills schemas | Repository source, pinned schema version. |
| Package hash, review, inventory, workspace install | `services/cosa` | `control_plane`. |
| Skill instructions and identity | `packages/agent_core` | `agent_registry.published_specs`, kind `skill`. |
| Credential/grant | `services/cosa` + secret manager | Connector tables and vault. |
| Tool policy/approval/idempotency | `agent_core`/`apps/cosa` | Existing governance and run ledgers. |

## 4. Portable package contract

### 4.1 Directory layout

```text
cosa-operations-plugin/
├── plugin.json
├── skills/
│   └── operations-report/
│       ├── SKILL.md
│       ├── references/report-format.md
│       └── assets/output-template.md
├── mcp.json
└── com.cosa/component-bindings.json
```

`plugin.json` is required. Each immediate child of `skills/` that contains `SKILL.md` is a discoverable skill; nested arbitrary folders are not discovered. A package must have at least one reviewed Skill or MCP component, even though the portable standard allows optional component directories. [Agent Plugins discovery rules](https://agent-plugins.org/specification)

### 4.2 `plugin.json`

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "cosa-operations",
  "version": "1.0.0",
  "description": "Read-only operational reporting workflows for COSA.",
  "author": {"name": "COSA Platform"},
  "license": "Proprietary",
  "extensions": {
    "com.cosa": {"catalog_key": "cosa.operations", "source_tier": "first_party"}
  }
}
```

Rules:

- Validate against vendored 1.0.0 schema. Do not retrieve schemas during runtime load; the standard requires locally recognized schema selection.
- Require SemVer and a deterministic package SHA-256 in COSA, even though portable `version` is optional.
- Treat `extensions.com.cosa` as a request, never an authorization. Catalog policy may reject or override it.
- Reject symlinks, absolute paths, traversal, or filesystem targets outside package root.

### 4.3 `SKILL.md`

```markdown
---
name: operations-report
description: Produces a read-only operational summary from approved COSA task data. Use for workspace task status, blockers, owners, and weekly operations reporting.
license: Proprietary
compatibility: Requires COSA operations-read capability and approved connector access.
metadata:
  cosa-skill-id: cosa.operations-report
  cosa-skill-version: "1.0.0"
---

# Operations report workflow

1. Confirm active workspace and reporting interval.
2. Request only approved `operations.task.list` data through the capability gateway.
3. Return a sourced summary without changing task data.
4. Report empty-data and uncertainty conditions explicitly.
```

Agent Skills requires `name`/`description` YAML frontmatter and supports references/assets/scripts. It recommends metadata-only discovery, full instructions at activation, then resources on demand. [Agent Skills specification](https://agentskills.io/specification)

COSA rules beyond the standard:

- `name` equals directory name, lowercase/hyphenated; `description` names business purpose, trigger and read/write boundary.
- Main file ≤500 lines and ≤5,000 tokens; deep detail remains one level deep in `references/`.
- Body defines inputs, output shape, data boundary, failure response and prohibited actions.
- No customer data, secrets, private key, signed URL, SQL credential or instruction that changes policy/tool authority.
- Omit `allowed-tools` in v1. It is experimental in Agent Skills and has no authority in COSA.
- Quarantine all package scripts. No cloud execution in pilot.

### 4.4 `mcp.json`

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "operations-api": {
      "type": "streamable-http",
      "url": "https://mcp.cosa.example/operations"
    }
  }
}
```

Rules:

- Schema version matches `plugin.json` exactly.
- Permit only HTTPS `streamable-http` whose hostname is in `COSA_PLUGIN_ALLOWED_MCP_ORIGINS`.
- Reject `stdio`, `sse`, unknown transport, configured header and redirect to a different origin.
- Never store `Authorization`, `Cookie`, API key or secret in `headers`/`env`; the standard calls them visible package data, not a secret mechanism.
- Runtime adds short-lived authorization only after both plugin and connector grants are usable.

## 5. COSA catalog model

Store immutable raw package in approved object storage; database stores sanitized inventory, never an unreviewed executable blob fetched by URL.

### 5.1 `plugin_packages`

| Field | Rule |
|---|---|
| `package_id` | `pkg_<12 hex>`, primary key. |
| `catalog_key` | Stable key, e.g. `cosa.operations`. |
| `plugin_name`, `plugin_version` | Exact verified manifest fields. |
| `package_sha256`, `manifest_schema_version` | Required and immutable. |
| `source_kind`, `source_ref`, `publisher`, `license` | First-party source metadata. |
| `review_status` | `draft`, `approved`, `rejected`, `retired`. |
| `reviewed_by`, `reviewed_at`, `retired_at` | Audit information. |
| `component_inventory` | Sanitized Skills/MCP names, transport and origin only. |

Unique key: `(catalog_key, plugin_version, package_sha256)`.

### 5.2 `workspace_plugin_installations`

`installation_id`, `company_id`, `workspace_id`, `package_id`, `state`, installer/audit fields, `enabled_skill_ids` and `enabled_mcp_server_names`. State is `enabled`, `disabled` or `revoked`; enforce unique `(company_id, workspace_id, package_id)`.

### 5.3 `session_plugin_grants`

`grant_id`, exact company/workspace/conversation/installation IDs, component/action subsets, `state`, `expires_at`, grant/revoke audit fields. State is `enabled`, `revoked` or `expired`.

This record permits a package component in a session. It does **not** replace `session_connector_grants`: an MCP action needs both the usable plugin grant and usable connector grant.

### 5.4 Run snapshot

At enqueue, persist IDs/digests—not secrets—in `RunRequest.metadata`:

```json
{
  "plugin_snapshot": [{
    "package_id": "pkg_a1b2c3d4e5f6",
    "catalog_key": "cosa.operations",
    "version": "1.0.0",
    "package_sha256": "<sha256>",
    "skill_refs": ["cosa.operations-report@1.0.0#<definition_hash>"],
    "session_plugin_grant_id": "spg_123"
  }]
}
```

Worker resolves the same pinned `SkillSpec`, then re-checks current plugin/connector grants before any side effect. It never silently upgrades to a new package version.

## 6. Lifecycle

### Intake and approval

1. CI receives package only from approved first-party repo/ref.
2. It rejects path/symlink escapes and builds deterministic file digest.
3. It validates portable manifests against vendored schemas.
4. It executes `skills-ref validate` plus COSA lint on every skill.
5. It reports scripts, MCP transport/origin, disallowed headers, secret patterns, prompt-injection markers and package size.
6. Platform reviewer approves exact hash; only then catalog state becomes `approved`.

Schema-valid is not security-approved. A conforming package can still give unsafe instructions or point to a harmful remote service.

### Installation, activation, revoke

1. Workspace admin selects approved catalog key/version and server-side component allowlist.
2. Control plane creates scoped installation; MCP components start disabled.
3. Session user creates a session plugin grant after conversation ownership check.
4. If component needs account data, user/admin completes existing connector authorization and session connector grant.
5. Run snapshots immutable identities, resolves skill, and invokes tool only after policy checks.
6. Revoking installation blocks future grants; revoking plugin/connector grant blocks later actions, returns typed block status, and preserves audit history.

## 7. Runtime flow

```text
L0: list only approved + installed + session-granted SkillIndexEntry records
 → task match against description/applicability
 → L1: exact pinned SkillSpec via SkillResolver
 → L2: one reviewed reference at a time
 → CapabilityGateway intersection:
   policy ∩ workspace plugin install ∩ session plugin grant
   ∩ connector authorization ∩ session connector grant ∩ approval
 → invoke and emit redacted audit/artifact lineage
```

Do not show all catalog instructions to all model runs. Progressive disclosure limits context cost and instruction cross-contamination. [Agent Skills progressive disclosure](https://agentskills.io/specification)

## 8. API contracts

All routes derive company/workspace/principal from authenticated context. Client does not set tenant IDs, source paths or secret refs.

| Route | Caller | Purpose |
|---|---|---|
| `POST /agent/admin/plugin-packages` | Platform admin/internal CI | Import pre-uploaded immutable object by `object_ref` and expected SHA-256. |
| `GET /agent/admin/plugin-packages` | Platform admin | Catalog/review metadata only. |
| `POST /agent/workspaces/{workspace_id}/plugins/{catalog_key}/install` | Workspace admin | Install reviewed version with component subset. |
| `PATCH /agent/workspaces/{workspace_id}/plugin-installations/{id}` | Workspace admin | Enable/disable reviewed subset. |
| `POST /agent/sessions/{conversation_id}/plugin-grants` | Authorized session user | Create scoped plugin grant; does not create credential. |
| `DELETE /agent/sessions/{conversation_id}/plugin-grants/{id}` | Grant owner/admin | Revoke grant. |

Worker-only gate:

```python
async def assert_usable_plugin_component(
    *, company_id: str, workspace_id: str, conversation_id: str,
    package_id: str, component_kind: Literal["skill", "mcp"],
    component_name: str, requested_action: str,
) -> ApprovedPluginComponent: ...
```

Return only pinned component identifiers and approved connector descriptor. Connector credential resolution remains a separate trusted control-plane action.

## 9. Security controls

| Threat | Required control |
|---|---|
| Supply-chain replacement | Source allowlist, deterministic SHA-256, immutable record, reviewer identity, exact run snapshot. |
| Invalid/mixed schemas | Offline vendored schemas; reject invalid manifest; isolate only bad MCP entry when the standard permits. |
| Local code execution | No stdio MCP or scripts in pilot; future process execution only isolated container/read-only root. |
| Credential leak | Vault `secret_ref`, no package secrets, redacted audit/API/event data. |
| Tenant escape | Company + workspace predicate on every install/grant query; conversation ownership before grant. |
| Prompt injection | References are untrusted data; never alter policy/grants/system instructions. |
| Privilege escalation | Ignore `allowed-tools` for authority; enforce exact action intersection. |
| Network exfiltration | Origin allowlist, redirect block, egress proxy, timeout/size limits, audit. |
| Context/cost growth | L0-only startup, 3 active skills/run, L2 on demand, existing run cost policy. |

## 10. CI and pilot verification

Package validation must cover valid import; missing required frontmatter; folder/name mismatch; invalid version/schema; MCP schema mismatch; secret/header/env patterns; traversal; changed byte gives new digest; script/stdio rejection.

Authorization/runtime tests must cover cross-workspace `404`; plugin grant without connector grant cannot invoke MCP; revoke/expiry blocks before tool/model side effect; pinned `1.0.0` never resolves to `1.0.1`; audit/artifact show package/SkillRef but no secret.

Run full Python, TypeScript and Flutter suites plus a whitespace check against the real integration database. A skipped control-plane/PostgreSQL integration test blocks pilot promotion.

## 11. Pilot configuration

| Key | Value |
|---|---|
| `COSA_PLUGIN_SOURCES` | `first_party` |
| `COSA_PLUGIN_ALLOWED_SCHEMA_VERSIONS` | `1.0.0` |
| `COSA_PLUGIN_ALLOWED_MCP_TRANSPORTS` | `streamable-http` |
| `COSA_PLUGIN_ALLOWED_MCP_ORIGINS` | `mcp.cosa.example` |
| `COSA_PLUGIN_MAX_PACKAGE_BYTES` | `5242880` |
| `COSA_PLUGIN_MAX_SKILLS_PER_RUN` | `3` |
| `COSA_PLUGIN_ALLOW_SCRIPTS` | `false` |
| `COSA_PLUGIN_REQUIRE_REVIEW` | `true` |

Missing configuration fails closed. Flutter receives only sanitized capability and state from Agent API.

## 12. Delivery sequence and definition of done

| Wave | Deliverable | Gate |
|---|---|---|
| A | Offline reader/validator, digest and CI fixture packages. | Schema/path/Skill validation pass; no runtime load. |
| B | Catalog, source review, workspace installation. | Immutable hash/version and tenant tests pass. |
| C | Import to existing SkillSpec registry and exact pins. | Resolver drift/missing tests pass. |
| D | Session plugin grant UI/API. | Capability manifest fails closed. |
| E | One read-only remote MCP component through existing connector grants. | Revoke/egress/audit tests pass. |
| F | Allowlisted workspace pilot for seven days. | No secret leak, tenant breach or unauthorized tool invocation. |

Pilot is complete only when a first-party read-only Skill + remote MCP package installs in one allowlisted workspace, resolves by pinned hash, rechecks grants before action, records lineage, and blocks correctly after revoke.

## 13. File-level implementation map

| File/area | Responsibility |
|---|---|
| `packages/agent_core/plugins/agent_plugins_v1.py` | Safe portable manifest/MCP reader and non-authoritative component inventory. |
| `packages/agent_core/plugins/package_digest.py` | Deterministic SHA-256 plus symlink/path validation. |
| `packages/agent_core/skills/agent_skills_importer.py` | `SKILL.md` to `SkillSpec`, then existing `publish_skill_spec`. |
| `packages/agent_core/plugins/manifest.py` | Preserve existing internal format until adapter migration passes. |
| `services/cosa/migrations/<next>_agent_plugin_catalog.up.sql` | Package catalog, workspace installation and session grants after checking actual next number. |
| `services/cosa/storage/control-plane-schema.ts` | Drizzle tables and indexes. |
| `services/cosa/services/workspace-plugin.service.ts` | Review/install/grant state machine. |
| `apps/cosa/capabilities/plugin_component_gate.py` | Worker-side plugin component assertion before tool invoke. |
| `apps/cosa/api/routes.py`, `apps/cosa/api/schemas.py` | Sanitized user/admin API. |
| `frontend/lib/core/manifest/` | Fail-closed plugin catalog/session grant gates. |

## 14. Related documents

- [QwenWork-inspired product adjustment](/Volumes/SSD/javis-saas/docs/architecture/QWENWORK_INSPIRED_PRODUCT_ADJUSTMENT_2026-08-26.md)
- [QwenWork-inspired workspace execution plan](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-08-26-qwenwork-inspired-workspace-execution.md)
- [Test readiness re-audit](/Volumes/SSD/javis-saas/docs/architecture/TEST_READINESS_REAUDIT_2026-08-26.md)
- [Agent Plugins specification](https://agent-plugins.org/specification)
- [Agent Skills specification](https://agentskills.io/specification)
