# AgentOS External Connector Pattern (§16.1-16.3)

Standard 2-tier integration architecture separating transport concerns from business governance.

---

## 1. Architectural Layers

```
External Service (e.g., Slack, Notion, GitHub)
     ↓ (OAuth linking flow via services/identity)
Secret Store (Vault / KMS)
     ↓ (Secure credential retrieval by workspace_id)
Connector Transport Client (agentos/connectors/<name>/client.py)
     - Manages HTTP transport, authentication headers, rate-limiting & exponential backoff retries
     - Zero business logic, zero raw token leaking to logs/memory
     ↓
COSA Tool Adapter (agentos/tools/clusters/<name>_tools.py)
     - Wraps operation as ToolSpecV2 with explicit RiskLevel (e.g. HIGH for external write)
     - Maps tool parameters to connector client calls
     ↓
Governance Kernel (evaluate_access() — Phase 10a)
     - 6-dimension evaluation (RBAC ∩ TenantPolicy ∩ PermissionLevel ∩ ToolRisk ∩ ExecutionMode ∩ DataScope)
     - Enforces approval pause/resume for high-risk external writes
     ↓ (HTTP / RPC)
Business Service Cluster (services/control-plane, services/commercial)
```

---

## 2. Guarantees & Constraints

1. **OAuth Ownership**: Token linking and lifecycle flows belong to `services/identity`. AgentOS connectors only retrieve linked tokens from the secret store.
2. **Secret Safety**: Credentials remain in Vault; they are never persisted into memory providers, vector databases, or trace spans.
3. **Audit Trail**: Every connector call logs sanitized metadata (endpoint, status code, latency) to `AuditSink` with all tokens and payload secrets redacted.
4. **Transport Isolation**: Retries, circuit breakers, and rate limiters live exclusively in `client.py`, never mixed into business tool adapters.

---

## 3. How to Add a New Connector (e.g., Notion)

1. **Create Transport Client** in `agentos/connectors/notion/client.py`:
   ```python
   class NotionConnectorClient:
       def __init__(self, secret_store: SecretStore, max_retries: int = 3): ...
       async def create_page(self, workspace_id: str, parent_id: str, title: str) -> dict: ...
   ```
2. **Create Tool Adapter** in `agentos/tools/clusters/notion_tools.py`:
   ```python
   def build_notion_tools(client: NotionConnectorClient) -> list[ToolSpecV2]:
       return [
           ToolSpecV2(
               name="notion.page.create",
               description="Create a page in Notion",
               handler=...,
               risk_level=ToolRiskLevel.HIGH,
               permission_class=PermissionClass.EXTERNAL_WRITE,
               tool_permission=ToolPermission.SCOPED_WRITE,
           )
       ]
   ```
3. **Register in Tool Registry**: Wire into `ToolRegistry.register()`.
