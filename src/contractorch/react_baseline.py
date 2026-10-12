"""contractorch.react_baseline — a simulated ReAct agent for comparison.

This baseline mimics how a prompt-driven ReAct agent behaves WITHOUT
contracts: at each step it scores tools by keyword overlap between the tool
description (+ its effect vocabulary) and the currently unsatisfied goals,
adds noise (standing in for LLM sampling variance), picks the best
applicable tool, executes, and observes. It has loop detection (same action
3x in a row -> give up) and a max-iteration cap — the standard ReAct guards.

It is intentionally a *reasonable* proxy, not a strawman: it never picks an
inapplicable tool (real ReAct agents usually respect obvious preconditions
stated in docs), but it cannot plan ahead, cannot parallelize, and can be
lured by distractor tools whose descriptions overlap the goal.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .contracts import GroundedContract
from .registry import ToolRegistry


@dataclass
class ReactResult:
    success: bool
    steps: int
    calls: list[GroundedContract] = field(default_factory=list)
    gave_up: str = ""


def _tokenize(text: str) -> set[str]:
    return {
        w.strip(".,()_").lower()
        for w in text.replace("/", " ").replace("-", " ").split()
        if len(w.strip(".,()_")) > 2
    }


class ReactAgent:
    def __init__(
        self,
        registry: ToolRegistry,
        seed: int = 0,
        noise: float = 0.35,
        max_iters: int = 14,
    ):
        self.registry = registry
        self.rng = random.Random(seed)
        self.noise = noise
        self.max_iters = max_iters
        # Precompute a text signature per tool: description + contract vocabulary.
        self._sig: dict[str, set[str]] = {}
        for c in registry.contract_list():
            vocab = " ".join([c.description] + c.pre + c.add + c.delete)
            self._sig[c.name] = _tokenize(vocab)

    def _groundings(self, name: str, param_pool: dict[str, list[str]]):
        import itertools

        c = self.registry.contracts[name]
        names = list(c.params.keys())
        if not names:
            yield self.registry.ground(name, {})
            return
        pools = [param_pool.get(n, []) for n in names]
        if any(not p for p in pools):
            return
        for combo in itertools.product(*pools):
            try:
                yield self.registry.ground(name, dict(zip(names, combo)))
            except KeyError:
                continue

    def run(
        self,
        initial: set[str],
        goal: set[str],
        param_pool: dict[str, list[str]],
    ) -> ReactResult:
        state = set(initial)
        goal = set(goal)
        calls: list[GroundedContract] = []
        recent: list[tuple[str, tuple]] = []

        for _ in range(self.max_iters):
            if goal <= state:
                return ReactResult(True, len(calls), calls)
            open_goals = goal - state
            goal_sig = _tokenize(" ".join(open_goals))

            # Score every applicable grounding by description overlap + noise.
            scored: list[tuple[float, GroundedContract]] = []
            for name in self.registry.contracts:
                overlap = len(self._sig[name] & goal_sig)
                for g in self._groundings(name, param_pool):
                    if not g.applicable(state):
                        continue
                    # Skip actions that change nothing (no progress possible).
                    if g.apply(state) == state:
                        continue
                    s = overlap + self.rng.uniform(0, self.noise) * max(overlap, 1)
                    # Small bonus for directly achieving an open goal.
                    if g.add & open_goals:
                        s += 1.0
                    scored.append((s, g))
            if not scored:
                return ReactResult(False, len(calls), calls, "no applicable action")
            scored.sort(key=lambda t: -t[0])
            chosen = scored[0][1]

            key = (chosen.name, tuple(sorted(chosen.params.items())))
            recent.append(key)
            if len(recent) >= 3 and recent[-1] == recent[-2] == recent[-3]:
                return ReactResult(False, len(calls), calls, "loop detected")
            calls.append(chosen)
            state = chosen.expected_state(state)

        return ReactResult(
            goal <= state, len(calls), calls,
            "" if goal <= state else "max iterations",
        )
