"""Unit tests for contractorch (run: .venv/bin/python -m pytest tests/ -q)."""

import sys

sys.path.insert(0, "src")

import pytest

from contractorch.contracts import GroundedContract, ToolContract, substitute
from contractorch.executor import Executor
from contractorch.parallel import check_compatible, layerize
from contractorch.planner import Planner
from contractorch.registry import mock_toolset


def test_substitute_ok():
    assert substitute("file_exists($path)", {"path": "/a"}) == "file_exists(/a)"


def test_substitute_unknown_param_raises():
    with pytest.raises(KeyError):
        substitute("file_exists($nope)", {"path": "/a"})


def test_ground_applicable_and_apply():
    c = ToolContract(name="t", pre=["p($x)"], add=["q($x)"],
                     delete=["p($x)"])
    g = c.ground({"x": "1"})
    assert g.applicable({"p(1)", "other"})
    assert not g.applicable({"p(2)"})
    assert g.apply({"p(1)", "other"}) == {"q(1)", "other"}


def test_compatible_write_write_conflict():
    reg = mock_toolset()
    a = reg.ground("write_report", {"data": "/d/a.csv", "path": "/d/r.txt"})
    b = reg.ground("write_report", {"data": "/d/b.csv", "path": "/d/r.txt"})
    assert not check_compatible(a, b).ok


def test_compatible_read_write_dependency():
    reg = mock_toolset()
    a = reg.ground("read_file", {"path": "/d/k.txt"})
    b = reg.ground("delete_file", {"path": "/d/k.txt"})
    assert not check_compatible(a, b).ok  # read's pre ∩ delete's effects


def test_compatible_safe_pair():
    reg = mock_toolset()
    a = reg.ground("fetch_profile", {"user": "amy"})
    b = reg.ground("fetch_orders", {"user": "ben"})
    assert check_compatible(a, b).ok


def test_layerize_interleaved_plan():
    """Planner emits [create(e), read(e), create(f), read(f)]; the layerizer
    must still co-locate the compatible pairs despite the interleaving."""
    reg = mock_toolset()
    plan = [
        reg.ground("create_file", {"path": "/d/e.txt", "content": "z"}),
        reg.ground("read_file", {"path": "/d/e.txt"}),
        reg.ground("create_file", {"path": "/d/f.txt", "content": "z"}),
        reg.ground("read_file", {"path": "/d/f.txt"}),
    ]
    layers, _ = layerize(plan, {"file_not_exists(/d/e.txt)",
                                "file_not_exists(/d/f.txt)"})
    assert len(layers) == 2
    assert {c.name for c in layers[0].calls} == {"create_file"}
    assert {c.name for c in layers[1].calls} == {"read_file"}


def test_planner_finds_chain():
    reg = mock_toolset()
    p = Planner(reg.contract_list())
    plan = p.plan({"file_exists(/d/a.csv)", "file_not_exists(/d/r.txt)"},
                  {"report_written(/d/r.txt)"},
                  {"path": ["/d/a.csv", "/d/r.txt"], "table": ["/d/a.csv"],
                   "predicate": ["x>0"], "data": ["/d/a.csv"]})
    assert plan is not None
    assert [c.name for c in plan] == [
        "parse_csv", "filter_rows", "aggregate", "finalize_table",
        "write_report",
    ]


def test_planner_uses_conditional_effects():
    """fetch_profile(root) with is_admin(root) should satisfy a goal on the
    conditional effect admin_panel_loaded(root)."""
    reg = mock_toolset()
    p = Planner(reg.contract_list())
    plan = p.plan({"is_admin(root)"}, {"admin_panel_loaded(root)"},
                  {"user": ["root"]})
    assert plan is not None
    assert [c.name for c in plan] == ["authenticate", "fetch_profile"]


def test_executor_replans_on_deviation():
    reg = mock_toolset()
    p = Planner(reg.contract_list())
    plan = p.plan(set(), {"profile_loaded(amy)"}, {"user": ["amy"]})
    assert plan is not None
    world = {"deviations": {
        ("fetch_profile", (("user", "amy"),)):
            {"add": [], "delete": ["profile_loaded(amy)"]},
    }}
    ex = Executor(reg, world=world)
    ok, final, trace = ex.run(plan, set(), {"profile_loaded(amy)"},
                              {"user": ["amy"]})
    assert ok
    assert trace.replans == 1
    assert "profile_loaded(amy)" in final


def test_check_compatible_symmetry():
    reg = mock_toolset()
    names = list(reg.contracts)
    import itertools
    for n1, n2 in itertools.product(names, names):
        c1, c2 = reg.contracts[n1], reg.contracts[n2]
        # ground with dummy params where possible
        try:
            a = reg.ground(n1, {k: "v" for k in c1.params})
            b = reg.ground(n2, {k: "v" for k in c2.params})
        except KeyError:
            continue
        assert check_compatible(a, b).ok == check_compatible(b, a).ok
