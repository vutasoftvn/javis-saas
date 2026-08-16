# Strategic Canvas 1–1–3

## Đặc tả triển khai cho Javis và Claude Code

**Phiên bản:** 1.0  
**Ngày:** 2026-08-09  
**Phạm vi:** Javis cho one-person company hoặc đội ngũ rất nhỏ  
**Nền tảng đích:** Flutter desktop/mobile, FastAPI/Python, PostgreSQL + pgvector, S3/MinIO Vault, agent-worker tách biệt  
**AI mặc định:** DeepSeek Flash qua AI Router; không khóa chặt vào tên model

---

## 1. Mục đích

Strategic Canvas 1–1–3 là mô-đun biến chiến lược thành công việc có thể thực thi. AI chỉ tạo bản nháp có bằng chứng; founder hoặc người có quyền chiến lược mới phê duyệt và kích hoạt.

Khung bắt buộc:

- 1 Tầm nhìn (Vision)
- 1 Sứ mệnh (Mission)
- 3 Giá trị cốt lõi (Core Values)
- 1 Project Context đã phê duyệt cho một lần phân tích
- 3 vị trí kết quả cho mỗi nhóm phân tích
- 3 Strategic Goals được kích hoạt
- Tối đa 3 Key Results cho một Objective
- Tối đa 3 initiative đang chạy trong toàn bộ chu kỳ 12 tuần
- Big 3 mỗi tuần và 1–3 task ưu tiên mỗi ngày

Chuỗi truy vết:

~~~text
Vision / Mission / 3 Core Values
  → Project Context + Internal Resources + Evidence
  → PESTEL: 6 factor × 3 slots
  → SWOT: 4 group × 3 slots
  → TOWS: 4 type × 3 options
  → 3 Strategic Goals
  → BSC Strategy Map
  → OKRs
  → 12 Week Year
  → Initiatives
  → Tasks: List, Calendar, Kanban
~~~

Một task chiến lược phải truy vết ngược được về Key Result, Strategic Goal, TOWS, SWOT, PESTEL và evidence. Task không có chuỗi này vẫn được tồn tại như task tự do, nhưng không được tính là tiến độ chiến lược.

### 1.1 Không thuộc phạm vi MVP

- AI tự approve hoặc tự kích hoạt kế hoạch.
- Bịa nhận định để làm đủ ba dòng.
- Tự sửa, hủy hoặc dời Task/OKR active khi có analysis mới.
- Thêm database/vector database khác ngoài PostgreSQL + pgvector.
- Biến BSC thành hệ thống KPI cồng kềnh.
- Gửi Telegram, Zalo, email, đăng mạng xã hội hay thay đổi hệ thống ngoài nếu chưa có approval riêng.

---

## 2. Vai trò, quyền và cổng phê duyệt

| Vai trò | Quyền chính | MVP |
|---|---|---|
| Founder / Strategy Owner | Tạo, sửa, phê duyệt, kích hoạt toàn bộ strategy | Vai trò mặc định |
| Admin | Soạn, review; chỉ approve nếu có capability strategy.approve | Không mặc định thay Founder |
| Contributor | Thêm evidence, cập nhật task, góp ý draft | Không chốt strategy |
| AI Service Account | Tạo draft, phân tích, gợi ý task | Không có quyền approve |

| Đối tượng | AI được làm | Cần approval trước khi |
|---|---|---|
| Foundation | Đề xuất, kiểm tra mâu thuẫn | Trở thành foundation chính thức |
| Project Context | Tóm tắt, phát hiện phần thiếu | Được dùng chạy pipeline official |
| PESTEL/SWOT/TOWS | Tạo draft kèm evidence/confidence | Được làm đầu vào official |
| Goals/BSC/OKR | Đề xuất, xếp hạng, liên kết | Được kích hoạt |
| 12 Week Plan | Chia nhỏ thành initiative/task/lịch nháp | Tạo schedule hoặc recurring task |
| External action | Chỉ tạo draft/outbox | Được gửi/thực thi |

Mọi approval lưu actor, role, revision, thời gian, quyết định approve/reject/request_changes, ghi chú và audit event. Chỉ revision approved được sử dụng làm nguồn official ở bước kế tiếp.

---

## 3. Mô hình domain và quy tắc bất biến

### 3.1 Canvas và revision

Mỗi workspace có thể có nhiều Canvas. MVP có thể chỉ dùng Canvas Company Strategy. Canvas có revision bất biến:

~~~text
draft → in_review → approved → superseded → archived
                 ↘ changes_requested → draft
~~~

Quy tắc:

1. Tối đa một revision approved cho một Canvas.
2. Không sửa trực tiếp revision approved.
3. Revision mới approved làm revision cũ thành superseded; không tự thay đổi plan active.
4. Đối tượng downstream luôn giữ strategy_revision_id đã sinh ra nó.

### 3.2 Ba slots, không phải ba khẳng định

Hệ thống tạo sẵn ba slot cho mỗi PESTEL factor, SWOT group, TOWS type và Goal set. Mỗi slot có trạng thái:

| Status | Ý nghĩa | UI |
|---|---|---|
| empty | Chưa phân tích | Ô trống có CTA |
| draft | AI/người dùng đã soạn | Viền nháp |
| verified | Có bằng chứng đã kiểm tra | Dấu xác thực |
| unverified | Có nhận định, chứng cứ chưa đủ | Cảnh báo vàng |
| data_gap | Chưa đủ dữ liệu để kết luận | CTA tạo validation task |
| rejected | Founder loại bỏ | Thu gọn, vẫn có audit |
| approved | Được chấp nhận trong revision | Khóa mềm |

Không được tự thay data_gap hoặc rejected bằng câu chung chung để đủ ba dòng. UI luôn giữ ba vị trí, nhưng có thể chỉ một hoặc hai vị trí là finding approved.

### 3.3 Giới hạn chống quá tải

| Đối tượng | Default | Ghi chú |
|---|---:|---|
| Strategic Goal active | 3 | Focus chính |
| BSC objective | 3–8 | Objective hỗ trợ phải liên kết một Goal |
| Key Result/Objective | 1–3 | Đo được và review được |
| Initiative active/cycle | 1–3 | Toàn hệ thống, không phải mỗi Goal |
| Big 3/tuần | 3 | Cam kết |
| Task ưu tiên/ngày | 1–3 | Daily focus |
| Kanban WIP in_progress | 3 | Giảm tồn đọng |

Các giá trị là workspace policy. Override chỉ bởi Founder/capability phù hợp và luôn có audit reason.

---

## 4. Luồng nghiệp vụ

~~~mermaid
flowchart TB
    F["1 Vision · 1 Mission · 3 Values"] --> C["Approved Project Context"]
    C --> P["PESTEL: 6 × 3 slots"]
    P --> S["SWOT: 4 × 3 slots"]
    S --> T["TOWS: 4 × 3 options"]
    T --> G["3 Strategic Goals"]
    G --> B["BSC Strategy Map"]
    B --> O["OKRs"]
    O --> W["12 Week Plan"]
    W --> I["Initiatives"]
    I --> K["Tasks"]
~~~

### 4.1 Foundation 1–1–3

User nhập một Vision, một Mission, ba Value cards. Mỗi Value có title, description và decision rule. Decision rule là câu có thể kiểm tra khi ra quyết định, không chỉ là khẩu hiệu.

Ví dụ: Giá trị Minh bạch có rule: Không công bố nhận định thị trường không gắn nguồn, ngày và confidence.

Ràng buộc:

| Field | Rule |
|---|---|
| Vision | 20–500 ký tự, không rỗng, đúng một |
| Mission | 20–500 ký tự, không rỗng, đúng một |
| Core Values | đúng ba, đánh số 1–3 |
| Decision rule | bắt buộc trên mỗi value |

AI có thể phát hiện mâu thuẫn/trùng nghĩa và đề xuất câu chữ; không được thay nội dung đã approved.

### 4.2 Project Context Pack

Mỗi lần phân tích dùng một Context Pack versioned gồm ba khối:

1. **Business Context:** khách hàng, vấn đề, sản phẩm/dịch vụ, mô hình doanh thu, scope và kết quả kỳ vọng.
2. **Internal Resources:** thời gian founder/nhân sự, ngân sách/runway, kỹ năng, công nghệ, dữ liệu, tài sản, đối tác, giới hạn/rủi ro.
3. **External Evidence:** thị trường, phản hồi khách hàng, đối thủ, pháp lý, tài chính hoặc nguồn tin đáng tin.

Evidence item:

~~~json
{
  "title": "Tên nguồn",
  "summary": "Dữ kiện đã tóm tắt, không phải suy đoán",
  "source_type": "customer_interview | market_report | internal_metric | regulation | competitor | note",
  "source_url_or_vault_uri": "https://... hoặc vault URI",
  "published_at": "2026-08-01",
  "captured_at": "2026-08-09T10:00:00Z",
  "reliability": "high | medium | low",
  "tags": ["market"]
}
~~~

Context Pack có draft, ready_for_review, approved, stale, superseded. Chỉ approved được dùng cho official analysis; preview output phải có watermark.

### 4.3 PESTEL: 6 × 3

Factors cố định: Political, Economic, Social, Technological, Environmental, Legal. Khi tạo revision, hệ thống tạo 18 slot.

Mỗi finding có factor, slot_no từ 1 đến 3, statement, direction, impact, time_horizon, evidence_ids, confidence, assumptions, validation_task_hint và slot_status.

Logic:

1. Context Pack Builder lấy revision approved và evidence được chọn.
2. AI tạo tối đa ba candidate cho mỗi factor, không tự tạo source.
3. Validator kiểm tra evidence thuộc Context Pack, format, ngày nguồn và trùng nghĩa.
4. Không đủ bằng chứng thì dùng unverified hoặc data_gap.
5. User review, sửa/reject/mark verified hoặc tạo task xác minh.

### 4.4 SWOT: 4 × 3

| Group | Nguồn bắt buộc/ưu tiên |
|---|---|
| Strength | Internal Resources hoặc internal metrics |
| Weakness | Internal Resources hoặc internal metrics |
| Opportunity | PESTEL finding hoặc external evidence |
| Threat | PESTEL finding hoặc external evidence |

Không cho AI tạo Strength/Weakness chỉ từ tin thị trường. Mỗi finding phải có origin_type và origin_ids.

### 4.5 TOWS: 4 × 3

| Type | Kết hợp | Mục đích |
|---|---|---|
| SO | Strength + Opportunity | Khai thác cơ hội bằng thế mạnh |
| ST | Strength + Threat | Dùng thế mạnh giảm rủi ro |
| WO | Weakness + Opportunity | Khắc phục điểm yếu để tận dụng cơ hội |
| WT | Weakness + Threat | Phòng thủ, giảm rủi ro kép |

Mỗi TOWS option phải có title, strategy_statement, expected_outcome, effort, impact, risk, confidence, validation_needed và ít nhất hai SWOT links đúng tổ hợp.

### 4.6 Ba Strategic Goals

AI lấy TOWS approved và các option unverified được Founder cho phép xem xét để đề xuất đúng ba goals. Mỗi goal có:

- title, description, expected outcome;
- primary BSC perspective;
- TOWS/evidence chain;
- strategic_fit, impact, feasibility, urgency, risk;
- assumptions và guardrails;
- decision summary ngắn, không phải reasoning nội bộ model.

Điểm minh bạch:

~~~text
priority_score =
  0.30 × strategic_fit +
  0.25 × impact +
  0.20 × feasibility +
  0.15 × urgency +
  0.10 × (100 - risk)
~~~

Founder có thể đổi thứ tự, sửa, reject hoặc tạo goal thủ công. Khi approval, chính xác ba goals là active; phần còn lại là parking_lot/rejected.

### 4.7 BSC, OKR, 12 Week Year và Task

BSC không tạo thêm goal mới; nó biểu diễn quan hệ nhân–quả của ba goals qua:

~~~text
Learning & Growth → Internal Process → Customer & Market → Financial
~~~

Mỗi Goal có một primary perspective. Objective hỗ trợ tối đa tổng 8 và phải liên kết Goal. BSC edge phải là DAG, không có vòng lặp.

Mỗi approved BSC objective tạo một Objective; Objective có 1–3 Key Results. KR phải có baseline, target, unit, direction, formula/cách đo, source of truth, owner, deadline và check-in cadence.

Sau approval OKR, AI đề xuất một 12 Week Cycle: tối đa ba active initiative, milestone tuần 1–12, Big 3 tuần hiện tại, task, dependency, estimate và lịch nháp. Founder approve trước khi activate.

Task là canonical entity. List, Calendar, Kanban là ba view của cùng task và status: inbox, planned, in_progress, blocked, waiting_approval, done, cancelled.

---

## 5. UX/UI Flutter

### 5.1 Navigation

~~~text
Global: Home | Strategy | Tasks | Calendar | Kanban | Approvals | Vault
Strategy: Overview | Foundation | Context | PESTEL | SWOT | TOWS |
          Goals | BSC Map | OKRs | 12 Weeks | Traceability
~~~

Nguyên tắc UI:

- Luôn hiện revision badge: Draft, In review, Approved, Stale hoặc Superseded.
- Các group analysis dùng chung layout ba slot.
- Evidence count, confidence, impact, status luôn hiện trên card.
- Approval dùng CTA rõ: Submit review, Approve revision, Request changes.
- Mobile dùng wizard; desktop dùng split pane Context/Evidence và Draft.

### 5.2 Canvas Overview

Nội dung:

1. Canvas name, active revision, status, last reviewed, nút New Revision.
2. Progress rail Foundation → Context → PESTEL → SWOT → TOWS → Goals → BSC → OKR → 12 Weeks.
3. Ba Goal cards: perspective, OKR progress, state.
4. Attention queue: data gaps, approvals, stale plan, blocker.
5. Today Top 3 Task có strategy link.

### 5.3 Foundation và Context

Foundation desktop có hai cột: cột trái nhập Vision/Mission/ba Value cards; cột phải là AI Consistency Check. Không có nút thêm value thứ tư. Khi xoá value, giữ Slot 1/2/3 trống có CTA hoàn thiện.

Context Builder là ba tab Business Context, Internal Resources, External Evidence. Evidence table có Source, Fact, Date, Reliability, Link và Selected. Chỉ evidence selected đi vào Context Pack gửi AI.

### 5.4 PESTEL, SWOT và TOWS

PESTEL desktop: grid 2 × 3; mỗi factor là ba cards xếp dọc. Card data_gap hiện lý do và CTA Create validation task.

SWOT desktop: matrix 2 × 2, mỗi quadrant ba cards. Strength/Weakness mặc định filter Internal; Opportunity/Threat filter PESTEL + External.

TOWS desktop: bốn cột SO/ST/WO/WT, mỗi cột ba option. Card hiển thị các chips nguồn như S1 + O2, impact, effort, risk và status. UI có sort hỗ trợ ưu tiên nhưng không auto approve.

### 5.5 Goals, BSC, OKR và 12 Weeks

Goal Board có đúng ba cards đánh số 1–3. Mỗi card hiện score breakdown, primary BSC perspective, TOWS/evidence chain, outcome, assumptions, risk. Nút Approve and Generate BSC Map chỉ enabled khi ba goal hợp lệ và user có capability.

BSC Map desktop có bốn lanes. User kéo nối edge; backend validate DAG trước khi lưu. Mobile thay bằng Upstream/Downstream list.

OKR screen giới hạn ba KR rows/Objective. Mỗi Objective có Why this matters drawer.

12 Week screen có timeline Week 1–12, tối đa ba initiative lanes và Big 3 mỗi tuần. Kéo Task vào tuần chỉ cập nhật planned_start_at/due_at; không tạo task copy.

### 5.6 Task Traceability Drawer

Task detail có:

~~~text
Task → Initiative → Key Result → Objective → BSC Objective
     → Strategic Goal → TOWS → SWOT → PESTEL → Evidence
~~~

Các node click được để mở snapshot của đúng revision. Task tự do hiện Không liên kết chiến lược và CTA Link to Initiative.

---

## 6. Backend architecture

### 6.1 Module boundaries

~~~text
backend/
  app/
    modules/
      strategy_canvas/
        api.py
        schemas.py
        models.py
        repository.py
        service.py
        policies.py
        validators.py
        revision_service.py
      strategy_analysis/
        context_pack_service.py
        pestel_service.py
        swot_service.py
        tows_service.py
        goal_service.py
        bsc_service.py
      okr/
      planning/
      tasks/
      approvals/
      ai_router/
      audit/
    workers/
      strategy_analysis_worker.py
      stale_detection_worker.py
      schedule_worker.py
~~~

API handler chỉ xác thực request, gọi service và trả response. Quyền, state transition, audit, invariant ba slots và transaction phải ở service/policy layer. Không dồn mọi logic vào một endpoint hoặc một AI orchestrator file.

### 6.2 Flutter structure

~~~text
flutter_app/lib/
  features/
    strategy_canvas/
      data/
      domain/
      presentation/
        canvas_overview/
        foundation/
        context_pack/
        pestel/
        swot/
        tows/
        goals/
        bsc_map/
        traceability/
    okr/
    twelve_week/
    tasks/
    approvals/
  shared/widgets/
    three_slot_section.dart
    evidence_chip.dart
    revision_badge.dart
    approval_cta.dart
    traceability_drawer.dart
~~~

Tạo reusable widget ThreeSlotSection. PESTEL factor, SWOT quadrant, TOWS type và Goal Board dùng chung model slot_no từ 1 đến 3, không tạo bốn implementation khác nhau cho cùng một rule.

---

## 7. PostgreSQL data model

### 7.1 Danh sách bảng

| Bảng | Mục đích |
|---|---|
| strategy_canvases | Canvas theo workspace |
| strategy_revisions | Revision bất biến và lifecycle |
| strategy_foundations | Vision, Mission, Values |
| core_values | Ba value items + decision rules |
| project_context_packs | Ba context blocks |
| evidence_items | Evidence từ Vault/nguồn ngoài |
| pestel_findings | 18 PESTEL slots |
| swot_findings | 12 SWOT slots |
| tows_options | 12 TOWS slots |
| strategic_goals | Ba goal slots/candidates/active |
| bsc_objectives | Primary/supporting BSC objectives |
| bsc_edges | Causal graph |
| okr_cycles, okr_objectives, key_results | OKRs |
| twelve_week_cycles, weekly_plans, initiatives | Kế hoạch thực thi |
| tasks | Task canonical, được bổ sung strategy links |
| approvals, ai_runs, audit_events | Governance và observability |

### 7.2 DDL: Canvas, revision, foundation, context

~~~sql
create table strategy_canvases (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id),
  name text not null,
  description text,
  status text not null check (status in ('active','archived')),
  created_by uuid not null references users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table strategy_revisions (
  id uuid primary key,
  canvas_id uuid not null references strategy_canvases(id),
  revision_no integer not null,
  status text not null check (status in (
    'draft','in_review','approved','changes_requested','superseded','archived'
  )),
  parent_revision_id uuid references strategy_revisions(id),
  created_by uuid not null references users(id),
  approved_by uuid references users(id),
  approved_at timestamptz,
  stale_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (canvas_id, revision_no)
);

create unique index one_approved_revision_per_canvas
  on strategy_revisions(canvas_id)
  where status = 'approved';

create table strategy_foundations (
  id uuid primary key,
  strategy_revision_id uuid not null unique references strategy_revisions(id),
  vision text not null check (char_length(vision) between 20 and 500),
  mission text not null check (char_length(mission) between 20 and 500),
  status text not null check (status in ('draft','approved')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table core_values (
  id uuid primary key,
  foundation_id uuid not null references strategy_foundations(id) on delete cascade,
  slot_no smallint not null check (slot_no between 1 and 3),
  title text not null,
  description text not null,
  decision_rule text not null,
  unique (foundation_id, slot_no)
);

create table evidence_items (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id),
  vault_revision_id uuid,
  title text not null,
  summary text not null,
  source_type text not null,
  source_url_or_vault_uri text,
  published_at timestamptz,
  captured_at timestamptz not null default now(),
  reliability text not null check (reliability in ('high','medium','low')),
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid not null references users(id),
  created_at timestamptz not null default now()
);

create table project_context_packs (
  id uuid primary key,
  strategy_revision_id uuid not null references strategy_revisions(id),
  business_context jsonb not null,
  internal_resources jsonb not null,
  status text not null check (status in (
    'draft','ready_for_review','approved','stale','superseded'
  )),
  approved_by uuid references users(id),
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table context_pack_evidence (
  context_pack_id uuid not null references project_context_packs(id) on delete cascade,
  evidence_id uuid not null references evidence_items(id),
  primary key (context_pack_id, evidence_id)
);
~~~

### 7.3 DDL: PESTEL, SWOT và TOWS

~~~sql
create table pestel_findings (
  id uuid primary key,
  strategy_revision_id uuid not null references strategy_revisions(id),
  context_pack_id uuid not null references project_context_packs(id),
  factor text not null check (factor in (
    'political','economic','social','technological','environmental','legal'
  )),
  slot_no smallint not null check (slot_no between 1 and 3),
  statement text,
  direction text check (direction in ('opportunity','threat','mixed','unknown')),
  impact text check (impact in ('high','medium','low')),
  time_horizon text check (time_horizon in ('now','3_months','12_months','long_term')),
  confidence text check (confidence in ('high','medium','low')),
  assumptions jsonb not null default '[]'::jsonb,
  validation_task_hint text,
  slot_status text not null check (slot_status in (
    'empty','draft','verified','unverified','data_gap','rejected','approved'
  )),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (strategy_revision_id, factor, slot_no)
);

create table finding_evidence_links (
  finding_type text not null check (finding_type in ('pestel','swot')),
  finding_id uuid not null,
  evidence_id uuid not null references evidence_items(id),
  primary key (finding_type, finding_id, evidence_id)
);

create table swot_findings (
  id uuid primary key,
  strategy_revision_id uuid not null references strategy_revisions(id),
  group_type text not null check (group_type in (
    'strength','weakness','opportunity','threat'
  )),
  slot_no smallint not null check (slot_no between 1 and 3),
  statement text,
  impact text check (impact in ('high','medium','low')),
  confidence text check (confidence in ('high','medium','low')),
  assumptions jsonb not null default '[]'::jsonb,
  slot_status text not null check (slot_status in (
    'empty','draft','verified','unverified','data_gap','rejected','approved'
  )),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (strategy_revision_id, group_type, slot_no)
);

create table swot_origin_links (
  swot_finding_id uuid not null references swot_findings(id) on delete cascade,
  origin_type text not null check (origin_type in (
    'internal_resource','internal_metric','pestel_finding','external_evidence'
  )),
  origin_id uuid not null,
  primary key (swot_finding_id, origin_type, origin_id)
);

create table tows_options (
  id uuid primary key,
  strategy_revision_id uuid not null references strategy_revisions(id),
  tows_type text not null check (tows_type in ('SO','ST','WO','WT')),
  slot_no smallint not null check (slot_no between 1 and 3),
  title text,
  strategy_statement text,
  expected_outcome text,
  effort text check (effort in ('high','medium','low')),
  impact text check (impact in ('high','medium','low')),
  risk text check (risk in ('high','medium','low')),
  confidence text check (confidence in ('high','medium','low')),
  validation_needed boolean not null default false,
  slot_status text not null check (slot_status in (
    'empty','draft','verified','unverified','data_gap','rejected','approved'
  )),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (strategy_revision_id, tows_type, slot_no)
);

create table tows_swot_links (
  tows_option_id uuid not null references tows_options(id) on delete cascade,
  swot_finding_id uuid not null references swot_findings(id),
  primary key (tows_option_id, swot_finding_id)
);
~~~

### 7.4 DDL: Goals, BSC và Task link

~~~sql
create table strategic_goals (
  id uuid primary key,
  strategy_revision_id uuid not null references strategy_revisions(id),
  slot_no smallint not null check (slot_no between 1 and 3),
  title text not null,
  description text not null,
  primary_bsc_perspective text not null check (primary_bsc_perspective in (
    'financial','customer_market','internal_process','learning_growth'
  )),
  scores jsonb not null,
  assumptions jsonb not null default '[]'::jsonb,
  guardrails jsonb not null default '[]'::jsonb,
  activation_status text not null check (activation_status in (
    'candidate','active','parking_lot','rejected'
  )),
  approved_by uuid references users(id),
  approved_at timestamptz,
  unique (strategy_revision_id, slot_no)
);

create table strategic_goal_tows_links (
  strategic_goal_id uuid not null references strategic_goals(id) on delete cascade,
  tows_option_id uuid not null references tows_options(id),
  primary key (strategic_goal_id, tows_option_id)
);

create table bsc_objectives (
  id uuid primary key,
  strategy_revision_id uuid not null references strategy_revisions(id),
  strategic_goal_id uuid not null references strategic_goals(id),
  perspective text not null check (perspective in (
    'financial','customer_market','internal_process','learning_growth'
  )),
  title text not null,
  description text,
  objective_kind text not null check (objective_kind in ('primary','supporting')),
  status text not null check (status in ('draft','approved','stale','archived'))
);

create table bsc_edges (
  id uuid primary key,
  strategy_revision_id uuid not null references strategy_revisions(id),
  source_bsc_objective_id uuid not null references bsc_objectives(id),
  target_bsc_objective_id uuid not null references bsc_objectives(id),
  relationship text not null default 'enables',
  unique (source_bsc_objective_id, target_bsc_objective_id),
  check (source_bsc_objective_id <> target_bsc_objective_id)
);

alter table tasks
  add column strategy_revision_id uuid references strategy_revisions(id),
  add column strategic_goal_id uuid references strategic_goals(id),
  add column bsc_objective_id uuid references bsc_objectives(id),
  add column okr_objective_id uuid,
  add column key_result_id uuid,
  add column initiative_id uuid;
~~~

Khi tạo revision, service phải tạo skeleton trong cùng một transaction:

~~~text
6 PESTEL factors × 3 = 18 slots
4 SWOT groups × 3 = 12 slots
4 TOWS types × 3 = 12 slots
3 Strategic Goal slots
~~~

MVP dùng slot_no check + unique indexes + create_strategy_revision_skeleton transaction service + integration tests. Không dùng trigger database phức tạp chỉ để đếm ba.

---

## 8. API contract

Prefix chung: /v1/workspaces/{workspace_id}/strategy.

### 8.1 Canvas và revision

| Method | Endpoint | Mục đích |
|---|---|---|
| POST | /canvases | Tạo Canvas |
| GET | /canvases | Danh sách Canvas |
| GET | /canvases/{canvas_id} | Overview + active revision |
| POST | /canvases/{canvas_id}/revisions | Tạo draft và skeleton slots |
| GET | /revisions/{revision_id} | Revision detail |
| POST | /revisions/{revision_id}/submit-review | Gửi duyệt |
| POST | /revisions/{revision_id}/approve | Phê duyệt |
| POST | /revisions/{revision_id}/request-changes | Yêu cầu sửa |

### 8.2 Foundation, Context và Evidence

| Method | Endpoint | Mục đích |
|---|---|---|
| PUT | /revisions/{revision_id}/foundation | Lưu 1 Vision, 1 Mission, 3 Values |
| POST | /revisions/{revision_id}/foundation/ai-review | AI consistency review |
| POST | /revisions/{revision_id}/context-packs | Tạo Context Pack |
| PUT | /context-packs/{context_pack_id} | Sửa ba khối context |
| POST | /context-packs/{context_pack_id}/evidence | Link evidence selected |
| POST | /context-packs/{context_pack_id}/approve | Approve Context Pack |
| POST | /evidence | Tạo evidence/link Vault |
| GET | /evidence | Search/filter evidence |

### 8.3 Analysis và approval

| Method | Endpoint | Mục đích |
|---|---|---|
| POST | /analysis/pestel:generate | Queue PESTEL |
| POST | /analysis/swot:generate | Queue SWOT |
| POST | /analysis/tows:generate | Queue TOWS |
| POST | /analysis/goals:generate | Queue đúng 3 goal candidates |
| PATCH | /pestel/{finding_id} | Sửa một PESTEL slot |
| PATCH | /swot/{finding_id} | Sửa một SWOT slot |
| PATCH | /tows/{option_id} | Sửa một TOWS option |
| POST | /analysis/{type}/submit-review | Submit group |
| POST | /analysis/{type}/approve | Approve group |
| POST | /findings/{finding_id}/create-validation-task | Tạo task từ data_gap |

Body tạo AI job:

~~~json
{
  "strategy_revision_id": "uuid",
  "context_pack_id": "uuid",
  "mode": "preview | official",
  "idempotency_key": "uuid",
  "provider_profile": "deepseek_flash_default"
}
~~~

Official mode chỉ nhận Context Pack approved. Preview mode tạo output draft riêng, không được dùng tạo BSC/OKR/plan official.

### 8.4 BSC, OKR, 12 Week và Task

| Method | Endpoint | Mục đích |
|---|---|---|
| POST | /goals/{revision_id}/approve-set | Activate đúng ba goals |
| POST | /bsc:generate | Draft BSC từ goals approved |
| PUT | /bsc/objectives/{id} | Sửa BSC objective |
| POST | /bsc/edges | Tạo causal edge, validate DAG |
| POST | /okrs:generate | Draft Objective/KR |
| POST | /okr-cycles/{id}/approve | Activate OKR cycle |
| POST | /twelve-week-cycles:generate | Draft 12 Week plan |
| POST | /twelve-week-cycles/{id}/approve | Activate plan/initiatives |
| GET | /tasks/{task_id}/traceability | Chuỗi Task đến Evidence |

Response chỉ trả JSON đã chuẩn hóa. Không trả raw prompt, hidden reasoning hoặc chain-of-thought của model.

---

## 9. AI orchestration qua AI Router

### 9.1 Kiến trúc chạy job

AI Router nhận provider_profile, giữ credential, timeout, rate limit, retry, budget và observability. Service chiến lược không gọi SDK model trực tiếp.

~~~text
Flutter
→ Strategy API authorization
→ Strategy Service preflight validation
→ ai_runs + transactional outbox
→ agent-worker builds immutable Context Snapshot
→ AI Router / DeepSeek
→ Pydantic JSON validation
→ traceability + policy validators
→ persist draft transactionally
→ audit event + WebSocket/SSE update
~~~

### 9.2 Context Snapshot

Không gửi toàn bộ Vault cho model. Gửi snapshot immutable của revision được chọn:

~~~json
{
  "strategy_revision_id": "uuid",
  "foundation": {
    "vision": "...",
    "mission": "...",
    "core_values": [
      {"title": "...", "decision_rule": "..."},
      {"title": "...", "decision_rule": "..."},
      {"title": "...", "decision_rule": "..."}
    ]
  },
  "project_context": {
    "business_context": {},
    "internal_resources": {},
    "constraints": {}
  },
  "evidence": [
    {
      "id": "ev-001",
      "summary": "...",
      "published_at": "2026-08-01",
      "reliability": "high"
    }
  ],
  "upstream_analysis": [],
  "requested_stage": "pestel"
}
~~~

AI chỉ dùng evidence IDs trong snapshot. Thu thập web/source là workflow khác; phải ghi evidence và cho user chọn trước khi đưa vào Context Pack.

### 9.3 System contract

~~~text
Bạn là Strategy Drafting Assistant của Javis.
Chỉ suy luận từ Foundation, Project Context, upstream analysis và Evidence IDs được cung cấp.
Không bịa source, URL, số liệu hoặc sự kiện.
Nếu chưa đủ chứng cứ, trả slot_status là data_gap hoặc unverified.
Trả đúng JSON schema; không trả markdown hay văn bản ngoài JSON.
Mỗi nhận định cần evidence_ids, confidence và assumptions.
Không approve, không tạo recurring schedule, không thay đổi Task đang chạy.
Tôn trọng đúng ba slots cho stage hiện tại; không tạo mục thứ tư.
~~~

### 9.4 PESTEL output schema mẫu

~~~json
{
  "factor": "economic",
  "slots": [
    {
      "slot_no": 1,
      "statement": "Nhận định có thể kiểm tra",
      "direction": "opportunity",
      "impact": "high",
      "time_horizon": "12_months",
      "evidence_ids": ["ev-001"],
      "confidence": "medium",
      "assumptions": ["Giả định"],
      "slot_status": "draft",
      "validation_task_hint": null
    },
    {
      "slot_no": 2,
      "statement": null,
      "evidence_ids": [],
      "confidence": "low",
      "assumptions": ["Thiếu dữ liệu"],
      "slot_status": "data_gap",
      "validation_task_hint": "Thu thập dữ liệu ..."
    },
    {
      "slot_no": 3,
      "statement": "Nhận định cần xác minh",
      "evidence_ids": ["ev-002"],
      "confidence": "low",
      "assumptions": ["Giả định"],
      "slot_status": "unverified"
    }
  ]
}
~~~

### 9.5 Validators trước persist

1. Pydantic/JSON schema hợp lệ.
2. Chính xác ba slots, slot_no là 1, 2, 3.
3. Evidence IDs thuộc Context Pack snapshot.
4. Verified/approved không được thiếu evidence.
5. PESTEL semantic duplicate vượt ngưỡng đi vào review queue, không ghi đè.
6. SWOT Strength/Weakness có internal origin; Opportunity/Threat có PESTEL/external origin.
7. TOWS có tối thiểu hai SWOT links và đúng cặp SO/ST/WO/WT.
8. Goal generator trả đúng ba candidates.
9. Goal active count không vượt ba.
10. BSC graph là DAG.
11. Objective có tối đa ba KR; active initiative không vượt policy.

Validation failure đặt ai_run là validation_failed. Không publish analysis draft. UI hiện “AI output cần chạy lại”; raw output chỉ nằm trong debug store có quyền hạn.

### 9.6 Idempotency, retry và cost

- Mỗi AI job có idempotency key, snapshot content hash, stage và provider profile.
- Cùng key/hash/stage completed thì trả result cũ, không tạo finding/task mới.
- Retry exponential tối đa ba lần với network/rate limit.
- Không retry JSON/policy failure bằng cùng prompt.
- Lưu prompt_version, provider_profile, token usage nếu provider trả về, latency, cost estimate, status và error category.
- Không lưu hidden reasoning; chỉ lưu decision summary, evidence IDs, assumptions và validation result.

---

## 10. Task, workflow, stale handling

### 10.1 Task integration

Task từ kế hoạch phải có strategy_revision_id, strategic_goal_id, bsc_objective_id, okr_objective_id, key_result_id và initiative_id khi dữ liệu tồn tại.

Task tạo từ data_gap:

- status khởi tạo: inbox hoặc planned;
- task_type: validation;
- title do AI gợi ý, người dùng sửa được;
- link ngược về PESTEL/SWOT/TOWS finding;
- hoàn thành task không tự tăng confidence hoặc approve finding;
- task tạo evidence candidate, Founder review trước khi link evidence.

### 10.2 Schedule và workflow

~~~text
Schedule hoặc Run now
→ workflow_run
→ idempotency + dedupe
→ task/analysis job
→ draft result
→ approval nếu có tác động
→ external outbox nếu được approve
~~~

Flutter không gọi model/connector trực tiếp. workflow_run có scheduled_for, started_at, finished_at, status, idempotency_key, correlation_id.

### 10.3 Stale detection

| Upstream change | Mark stale | Cấm |
|---|---|---|
| Foundation/Context | PESTEL trở xuống | Không auto run lại |
| PESTEL | SWOT/TOWS/Goals/BSC/OKR | Không auto hủy plan |
| SWOT/TOWS | Goals/BSC/OKR | Không auto sửa active goal |
| Goals/BSC | OKR/12 Week plan | Không auto sửa Task |

Stale detection chỉ tạo notification và review task. Founder chọn Create new revision, Keep current plan until cycle end, hoặc Review now.

### 10.4 Transaction boundaries

- Create revision + skeleton slots: một transaction.
- Persist kết quả AI stage: một transaction sau khi mọi validator pass.
- Approve ba goals commit trước; BSC generator queue bằng transactional outbox sau.
- Tạo task từ 12-week approval theo batch idempotent.
- Audit event ghi cùng transaction với domain change.

---

## 11. Realtime, offline, Vault và audit

- Flutter nhận job/approval/task updates qua WebSocket hoặc SSE.
- SQLite Flutter là offline cache/outbox, không phải source of truth.
- Request offline chứa client generated idempotency key; server resolve bằng revision và update timestamp.
- Evidence, decision record, export strategy report lưu S3/MinIO Vault theo revision. PostgreSQL lưu metadata/relations/index.
- Vault content sau khi được link không chỉnh evidence cũ tại chỗ. Content update tạo Vault revision mới, được dùng cho strategy revision mới.

Vault layout:

~~~text
vault/
  strategy/
    {workspace_slug}/
      {canvas_slug}/
        revisions/
          r001/
            foundation.md
            context-pack.md
            pestel.md
            swot.md
            tows.md
            goals.md
            bsc-map.md
            okr.md
            12-week-plan.md
~~~

Capability tối thiểu:

~~~text
strategy.read
strategy.edit_draft
strategy.submit_review
strategy.approve
strategy.generate_ai
strategy.link_evidence
strategy.manage_bsc
okr.manage
planning.manage
task.manage
workflow.schedule
external_action.approve
~~~

Audit payload tối thiểu:

~~~json
{
  "event_type": "strategy.goal_set_approved",
  "workspace_id": "uuid",
  "actor_type": "user | ai | system",
  "actor_id": "uuid",
  "entity_type": "strategic_goal_set",
  "entity_id": "uuid",
  "strategy_revision_id": "uuid",
  "before": {},
  "after": {},
  "correlation_id": "uuid",
  "created_at": "2026-08-09T..."
}
~~~

Không log credential, raw sensitive docs, raw prompt hoặc hidden model reasoning vào audit.

---

## 12. Kiểm thử và tiêu chí nghiệm thu

### 12.1 Unit tests

- Foundation validator từ chối không đúng ba Core Values.
- Skeleton service tạo đúng 18 PESTEL, 12 SWOT, 12 TOWS và 3 Goal slots.
- Finding verified/approved bị từ chối nếu không có evidence.
- Strength/Weakness bị từ chối nếu chỉ có external evidence.
- Opportunity/Threat bị từ chối nếu không có PESTEL/external origin.
- TOWS option sai tổ hợp bị từ chối.
- Goal active thứ tư bị từ chối.
- KR thứ tư trong Objective bị từ chối.
- BSC edge tạo cycle bị từ chối.
- Initiative active thứ tư bị từ chối theo default workspace policy.

### 12.2 Integration tests

1. Founder tạo Canvas revision; skeleton slots được tạo trong một transaction.
2. Foundation/Context Pack approve thành công; AI job official được phép queue.
3. AI PESTEL trả slot No. 2 là data_gap; database và UI giữ data_gap có CTA validation task.
4. Evidence được thêm sau đó không làm mutate revision cũ; user phải tạo/approve revision mới.
5. PESTEL, SWOT, TOWS approved tạo đúng ba goal candidates.
6. Admin không có strategy.approve nhận HTTP 403 khi approve goals.
7. Founder approve ba goals thì BSC job mới được queue.
8. Task từ initiative trả traceability chain đầy đủ đến evidence.
9. Workflow chạy lại cùng idempotency key không tạo workflow_run/task trùng.
10. PESTEL revision mới làm downstream stale nhưng không thay đổi task active.

### 12.3 E2E và UI acceptance

- Desktop/mobile luôn thấy ba slots của cùng group.
- Data gap phân biệt rõ với unverified/rejected.
- User không có quyền không thể invoke approval API và không thấy CTA misleading.
- Goal Board không thể active sai số lượng ba.
- List, Calendar, Kanban thay đổi cùng một task/status.
- Traceability Drawer đi ngược ít nhất đến Strategic Goal; với full links đi đến Evidence.
- AI job có state queued/running/completed/failed, không khóa ứng dụng.
- Accessibility: keyboard focus, status text, contrast và loading state đầy đủ.

---

## 13. Lộ trình triển khai

### Phase 0 — Chuẩn bị

1. Audit schema hiện có: workspace, roles/capabilities, tasks, approvals, audit, workflow runs.
2. Không thay thế schema cũ bằng destructive migration.
3. Tạo migrations an toàn, module boundaries, test fixtures.
4. Bổ sung feature flag strategy_canvas_113.

**Hoàn tất khi:** migration chạy trên database trống và dev database; task/approval hiện có không lỗi.

### Phase 1 — Foundation và Context

1. Canvas, revision, foundation, core_values, evidence, context tables.
2. Skeleton service và API.
3. Flutter Overview, Foundation, Context Builder.
4. Approval/audit Foundation và Context.

**Hoàn tất khi:** Founder tạo 1–1–3 Foundation, Context Pack, evidence selection và revision history.

### Phase 2 — Analyses

1. PESTEL/SWOT/TOWS tables, link tables, validators.
2. AI Router contract, agent worker jobs, idempotency.
3. PESTEL Matrix, SWOT Matrix, TOWS Board.
4. Validation task từ data_gap.

**Hoàn tất khi:** AI chỉ publish draft valid, có evidence chain, thiếu dữ liệu thì tạo data_gap.

### Phase 3 — Goal đến thực thi

1. Goal scoring, board, activate exactly three.
2. BSC graph/DAG validation và UI.
3. OKR/KR limits.
4. 12-week planning, initiative limits, task traceability.

**Hoàn tất khi:** task truy vết đến strategy và only approved plan mới active.

### Phase 4 — Operational hardening

1. Transactional outbox, scheduler, dedupe, retries.
2. Realtime jobs/approvals.
3. Stale detection/review queue.
4. Offline cache/conflicts, export Vault report, E2E/accessibility.

**Hoàn tất khi:** workflow lặp không tạo trùng; revision stale không phá plan đang chạy.

---

## 14. Prompt giao việc cho Claude Code

### Prompt A — Phase 1

~~~text
Đọc toàn bộ file STRATEGIC_CANVAS_1_1_3_CLAUDE_CODE_SPEC.md trước khi sửa code.
Triển khai riêng Phase 1 cho Javis hiện có: Canvas, immutable revision, Foundation 1–1–3, Context Pack, Evidence selection, approval và audit.
Giữ kiến trúc Flutter + FastAPI + PostgreSQL hiện tại. Không thêm database hay queue framework mới.
Task hiện có không được phá vỡ. Dùng migration an toàn, service/repository tách biệt, Pydantic schemas và tests.
Tạo đúng ba Core Value slots, không cho tạo value thứ tư. Chỉ Founder/capability strategy.approve được approve.
Khi hoàn tất, chạy test, lint và format hiện có; báo cáo file sửa, migration, endpoint, test result và phần còn lại của Phase 2.
Không triển khai Phase 2–4.
~~~

### Prompt B — Phase 2

~~~text
Đọc đặc tả Strategic Canvas 1–1–3 và kiểm tra Phase 1 trước khi sửa code.
Triển khai riêng Phase 2: PESTEL 6×3, SWOT 4×3, TOWS 4×3; AI drafts qua AI Router/agent-worker; Pydantic và traceability validators; Flutter Matrix/Board; Create Validation Task.
Không gọi model trực tiếp từ API handler hoặc Flutter. AI không được approve. Không tự điền dữ liệu để đủ ba slots: dùng data_gap.
Mỗi output phải link evidence IDs thuộc Context Pack. Viết integration tests cho SWOT origins, TOWS pairing, slot invariant và idempotency.
Không triển khai Goals/BSC/OKR/12 Week.
~~~

### Prompt C — Phase 3

~~~text
Đọc đặc tả Strategic Canvas 1–1–3 và kiểm tra implementation Phase 1–2.
Triển khai Phase 3: đúng ba Strategic Goals, Goal Approval Board, BSC Strategy Map dạng DAG, OKR tối đa ba KR/Objective, 12 Week Cycle, tối đa ba active initiatives và task traceability.
Task vẫn canonical; List/Calendar/Kanban chỉ dùng task hiện có. Không tự chuyển schedule thành external action.
Thêm migrations tương thích, API, Flutter UI, unit/integration/E2E tests; chạy test/lint/format rồi báo cáo kết quả và migration cần áp dụng.
Không tự thay đổi Task/OKR active khi có strategy revision mới.
~~~

### Prompt D — Phase 4

~~~text
Đọc đặc tả Strategic Canvas 1–1–3 và kiểm tra implementation Phase 1–3.
Triển khai Phase 4: transactional outbox, schedule/retry/dedupe, realtime updates, stale review queue, Flutter offline cache conflict handling, Vault export và E2E/accessibility.
Scheduler chỉ tạo workflow runs idempotent. External actions không được thực thi nếu chưa qua approval/outbox policy.
Không thay đổi business rules, schema và existing task behavior ngoài phạm vi đặc tả. Chạy toàn bộ test/lint/format hiện có và báo cáo rõ ràng bất kỳ migration hay feature flag nào cần bật.
~~~

---

## 15. Definition of Done

Strategic Canvas 1–1–3 hoàn tất khi:

1. Founder đi từ 1 Vision, 1 Mission, 3 Core Values đến 12 Week Plan và Task.
2. PESTEL/SWOT/TOWS luôn có ba slots nhưng data_gap được giữ trung thực.
3. Mọi AI draft có evidence, confidence, assumptions, prompt version, validation state; không có fabricated source.
4. Không có strategy, goal, OKR, recurring schedule hoặc external action nào active nếu thiếu approval hợp lệ.
5. Có đúng ba active Strategic Goals; task chiến lược truy vết được đến Goal, và khi đầy đủ đến Evidence.
6. List, Calendar, Kanban là ba view của cùng Task.
7. Revision, stale, retry và task generation idempotent, có audit và không phá kế hoạch đang thực hiện.

Kết quả mà Javis phải đem lại mỗi ngày: founder nhìn thấy ba việc ưu tiên, biết chúng đang làm tiến độ cho mục tiêu nào, và hiểu mục tiêu đó bắt nguồn từ bằng chứng/chiến lược nào.
