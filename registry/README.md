# Skill Registry Storage

Thư mục lưu trữ immutable skill packages và artifacts của Supply Chain theo chuẩn AI Agent OS Master Architecture (§20, §23).

## Cấu trúc:
```text
registry/
  packages/           # Immutable tarball / zip / artifacts của verified skills
  state/              # State store của Registry (manifest index, trust tiers, approval logs)
```
