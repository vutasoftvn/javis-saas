# COSA — Agent Workforce Control Plane Integration

Kiến trúc lõi sau điều chỉnh:

```text
Vision
  ↓
Mission
  ↓
Core Values
  ↓
Project
  ↓
Objective
  ↓
OKRs
  ↓
12 Week Year
  ↓
Weekly Tactics
  ↓
Tasks
  ↓
Human / AI Agent
  ↓
Execution
  ↓
Work Product
  ↓
Review
  ↓
Scoreboard
  ↓
Week 13
```

Startup Validation không nằm trong flow COSA.

Kiến trúc Agent Workforce:

```text
Founder OS
    ↓
Agent Workforce Control Plane
    ├── Agent Registry
    ├── Org Chart
    ├── Runtime Adapter
    ├── Skill Registry
    ├── Permissions
    ├── Human Approval
    ├── Budget
    ├── Cost Ledger
    ├── Event Bus
    ├── Heartbeat
    ├── Routine
    ├── Execution Workspace
    ├── Trust Boundary
    ├── Work Products
    └── Audit Log
            ↓
      Runtime Adapter Layer
            ↓
Claude Code / Codex / Gemini / DeepSeek / OpenClaw / HTTP
            ↓
MCP / n8n / GitHub / CRM / Email / Zalo / Telegram
```

Nguyên tắc triển khai:

- Agent không gắn cứng với model/provider.
- Event-driven trước, schedule sau, polling cuối cùng.
- Prompt, Skill, Policy và Spec phải tách riêng.
- Prompt/Spec/Policy quan trọng chỉ Founder/Admin được sửa.
- Có version, diff và Reset to Default.
- Human và Agent dùng chung Permission Engine.
- Action LOW có thể tự chạy; HIGH phải approval; CRITICAL chỉ Founder.
- Mọi Agent Run phải theo dõi cost.
- Coding Agent phải có workspace riêng.
- External input mặc định là untrusted.
- Agent không được tự thuê/tạo agent khác.
- Agent không tự mở rộng scope; chỉ tạo Recommendation.
- Chat/Voice chỉ là command interface, không tự động kích hoạt Project workflow.
- Company data, API key và configuration thuộc từng company cài COSA riêng.
- Export Company Package không được chứa secret.

Triển khai theo thứ tự:

**Phase A — Core Control Plane**  
Agent Registry → Runtime Adapter → Task Assignment → Agent Run → Audit.

**Phase B — Governance**  
Permission → Risk Policy → Approval → Budget → Cost Ledger.

**Phase C — Skills**  
Skill Registry → loader → version → customize → reset default.

**Phase D — Automation**  
Event Bus → Heartbeat → Routine.

**Phase E — Secure Execution**  
Workspace → Low Trust → Secret → Runtime Capability → Loop Protection.

**Phase F — UX**  
Hologram Workforce → Agent Cards → Approval Inbox → Cost Dashboard → Run History.

Đích kiến trúc:

> **COSA = Founder Operating System + AI Workforce Control Plane**

Founder là authority cuối cùng; các AI Agent là lực lượng phân tích và thực thi có vai trò, skill, quyền, ngân sách, runtime và trách nhiệm giải trình rõ ràng.