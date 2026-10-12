# ContractOrch: Planning Over Tool Contracts with Provably-Safe Parallelization

**Habib Ur Rehman** · October 2026

## Abstract

LLM tool orchestration today is prompt-driven: the model reads tool
descriptions and picks what looks relevant. This produces two failure modes
we measure directly: plans that never reach the goal (our ReAct baseline
succeeds on only 89.3% of 30 multi-step tasks), and parallelism that is
either never attempted or unsound. ContractOrch replaces description
matching with **contracts**: every tool declares preconditions, effects,
and conditional effects in a typed DSL. A planner chains contracts to a
goal state; an effect-intersection analysis proves which calls may run
concurrently; an executor verifies conditional effects at runtime and
replans on deviation. On a 30-task benchmark over a 15-tool mock suite,
ContractOrch achieves **100% plan success** vs 89.3% for the ReAct
baseline, finds **100% of safe parallelizations** (23/23 ground-truth
pairs), detects planted conflicts with **1.0 precision / 1.0 recall**,
and yields a **1.29× mean simulated speedup**.

## 1. The gap

Existing approaches to reliable tool use cluster in three places, none of
which does what ContractOrch does:

- **Constrained generation / validators** (e.g. Instructor, Guardrails,
  LangChain's structured output): validate *outputs* against schemas. They
  say nothing about *sequencing* — which tool to call, in which order,
  or which calls are safe together.
- **Contract-filtered tool selection** (Contract2Tool, and the general
  "tool contract" literature): contracts are used to *filter* or *rank*
  candidate tools for an LLM to choose from. The LLM still does the
  planning, and parallelism is left to prompting.
- **Classical AI planning** (STRIPS/PDDL planners): plan over
  preconditions and effects, but are not connected to LLM tool
  ecosystems, have no notion of conditional-effect verification at
  runtime, and do not address safe parallelization of tool calls.

To our knowledge, **no existing system plans tool sequences directly
over contracts, and none derives safe parallelism from
effect-intersection analysis**. That is the gap ContractOrch fills.

## 2. Method

### 2.1 Contract DSL

A `ToolContract` (Pydantic model) declares:

- `pre`: predicates that must hold before the call (templates with
  `$param` placeholders, e.g. `file_exists($path)`)
- `add` / `delete`: predicates the call establishes / retracts
- `cond_effects`: `(when, add, delete)` branches — effects that fire only
  when `when` holds in the pre-state
- `cost`: simulated step cost for speedup measurement

Grounding substitutes call parameters into templates, yielding a
`GroundedContract` with set-valued pre/add/delete.

### 2.2 Planner

Forward A\* over grounded calls. State transitions use **expected
states**: conditional effects whose `when` holds are assumed to fire.
Heuristic: number of unsatisfied goal predicates. Action cost: the
tool's declared cost. Parameter bindings come from a per-task candidate
pool (in production: entity extraction from the task text).

### 2.3 Effect-intersection parallelization (the core invention)

Two grounded calls may share a parallel layer **iff** their contracts
prove it safe:

1. **No write-write conflict:** `effects(A) ∩ effects(B) = ∅`
2. **No cross-dependency:** `pre(A) ∩ effects(B) = ∅` and symmetrically

A sequential plan is compressed into layers: each step enters the
earliest layer whose start-state satisfies its preconditions and in
which it is pairwise-compatible with every step already placed. Layer
start-states are recomputed after every placement (a subtle correctness
point: placing a step into an earlier layer changes what later layers
start from — we caught and fixed this during development).

### 2.4 Executor with replan-on-deviation

Layers execute in order; within a layer, calls are order-free (proven
compatible). After each layer, the executor compares the actual state
against the contract-predicted state. On deviation — e.g. a conditional
effect that did not fire — it replans from the actual state (up to 5
replans). This is how conditional branches are handled without
branching the plan itself.

## 3. Benchmark

30 tasks over a 15-tool mock suite (file ops, API calls, data
transforms): 10 sequential chains, 12 parallelizable tasks with
known-optimal layered plans, 8 conflict traps + conditional-effect
tasks (including a scripted API flake that forces a replan). The ReAct
baseline scores tools by description/contract-vocabulary overlap with
open goals plus sampling noise — a reasonable proxy for prompt-driven
selection, with loop detection and a 14-iteration cap (not a strawman).

## 4. Results (all measured, CPU)

| Metric | ContractOrch | ReAct baseline |
|---|---|---|
| Plan success (30 tasks) | **1.000** | 0.893 (5 seeds) |
| Safe-parallelization recall (23 pairs) | **1.000** | n/a (never parallelizes) |
| Conflict precision / recall (12 probes) | **1.00 / 1.00** | n/a |
| Mean simulated speedup | **1.29×** | 1.00× |
| Replans triggered (flaky-API task) | 1 (recovered) | n/a |

Kill-gate (success > baseline AND recall ≥ 0.90): **PASS**.

## 5. Limitations (honest)

- **Mock toolset, simulated costs.** The 15 tools are deterministic
  mocks; speedup is measured in declared step-costs, not wall-clock
  time on real APIs. The conflict analysis is exact *relative to the
  contracts* — if a tool's contract lies about its effects, all
  guarantees are void. Contract authorship/verification is out of
  scope.
- **Parameter pools are given.** The planner enumerates bindings from a
  per-task candidate pool; grounding parameters from free text (entity
  extraction / schema-guided generation) is future work.
- **Conditional effects are expected, not branched.** The planner
  assumes `when`-conditions fire and the executor replans otherwise;
  true contingency planning (branching on both outcomes) is not
  implemented.
- **ReAct baseline is simulated.** It models description-overlap tool
  selection with noise rather than calling a real LLM, so the 89.3%
  figure is a proxy, not a measurement of any specific model.

## 6. Conclusion

Contracts turn tool orchestration from a prompting problem into a
planning problem — and once tools have contracts, safe parallelism
falls out of set arithmetic rather than guesswork. The next step is
real toolsets with LLM-grounded parameters, where we expect the gap
over description-driven routing to widen.

## Citation

```bibtex
@software{rehman2026contractorch,
  author = {Rehman, Habib Ur},
  title = {ContractOrch: Planning Over Tool Contracts with Provably-Safe Parallelization},
  year = {2026},
  url = {https://github.com/habib-analyst/contractorch}
}
```
