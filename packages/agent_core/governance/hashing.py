from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel


from typing import Union


def definition_hash(model: Union[BaseModel, dict]) -> str:
    """sha256 của canonical JSON của 1 Pydantic model hoặc dict — dùng để pin 1
    executable spec (AgentSpec/WorkflowSpec) theo đúng nội dung thật, thay
    vì dựa vào version do con người gán (dễ quên bump, hoặc bump nhầm mà
    nội dung không đổi/đổi mà không bump — silent drift). `sort_keys=True`
    đảm bảo thứ tự field lúc construct không ảnh hưởng tới hash."""
    if isinstance(model, BaseModel):
        data = model.model_dump(mode="json")
    elif isinstance(model, dict):
        data = model
    else:
        raise TypeError(f"Expected BaseModel or dict, got {type(model).__name__}")
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

