# PART 0 — Reconcile và sẵn sàng governance

**Ngày:** 2026-08-28
**Phần của:** [marketingskills-makerskills-program](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §5
**Nhánh đề xuất:** `msmk/part0-reconcile-governance`
**Phụ thuộc:** không

## Context

Trước khi adapt bất kỳ skill nào, phải khoá lại nền governance đang lệch:

- `docs/development/add-skill.md:17` hướng dẫn `skill.yaml` tại `packages/agent_core/skills/library/<id>/`,
  trong khi validator `packages/agent_core/skills/skillpack_contract.py`, `docs/features/skills.md:30`
  và cả 16 pack thực tế dùng `manifest.yaml` + `SKILL.md` tại `skillpacks/<domain>/<id>/`.
  Contributor theo doc cũ sẽ tạo pack sai contract.
- Chưa có ledger nguồn/giấy phép cho việc adapt từ kho ngoài.
- Chưa chốt taxonomy evidence/provenance dùng chung cho 18 pack + Part CTX + Part SEARCH.
- Cần bảo đảm `scripts/validate_skillpacks.py` + `tests/agent_core/skills/test_skillpack_contract.py`
  thực sự chạy trong CI trước khi 18 pack đổ vào.

Part 0 **không đổi hành vi runtime**. Deliverable chính: một inventory 18 hạng mục (map 1:1 với
18 pack ở §4 program), mỗi hạng mục có `status ∈ {pending, adapted, published, pinned}`.

## Danh sách file + thay đổi

### 0.1 Chốt một contract skillpack duy nhất

| File | Thay đổi |
| --- | --- |
| `docs/development/add-skill.md` | Bỏ mục "Viết `SKILL.md` + `skill.yaml`" và đường dẫn `packages/agent_core/skills/library/<id>/`. Thay bằng: nguồn tại `skillpacks/<domain>/<skill-id>/{manifest.yaml,SKILL.md}`, `runtime.entrypoint: SKILL.md`, frontmatter `name = normalize_discovery_name(metadata.id)`. Giữ nguyên phần vòng đời `Draft→Candidate→Evaluated→Published` và `publish_skill_spec()`. |
| `docs/features/skills.md` | §16 checkbox "manifest.yaml chưa bổ sung field liên kết registry": ghi rõ quyết định **không** thêm field đó (tránh floating ref); publish là bước tách rời qua `publish_skill_spec()`. §3 "3 tầng skill infra": xác nhận `skillpacks/` = tầng 1 (source-only). |

### 0.2 Test harness + validator trong CI

| File | Thay đổi |
| --- | --- |
| `.github/workflows/quality.yml` | Xác nhận (thêm nếu thiếu) bước chạy `python scripts/validate_skillpacks.py` và `python -m pytest tests/agent_core/skills/test_skillpack_contract.py`. Fail job nếu một trong hai đỏ. |
| `scripts/validate_skillpacks.py` (hoặc `packages/agent_core/skills/skillpack_contract.py`) | Thêm rule **fail**: nếu `manifest.runtime.tools` chứa ID không nằm trong tập capability đã đăng ký ở `build_cosa_agent_plane()`. Tập ID lấy tĩnh từ các SPEC constant trong `apps/cosa/capabilities/*.py` (`OPERATIONS_TASK_LIST_SPEC.id`, …) — đọc bằng import tĩnh, không khởi tạo plane. Cho phép whitelist tạm (`web.search`) qua hằng `KNOWN_PENDING_CAPABILITIES` có comment ngày gỡ. |
| `tests/agent_core/skills/test_skillpack_contract.py` | Thêm case cho rule trên (pack khai tool chưa đăng ký → violation; pack khai tool trong whitelist → chỉ cảnh báo/không violation). Cập nhật `test_repaired_skillpack_contracts` để chấp nhận số pack sẽ tăng lên 34 sau Part A (16 cũ + 18), và assert đúng nhóm domain (`marketing`, `strategy`, `commercial`, `sales`, `research`, `finance`, `platform`, `operations`, `core`, `okr`, `tasks`, `twelve-week-year`). |

### 0.3 Source-attribution ledger (inventory 18 hạng mục)

| File | Thay đổi |
| --- | --- |
| `docs/integrations/skill-source-attribution.md` (mới) | Bảng cột: `cosa_skill_id \| nhóm(A/B/C) \| upstream_repo \| commit_sha \| upstream_skill(s) \| upstream_version \| license \| status \| last_reviewed \| notes`. 18 dòng khởi tạo `status=pending`, `commit_sha` = SHA snapshot trong adoption-plan (`b1aaa36…` marketingskills, `33cb387…` makerskills). Mục "Quy tắc": không submodule, không background auto-update, nâng version upstream là thủ công có review; khi sao chép đáng kể phải kèm MIT notice + URL + SHA. |

Mẫu review record (dán vào cuối mỗi `SKILL.md` ở Part A, section `## Nguồn`):

```yaml
upstream:
  repository: coreyhaines31/marketingskills   # hoặc makerskills
  commit: <40-char SHA>
  skill: <tên skill nguồn>
  upstream_version: <metadata.version>
  license: MIT
adaptation:
  kept: [nguyên tắc/template giữ nguyên]
  changed: [path, tool, terminology, data model đã đổi]
  added: [governance, workspace, approval, audit]
  excluded: [tool/provider/side effect không nhận]
```

### 0.4 Chốt taxonomy evidence/provenance

| File | Thay đổi |
| --- | --- |
| `docs/features/marketing-evidence-taxonomy.md` (mới) | Định nghĩa trường: `source_url`, `captured_at`, `captured_by`, `workspace_id`, `confidence` (`low\|medium\|high`), `trust` (`unreviewed\|verified\|deprecated\|superseded`), `sensitivity` (`public\|internal\|confidential`), `review_status`, `supersedes`, `evidence_id`. Bảng ánh xạ sang `KnowledgeDocument.authority_class` (`packages/agent_core/knowledge/models.py:38-50`) + `ingest_status`. Ghi rõ: taxonomy này **bổ sung** metadata, không thay `authority_class`. Part CTX (`marketing_context_evidence`) và Part SEARCH (payload provenance) đều dùng đúng tên trường này. |

## Test

- `python scripts/validate_skillpacks.py` — 0 violation trên 16 pack hiện có; rule tool-chưa-đăng-ký
  bắt đúng khi cố tình thêm 1 tool giả vào 1 manifest (revert sau).
- `python -m pytest tests/agent_core/skills/test_skillpack_contract.py -q` — xanh, gồm case mới.
- Không có test runtime nào đổi kết quả (Part 0 không chạm plane).

## Verify

```text
python -m pytest tests/agent_core/skills/test_skillpack_contract.py -q
python scripts/validate_skillpacks.py
# mở PR giả có 1 manifest thêm tool "foo.bar" chưa đăng ký ⇒ CI quality.yml phải đỏ
```

## Definition of Done

- [ ] `docs/development/add-skill.md` không còn nhắc `skill.yaml` / `skills/library/`; mô tả đúng
      contract `manifest.yaml`+`SKILL.md` tại `skillpacks/<domain>/<id>/`.
- [ ] `docs/features/skills.md` ghi rõ không thêm field liên kết registry vào manifest.
- [ ] `.github/workflows/quality.yml` chạy validator + contract test, fail-closed.
- [ ] Validator có rule fail cho tool chưa đăng ký (trừ whitelist `web.search` có ngày gỡ).
- [ ] `docs/integrations/skill-source-attribution.md` tồn tại, 18 dòng `status=pending`, có SHA snapshot.
- [ ] `docs/features/marketing-evidence-taxonomy.md` tồn tại, có bảng ánh xạ `authority_class`.
- [ ] Không có SkillSpec nào được publish; `build_cosa_agent_plane()` vẫn đúng 5 capability;
      `tests/apps/cosa/test_agent_plane_skillpack_boundary.py` xanh.
