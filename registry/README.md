# Skill Registry Storage

Thư mục lưu trữ immutable skill packages và artifacts của Supply Chain.

## Cấu trúc:
```text
registry/
  packages/           # Immutable tarball / zip / artifacts của verified skills
  state/              # State store của Registry (manifest index, trust tiers, approval logs)
```

> Tham chiếu gốc "AI Agent OS Master Architecture §20, §23" đã lỗi thời (tài liệu không còn trong repo). Xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần A (mục A12) và Phần G — thư mục này là storage backend (artifact) cho `packages/agent/registry/` (Wave 3, module Python) và bổ sung cho bảng DB `agent_registry.published_specs` (metadata/version pin), không trùng nhau: DB lưu metadata, thư mục này lưu artifact thật.
