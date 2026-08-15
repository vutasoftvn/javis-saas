# COSA OpenSandbox Integration
## Thiết kế COSA Agent Runtime với lớp thực thi an toàn cho AI Agent

**Trạng thái:** Đề xuất triển khai  
**Phạm vi:** COSA v13.1 / v13.2 và các bản tiếp theo  
**Mục tiêu:** Tích hợp OpenSandbox như lớp Execution Runtime cho COSA, không thay thế FastAPI, PostgreSQL, n8n, MCP, LiveKit hay các LLM hiện có.

---

# 1. Executive Summary

COSA hiện đang phát triển theo hướng **Founder OS / One Person Company OS**, trong đó AI không chỉ trả lời câu hỏi mà cần có khả năng:

- phân tích dữ liệu;
- đọc/ghi file;
- chạy Python;
- chạy CLI;
- tự động hóa browser;
- thực thi workflow;
- gọi các công cụ bên ngoài;
- tạo báo cáo;
- xử lý dữ liệu Sales/Marketing/Finance;
- thực thi các tác vụ của Coding Agent;
- vận hành trên PC/Mac/VPS riêng của khách hàng.

Vấn đề quan trọng xuất hiện khi AI bắt đầu **thực thi code hoặc command**:

> Không nên cho code do AI sinh ra chạy trực tiếp trên host COSA.

OpenSandbox giải quyết đúng lớp vấn đề này.

Đề xuất:

```text
LLM        = Think
Memory     = Remember
n8n        = Orchestrate
OpenSandbox= Execute
LiveKit    = Communicate
COSA Core  = Govern
```

OpenSandbox nên được tích hợp thành một thành phần của:

# COSA Agent Runtime

và KHÔNG trở thành core business logic của COSA.

---

# 2. OpenSandbox là gì?

Repository:

https://github.com/opensandbox-group/OpenSandbox

OpenSandbox là một sandbox runtime dành cho AI applications/agents.

Các capability quan trọng:

- Sandbox lifecycle management
- Command execution
- File operations
- Python / code execution
- Docker runtime
- Kubernetes runtime
- Multi-language SDK
- CLI
- MCP integration
- Network egress policy
- Credential Vault
- Observability
- Browser / agent sandbox scenarios
- Coding agent scenarios

Kiến trúc này phù hợp để cô lập workload do AI tạo ra khỏi COSA host.

---

# 3. Vai trò OpenSandbox trong COSA

OpenSandbox KHÔNG thay thế:

- FastAPI
- PostgreSQL
- n8n
- DeepSeek
- ChatGPT
- Gemini
- Claude Code
- MCP
- LiveKit

OpenSandbox chỉ chịu trách nhiệm:

> Safe Execution Runtime

Kiến trúc đề xuất:

```text
                      COSA
                       │
              ┌────────▼────────┐
              │   COSA Core     │
              │    FastAPI      │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │ Agent Runtime   │
              └────────┬────────┘
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
     ▼                 ▼                 ▼
    LLM              Memory           Workflow
 DeepSeek          PostgreSQL            n8n
 ChatGPT           Vector DB
 Gemini
     │
     └────────────────┐
                      ▼
                Tool Gateway
                      │
        ┌─────────────┼──────────────┐
        │             │              │
        ▼             ▼              ▼
       MCP         Internal API   OpenSandbox
                                      │
                     ┌────────────────┼─────────────┐
                     ▼                ▼             ▼
                   Python           Browser        CLI
```

---

# 4. COSA Agent Runtime

Đề xuất tạo module mới:

```text
cosa/
└── agent_runtime/
    ├── orchestrator/
    ├── execution/
    ├── permissions/
    ├── tools/
    ├── sandbox/
    ├── workflow/
    ├── memory/
    ├── audit/
    └── policies/
```

Logical architecture:

```text
COSA Agent Runtime

├── Agent Orchestrator
├── Model Router
├── Tool Registry
├── MCP Gateway
├── Permission Engine
├── Workflow Engine
│   └── n8n
├── Execution Engine
│   ├── LocalExecutor
│   └── OpenSandboxExecutor
├── Memory Engine
├── Credential Broker
├── Audit Engine
└── Observability
```

---

# 5. Execution Provider Abstraction

Không hard-code OpenSandbox trực tiếp vào Agent.

Tạo interface:

```python
class ExecutionProvider:

    async def create_workspace(self, policy):
        ...

    async def execute(self, command):
        ...

    async def upload_file(self, file):
        ...

    async def download_file(self, path):
        ...

    async def terminate(self):
        ...
```

Implementations:

```text
ExecutionProvider

├── LocalExecutor
│
└── OpenSandboxExecutor
```

Mục tiêu:

- task đơn giản có thể dùng LocalExecutor;
- task có code/browser/CLI chưa tin cậy dùng OpenSandboxExecutor;
- có thể thay runtime khác trong tương lai;
- tránh vendor lock-in.

---

# 6. Sandbox Lifecycle

Mỗi task quan trọng nên tạo một sandbox riêng.

Recommended flow:

```text
User
 ↓
COSA Agent
 ↓
Task Planner
 ↓
Permission Engine
 ↓
Sandbox Policy
 ↓
Create Sandbox
 ↓
Mount/Input
 ↓
Execute
 ↓
Collect Output
 ↓
Validate
 ↓
Save Result
 ↓
Audit
 ↓
Destroy Sandbox
```

Ví dụ:

```text
Job: COSA-AGENT-2026-00128

/input
/workspace
/output
/tmp
```

Lifecycle:

```text
CREATED
   ↓
PREPARING
   ↓
RUNNING
   ↓
COLLECTING
   ↓
COMPLETED
   ↓
DESTROYED
```

Failure:

```text
RUNNING
   ↓
FAILED
   ↓
AUDITED
   ↓
DESTROYED
```

---

# 7. Sandbox theo JOB, không theo Agent

Không nên:

```text
Marketing Agent
    ↓
Permanent container
```

Nên:

```text
Marketing Agent
    ↓
Job
    ↓
Ephemeral Sandbox
```

Ví dụ:

```text
"Phân tích 20 đối thủ"

Research Agent
     ↓
Job #1238
     ↓
Sandbox
 ├── browser
 ├── python
 └── files
     ↓
report.md
     ↓
COSA Knowledge
     ↓
Destroy
```

Lợi ích:

- giảm attack surface;
- dễ audit;
- tránh trạng thái rác;
- giảm nguy cơ credential leak;
- dễ giới hạn tài nguyên;
- dễ multi-tenant.

---

# 8. Permission Engine

OpenSandbox không thay thế authorization của COSA.

COSA phải có lớp:

```text
Permission Engine
```

Ví dụ permission:

```yaml
agent: marketing_agent

permissions:

  filesystem:
    read:
      - /input
      - /workspace

    write:
      - /workspace
      - /output

  network:
    allow:
      - google.com
      - facebook.com
      - linkedin.com

  commands:
    allow:
      - python
      - node

  credentials:
    allow:
      - marketing_api

  max_execution_seconds: 600

  max_memory_mb: 2048

  max_cpu: 2
```

---

# 9. Network Policy

Default policy:

```text
DENY ALL
```

Sau đó allowlist.

Ví dụ Finance Agent:

```text
Internet
   ✕

Allowed:
- COSA Internal API
- approved banking API
- approved accounting source
```

Marketing Agent:

```text
Allowed:

- search engines
- selected social networks
- approved marketing APIs
```

Research Agent:

```text
Allowed:

- public internet
- nhưng block:
  - localhost
  - private LAN
  - metadata endpoints
```

---

# 10. Credential Security

Không đưa API key trực tiếp vào prompt.

Không:

```text
SYSTEM PROMPT:

Facebook API key = ...
```

Không:

```text
ENV:
FACEBOOK_TOKEN=...
```

nếu Agent có thể đọc toàn bộ env.

Recommended:

```text
COSA Secrets
     ↓
Credential Broker
     ↓
OpenSandbox Credential Vault
     ↓
Outbound request
```

Agent chỉ biết:

```text
service = facebook
```

Agent không nên nhìn thấy secret thật.

---

# 11. Agent Trust Levels

Đề xuất 4 trust level.

## LEVEL 0 — CHAT

Không execution.

```text
LLM only
```

Ví dụ:

- hỏi đáp;
- brainstorming;
- tư vấn.

---

## LEVEL 1 — READ

Cho phép đọc dữ liệu.

```text
LLM
 ↓
Read Tools
```

Không shell.

---

## LEVEL 2 — SANDBOX EXECUTION

```text
LLM
 ↓
OpenSandbox
```

Cho phép:

- Python
- file processing
- browser
- CLI hạn chế.

---

## LEVEL 3 — CONTROLLED ACTION

Có tác động external system.

Ví dụ:

- gửi email;
- đăng social;
- thay CRM;
- tạo invoice.

Flow:

```text
Agent
 ↓
Sandbox
 ↓
Proposed Action
 ↓
Approval Policy
 ↓
Execute
```

---

# 12. Human Approval

Các operation có hậu quả nên yêu cầu approval.

Ví dụ:

```text
Agent:
"Đã chuẩn bị chiến dịch"

Actions:

✓ 12 posts
✓ target audience
✓ budget

[Approve]
[Edit]
[Reject]
```

Sau approval:

```text
COSA
 ↓
n8n
 ↓
External API
```

Không nhất thiết để sandbox trực tiếp publish.

---

# 13. n8n + OpenSandbox

Hai công nghệ giải quyết hai vấn đề khác nhau.

```text
n8n
=
Workflow Orchestration

OpenSandbox
=
Execution Isolation
```

Recommended:

```text
COSA Agent
     ↓
n8n
     ↓
OpenSandbox
     ↓
Python
     ↓
result
     ↓
n8n
     ↓
CRM / Email / COSA
```

Ví dụ Sales:

```text
New Leads
 ↓
n8n
 ↓
OpenSandbox
 ↓
clean + deduplicate
 ↓
lead scoring
 ↓
n8n
 ↓
CRM
```

---

# 14. MCP Integration

OpenSandbox có MCP integration.

COSA nên chuẩn hóa tool layer:

```text
COSA MCP Gateway
```

Architecture:

```text
Agent
 │
 ├── MCP postgres
 │
 ├── MCP filesystem
 │
 ├── MCP n8n
 │
 ├── MCP browser
 │
 └── MCP sandbox
        ↓
    OpenSandbox
```

Agent không cần biết implementation cụ thể bên dưới.

---

# 15. Marketing Agent

OpenSandbox đặc biệt hữu ích với Marketing.

Flow:

```text
Marketing Goal
 ↓
Marketing Agent
 ↓
Research
 ↓
OpenSandbox
 ├── Browser
 ├── Python
 └── File processing
 ↓
Market Intelligence
 ↓
Campaign Design
 ↓
Approval
 ↓
n8n
 ↓
Distribution
```

Use cases:

- competitor research;
- keyword analysis;
- content analysis;
- CSV processing;
- customer segmentation;
- campaign report;
- website audit;
- content clustering.

---

# 16. Sales Agent

Flow:

```text
Lead Sources
 ↓
n8n
 ↓
Sales Agent
 ↓
OpenSandbox
 ↓
Data Processing
 ├── normalize
 ├── deduplicate
 ├── classify
 └── score
 ↓
CRM
 ↓
Follow-up Workflow
```

Không cho Sales Agent tự động:

- ký hợp đồng;
- chốt thay user;
- gửi nội dung quan trọng không approval.

---

# 17. Finance Agent

Finance Agent nên có policy nghiêm nhất.

Recommended:

```text
Finance Agent
 ↓
READ financial data
 ↓
Sandbox
 ↓
Python Analysis
 ↓
Report
```

Không cho sandbox:

```text
DELETE transactions
CHANGE ledger
TRANSFER money
```

Nếu cần mutation:

```text
Agent
 ↓
proposal
 ↓
COSA validation
 ↓
human approval
 ↓
Finance API
```

---

# 18. Research Agent

Research là một trong các use case tốt nhất.

```text
Question
 ↓
Research Agent
 ↓
Browser Sandbox
 ↓
Sources
 ↓
Python
 ↓
Analysis
 ↓
Structured Report
 ↓
Knowledge
```

Artifacts:

```text
/output

research.json
sources.json
report.md
dataset.csv
```

---

# 19. Coding Agent

OpenSandbox có thể trở thành runtime cho Coding Agent.

```text
COSA
 ↓
Coding Agent
 ↓
OpenSandbox
 ↓
Git clone
 ↓
Claude Code / Codex / Gemini CLI
 ↓
Tests
 ↓
Patch
```

Không cho coding agent chạy trực tiếp trên production host.

---

# 20. Skill Marketplace

OpenSandbox tạo nền tảng tốt để COSA có Skill Marketplace sau này.

Skill manifest:

```yaml
name: competitor_research

runtime:
  type: sandbox

permissions:

  network:
    - google.com

  filesystem:
    read:
      - /input

    write:
      - /output

resources:

  cpu: 1
  memory: 1024

timeout: 300
```

Flow:

```text
Skill
 ↓
Permission Validation
 ↓
Sandbox
 ↓
Execute
 ↓
Result
```

Third-party Skill không được execute trực tiếp trên COSA host.

---

# 21. COSA Desktop

Kiến trúc desktop:

```text
COSA Desktop

Flutter
   │
   ▼
Local COSA API
FastAPI
   │
   ├── PostgreSQL
   │
   ├── n8n
   │
   └── OpenSandbox
           ↓
         Docker
```

Recommended deployment:

```text
Desktop App
+
Docker runtime
```

Không bắt buộc sandbox với mọi user.

Có setting:

```text
Execution Mode

○ Disabled
○ Local Executor
● Secure Sandbox
```

---

# 22. VPS Deployment

Recommended:

```text
Customer VPS

├── COSA API
├── PostgreSQL
├── n8n
├── OpenSandbox
├── Reverse Proxy
└── Observability
```

Các component tách container.

Không:

```text
ONE giant container
```

---

# 23. Kubernetes

Không cần Kubernetes ở giai đoạn đầu.

Roadmap:

```text
Phase 1
Docker

Phase 2
Docker production

Phase 3
Kubernetes
```

Kubernetes chỉ cần khi:

- nhiều sandbox đồng thời;
- multi-user;
- high availability;
- workload scheduling;
- horizontal scale;
- enterprise deployment.

---

# 24. COSA Sandbox API

Đề xuất COSA không để Agent gọi OpenSandbox API trực tiếp.

Tạo adapter:

```text
/api/runtime/
```

Endpoints nội bộ:

```text
POST /runtime/jobs

GET /runtime/jobs/{id}

POST /runtime/jobs/{id}/execute

POST /runtime/jobs/{id}/files

GET /runtime/jobs/{id}/artifacts

DELETE /runtime/jobs/{id}
```

---

# 25. Database Schema

## execution_jobs

```text
id
workspace_id
agent_id
user_id
sandbox_id
provider
status
policy_id
created_at
started_at
completed_at
destroyed_at
error
```

---

## execution_steps

```text
id
job_id
step_type
command
status
started_at
completed_at
exit_code
```

Không lưu secret.

---

## execution_artifacts

```text
id
job_id
path
mime_type
size
hash
storage_location
created_at
```

---

## execution_audit

```text
id
job_id
agent_id
action
resource
policy_decision
timestamp
metadata
```

---

# 26. Policy Schema

```text
sandbox_policies

id
name
agent_type
network_policy
filesystem_policy
command_policy
credential_policy
resource_limit
timeout
approval_policy
```

---

# 27. Observability

Mỗi sandbox phải gắn:

```text
trace_id
job_id
agent_id
workspace_id
user_id
```

Không log:

- API key;
- password;
- access token;
- private customer data không cần thiết.

Metrics:

```text
sandbox_created_total

sandbox_failed_total

sandbox_duration

sandbox_cpu

sandbox_memory

command_execution_total

policy_denied_total
```

---

# 28. Error Handling

Nếu sandbox lỗi:

```text
Execution Error
 ↓
Collect logs
 ↓
Sanitize
 ↓
Agent retry?
```

Retry policy:

```text
MAX_RETRY = 2
```

Không infinite retry.

---

# 29. Resource Limits

Default:

```text
CPU:
1

RAM:
1024 MB

Timeout:
300 sec

Disk:
1 GB
```

Research heavy:

```text
CPU:
2

RAM:
2048 MB

Timeout:
900 sec
```

Configuration theo Agent.

---

# 30. Cleanup

Scheduled cleanup:

```text
every 10 minutes
```

Detect:

```text
sandbox.status != RUNNING
AND
age > TTL
```

Then:

```text
destroy sandbox
```

Artifacts cần thiết phải copy ra khỏi sandbox trước.

---

# 31. Artifact Pipeline

Không dùng sandbox làm persistent storage.

Flow:

```text
Sandbox
 ↓
/output/report.md
 ↓
Artifact Validator
 ↓
COSA Storage
 ↓
Knowledge
```

Sandbox bị destroy.

---

# 32. Memory Integration

Không để Agent tự quyết định mọi thứ cần nhớ.

Flow:

```text
Sandbox result
 ↓
Memory Extractor
 ↓
Memory Policy
 ↓
PostgreSQL / Vector Store
```

Phân biệt:

```text
Task Artifact
Working Memory
Project Memory
Long-term Knowledge
```

---

# 33. LiveKit

LiveKit không liên kết trực tiếp OpenSandbox.

Flow:

```text
User Voice
 ↓
LiveKit
 ↓
COSA Agent
 ↓
Task
 ↓
OpenSandbox
 ↓
Result
 ↓
Agent
 ↓
LiveKit
 ↓
Voice response
```

LiveKit = communication layer.

---

# 34. DeepSeek Harness

Nếu COSA áp dụng kiến trúc harness:

```text
Harness
 ↓
Plan
 ↓
Tool Selection
 ↓
Execution
```

Execution không chạy trực tiếp.

Recommended:

```text
DeepSeek Harness
 ↓
COSA Tool Registry
 ↓
COSA Execution Router
 ↓
OpenSandbox
```

---

# 35. Security Principles

## Principle 1

```text
Default Deny
```

## Principle 2

```text
Least Privilege
```

## Principle 3

```text
Ephemeral Execution
```

## Principle 4

```text
No Secrets in Prompt
```

## Principle 5

```text
No direct host execution
```

với untrusted AI code.

## Principle 6

```text
Every action is auditable
```

---

# 36. Threat Model

COSA phải giả định AI-generated code có thể:

- xóa file;
- đọc secret;
- scan LAN;
- tải malware;
- crypto mine;
- gửi dữ liệu ra ngoài;
- chạy fork bomb;
- consume RAM;
- consume CPU;
- cố thoát sandbox;
- inject command.

Do đó sandbox chỉ là 1 lớp defense.

Full protection:

```text
Authorization
+
Policy
+
Sandbox
+
Network isolation
+
Credential isolation
+
Resource limits
+
Audit
```

---

# 37. Không nên làm

Không:

```text
LLM
 ↓
os.system(...)
```

trên COSA backend.

Không:

```text
Agent
 ↓
SSH production
```

Không expose:

```text
Docker socket
```

vào sandbox.

Không mount:

```text
/
```

host filesystem.

Không đưa:

```text
.env
```

COSA vào sandbox.

---

# 38. Phase 1 — MVP Integration

Mục tiêu:

Python execution an toàn.

Triển khai:

```text
ExecutionProvider
OpenSandboxExecutor
Job lifecycle
Resource limit
Filesystem isolation
Audit
```

Agent đầu tiên:

```text
Research Agent
```

Use case:

```text
CSV
 ↓
Python
 ↓
Analysis
 ↓
report
```

---

# 39. Phase 2 — Browser Agent

Add:

```text
Browser sandbox
Playwright
Network policy
Artifact collection
```

Agents:

```text
Marketing
Research
Sales
```

---

# 40. Phase 3 — n8n Integration

Flow:

```text
n8n
 ↓
COSA Execution API
 ↓
OpenSandbox
```

Add:

- webhook;
- async jobs;
- workflow callback;
- task status.

---

# 41. Phase 4 — Coding Agent

Add:

```text
Git workspace
Claude Code
Codex
Gemini CLI
tests
```

COSA có thể trở thành AI Developer Workspace.

---

# 42. Phase 5 — Skill Runtime

Add:

```text
Skill Manifest
Permission Manifest
Sandbox Runtime
Skill Registry
```

Chuẩn bị cho marketplace.

---

# 43. Phase 6 — Enterprise

Optional:

```text
Kubernetes
secure runtime
advanced network control
multi-tenant scheduler
sandbox pool
quota
billing
```

---

# 44. Feature Flags

Vì COSA đang phát triển theo hướng v13.1/v13.2, không nên phá chức năng hiện hữu.

Feature flags:

```text
ENABLE_AGENT_RUNTIME=true

ENABLE_OPENSANDBOX=false

ENABLE_SANDBOX_BROWSER=false

ENABLE_SANDBOX_CODING=false

ENABLE_SKILL_SANDBOX=false
```

Ban đầu:

```text
ENABLE_AGENT_RUNTIME=true
ENABLE_OPENSANDBOX=true
```

chỉ môi trường development.

---

# 45. Suggested Project Structure

Backend:

```text
backend/

app/

├── agent_runtime/

│   ├── orchestrator.py
│
│   ├── execution/
│   │   ├── base.py
│   │   ├── local_executor.py
│   │   └── opensandbox_executor.py
│
│   ├── sandbox/
│   │   ├── lifecycle.py
│   │   ├── policies.py
│   │   └── artifacts.py
│
│   ├── permissions/
│   │   └── engine.py
│
│   ├── credentials/
│   │   └── broker.py
│
│   ├── audit/
│   │   └── logger.py
│
│   └── tools/
│       └── registry.py
```

---

# 46. Flutter UI

Add section:

```text
AI Operations
```

Pages:

```text
Agent Runs

Sandbox Jobs

Approvals

Artifacts

Audit
```

Agent Run screen:

```text
Research Agent

STATUS:
RUNNING

Current step:

Analyzing competitors

Sandbox:

Secure

CPU:
22%

Memory:
480MB

Elapsed:
2m14s
```

---

# 47. Founder UX

Founder không cần biết thuật ngữ Docker/OpenSandbox.

UI nên dùng:

```text
Execution environment:

● Secure
```

Không:

```text
runtimeClassName: kata-qemu
```

Technical setting chỉ dành admin.

---

# 48. Policy Presets

Preset:

## Safe Analysis

```text
Python
No internet
Read input
Write output
```

## Research

```text
Python
Browser
Public internet
```

## Marketing

```text
Python
Browser
Approved APIs
```

## Finance

```text
Python
No arbitrary internet
Read-only data
```

## Coding

```text
Git
CLI
Package manager
Restricted network
```

---

# 49. Recommended Default Agents

Phase đầu chỉ sandbox các Agent có lợi rõ ràng:

```text
1. Research Agent
2. Marketing Agent
3. Sales Data Agent
4. Finance Analysis Agent
5. Coding Agent
```

Không sandbox:

```text
OKR Coach

12WY Coach

Strategy Chat
```

nếu chỉ sử dụng LLM.

---

# 50. OpenSandbox Upgrade Strategy

OpenSandbox đang phát triển nhanh.

Không import internal implementation.

Chỉ phụ thuộc:

```text
official API
official SDK
stable protocol
```

Wrap trong:

```text
OpenSandboxExecutor
```

Khi upstream thay đổi:

```text
only adapter changes
```

COSA business logic không thay đổi.

---

# 51. Definition of Done — Phase 1

Phase 1 hoàn tất khi:

- [ ] Agent tạo sandbox
- [ ] Sandbox chạy Python
- [ ] Sandbox đọc input
- [ ] Sandbox ghi output
- [ ] CPU/RAM giới hạn
- [ ] Timeout hoạt động
- [ ] Sandbox destroy sau job
- [ ] Audit lưu job
- [ ] Artifact được copy về COSA
- [ ] Secret không xuất hiện trong logs
- [ ] Failure không ảnh hưởng COSA host

---

# 52. Acceptance Test

Test:

```text
User uploads sales.csv
```

COSA:

```text
Sales Analysis Agent
```

Sandbox:

```text
python analyze.py
```

Result:

```text
sales_summary.json
sales_report.md
```

COSA:

```text
display result
```

Sandbox:

```text
destroy
```

Audit:

```text
completed
```

---

# 53. Kiến trúc COSA đề xuất cuối cùng

```text
                     COSA FOUNDER OS
                            │
                  ┌─────────▼─────────┐
                  │ Interaction Layer │
                  │ Flutter / LiveKit │
                  └─────────┬─────────┘
                            │
                  ┌─────────▼─────────┐
                  │     COSA Core     │
                  │      FastAPI      │
                  └─────────┬─────────┘
                            │
                  ┌─────────▼─────────┐
                  │ COSA Agent Runtime│
                  └─────────┬─────────┘
                            │
        ┌───────────────────┼────────────────────┐
        │                   │                    │
        ▼                   ▼                    ▼
    Intelligence          Memory              Workflow
        │                   │                    │
DeepSeek/ChatGPT        PostgreSQL              n8n
Gemini/others           Vector/Knowledge         │
        │                                        │
        └──────────────┐                         │
                       ▼                         │
                   Tool Layer ◄──────────────────┘
                       │
            ┌──────────┼───────────┐
            │          │           │
            ▼          ▼           ▼
           MCP     Internal API  Execution
                                   │
                          ┌────────▼────────┐
                          │ OpenSandbox     │
                          └────────┬────────┘
                                   │
                      ┌────────────┼────────────┐
                      ▼            ▼            ▼
                    Python       Browser        CLI
```

---

# 54. Kết luận

OpenSandbox rất phù hợp với COSA nhưng phải được đặt đúng vai trò.

Không coi OpenSandbox là:

```text
Agent Framework
```

Mà coi là:

```text
Secure Execution Infrastructure
```

Cấu trúc cốt lõi:

```text
COSA Core
    │
    ▼
COSA Agent Runtime
    │
    ├── Intelligence
    ├── Memory
    ├── Workflow
    ├── Permission
    ├── Tools
    │
    └── Execution
          │
          └── OpenSandbox
```

Đây là nền tảng giúp COSA chuyển từ:

> AI hỗ trợ Founder

sang:

> AI Workforce thực sự có khả năng thực thi công việc nhưng vẫn được COSA quản trị, giới hạn quyền và audit.

---

# 55. Ưu tiên triển khai cho Claude Code

Ưu tiên:

```text
P0
ExecutionProvider abstraction

P0
OpenSandboxExecutor

P0
Job lifecycle

P0
Policy + resource limits

P0
Artifact pipeline

P0
Audit

P1
Research Agent integration

P1
n8n integration

P1
Browser sandbox

P2
Marketing / Sales sandbox

P2
Coding Agent

P3
Skill Runtime

P3
Kubernetes
```

Không rewrite COSA hiện tại.

Triển khai theo nguyên tắc:

```text
ADD
not
REPLACE
```

và dùng feature flags để rollout dần.

---

# 56. Tài liệu tham khảo

- OpenSandbox repository: https://github.com/opensandbox-group/OpenSandbox
- OpenSandbox Python SDK: https://github.com/opensandbox-group/OpenSandbox/tree/main/sdks/sandbox/python
- OpenSandbox JavaScript SDK: https://github.com/opensandbox-group/OpenSandbox/tree/main/sdks/sandbox/javascript
- OpenSandbox CLI: https://github.com/opensandbox-group/OpenSandbox/tree/main/cli
- OpenSandbox egress component: https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/components/egress.md
- OpenSandbox API specs: https://github.com/opensandbox-group/OpenSandbox/tree/main/specs

---

**Implementation note:** Claude Code nên bắt đầu từ `ExecutionProvider` và một proof-of-concept `Research Agent -> OpenSandbox -> Python -> Artifact`, không triển khai toàn bộ architecture trong một lần.
