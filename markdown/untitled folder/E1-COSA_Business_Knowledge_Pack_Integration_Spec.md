# COSA BUSINESS KNOWLEDGE PACK
## Native Integration Specification tham khảo VietNam-Business-Builder

**Trạng thái:** Implementation Specification
**Mục tiêu:** Tích hợp có chọn lọc các tri thức, mẫu tài liệu, SOP, capability và legal reference hữu ích từ VietNam-Business-Builder vào kiến trúc native hiện tại của COSA.
**Nguyên tắc:** Local-first, company-owned, factory-default + company override, không copy nguyên plugin/orchestrator, không tạo kiến trúc song song.
**Đối tượng triển khai:** Claude Code trên codebase COSA hiện tại.

---

## 1. Quyết định kiến trúc

VietNam-Business-Builder là **nguồn tham khảo nội dung và cấu trúc business knowledge**, không phải runtime dependency và không phải subsystem của COSA.

COSA chỉ học và chuyển hóa các phần cần thiết thành native objects:

- Business Domain;
- Business Capability;
- Skill Package;
- SOP;
- Template;
- Reference;
- Legal Source;
- Living Artifact;
- Business Pack;
- Local Update Manifest.

Không cài nguyên plugin `bb-*` vào runtime COSA. Không tạo `bb-orchestrator` trong COSA. Không để tên MODORO xuất hiện trong UX hoặc artifact của khách hàng, ngoại trừ attribution/license trong source package nếu COSA tái sử dụng trực tiếp nội dung được cấp phép.

---

## 2. COSA hiện tại là trung tâm

Kiến trúc triển khai phải theo COSA native:

```text
Founder
  ↓
COSA Chat / Voice / UI
  ↓
Intent + Context + Business Capability
  ↓
COSA Control Plane
  ↓
Goal / Issue / Task / Agent / Skill / Tool
  ↓
Artifact / Business Data
  ↓
Hologram Hub / Decision / Review
```

Business Knowledge Pack là nguồn tri thức phục vụ các thành phần trên, không thay thế Control Plane.

---

## 3. Những gì lấy từ VietNam-Business-Builder

Repo tham khảo phân loại tài liệu thành năm nhóm:

- `POL`: Policy — chính sách/quy định;
- `MAN`: Manual — sổ tay/hướng dẫn;
- `SOP`: Standard Operating Procedure — quy trình;
- `FRM`: Form/Template — biểu mẫu;
- `RPT`: Report — báo cáo/phân tích.

COSA nên giữ taxonomy này vì ngắn gọn và phù hợp quản trị artifact.

Repo cũng chia nghiệp vụ thành các miền:

1. Governance;
2. Strategy;
3. Finance;
4. People;
5. Operations;
6. Sales;
7. Marketing;
8. Customer;
9. Product & Technology;
10. Training;
11. Reporting;
12. Growth.

COSA dùng các miền trên như **Business Domain taxonomy**, không dùng như menu bắt buộc và không dùng 5 tầng của repo làm software architecture.

---

# PHẦN A — BUSINESS PACK ARCHITECTURE

## 4. Khái niệm Business Pack

Business Pack là package nội dung business native của COSA.

Một pack có thể chứa:

```text
capabilities/
skills/
sops/
templates/
references/
legal/
schemas/
examples/
pack.yaml
```

Ví dụ:

```text
governance/
finance/
operations/
sales/
marketing/
customer/
reporting/
```

Không bắt buộc mọi company sử dụng mọi pack.

---

## 5. Factory Pack và Company Pack

COSA phải phân biệt rõ hai lớp.

### Factory Pack

Do COSA cung cấp.

- read-only đối với runtime thông thường;
- có version;
- có checksum;
- có source/provenance;
- có thể nhận update trong tương lai;
- có thể reset về mặc định.

### Company Pack

Thuộc doanh nghiệp cài COSA.

- tạo từ factory default hoặc tạo mới;
- được admin chỉnh sửa;
- dữ liệu local/private;
- không bị ghi đè khi update factory;
- có version riêng;
- có lịch sử chỉnh sửa.

Resolution:

```text
Company Override
      ↓
Factory Default
```

Nếu company không override, dùng factory.

Nếu company đã override, update factory không được ghi đè.

---

## 6. Cấu trúc local đề xuất

```text
.cosa/
├── factory/
│   ├── packs/
│   │   ├── governance/
│   │   ├── finance/
│   │   ├── operations/
│   │   ├── sales/
│   │   ├── marketing/
│   │   ├── customer/
│   │   ├── product-tech/
│   │   ├── training/
│   │   ├── reporting/
│   │   └── growth/
│   ├── legal/
│   └── manifest.json
│
├── company/
│   ├── packs/
│   ├── legal-notes/
│   ├── artifacts/
│   └── manifest.json
│
└── updates/
    ├── available/
    ├── downloaded/
    ├── pending-merge/
    └── history/
```

Nếu codebase hiện tại có thư mục/spec store khác, Claude Code phải map vào cấu trúc hiện hữu thay vì tạo `.cosa` mới một cách máy móc.

---

# PHẦN B — DOMAIN VÀ DANH MỤC CẦN THIẾT

## 7. Nguyên tắc curated essentials

Không import 204 mẫu chỉ để đạt số lượng.

Mỗi tài liệu tham khảo phải được đánh giá:

- có dùng thường xuyên không;
- có phù hợp startup/SME không;
- COSA đã có chức năng tương đương chưa;
- có tạo business value trực tiếp không;
- có phụ thuộc ngành không;
- có rủi ro pháp lý/tài chính không;
- có nên để optional pack không.

Phân loại triển khai:

- `CORE`: cài mặc định;
- `OPTIONAL`: có sẵn nhưng chưa kích hoạt;
- `FUTURE`: chưa triển khai;
- `REFERENCE_ONLY`: chỉ dùng làm nguồn nghiên cứu.

---

## 8. Governance Pack — CORE

Các capability/mẫu nên đưa vào COSA:

### CORE

- Company Profile;
- Company Legal Information;
- RACI / phân quyền;
- Risk Policy;
- Code of Conduct;
- NDA template;
- Service Agreement template;
- Compliance Checklist;
- License/Permit Register;
- License Renewal Calendar;
- Data Protection Policy;
- Document Approval Policy.

### OPTIONAL

- Shareholder Agreement;
- Board Meeting Minutes;
- Board Regulations;
- Agency Agreement;
- Business Cooperation Agreement;
- Insurance Register.

### Không auto-generate toàn bộ

Artifact pháp lý chỉ tạo khi user cần hoặc khi capability assessment đề xuất.

---

## 9. Strategy Pack — FEATURE-FLAG / PARTIAL

COSA hiện không được tự động bật lại các flow chiến lược đã disable.

Không đưa PESTEL/SWOT/TOWS vào flow mặc định chỉ vì repo tham khảo có SWOT.

Các nội dung có thể giữ dưới dạng optional/reference:

- Company Profile;
- Vision;
- Mission;
- Core Values;
- Business Model Canvas;
- Ideal Customer Profile;
- Competitive Landscape;
- Business Plan;
- OKR Template;
- Strategic Roadmap;
- Risk Register;
- Scenario Planning;
- Business Continuity Plan.

Các artifact chiến lược chỉ hoạt động theo feature flags và kiến trúc COSA hiện hành.

---

## 10. Finance Pack — CORE / HIGH PRIORITY

Nên có:

- Financial Policy;
- Internal Spending Policy;
- Receivable Policy;
- Pricing Policy;
- Cost Structure;
- Annual Budget;
- Cash-flow Forecast;
- Financial Scenario Planning;
- Break-even Analysis;
- Cash In/Out SOP;
- Receivable Reconciliation SOP;
- Monthly Close SOP;
- Receipt/Payment Form;
- Receivable Tracker;
- P&L Report;
- Balance Sheet;
- Cash Flow Statement;
- Monthly Finance Dashboard.

Lưu ý:

COSA không được đóng đinh chuẩn kế toán/pháp luật từ repo tham khảo. Các yêu cầu pháp lý/kế toán phải đọc từ Legal/Accounting Knowledge Pack hiện hành của company.

---

## 11. People Pack — OPTIONAL ban đầu

Do COSA hiện ưu tiên founder/admin và sau này mới thêm nhân viên, People Pack nên cài dưới dạng optional.

Nên chuẩn bị:

- Org Chart;
- Job Description Template;
- Headcount Plan;
- Employee Rules;
- Compensation Policy;
- Leave Policy;
- Information Security Policy;
- Recruitment SOP;
- Interview Questions;
- Candidate Scorecard;
- Offer Letter;
- Onboarding SOP;
- Employee Handbook;
- 30/60/90 Onboarding Checklist;
- Offboarding SOP;
- Performance Review Policy;
- Individual KPI Template.

Không cần kích hoạt UI khi company chỉ có founder.

---

## 12. Operations Pack — CORE

Nên có:

- Standard SOP Template;
- Core Process SOP;
- Daily Operations Checklist;
- Incident Handling SOP;
- Vendor Evaluation SOP;
- Vendor Scorecard;
- Purchase/Procurement SOP;
- Asset Register;
- Quality Policy;
- Meeting Policy;
- Meeting Minutes Template;
- Weekly Report Template;
- Internal Communication SOP;
- Operations Manual.

Các module quản lý kho/văn phòng chỉ kích hoạt theo ngành/company need.

---

## 13. Sales Pack — CORE

Nên có:

- Sales Strategy;
- Pricing Strategy;
- Distribution Channel Strategy;
- Unit Economics;
- Sales Process SOP;
- Sales Script;
- Objection Handling;
- Quotation SOP;
- Proposal Template;
- Sales Agreement Template;
- Sales Playbook;
- Pipeline Tracker;
- CRM Setup Guide;
- Sales Report;
- Partner Onboarding.

Các object động như lead/opportunity/pipeline phải lưu trong CRM database, không biến template file thành system of record.

---

## 14. Marketing Pack — CORE

Nên kết hợp với Marketing Skills hiện tại của COSA, không tạo hệ marketing thứ hai.

Các artifact/template cần thiết:

- Annual Marketing Plan;
- Content Strategy;
- Customer Journey Map;
- Marketing Competitor Analysis;
- Marketing Budget Allocation;
- Paid Ads SOP;
- SEO SOP;
- Email Marketing SOP;
- Social Media Playbook;
- Content Calendar.

Nếu COSA đã có skill mạnh hơn từ nguồn khác, giữ skill hiện tại và chỉ nhập template/reference hữu ích.

---

## 15. Customer Pack — CORE

Tách Customer capability khỏi CRM.

CRM = system of record.

Customer Pack = methodology + processes.

Nên có:

- Customer Experience Standards;
- Customer Onboarding SOP;
- After-sales SOP;
- NPS/CSAT Survey;
- Complaint Handling SOP;
- Refund/Warranty Policy;
- Complaint Log schema/template;
- Customer Segmentation SOP;
- Retention/Loyalty Playbook;
- Customer Health Score;
- Referral Program;
- Review/Testimonial Collection SOP.

---

## 16. Product & Technology Pack — CORE cho software company

Nên có:

- Product/Service Catalog;
- Product Roadmap;
- New Product Development SOP;
- Product Brief;
- Quality Control SOP;
- Tech Stack Map;
- IT Policy;
- Cybersecurity Policy;
- Backup SOP;
- System Account Register;
- Kaizen/Improvement Board;
- Improvement Proposal;
- SOP Review & Update Process.

Build Spec của COSA vẫn là object native hiện có, không thay bằng Product Brief.

---

## 17. Training Pack — OPTIONAL

Nên có khi company có nhân viên:

- Training Policy;
- Training Needs Assessment;
- Annual Training Plan;
- New Employee Training;
- Leadership Development;
- Training Material Template;
- Training Effectiveness Assessment;
- Mentoring/Coaching Program;
- Knowledge Management Guide;
- Training ROI Report.

---

## 18. Reporting Pack — CORE

Reporting là nguồn dữ liệu quan trọng cho Hologram Hub.

Nên có:

- Reporting Policy;
- KPI Dictionary;
- Data Collection/Verification SOP;
- Monthly Management Report;
- Financial Report Template;
- Dashboard Design Guide;
- Quarterly Business Review;
- Benchmarking Report;
- Annual Report.

Các báo cáo nên tạo từ structured business data trước, AI chỉ diễn giải và bổ sung narrative.

---

## 19. Growth Pack — OPTIONAL / FUTURE

Nên có dưới dạng pack bật theo maturity:

- Pitch Deck;
- Financial Valuation Model;
- Investment Memo;
- Cap Table;
- Term Sheet Template;
- Market Expansion Analysis;
- Franchise Model;
- Franchise Operations Manual;
- Exit Strategy;
- Succession Plan;
- Business Valuation Report.

Các nội dung đầu tư/pháp lý có risk policy cao.

---

# PHẦN C — COSA BUSINESS PACK STANDARD

## 20. Mẫu `pack.yaml`

```yaml
id: governance
name:
  vi: "Quản trị & Tuân thủ"
  en: "Governance & Compliance"
version: "1.0.0"
schema_version: "1"
status: active
source:
  type: cosa-factory
  references:
    - VietNam-Business-Builder
scope:
  company_types:
    - startup
    - sme
  jurisdictions:
    - VN
features:
  auto_enable: true
  company_override: true
  factory_reset: true
contents:
  capabilities_dir: capabilities
  skills_dir: skills
  sops_dir: sops
  templates_dir: templates
  references_dir: references
  legal_dir: legal
update_policy:
  channel: stable
  preserve_company_override: true
  require_admin_review_on_conflict: true
```

---

## 21. Mẫu Capability File

`capabilities/create-nda.yaml`

```yaml
id: governance.create_nda
name:
  vi: "Tạo thỏa thuận bảo mật"
domain: governance
execution_mode: assisted
artifact_type: POL
risk:
  level: high
  admin_review: true
required_context:
  - company
inputs:
  required:
    - parties
    - confidentiality_scope
    - purpose
  optional:
    - duration
    - governing_law
uses:
  skill: legal-document-drafting
  sop: create-legal-document
  template: nda-vn
legal_context:
  required: true
  jurisdiction: VN
output:
  canonical_format: structured_document
  allowed_exports:
    - docx
    - pdf
    - md
```

---

## 22. Mẫu `SKILL.md`

```markdown
---
id: legal-document-drafting
name: Legal Document Drafting
domain: governance
version: 1.0.0
risk: high
---

# Mục tiêu

Hỗ trợ soạn thảo bản nháp tài liệu quản trị/pháp lý dựa trên dữ liệu company và nguồn pháp lý hiện hành.

# Không được làm

- Không tự khẳng định tài liệu là tư vấn pháp lý cuối cùng.
- Không dùng văn bản pháp luật đã hết hiệu lực nếu có nguồn mới hơn.
- Không thay đổi nội dung Legal Source gốc.
- Không thực thi/publish tài liệu high-risk khi chưa qua policy approval.

# Context được phép

- Company profile
- Company governance configuration
- User-provided transaction/party data
- Active Legal Knowledge Pack

# Quy trình

1. Xác định loại tài liệu.
2. Kiểm tra input bắt buộc.
3. Resolve legal references hiện hành.
4. Resolve company template override; nếu không có dùng factory template.
5. Tạo structured artifact draft.
6. Gắn legal source references và version.
7. Đánh dấu `review_required=true`.

# Output contract

- artifact_type
- title
- sections
- variables_used
- legal_sources
- unresolved_items
- review_required
```

---

## 23. Mẫu SOP

`sops/create-legal-document.yaml`

```yaml
id: governance.create_legal_document
version: "1.0.0"
objective: "Tạo bản nháp tài liệu quản trị/pháp lý có nguồn và khả năng truy vết."
steps:
  - id: collect_inputs
    action: validate_required_inputs
  - id: resolve_template
    action: resolve_company_then_factory
  - id: resolve_legal
    action: load_active_legal_sources
  - id: create_draft
    action: run_skill
  - id: persist
    action: create_artifact
  - id: request_review
    condition: risk_level >= high
business_rules:
  - company_override_has_priority
  - legal_source_is_immutable
  - expired_legal_source_cannot_be_default
  - high_risk_artifact_requires_review
```

---

## 24. Mẫu Template Metadata

`templates/nda-vn/template.yaml`

```yaml
id: nda-vn
name: "NDA Việt Nam — Factory Template"
type: POL
version: "1.0.0"
status: active
jurisdiction: VN
source: cosa-factory
editable_copy: true
company_override_key: governance.templates.nda-vn
legal_refs: []
variables:
  - party_a
  - party_b
  - purpose
  - confidential_information
  - term
sections:
  - parties
  - purpose
  - definition
  - obligations
  - exclusions
  - term
  - remedies
  - governing_law
  - signatures
```

`templates/nda-vn/body.md`

```markdown
# THỎA THUẬN BẢO MẬT

> Factory template. Phải được kiểm tra lại theo Legal Knowledge Pack hiện hành trước khi sử dụng chính thức.

## 1. Các bên

{{party_a}}

{{party_b}}

## 2. Mục đích

{{purpose}}

## 3. Thông tin bảo mật

{{confidential_information}}

## 4. Nghĩa vụ bảo mật

[Company/factory content]

## 5. Ngoại lệ

[Company/factory content]

## 6. Thời hạn

{{term}}

## 7. Luật áp dụng

Được resolve từ Legal Knowledge Pack tại thời điểm tạo artifact.

## 8. Chữ ký

[Signature block]
```

Lưu ý: đây là skeleton kỹ thuật, không phải nội dung pháp lý hoàn chỉnh.

---

# PHẦN D — LEGAL KNOWLEDGE PACK

## 25. Nguyên tắc

Văn bản pháp luật là dữ liệu nguồn có version, không phải prompt.

Không hard-code luật vào Skill.

Không cho company sửa nội dung nguồn pháp luật rồi ghi đè source gốc.

Company có thể:

- thêm ghi chú;
- map điều luật vào SOP;
- đánh dấu applicability;
- thêm interpretation nội bộ;
- upload văn bản mới;
- chọn nguồn active sau khi kiểm tra.

---

## 26. Cấu trúc Legal Source

`legal/sources/<id>/metadata.yaml`

```yaml
id: vn-law-example
jurisdiction: VN
title: "Tên văn bản"
document_type: law
identifier: ""
issuer: ""
issued_date: null
effective_date: null
expiry_date: null
status: unknown
version: "1"
source_url: ""
source_file: source.pdf
text_file: normalized.md
last_verified_at: null
verified_by: null
supersedes: []
superseded_by: []
tags: []
checksum: ""
```

---

## 27. Company Legal Annotation

`company/legal-notes/vn-law-example.yaml`

```yaml
legal_source_id: vn-law-example
company_id: ""
applicability:
  status: unknown
  business_areas: []
notes: []
linked_sops: []
linked_templates: []
reviewed_at: null
reviewed_by: null
```

Không sửa `factory/legal/.../source.*`.

---

## 28. Trạng thái pháp lý

COSA cần tối thiểu:

```text
current
amended
superseded
expired
unknown
```

Nếu `unknown`, AI phải nói rõ chưa xác minh thay vì suy đoán.

---

## 29. Legal Resolver

Pseudo flow:

```text
Capability needs law
      ↓
Jurisdiction Resolver
      ↓
Legal Source Catalog
      ↓
Filter active/current
      ↓
Company applicability notes
      ↓
Skill Context
```

Không đưa tất cả legal documents vào context.

---

# PHẦN E — LIVING ARTIFACT

## 30. Artifact không phải file chết

Mọi tài liệu quan trọng được lưu thành COSA Artifact với metadata.

```yaml
id:
company_id:
project_id:
domain:
capability_id:
document_type: SOP
factory_template_id:
factory_template_version:
company_template_version:
title:
status: draft
owner:
approved_by:
effective_date:
review_date:
content:
legal_sources: []
source_work: []
version: 1
created_at:
updated_at:
```

---

## 31. Artifact status

```text
draft
review
approved
active
superseded
archived
```

Không dùng `approved` cho mọi loại artifact nếu company không cần formal approval.

---

## 32. Export

Canonical artifact lưu structured/local data.

Export khi cần:

- Markdown;
- DOCX;
- PDF;
- XLSX;
- HTML.

File format không phải system of record.

---

# PHẦN F — FACTORY UPDATE / COMPANY OVERRIDE

## 33. Mục tiêu tương lai

COSA Update Server có thể phát hành:

- business pack;
- skill;
- template;
- SOP;
- reference;
- legal metadata/source;
- schema;
- migration instruction.

Server không cần nhận dữ liệu company.

---

## 34. Update Manifest mẫu

```json
{
  "package": "governance",
  "version": "1.2.0",
  "schema_version": "1",
  "released_at": "2026-08-18T00:00:00Z",
  "channel": "stable",
  "files": [
    {
      "path": "templates/nda-vn/template.yaml",
      "sha256": "...",
      "change": "modified"
    }
  ],
  "breaking": false,
  "requires_admin_review": true,
  "release_notes": "Cập nhật factory template."
}
```

---

## 35. Update flow

```text
Update Server
    ↓
Fetch manifest
    ↓
Compare local factory version
    ↓
Download to staging
    ↓
Verify checksum/signature
    ↓
Detect company overrides
    ↓
Install new Factory Version
    ↓
Company Override remains unchanged
    ↓
Optional Merge Review
```

---

## 36. Quy tắc merge

Không bao giờ:

```text
new factory → overwrite company file
```

Nếu company có override:

```text
Old Factory
New Factory
Company Override
      ↓
Diff Viewer
      ↓
Admin chooses:
KEEP COMPANY
ACCEPT NEW FACTORY
MERGE
RESET TO FACTORY
```

---

## 37. Mẫu conflict metadata

```yaml
id: conflict-001
asset_id: governance.templates.nda-vn
old_factory_version: 1.0.0
new_factory_version: 1.1.0
company_override_version: 3
status: pending
resolution: null
```

---

# PHẦN G — DATABASE / INDEX

## 38. Không bắt buộc lưu raw content hai lần

Nếu COSA hiện lưu file local và metadata trong PostgreSQL, tiếp tục pattern đó.

Đề xuất logical entities:

- `business_packs`;
- `business_capabilities`;
- `pack_assets`;
- `company_overrides`;
- `legal_sources`;
- `legal_annotations`;
- `artifacts`;
- `artifact_versions`;
- `update_manifests`;
- `update_conflicts`.

Claude Code phải map vào schema hiện hữu và tránh tạo table trùng.

---

## 39. Asset identity

Mọi asset factory cần stable ID.

Ví dụ:

```text
governance.templates.nda-vn
governance.sops.create-legal-document
finance.templates.cashflow-forecast
sales.sops.sales-process
```

Path file có thể đổi nhưng ID không nên đổi nếu semantics không đổi.

---

# PHẦN H — UI/UX

## 40. Không tạo 204 menu

Founder không duyệt file tree để sử dụng COSA.

UI chính hiển thị capability:

```text
Tạo NDA
Thiết kế SOP bán hàng
Tạo Customer Onboarding
Lập Cashflow Forecast
Chuẩn bị Monthly Report
```

Advanced Admin mới thấy:

```text
Business Packs
Skills
SOPs
Templates
Legal Sources
Versions
Updates
```

---

## 41. Business Pack Admin

Mỗi pack hiển thị:

- version factory;
- version company;
- assets;
- overrides;
- update available;
- conflicts;
- reset;
- export/import.

---

## 42. Legal Admin

Hiển thị:

- legal source;
- status;
- effective date;
- last verified;
- linked capabilities;
- linked SOP/templates;
- company notes;
- update available.

---

# PHẦN I — TÍCH HỢP VỚI COSA CONTROL PLANE

## 43. Flow tạo work

```text
Founder Request
      ↓
Intent
      ↓
Business Capability
      ↓
Resolve Company Pack
      ↓
Resolve SOP + Skill + Template + References
      ↓
COSA Goal/Issue/Task/Agent execution as required
      ↓
Artifact
      ↓
Hologram / Business System
```

Business Pack không có orchestrator riêng.

---

## 44. Direct vs agentic

Ví dụ tạo checklist đơn giản có thể direct.

Research, analysis hoặc multi-step work có thể giao Agent qua COSA Control Plane.

Business Pack chỉ mô tả capability và knowledge assets; Control Plane quyết định execution phù hợp.

---

## 45. Risk policy

Các nhóm mặc định high-risk:

- legal;
- employment;
- financial record changes;
- tax/compliance;
- investment documents;
- production deployment;
- external publication/actions.

High-risk không có nghĩa mọi draft phải chặn. Có thể tạo draft trực tiếp nhưng cần review trước action chính thức.

---

# PHẦN J — FILE MẪU CORE PACK

## 46. Mẫu SOP Template chung

`operations/templates/sop-standard/body.md`

```markdown
# {{sop_title}}

**Mã:** {{sop_code}}
**Owner:** {{owner}}
**Version:** {{version}}
**Ngày hiệu lực:** {{effective_date}}

## 1. Mục đích

{{purpose}}

## 2. Phạm vi

{{scope}}

## 3. Vai trò và trách nhiệm

{{roles}}

## 4. Input

{{inputs}}

## 5. Quy trình

{{steps}}

## 6. Output

{{outputs}}

## 7. Kiểm soát rủi ro

{{controls}}

## 8. KPI/SLA

{{metrics}}

## 9. Biểu mẫu liên quan

{{forms}}

## 10. Lịch sử thay đổi

{{change_history}}
```

---

## 47. Mẫu Weekly Report

```markdown
# BÁO CÁO TUẦN

## Kết quả chính

- {{result_1}}
- {{result_2}}
- {{result_3}}

## KPI

{{kpi_table}}

## Việc chưa hoàn thành

{{unfinished}}

## Vấn đề / Rủi ro

{{issues}}

## Quyết định cần founder

{{decisions}}

## Top 3 tuần tới

1. {{next_1}}
2. {{next_2}}
3. {{next_3}}
```

Hologram có thể đọc `decisions` và `issues` để sinh Executive Cards.

---

## 48. Mẫu Customer Complaint SOP

```yaml
id: customer.complaint_handling
objective: "Tiếp nhận, phân loại, xử lý và học từ khiếu nại khách hàng."
steps:
  - capture_case
  - classify_severity
  - assign_owner
  - investigate
  - propose_resolution
  - obtain_approval_if_compensation_required
  - respond_customer
  - close_case
  - extract_learning
outputs:
  - complaint_record
  - resolution
  - learning_signal
hologram:
  create_signal_if:
    - severity >= high
    - repeated_pattern == true
```

---

## 49. Mẫu Sales Process SOP

```yaml
id: sales.standard_process
stages:
  - lead
  - qualify
  - discovery
  - proposal
  - negotiation
  - won
  - lost
required_data:
  qualify:
    - customer_need
    - decision_role
    - expected_value
  proposal:
    - scope
    - price
    - timeline
metrics:
  - conversion_rate
  - average_deal_size
  - sales_cycle
  - win_rate
system_of_record: crm
```

---

## 50. Mẫu KPI Definition

```yaml
id: sales.win_rate
name: Win Rate
owner: sales
formula: won_opportunities / closed_opportunities
unit: percent
frequency: weekly
source: crm
thresholds:
  warning: null
  critical: null
notes: "Company tự cấu hình benchmark; không hard-code benchmark từ nguồn tham khảo."
```

---

## 51. Mẫu Cashflow Forecast Template metadata

```yaml
id: finance.cashflow_forecast
artifact_type: RPT
frequency: monthly
periods: 12
inputs:
  - opening_cash
  - expected_collections
  - payroll
  - operating_expenses
  - tax_payments
  - capex
outputs:
  - closing_cash
  - runway
  - low_cash_alert
scenario_support: true
```

---

## 52. Mẫu Product Brief

```markdown
# PRODUCT BRIEF

## Problem
{{problem}}

## Target User
{{target_user}}

## Desired Outcome
{{outcome}}

## Scope
{{scope}}

## Non-goals
{{non_goals}}

## Constraints
{{constraints}}

## Success Metrics
{{success_metrics}}

## Related Build Specs
{{build_spec_refs}}
```

Product Brief không thay Build Spec.

---

# PHẦN K — PROVENANCE / LICENSE

## 53. Nguồn tham khảo

VietNam-Business-Builder được dùng như reference source để thiết kế danh mục business artifacts, domain taxonomy, skill/reference pattern và sample concepts.

Nếu COSA copy hoặc sửa trực tiếp file/nội dung có bản quyền từ repository MIT này, package/source distribution phải giữ copyright notice và MIT license theo điều khoản của repository.

Nếu COSA chỉ học ý tưởng/taxonomy rồi viết nội dung mới từ đầu, vẫn nên lưu provenance nội bộ để biết nguồn nghiên cứu.

Mẫu:

```yaml
provenance:
  inspired_by:
    - name: VietNam-Business-Builder
      source: github
      license: MIT
  cosa_authored: true
```

---

# PHẦN L — IMPLEMENTATION PLAN CHO CLAUDE CODE

## 54. Phase 0 — Audit

KHÔNG code ngay.

Claude Code phải kiểm tra:

- COSA đang lưu skill ở đâu;
- prompt/spec ở đâu;
- factory reset hiện tại;
- company-level local data;
- file storage;
- PostgreSQL metadata;
- artifact model;
- permission admin;
- existing legal knowledge;
- marketing skill integration;
- finance/accounting structures;
- Hologram inputs;
- update/version mechanisms nếu đã có.

Tạo:

`BUSINESS_PACK_CURRENT_STATE.md`

với mỗi component:

```text
EXISTS
PARTIAL
MISSING
CONFLICT
```

---

## 55. Phase 1 — Package Standard

Implement tối thiểu:

- Pack manifest;
- stable asset ID;
- factory/company resolution;
- pack loader;
- version metadata;
- admin-only override;
- reset factory.

Không import toàn bộ domain ngay.

---

## 56. Phase 2 — Pilot Packs

Pilot 4 pack quan trọng:

1. Governance;
2. Operations;
3. Sales;
4. Reporting.

Mỗi pack chỉ 3–5 capability đầu tiên.

Test end-to-end trước khi mở rộng.

---

## 57. Phase 3 — Legal Knowledge

Implement:

- LegalSource;
- LegalAnnotation;
- status/effective date;
- file storage;
- immutable source;
- company note;
- reference linking.

Không tự động cập nhật luật từ internet trong phase này.

---

## 58. Phase 4 — Remaining Business Packs

Mở rộng:

- Finance;
- Marketing;
- Customer;
- Product-Tech;
- People/Training optional;
- Growth optional.

Phải đối chiếu với module COSA đã có để tránh duplicate.

---

## 59. Phase 5 — Update-ready Architecture

Chỉ xây local manifest/conflict model trước.

Không bắt buộc có central update server ngay.

Chuẩn bị interface:

```text
PackUpdateProvider
```

Local provider trước.

Remote COSA Update Server bổ sung sau.

---

# PHẦN M — ACCEPTANCE TESTS

## 60. Factory / company

- Company sửa template → factory không đổi.
- Factory update → company override không đổi.
- Reset → company có thể quay về factory.
- Diff → xem được factory cũ/mới/company.

## 61. Legal

- Legal source gốc không sửa từ company UI.
- Company note lưu riêng.
- Source expired không được resolve mặc định.
- Unknown status phải được báo là chưa xác minh.

## 62. Capability

- User chọn capability, không cần biết file path.
- Pack resolver chọn company override trước.
- Artifact ghi lại template/version/reference đã dùng.

## 63. Security

- Chỉ Admin sửa factory override/spec quan trọng.
- Company data không gửi về license server.
- API key không nằm trong pack.

## 64. Compatibility

- Không tạo orchestrator cạnh tranh COSA Control Plane.
- Không bật lại Strategy/PES­TEL/SWOT/TOWS trái feature flag.
- Không duplicate CRM system of record bằng spreadsheet/template.
- Không duplicate Build Spec.

---

# PHẦN N — PROMPT MASTER CHO CLAUDE CODE

```text
Bạn đang triển khai COSA Business Knowledge Pack dựa trên tài liệu
"COSA BUSINESS KNOWLEDGE PACK — Native Integration Specification".

QUAN TRỌNG:

VietNam-Business-Builder chỉ là nguồn tham khảo.
KHÔNG cài nguyên plugin.
KHÔNG tạo bb-orchestrator.
KHÔNG đổi COSA architecture sang kiến trúc 5 tầng của repo.
KHÔNG import 204 files một cách máy móc.

COSA hiện tại là source of truth cho architecture.

Mục tiêu:

1. Chuẩn hóa Business Pack native.
2. Lưu factory assets local.
3. Tạo company override local/private.
4. Company override luôn ưu tiên factory.
5. Factory update trong tương lai không ghi đè company content.
6. Chuẩn hóa Skill + SOP + Template + Reference + Legal Source.
7. Kết quả business quan trọng trở thành COSA Artifact.
8. Legal source có version/status/effective date/provenance.
9. Không hard-code nội dung luật vào prompt.
10. Chỉ Admin được sửa/reset các tài sản quan trọng.

TRƯỚC KHI CODE:

Audit codebase và tạo BUSINESS_PACK_CURRENT_STATE.md.

Với từng capability hiện có, đánh dấu:
EXISTS / PARTIAL / MISSING / CONFLICT.

Kiểm tra đặc biệt:
- skill registry hiện tại;
- prompt storage;
- local file structure;
- company-specific data;
- artifact;
- admin permissions;
- factory reset;
- legal knowledge;
- update/versioning;
- marketing;
- finance;
- CRM;
- Hologram.

Không sửa code trước khi hoàn thành audit.

SAU AUDIT:

Đề xuất migration nhỏ nhất để thêm Business Pack Standard mà không rewrite COSA.

Pilot chỉ:
Governance + Operations + Sales + Reporting.

Mỗi pilot pack 3–5 capabilities.

Sau pilot:
- run tests;
- document changes;
- verify local ownership;
- verify factory/company override;
- verify no duplicated architecture.

Dừng sau pilot và báo cáo kết quả.
```

---

# PHẦN O — KẾT LUẬN KIẾN TRÚC

VietNam-Business-Builder cung cấp một nguồn tham khảo quan trọng về **những gì một doanh nghiệp cần được hệ thống hóa**, nhưng COSA phải chuyển hóa nó thành tài sản native, local và sống theo thời gian.

Mô hình chốt:

```text
COSA Factory Knowledge
        ↓
Install / Enable
        ↓
Company Local Copy / Override
        ↓
Founder + Team customize
        ↓
COSA Capability uses Pack
        ↓
Agent / Tool execution
        ↓
Living Artifact
        ↓
Business Operation
        ↓
Hologram / Review / Decision
```

Sau này:

```text
COSA Update Server
        ↓
New Factory Pack / Legal Reference / Skill / Template
        ↓
Local update staging
        ↓
Diff / Merge
        ↓
Company data preserved
```

Nguyên tắc cuối cùng:

> COSA cung cấp bộ tri thức và mẫu chuẩn để bắt đầu; mỗi doanh nghiệp sở hữu, chỉnh sửa và vận hành bản local của chính mình. Bản cập nhật COSA chỉ nâng cấp factory knowledge, không chiếm quyền sở hữu nội dung company.

