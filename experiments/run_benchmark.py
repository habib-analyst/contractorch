"""Run the 30-task benchmark: contractorch vs ReAct baseline.

Metrics:
  1. plan success rate (contractorch vs ReAct, 5 seeds)
  2. parallelization recall vs known-optimal parallel pairs (kill-gate: >= 0.90)
  3. simulated speedup: sequential cost / parallel-layer cost
  4. conflict-detection precision/recall on planted probe pairs

Kill-gate: contractorch success > ReAct success AND parallel recall >= 0.90.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "src")

from contractorch.benchmark import conflict_probes, tasks
from contractorch.executor import Executor
from contractorch.parallel import (
    check_compatible,
    layerize,
    parallel_cost,
    sequential_cost,
)
from contractorch.planner import Planner
from contractorch.react_baseline import ReactAgent
from contractorch.registry import mock_toolset


def key_of(call) -> tuple:
    return (call.name, tuple(sorted(call.params.items())))


def main() -> dict:
    reg = mock_toolset()
    planner = Planner(reg.contract_list())
    T = tasks()

    # ---- 1. success rates ----
    co_ok, co_layers_total, co_par_layers = 0, 0, 0
    seq_cost_sum, par_cost_sum = 0.0, 0.0
    react_ok = 0
    react_runs = 0
    per_task = []

    for t in T:
        plan = planner.plan(set(t.initial), set(t.goal), t.param_pool)
        if plan is None:
            per_task.append({"id": t.id, "contractorch": False, "react": None,
                             "note": "planner failed"})
            continue
        layers, _ = layerize(plan, set(t.initial))
        world = {"deviations": dict(t.deviations)}
        ex = Executor(reg, world=world)
        ok, final, trace = ex.run(plan, set(t.initial), set(t.goal), t.param_pool)
        co_ok += int(ok)
        co_layers_total += len(layers)
        co_par_layers += sum(1 for L in layers if len(L.calls) > 1)
        seq_cost_sum += sequential_cost(plan)
        par_cost_sum += parallel_cost(layers)

        r_ok = 0
        for seed in range(5):
            r = ReactAgent(reg, seed=seed).run(
                set(t.initial), set(t.goal), t.param_pool)
            r_ok += int(r.success)
            react_runs += 1
        react_ok += r_ok
        per_task.append({"id": t.id, "contractorch": ok,
                         "react_mean": r_ok / 5,
                         "layers": len(layers),
                         "replans": trace.replans})

    # ---- 2. parallelization recall ----
    pair_total, pair_found = 0, 0
    for t in T:
        plan = planner.plan(set(t.initial), set(t.goal), t.param_pool)
        if plan is None:
            continue
        layers, _ = layerize(plan, set(t.initial))
        layer_sets = [{key_of(c) for c in L.calls} for L in layers]
        for layer in t.optimal:
            if len(layer) < 2:
                continue
            for i in range(len(layer)):
                for j in range(i + 1, len(layer)):
                    a = (layer[i][0], tuple(sorted(layer[i][1].items())))
                    b = (layer[j][0], tuple(sorted(layer[j][1].items())))
                    pair_total += 1
                    if any(a in s and b in s for s in layer_sets):
                        pair_found += 1

    # ---- 4. conflict probe precision/recall ----
    tp = fp = tn = fn = 0
    for (n1, p1), (n2, p2), should in conflict_probes():
        a = reg.ground(n1, p1)
        b = reg.ground(n2, p2)
        verdict = check_compatible(a, b).ok
        if should and verdict:
            tp += 1
        elif should and not verdict:
            fn += 1
        elif not should and not verdict:
            tn += 1
        else:
            fp += 1

    n = len(T)
    results = {
        "n_tasks": n,
        "contractorch_success": co_ok / n,
        "react_success": react_ok / react_runs,
        "parallel_recall": pair_found / pair_total if pair_total else 0.0,
        "parallel_pairs": {"found": pair_found, "total": pair_total},
        "mean_layers_per_task": co_layers_total / n,
        "parallel_layers_used": co_par_layers,
        "mean_speedup": seq_cost_sum / par_cost_sum if par_cost_sum else 0.0,
        "conflict_precision": tp / (tp + fp) if (tp + fp) else 0.0,
        "conflict_recall": tp / (tp + fn) if (tp + fn) else 0.0,
        "conflict_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "per_task": per_task,
    }
    kill = (results["contractorch_success"] > results["react_success"]
            and results["parallel_recall"] >= 0.90)
    results["kill_gate"] = "PASS" if kill else "FAIL"
    return results


if __name__ == "__main__":
    res = main()
    print(json.dumps(res, indent=1))
    with open("results/summary.json", "w") as f:
        json.dump(res, f, indent=1)
