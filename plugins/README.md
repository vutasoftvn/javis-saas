# Plugins Directory

Thư mục chứa các deployable plugins mở rộng theo chuẩn AI Agent OS Master Architecture (§7, §8).

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
