[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/habib-analyst/contractorch.svg)](https://github.com/habib-analyst/contractorch/stargazers)

# contractorch

**Stop picking tools by vibes.** Give every tool a contract — preconditions, effects, conditional effects — and let a planner chain them to your goal. Safe parallelism falls out of set arithmetic: two calls run together *iff* their contracts prove they can't conflict.

## Quickstart

```bash
pip install contractorch
```

```python
from contractorch import Planner, Executor, layerize, mock_toolset

reg = mock_toolset()
plan = Planner(reg.contract_list()).plan(
    initial={"file_exists(/d/a.csv)", "file_not_exists(/d/r.txt)"},
    goal={"report_written(/d/r.txt)"},
    param_pool={"path": ["/d/a.csv", "/d/r.txt"], "table": ["/d/a.csv"],
                "predicate": ["x>0"], "data": ["/d/a.csv"]},
)
layers, _ = layerize(plan, {"file_exists(/d/a.csv)"})
ok, final, trace = Executor(reg).run(
    plan, {"file_exists(/d/a.csv)", "file_not_exists(/d/r.txt)"},
    {"report_written(/d/r.txt)"}, pool)
print(ok, [c.name for c in plan])
```

Expected output:

```
True ['parse_csv', 'filter_rows', 'aggregate', 'finalize_table', 'write_report']
```

## Measured results

30-task benchmark (10 sequential chains, 12 parallelizable, 8 conflict traps + conditionals), 15-tool mock suite, ReAct baseline = description-overlap tool selection with noise, 5 seeds:

| Metric | contractorch | ReAct baseline |
|---|---|---|
| Plan success rate | **1.000** | 0.893 |
| Safe-parallelization recall (23 pairs) | **1.000** | — (never parallelizes) |
| Conflict-detection precision / recall | **1.00 / 1.00** | — |
| Mean simulated speedup | **1.29×** | 1.00× |

Kill-gate (beat baseline AND recall ≥ 0.90): **PASS**.

## How it works

```
 goal ──► Planner (A* over contracts) ──► sequential plan
                                                │
                                                ▼
                                    Parallelizer (effect-intersection)
                                     1. effects(A) ∩ effects(B) = ∅      (no write-write)
                                     2. pre(A) ∩ effects(B) = ∅          (no cross-deps)
                                                │
                                                ▼
                                    Executor ──► verify layer, replan on deviation
```

- **Contracts** (`contracts.py`): Pydantic DSL — `pre`, `add`, `delete`, `cond_effects` with `$param` templates.
- **Planner** (`planner.py`): forward A\* over grounded calls, planning on *expected* states (conditional effects assumed, verified later).
- **Parallelizer** (`parallel.py`): compresses a sequential plan into provably-safe layers; layer start-states recomputed after every placement.
- **Executor** (`executor.py`): runs layers, compares actual vs predicted state, replans from reality on deviation (up to 5 replans).

Run the benchmark yourself: `python experiments/run_benchmark.py` → `results/summary.json`.

## Limitations

Mock toolset with simulated costs; contracts are trusted (a lying contract voids the guarantees); parameter pools are given per task; the ReAct baseline is simulated, not a real LLM. Full account in [paper/PAPER.md](paper/PAPER.md).

## Citation

```bibtex
@software{rehman2026contractorch,
  author = {Rehman, Habib Ur},
  title = {ContractOrch: Planning Over Tool Contracts with Provably-Safe Parallelization},
  year = {2026},
  url = {https://github.com/habib-analyst/contractorch}
}
```

---
Built by [Habib Ur Rehman](https://github.com/habib-analyst) · ML/AI Engineer & healthcare-AI researcher ·
[LinkedIn](https://www.linkedin.com/in/hur-dev) · [habib.top](https://habib.top)
