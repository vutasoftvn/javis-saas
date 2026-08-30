"""Bootstrap các skillpack built-in vào registry trước khi agent khởi động.

Fail-closed: bất kỳ lỗi nào (thiếu bundle root, vi phạm contract, parse lỗi,
publish lỗi) đều raise `BuiltinSkillpackSeedError` ngay lập tức — không log-và-
bỏ-qua một pack, không để lại trạng thái khởi tạo dở dang (Wave M2b Global
Constraints: "Built-in startup fails closed for missing source, contract
violation, parse failure, or pin/hash mismatch").

Đây là file `apps/cosa/` (composition layer), KHÔNG phải `packages/agent/` —
vì `resolve_skillpacks_root`/`BuiltinSkillpackSeedError` gắn với đường dẫn
triển khai thật của COSA (`COSA_SKILLPACKS_ROOT`, `/app/skillpacks`), giữ
`packages/agent` generic đúng ranh giới 4 vùng kiến trúc trong CLAUDE.md.
"""

from __future__ import annotations

import os
from pathlib import Path

from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import SpecRegistryRepository
from agent.registry.publisher import publish_skill_spec
from agent.skills.skillpack_contract import validate_skillpack_tree

__all__ = [
    "BuiltinSkillpackSeedError",
    "resolve_skillpacks_root",
    "seed_builtin_skillpacks",
]


class BuiltinSkillpackSeedError(RuntimeError):
    """Raise khi bundle skillpack built-in không thể nạp an toàn — bất kỳ
    entrypoint thật nào (api/app.py, worker/main.py) phải để lỗi này làm
    startup fail-closed, không catch rồi chạy tiếp với AgentSpec dở dang."""


def resolve_skillpacks_root(root: Path | None = None) -> Path:
    """Xác định thư mục gốc chứa skillpack built-in.

    Ưu tiên `root` truyền vào (dùng cho test), sau đó biến môi trường
    `COSA_SKILLPACKS_ROOT`, mặc định `/app/skillpacks` (đường dẫn trong image
    production). Raise ngay nếu thư mục không tồn tại — không âm thầm seed
    rỗng."""
    candidate = root or Path(os.environ.get("COSA_SKILLPACKS_ROOT", "/app/skillpacks"))
    if not candidate.is_dir():
        raise BuiltinSkillpackSeedError(f"Built-in skillpacks are unavailable at {candidate}")
    return candidate.resolve()


async def seed_builtin_skillpacks(
    spec_registry: SpecRegistryRepository,
    *,
    capability_ids: set[str],
    skillpacks_root: Path | None = None,
) -> tuple[PublishedSpecRecord, ...]:
    """Validate toàn bộ cây skillpack rồi publish từng manifest theo thứ tự
    sắp xếp (deterministic). Bất kỳ violation hay lỗi parse/publish nào cũng
    raise `BuiltinSkillpackSeedError` ngay, không publish một phần.

    `parse_skillpack_spec` được import lazy (trong hàm, không ở module scope)
    để tránh circular import: `apps/cosa/api/__init__.py` -> `app.py` import
    `apps.cosa.agents.seed` ở module scope, còn `apps.cosa.agents.seed` import
    module này (`skillpack_seed`) — nếu import `apps.cosa.api.skillpack_mapper`
    ở module scope thì vòng lặp import khép kín ngay lúc load module."""
    from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

    root = resolve_skillpacks_root(skillpacks_root)
    violations = validate_skillpack_tree(root, registered_capabilities=capability_ids)
    if violations:
        details = "; ".join(f"{item.path}:{item.rule}" for item in violations)
        raise BuiltinSkillpackSeedError(details)

    records: list[PublishedSpecRecord] = []
    for manifest_path in sorted(root.rglob("manifest.yaml")):
        try:
            spec = parse_skillpack_spec(manifest_path.parent)
            record = await publish_skill_spec(
                spec,
                repository=spec_registry,
                publisher="cosa_built_in",
            )
        except Exception as exc:
            raise BuiltinSkillpackSeedError(
                f"Cannot publish {manifest_path.parent}: {exc}"
            ) from exc
        records.append(record)
    return tuple(records)
