# STATUS — contractorch

**State: DONE.** Kill-gate PASS. Push payload staged at
`hidden_files/contractorch_push_payload.json`. Awaiting parent: repo
creation via browser, then parent pushes.

## Pipeline
- [x] Contract DSL (`contracts.py`) — Pydantic, $param templates, cond effects
- [x] Planner (`planner.py`) — A* over grounded calls, expected-state semantics
- [x] Parallelizer (`parallel.py`) — effect-intersection, layerize with start-state recompute
- [x] Executor (`executor.py`) — verify + replan-on-deviation (5 max)
- [x] Mock toolset (15 tools) + ReAct baseline
- [x] 30-task benchmark — kill-gate PASS
- [x] 11/11 unit tests
- [x] Paper, branded README, LinkedIn draft, packaging

## Key numbers (measured, CPU)
- Plan success: **1.000** (contractorch) vs **0.893** (ReAct, 5 seeds)
- Parallelization recall: **1.000** (23/23 pairs)
- Conflict precision/recall: **1.00 / 1.00** (12 probes)
- Mean simulated speedup: **1.29x**
- Tests: 11/11

## Bugs caught during build
1. `heapq.heappush` called without the heap argument (planner).
2. `delete_file` did not re-establish `file_not_exists` — create-after-delete
   was unplannable. Fixed in contract.
3. Planner ignored conditional effects (`apply` vs `expected_state`) — t29
   unplannable. Planner now plans over expected states; executor verifies.
4. `layerize` snapshotted layer start-states at creation; later placements
   into earlier layers invalidated them (t16/t17/t18 recall misses).
   Fixed by recomputing start-states after every placement.

## Limitations (in paper + README)
Mock toolset/simulated costs; contracts trusted; param pools given;
ReAct baseline simulated, not a real LLM.
