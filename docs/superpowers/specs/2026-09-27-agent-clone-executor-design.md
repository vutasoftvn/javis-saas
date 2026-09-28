# C1 — Executor CLONE/PUBLISH cho AGENT (thiết kế)

Ngày: 2026-09-28 · Plan nguồn: `docs/superpowers/plans/2026-09-27-hub-operations-phase2-phase3.md` mục C1.
Founder đã gỡ lệnh cấm "không code trực tiếp" của C1 (2026-09-27); spec này viết trước rồi triển khai luôn.
Quy tắc 13 vẫn giữ nguyên: **không** mở API/UI sửa agent built-in. Agent của founder luôn là một *bản clone
bị ràng buộc* của một agent built-in, không phải agent tự do.

## 0. Hiện trạng (đã có trước spec này)

| Mảng | Đã có | Chỗ hở |
|---|---|---|
| Lệnh (company) | `commandFounderAsset` ghi `founder_asset_events` + outbox `founder.asset.commanded.v1`; `handleAssetStatusCallback`; `getFounderAssetEvents` | callback PUBLISH của AGENT không mang gì ngoài `assetRef` → company không biết agent gốc/capability |
| Consumer (apps/cosa) | `dispatch_founder_asset_command` → `AuthoringService` (`clone/edit/evaluate/publish`) + callback outbox bền | clone AGENT từ built-in dùng hash giả `sha256:placeholder`, asset id cố định `clone.<id>` (clone lần 2 đụng khoá) |
| Evaluation | chỉ structural (secret/shell), sandbox không capability | không chặn leo thang quyền, không giới hạn nội dung |
| Deploy (company) | `createWorkspaceAgent` nhận pin bất kỳ; `deployAgentToProject`; `getProjectDeploymentAuthority` | không đòi biên nhận publish; không cấp grant cho agent custom |
| Runtime (worker) | chạy built-in qua `AGENT_PROFILE_SPECS[agent_profile]` + `SpecResolver` exact-hash | agent workspace đã PUBLISHED không chạy được |

## 1. Nơi lưu draft

Tái dùng repo workspace asset sẵn có (`agent.workspace_assets` + `agent.workspace_asset_versions`,
`PostgresWorkspaceAssetRepository`). **Không migration mới.** `content_json` của asset AGENT là một
*override manifest* (schema `workspace_agent.v1`), không phải bản sao spec đầy đủ:

```json
{
  "schema": "workspace_agent.v1",
  "origin": {"profile_key": "operations", "spec_id": "cosa.agents.operations",
             "version": "1.9.0", "definition_hash": "<hash spec gốc>"},
  "name": "Trợ lý vận hành Sao Mai",
  "description": "…",
  "instructions_addendum": "…",
  "capability_refs": ["operations.task.list", "…"]
}
```

Vì manifest chỉ chứa các trường được phép tuỳ biến, model policy / autonomy (tier) / prompt_ref /
pinned_skills **không thể** bị đổi: chúng luôn lấy từ spec gốc đã pin. Khoá lạ trong manifest → evaluation FAIL.

## 2. Lineage

- Lệnh CLONE với `assetKind=AGENT` và `assetRef.assetId` là **id spec built-in** (`cosa.agents.<profile>`)
  → consumer pin spec gốc: nếu lệnh mang `version`+`definitionHash` thì phải khớp tuyệt đối (spec đang
  import hoặc bản bất biến trong spec registry); không mang thì pin bản built-in hiện hành. Không còn
  hash giả.
- Chỉ clone được profile vận hành của Project startup team có spec (`PROJECT_TEAM_OPERATING_PROFILES`),
  trừ `customer_support` (nhánh copilot + knowledge gate riêng) và `founder_assistant`.
- Asset id tất định theo lệnh: `custom.<profile>.<commandId>`, version `0.1.0`. Lặp lại cùng lệnh → trả
  lại draft đã có (idempotent), clone lần hai của cùng built-in không đụng khoá.
- Lineage ghi ở **hai nơi**: `workspace_assets.origin_*` + `origin_json` (bất biến sau khi tạo, repo
  không cập nhật khi upsert) và `content.origin`. Evaluation đòi hai nơi khớp nhau → EDIT_DRAFT không
  thể đổi agent gốc.
- Scope: AGENT clone mặc định `WORKSPACE` (agent là tài sản workspace, vào Project qua
  `deployAgentToProject`). `metadata.scope = "PROJECT_SANDBOX"` (cần `projectId`) cho agent chỉ-hướng-dẫn;
  luật sandbox cũ vẫn áp dụng (không capability_refs).

## 3. Ai validate/evaluate

Consumer event `founder.asset.commanded.v1` (process events của apps/cosa), **đồng bộ trong lần xử lý
lệnh EVALUATE**; kết quả đi qua callback outbox bền về company. Luật cho kind AGENT
(`apps/cosa/assets/workspace_agent.py::evaluate_workspace_agent_content`), mỗi luật có mã:

| Mã | Luật |
|---|---|
| `AGENT_MANIFEST_INVALID` | sai schema / có khoá lạ (model_policy, autonomy_level, instructions, …) |
| `AGENT_ORIGIN_REQUIRED` | asset AGENT không có lineage built-in (tạo từ đầu bằng CREATE) |
| `AGENT_ORIGIN_MISMATCH` | `content.origin` khác lineage bất biến của asset |
| `AGENT_ORIGIN_UNAVAILABLE` | agent gốc không còn là built-in clone được, hoặc không resolve được đúng version+hash |
| `AGENT_CAPABILITY_ESCALATION` | `capability_refs` ⊄ `capability_refs` của spec gốc đã pin |
| `AGENT_NAME_INVALID` | tên rỗng hoặc > 80 ký tự |
| `AGENT_DESCRIPTION_TOO_LONG` | mô tả > 500 ký tự |
| `AGENT_ADDENDUM_TOO_LONG` | addendum > 4000 ký tự |
| `AGENT_SECRET_DETECTED` | chuỗi giống secret (cùng pattern company `founder-asset-authoring.service.ts`) |

FAIL → callback `REJECTED` với `safeReasonCode` = mã đầu tiên. PASS → `REVIEW_REQUIRED`.

## 4. Điều kiện publish

Giữ nguyên cơ chế hiện có và siết thêm: PUBLISH phải mang `assetRef` chính xác (id, version,
definitionHash); evaluation mới nhất của **đúng version** phải PASS **và cùng definitionHash**; version
đã PUBLISHED bất biến (repo từ chối sửa nội dung ngoài DRAFT/CANDIDATE). Callback PUBLISH của AGENT mang
thêm `agentManifest` (nguồn tin cậy vì do worker ký service token):

```json
{"originProfileKey": "operations",
 "originSpec": {"id": "cosa.agents.operations", "version": "1.9.0", "definitionHash": "…"},
 "capabilityRefs": ["…"], "displayName": "…"}
```

Company lưu vào metadata của sự kiện PUBLISH (`metadata.agentManifest`) — đây là **biên nhận publish**.

## 5. Company: workspace agent, grant, compliance

- `createWorkspaceAgent({originKind: "WORKSPACE_CLONE", agentAssetId, agentAssetVersion,
  agentDefinitionHash})` **bắt buộc** có biên nhận PUBLISH SUCCESS khớp tuyệt đối (như
  `bindWorkflowToProject`). Nếu pin trùng một biên nhận AGENT thì luôn bị coi là `WORKSPACE_CLONE`
  (không lách bằng originKind khác). `workforceMemberId` cho clone do server tạo: một AI member riêng
  cho (asset, version) qua `ensureAiWorkforceMemberForAsset` — grant của agent gốc **không** dùng chung.
- `deployAgentToProject` cho workspace agent `WORKSPACE_CLONE`: cấp grant scope Project =
  `AGENT_PROFILE_GRANTED_CAPABILITIES[originProfileKey] ∩ agentManifest.capabilityRefs`
  (`ensureProfileCapabilityGrants` + `capabilityFilter`), gán role `startup_team_agent` như agent gốc.
  Tạm dừng (`pauseProjectDeployment`) thu hồi đúng các grant đó.
- Compliance: run của agent custom đánh giá bằng **spec gốc** (`apply_compliance(compliance_spec=…)` —
  cơ chế sẵn có của advisor overlay), nên dùng lại đúng binding catalog AI system của agent gốc
  (`system_key = cosa.agents.<profile>`). Không cần system version mới.

## 6. Runtime resolve (worker)

Đường phase-1 là `agent_profile` của conversation + run-authority startup team. Mở rộng: request chat
mang thêm `project_agent_deployment_id` (tuỳ chọn) → payload run. Worker **không tin** tham chiếu này:

1. Gọi company `GET /internal/operations/projects/:projectId/agent-deployments/:id/deployment-authority`
   (`CompanyServiceClient.get_project_agent_deployment_authority`); đòi `state == ACTIVE`, đúng
   workspace + project.
2. Pin `agentSpec {id, version, definitionHash}` từ company → load asset
   `get_version(workspace, id, version)`: phải là AGENT, `PUBLISHED`, `definition_hash` khớp tuyệt đối.
   Không bao giờ "latest". RETIRED/không PUBLISHED/lệch hash → `run.failed` với mã rõ
   (`workspace_agent_not_published`, `workspace_agent_hash_mismatch`, …).
3. Chạy lại toàn bộ luật evaluation trên manifest (phòng dữ liệu hỏng) rồi resolve spec gốc đúng
   version+hash (spec đang import hoặc registry bất biến — như `_spec_for_authority`).
4. Dựng `AgentSpec` hiệu lực = spec gốc + override: `id = workspace.<ws>.<assetId>`,
   `version = asset version`, `instructions = gốc + "\n\n" + addendum`, `capability_refs` thu hẹp,
   `tool_contract_refs` lọc theo capability còn lại, `metadata` ghi lineage + tên hiển thị +
   `origin_agent_spec_id`. Model route tra theo `origin_agent_spec_id` (không đổi model policy);
   compliance theo spec gốc; `agent_profile` của run = profile gốc (bỏ giá trị client gửi).
5. `agent_workforce_member_id` = AI member của workspace agent (từ deployment authority) → live
   authorization ticket chỉ qua được grant đã thu hẹp. REQUIRE_APPROVAL cho T2 trong chat giữ nguyên
   (theo capability, không theo agent).

Agent custom vì vậy **không bao giờ ít kiểm soát hơn** agent gốc: tập tool ⊆ gốc, grant ⊆ gốc,
tier/approval/compliance theo capability và spec gốc.

## 7. Ngoài phạm vi / còn lại

- UI Flutter (C2). Sửa agent đã publish = clone mới (chưa có "version mới của cùng asset").
- Lệnh `RETIRE` asset chưa có executor; dừng agent dùng `pauseProjectDeployment`/retire workspace agent
  ở company (runtime đã fail-closed với deployment không ACTIVE).
- Lịch (schedule): control-plane snapshot chưa mang `project_agent_deployment_id`; worker đã nhận field
  này nếu payload có.
