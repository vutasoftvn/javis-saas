from uuid import uuid4

from agent.workforce.escalation import DEFAULT_HOP_CAP, next_escalation_target


def _chain(n):
    ids = [uuid4() for _ in range(n)]
    nodes = {ids[i]: (ids[i + 1] if i + 1 < n else None, "ACTIVE") for i in range(n)}
    return nodes, ids


def test_escalates_to_direct_manager_first():
    nodes, ids = _chain(3)
    t = next_escalation_target(nodes=nodes, assignment_id=ids[0], hop=0)
    assert (t.kind, t.assignment_id, t.hop) == ("manager", ids[1], 1)


def test_top_of_chain_goes_to_operator():
    nodes, ids = _chain(2)
    t = next_escalation_target(nodes=nodes, assignment_id=ids[1], hop=0)
    assert (t.kind, t.assignment_id, t.reason) == ("operator", None, "no_manager")


def test_hop_cap_stops_at_operator_even_with_managers_left():
    nodes, ids = _chain(6)
    t = next_escalation_target(nodes=nodes, assignment_id=ids[0], hop=DEFAULT_HOP_CAP)
    assert (t.kind, t.reason) == ("operator", "hop_cap_reached")


def test_retired_manager_sends_to_operator():
    nodes, ids = _chain(3)
    nodes[ids[1]] = (ids[2], "RETIRED")
    assert next_escalation_target(nodes=nodes, assignment_id=ids[0], hop=0).kind == "operator"


def test_unknown_assignment_goes_to_operator():
    assert next_escalation_target(nodes={}, assignment_id=uuid4(), hop=0).kind == "operator"


def test_walk_always_terminates_within_cap():
    # Thay thế cho property test (hypothesis không có trong dev deps của repo).
    for length in range(0, 13):
        for cap in range(0, 7):
            nodes, ids = _chain(max(length, 1))
            current, hop, steps = ids[0], 0, 0
            while True:
                t = next_escalation_target(nodes=nodes, assignment_id=current, hop=hop, hop_cap=cap)
                steps += 1
                assert steps <= cap + 1, (length, cap)
                if t.kind == "operator":
                    break
                current, hop = t.assignment_id, t.hop
