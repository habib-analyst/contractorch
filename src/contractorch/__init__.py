"""contractorch — orchestrate tools by contract, not by vibes.

Tools declare preconditions and effects in a typed DSL. The planner chains
contracts to reach a goal state; the parallelizer proves which calls may run
concurrently via effect-intersection analysis; the executor verifies
conditional effects at runtime and replans on deviation.
"""

from .contracts import CondEffect, GroundedContract, ToolContract, WorldState
from .executor import Executor, ExecutionTrace
from .parallel import (
    Compatibility,
    Layer,
    apply_layers,
    check_compatible,
    find_conflicts,
    layerize,
    parallel_cost,
    sequential_cost,
)
from .planner import Planner
from .react_baseline import ReactAgent, ReactResult
from .registry import ToolRegistry, mock_toolset

__version__ = "0.1.0"

__all__ = [
    "CondEffect",
    "GroundedContract",
    "ToolContract",
    "WorldState",
    "Executor",
    "ExecutionTrace",
    "Compatibility",
    "Layer",
    "apply_layers",
    "check_compatible",
    "find_conflicts",
    "layerize",
    "parallel_cost",
    "sequential_cost",
    "Planner",
    "ReactAgent",
    "ReactResult",
    "ToolRegistry",
    "mock_toolset",
    "__version__",
]
