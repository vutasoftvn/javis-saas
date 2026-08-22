# backend/tests/agentos/observability/test_trace_tree.py
from agentos.observability.trace_tree import build_trace_tree


def test_build_trace_tree_nests_children_under_parent():
    spans = [
        {"span_id": "root", "parent_span_id": None, "name": "agent_run.started", "run_id": "r1"},
        {"span_id": "child1", "parent_span_id": "root", "name": "tool_call.started", "run_id": "r1", "tool_name": "a"},
        {"span_id": "child2", "parent_span_id": "root", "name": "tool_call.started", "run_id": "r1", "tool_name": "b"},
    ]

    tree = build_trace_tree(spans)

    assert len(tree) == 1
    root = tree[0]
    assert root.span_id == "root"
    assert [c.span_id for c in root.children] == ["child1", "child2"]
    assert root.children[0].payload == {"tool_name": "a"}


def test_build_trace_tree_supports_grandchildren():
    spans = [
        {"span_id": "root", "parent_span_id": None, "name": "agent_run.started", "run_id": "r1"},
        {"span_id": "mid", "parent_span_id": "root", "name": "skill_execution", "run_id": "r1"},
        {"span_id": "leaf", "parent_span_id": "mid", "name": "tool_call.started", "run_id": "r1"},
    ]

    tree = build_trace_tree(spans)

    assert tree[0].children[0].children[0].span_id == "leaf"


def test_build_trace_tree_treats_multiple_top_level_spans_as_separate_roots():
    spans = [
        {"span_id": "a", "parent_span_id": None, "name": "a", "run_id": "r1"},
        {"span_id": "b", "parent_span_id": None, "name": "b", "run_id": "r1"},
    ]

    tree = build_trace_tree(spans)

    assert [n.span_id for n in tree] == ["a", "b"]
