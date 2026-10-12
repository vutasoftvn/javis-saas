from uuid import uuid4

import pytest

from agent.workforce.reporting import (
    MAX_REPORTING_DEPTH,
    ReportingLineError,
    check_reporting_line,
    direct_reports,
    manager_chain,
)


def _nodes(**spec):
    """spec: name -> (parent_name | None, status). Trả (nodes, ids)."""
    ids = {name: uuid4() for name in spec}
    nodes = {ids[n]: (ids[p] if p else None, st) for n, (p, st) in spec.items()}
    return nodes, ids


def test_no_parent_is_always_valid():
    nodes, ids = _nodes(a=(None, "ACTIVE"))
    check_reporting_line(assignment_id=ids["a"], parent_id=None, nodes=nodes)


def test_self_reference_is_rejected():
    nodes, ids = _nodes(a=(None, "ACTIVE"))
    with pytest.raises(ReportingLineError) as e:
        check_reporting_line(assignment_id=ids["a"], parent_id=ids["a"], nodes=nodes)
    assert e.value.code == "self_reference"


def test_missing_parent_is_rejected():
    nodes, ids = _nodes(a=(None, "ACTIVE"))
    with pytest.raises(ReportingLineError) as e:
        check_reporting_line(assignment_id=ids["a"], parent_id=uuid4(), nodes=nodes)
    assert e.value.code == "parent_not_found"


def test_retired_parent_is_rejected():
    nodes, ids = _nodes(a=(None, "ACTIVE"), boss=(None, "RETIRED"))
    with pytest.raises(ReportingLineError) as e:
        check_reporting_line(assignment_id=ids["a"], parent_id=ids["boss"], nodes=nodes)
    assert e.value.code == "parent_not_active"


def test_cycle_through_existing_chain_is_rejected():
    # a <- b <- c ; đặt a báo cáo cho c sẽ tạo vòng a -> c -> b -> a
    nodes, ids = _nodes(a=(None, "ACTIVE"), b=("a", "ACTIVE"), c=("b", "ACTIVE"))
    with pytest.raises(ReportingLineError) as e:
        check_reporting_line(assignment_id=ids["a"], parent_id=ids["c"], nodes=nodes)
    assert e.value.code == "cycle"


def test_depth_limit_is_enforced():
    spec = {"n0": (None, "ACTIVE")}
    for i in range(1, MAX_REPORTING_DEPTH + 1):
        spec[f"n{i}"] = (f"n{i - 1}", "ACTIVE")
    spec["new"] = (None, "ACTIVE")
    nodes, ids = _nodes(**spec)
    with pytest.raises(ReportingLineError) as e:
        check_reporting_line(
            assignment_id=ids["new"], parent_id=ids[f"n{MAX_REPORTING_DEPTH}"], nodes=nodes
        )
    assert e.value.code == "depth_exceeded"


def test_valid_attachment_passes():
    nodes, ids = _nodes(boss=(None, "ACTIVE"), a=(None, "ACTIVE"))
    check_reporting_line(assignment_id=ids["a"], parent_id=ids["boss"], nodes=nodes)


def test_manager_chain_returns_nearest_first_and_respects_max_hops():
    nodes, ids = _nodes(
        ceo=(None, "ACTIVE"), vp=("ceo", "ACTIVE"), lead=("vp", "ACTIVE"), dev=("lead", "ACTIVE")
    )
    assert manager_chain(nodes, ids["dev"]) == [ids["lead"], ids["vp"], ids["ceo"]]
    assert manager_chain(nodes, ids["dev"], max_hops=2) == [ids["lead"], ids["vp"]]


def test_manager_chain_stops_at_inactive_manager():
    nodes, ids = _nodes(
        ceo=(None, "ACTIVE"), vp=("ceo", "RETIRED"), lead=("vp", "ACTIVE"), dev=("lead", "ACTIVE")
    )
    assert manager_chain(nodes, ids["dev"]) == [ids["lead"]]


def test_manager_chain_survives_a_corrupt_cycle():
    a, b = uuid4(), uuid4()
    nodes = {a: (b, "ACTIVE"), b: (a, "ACTIVE")}
    assert len(manager_chain(nodes, a)) <= MAX_REPORTING_DEPTH


def test_direct_reports_lists_only_active():
    nodes, ids = _nodes(
        boss=(None, "ACTIVE"), a=("boss", "ACTIVE"), b=("boss", "RETIRED"), c=(None, "ACTIVE")
    )
    assert direct_reports(nodes, ids["boss"]) == [ids["a"]]
