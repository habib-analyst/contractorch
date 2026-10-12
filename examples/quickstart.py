"""Quickstart: plan a goal, parallelize it, execute it."""

import sys

sys.path.insert(0, "src")

from contractorch import (
    Executor,
    Planner,
    layerize,
    mock_toolset,
    parallel_cost,
    sequential_cost,
)

reg = mock_toolset()
planner = Planner(reg.contract_list())

initial = {"file_exists(/d/a.csv)", "file_not_exists(/d/r.txt)"}
goal = {"report_written(/d/r.txt)"}
pool = {
    "path": ["/d/a.csv", "/d/r.txt"],
    "table": ["/d/a.csv"],
    "predicate": ["x>0"],
    "data": ["/d/a.csv"],
}

plan = planner.plan(initial, goal, pool)
print("sequential plan:")
for c in plan:
    print(f"  - {c.name}{c.params}")

layers, _ = layerize(plan, initial)
print("\nparallel layers:")
for i, layer in enumerate(layers):
    print(f"  layer {i}: {[c.name for c in layer.calls]}")

ex = Executor(reg)
ok, final, trace = ex.run(plan, initial, goal, pool)
print(f"\nexecuted: success={ok}, calls={trace.calls_executed}, "
      f"replans={trace.replans}")
print(f"simulated cost: sequential={sequential_cost(plan):.1f} -> "
      f"parallel={parallel_cost(layers):.1f}")
