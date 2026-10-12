"""contractorch.planner — A* planning over tool contracts.

Given an initial world state and a goal (set of predicates), the planner
searches the space of *grounded tool calls* — precondition chaining, not
LLM vibes. Heuristic: number of unsatisfied goal predicates. Action cost:
each tool's declared cost.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field

from .contracts import GroundedContract, ToolContract

_counter = itertools.count()


@dataclass(order=True)
class _Node:
    f: float
    g: float = field(compare=False)
    state: frozenset = field(compare=False)
    plan: tuple = field(compare=False)  # tuple[GroundedContract, ...]
    tie: int = field(compare=False, default_factory=lambda: next(_counter))


class Planner:
    def __init__(self, contracts: list[ToolContract], max_expansions: int = 20000):
        self.contracts = {c.name: c for c in contracts}
        self.max_expansions = max_expansions

    def _groundings(
        self, contract: ToolContract, param_pool: dict[str, list[str]]
    ) -> list[GroundedContract]:
        """Enumerate grounded calls for one tool from the candidate pool."""
        names = list(contract.params.keys())
        if not names:
            return [contract.ground({})]
        pools = [param_pool.get(n, []) for n in names]
        if any(not p for p in pools):
            return []
        out = []
        for combo in itertools.product(*pools):
            params = dict(zip(names, combo))
            try:
                out.append(contract.ground(params))
            except KeyError:
                continue
        return out

    def _heuristic(self, state: frozenset, goal: set[str]) -> float:
        return float(len(set(goal) - set(state)))

    def plan(
        self,
        initial: set[str],
        goal: set[str],
        param_pool: dict[str, list[str]],
    ) -> list[GroundedContract] | None:
        """Return a sequential plan (list of grounded calls) or None."""
        goal = set(goal)
        start = frozenset(initial)
        if goal <= set(start):
            return []

        # Precompute all groundings once (pool is small in practice).
        groundings: list[GroundedContract] = []
        for c in self.contracts.values():
            groundings.extend(self._groundings(c, param_pool))

        open_heap: list[_Node] = [
            _Node(self._heuristic(start, goal), 0.0, start, ())
        ]
        best_g: dict[frozenset, float] = {start: 0.0}
        expansions = 0

        while open_heap and expansions < self.max_expansions:
            node = heapq.heappop(open_heap)
            if node.g > best_g.get(node.state, float("inf")):
                continue
            expansions += 1
            state = set(node.state)
            for gc in groundings:
                if not gc.applicable(state):
                    continue
                # Plan over *expected* states: conditional effects whose
                # `when` holds are assumed to fire. The executor verifies
                # this assumption at runtime and replans on deviation.
                ns = frozenset(gc.expected_state(state))
                ng = node.g + gc.cost
                if ng >= best_g.get(ns, float("inf")):
                    continue
                best_g[ns] = ng
                nplan = node.plan + (gc,)
                if goal <= set(ns):
                    return list(nplan)
                heapq.heappush(
                    open_heap,
                    _Node(ng + self._heuristic(ns, goal), ng, ns, nplan),
                )
        return None
