"""contractorch.executor — executes layered plans against the mock world.

Within a layer, calls run "in parallel" (simulated; order-free because the
parallelizer proved them compatible). After each layer the executor compares
the actual world state against the contract-predicted state; on deviation
(e.g. a conditional effect that did not fire) it replans from the actual
state — this is how conditional branches are handled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import GroundedContract
from .parallel import Layer, apply_layers, layerize
from .planner import Planner
from .registry import ToolRegistry


@dataclass
class ExecutionTrace:
    layers_executed: int = 0
    calls_executed: int = 0
    replans: int = 0
    deviations: list[str] = field(default_factory=list)
    parallel_layers_used: int = 0


class Executor:
    def __init__(
        self,
        registry: ToolRegistry,
        world: dict[str, Any] | None = None,
        max_replans: int = 5,
    ):
        self.registry = registry
        self.world = world if world is not None else {}
        self.max_replans = max_replans
        self.trace = ExecutionTrace()

    def _run_call(self, call: GroundedContract, state: set[str]) -> set[str]:
        """Run one mock tool; return the actual post-state.

        The mock world is contract-driven: the actual outcome is the
        contract's *expected* state, except when a scripted deviation is
        registered in self.world['deviations'] (used to test replanning).
        """
        key = (call.name, tuple(sorted(call.params.items())))
        dev = self.world.get("deviations", {}).pop(key, None)  # one-shot
        if dev is not None:
            # Scripted deviation: apply this state delta instead.
            add = set(dev.get("add", []))
            delete = set(dev.get("delete", []))
            return (state | add) - delete
        return call.expected_state(state)

    def run(
        self,
        plan: list[GroundedContract],
        initial: set[str],
        goal: set[str],
        param_pool: dict[str, list[str]],
    ) -> tuple[bool, set[str], ExecutionTrace]:
        """Execute a plan (layerized), replanning on deviation. Returns
        (success, final_state, trace)."""
        self.trace = ExecutionTrace()
        state = set(initial)
        remaining_plan = list(plan)

        while True:
            layers, _ = layerize(remaining_plan, state)
            done = True
            for layer in layers:
                self.trace.layers_executed += 1
                if len(layer.calls) > 1:
                    self.trace.parallel_layers_used += 1
                # Predict, then execute each call in the layer.
                predicted = set(state)
                for c in layer.calls:
                    predicted = c.expected_state(predicted)
                actual = set(state)
                for c in layer.calls:
                    if not c.applicable(actual):
                        # Precondition violated mid-layer: treat as deviation.
                        self.trace.deviations.append(
                            f"precondition failed: {c.name}{c.params}"
                        )
                        done = False
                        break
                    actual = self._run_call(c, actual)
                    self.trace.calls_executed += 1
                if not done:
                    break
                if actual != predicted:
                    self.trace.deviations.append(
                        f"layer {[c.name for c in layer.calls]}: "
                        f"expected {sorted(predicted - actual)} missing, "
                        f"{sorted(actual - predicted)} unexpected"
                    )
                    state = actual
                    done = False
                    break
                state = actual
            if done:
                break
            # Replan from the actual state.
            self.trace.replans += 1
            if self.trace.replans > self.max_replans:
                return False, state, self.trace
            planner = Planner(self.registry.contract_list())
            remaining_plan = planner.plan(state, goal, param_pool)
            if remaining_plan is None:
                return False, state, self.trace

        return goal <= state, state, self.trace
