from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel


def definition_hash(model: BaseModel) -> str:
    """sha256 của canonical JSON của 1 Pydantic model — dùng để pin 1
    executable spec (AgentSpec/WorkflowSpec) theo đúng nội dung thật, thay
    vì dựa vào version do con người gán (dễ quên bump, hoặc bump nhầm mà
    nội dung không đổi/đổi mà không bump — silent drift). `sort_keys=True`
    đảm bảo thứ tự field lúc construct không ảnh hưởng tới hash."""
    canonical = json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
