"""contractorch.registry — tool registry + the mock toolset used for benchmarking.

Each mock tool is a Python callable paired with a machine-checkable contract.
The mock world is an in-memory dict; tools mutate it, and the executor derives
the *actual* post-state from the contract's expected effects (deterministic
mocks) or from scripted deviations (for conditional-effect tests).
"""

from __future__ import annotations

from typing import Any, Callable

from .contracts import GroundedContract, ToolContract


class ToolRegistry:
    def __init__(self) -> None:
        self.contracts: dict[str, ToolContract] = {}
        self.impls: dict[str, Callable[..., dict[str, Any]]] = {}

    def register(
        self, contract: ToolContract, impl: Callable[..., dict[str, Any]] | None = None
    ) -> None:
        self.contracts[contract.name] = contract
        if impl is not None:
            self.impls[contract.name] = impl

    def ground(self, name: str, params: dict[str, Any]) -> GroundedContract:
        return self.contracts[name].ground(params)

    def contract_list(self) -> list[ToolContract]:
        return list(self.contracts.values())


def _t(
    name: str,
    description: str,
    params: dict[str, str],
    pre: list[str],
    add: list[str],
    delete: list[str] | None = None,
    cost: float = 1.0,
    cond_effects: list[dict] | None = None,
) -> ToolContract:
    from .contracts import CondEffect

    return ToolContract(
        name=name,
        description=description,
        params=params,
        pre=pre,
        add=add,
        delete=delete or [],
        cost=cost,
        cond_effects=[CondEffect(**c) for c in (cond_effects or [])],
    )


def mock_toolset() -> ToolRegistry:
    """14 mock tools across file ops, API calls, and data transforms."""
    reg = ToolRegistry()

    def impl(**kw: Any) -> dict[str, Any]:
        return {"ok": True}

    # ---- file ops ----
    reg.register(
        _t("create_file", "Create a new file with given content",
           {"path": "str", "content": "str"},
           pre=["file_not_exists($path)"],
           add=["file_exists($path)"], cost=1.0), impl)
    reg.register(
        _t("read_file", "Read an existing file",
           {"path": "str"},
           pre=["file_exists($path)"],
           add=["file_read($path)"], cost=0.5), impl)
    reg.register(
        _t("delete_file", "Delete an existing file",
           {"path": "str"},
           pre=["file_exists($path)"],
           add=["file_deleted($path)", "file_not_exists($path)"],
           delete=["file_exists($path)"], cost=0.5), impl)
    reg.register(
        _t("move_file", "Move a file to a new path",
           {"src": "str", "dst": "str"},
           pre=["file_exists($src)", "file_not_exists($dst)"],
           add=["file_exists($dst)"],
           delete=["file_exists($src)"], cost=1.0), impl)

    # ---- API ----
    reg.register(
        _t("authenticate", "Authenticate a user, enabling API calls",
           {"user": "str"},
           pre=[], add=["authenticated($user)"], cost=2.0), impl)
    reg.register(
        _t("fetch_profile", "Fetch a user's profile (admins also unlock the admin panel)",
           {"user": "str"},
           pre=["authenticated($user)"],
           add=["profile_loaded($user)"], cost=2.0,
           cond_effects=[{
               "when": ["is_admin($user)"],
               "add": ["admin_panel_loaded($user)"],
               "delete": [],
           }]), impl)
    reg.register(
        _t("fetch_orders", "Fetch a user's order history",
           {"user": "str"},
           pre=["authenticated($user)"],
           add=["orders_loaded($user)"], cost=2.0), impl)
    reg.register(
        _t("send_email", "Send an email to a recipient",
           {"user": "str", "to": "str"},
           pre=["authenticated($user)", "profile_loaded($user)"],
           add=["email_sent($to)"], cost=1.5), impl)

    # ---- data transforms ----
    reg.register(
        _t("parse_csv", "Parse a CSV file into a table",
           {"path": "str"},
           pre=["file_exists($path)"],
           add=["table_loaded($path)"], cost=1.5), impl)
    reg.register(
        _t("filter_rows", "Filter table rows by a predicate",
           {"table": "str", "predicate": "str"},
           pre=["table_loaded($table)"],
           add=["table_filtered($table)"], cost=1.0), impl)
    reg.register(
        _t("aggregate", "Aggregate a filtered table",
           {"table": "str"},
           pre=["table_filtered($table)"],
           add=["table_aggregated($table)"], cost=1.5), impl)
    reg.register(
        _t("join_tables", "Join two loaded tables",
           {"t1": "str", "t2": "str"},
           pre=["table_loaded($t1)", "table_loaded($t2)"],
           add=["table_joined($t1,$t2)"], cost=2.0), impl)
    reg.register(
        _t("write_report", "Write an analysis report from aggregated or joined data",
           {"data": "str", "path": "str"},
           pre=["report_source_ready($data)", "file_not_exists($path)"],
           add=["report_written($path)", "file_exists($path)"], cost=1.0), impl)
    # Helper: mark a table as report-ready (models a tiny transform step)
    reg.register(
        _t("finalize_table", "Mark an aggregated table ready as a report source",
           {"table": "str"},
           pre=["table_aggregated($table)"],
           add=["report_source_ready($table)"], cost=0.5), impl)
    reg.register(
        _t("finalize_join", "Mark a joined table ready as a report source",
           {"t1": "str", "t2": "str"},
           pre=["table_joined($t1,$t2)"],
           add=["report_source_ready(join($t1,$t2))"], cost=0.5), impl)

    return reg
