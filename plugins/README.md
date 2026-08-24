# Plugins Directory

Thư mục chứa các deployable plugins mở rộng.

## Cấu trúc Plugin chuẩn:
```text
plugins/
  <plugin-name>/
    manifest.yaml      # Metadata, version, permissions, dependencies
    skills/            # Domain skills
    tools/             # Typed tools / MCP definitions
    resources/         # Prompts, schemas, templates
    ui/                # UI widgets / views (optional)
```

> Tham chiếu gốc "AI Agent OS Master Architecture §7, §8" đã lỗi thời (tài liệu không còn trong repo). Xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần A (mục A13) và `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §11 (Plugin architecture, trust tiers, lifecycle `DISCOVERED→...→RETIRED`) — `packages/agent_core/plugins/manifest.py` đọc/validate manifest từ thư mục này.
