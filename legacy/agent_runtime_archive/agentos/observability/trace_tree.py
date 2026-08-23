# backend/agentos/observability/trace_tree.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TraceNode(BaseModel):
    span_id: str
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    children: list["TraceNode"] = Field(default_factory=list)


TraceNode.model_rebuild()


def build_trace_tree(spans: list[dict[str, Any]]) -> list[TraceNode]:
    """Nest a flat TraceRecorder.export() span list into a tree by
    parent_span_id (blueprint §55). Spans with no parent (or an unknown
    parent) become roots — a run with no nesting at all (every span
    top-level, which is what real Executor-produced spans look like
    today) is still a valid, degenerate tree, not an error.
    """
    nodes: dict[str, TraceNode] = {}
    for span in spans:
        payload = {k: v for k, v in span.items() if k not in {"span_id", "parent_span_id", "name", "run_id"}}
        nodes[span["span_id"]] = TraceNode(span_id=span["span_id"], name=span["name"], payload=payload)

    roots: list[TraceNode] = []
    for span in spans:
        node = nodes[span["span_id"]]
        parent_id = span.get("parent_span_id")
        if parent_id is not None and parent_id in nodes:
            nodes[parent_id].children.append(node)
        else:
            roots.append(node)
    return roots
