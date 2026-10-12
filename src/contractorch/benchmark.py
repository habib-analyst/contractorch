"""contractorch.benchmark — 30 multi-step tasks with known-optimal plans.

Task categories:
  * t01-t10: sequential chains (no safe parallelism; tests planning correctness)
  * t11-t22: parallelizable (tests effect-intersection layer compression)
  * t23-t30: conflict traps + conditional effects (tests safety + replanning)

Each task carries its optimal layered plan so we can measure parallelization
recall against ground truth, plus planted conflict probe pairs for the
check_compatible() precision/recall test.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    id: str
    description: str
    initial: list[str]
    goal: list[str]
    param_pool: dict[str, list[str]]
    # known-optimal layered plan: list of layers; each layer = list of
    # (tool_name, params) that may run in parallel
    optimal: list[list[tuple[str, dict]]] = field(default_factory=list)
    # scripted one-shot deviations for the executor: {(tool, sorted params): delta}
    deviations: dict = field(default_factory=dict)


def _p(**kw) -> dict:
    return kw


def tasks() -> list[Task]:
    T: list[Task] = []

    # ---------------- sequential chains ----------------
    T.append(Task(
        "t01", "CSV pipeline: parse -> filter -> aggregate -> finalize -> report",
        ["file_exists(/d/a.csv)", "file_not_exists(/d/r1.txt)"],
        ["report_written(/d/r1.txt)"],
        {"path": ["/d/a.csv", "/d/r1.txt"], "table": ["/d/a.csv"],
         "predicate": ["x>0"], "data": ["/d/a.csv"]},
        optimal=[[("parse_csv", _p(path="/d/a.csv"))],
                 [("filter_rows", _p(table="/d/a.csv", predicate="x>0"))],
                 [("aggregate", _p(table="/d/a.csv"))],
                 [("finalize_table", _p(table="/d/a.csv"))],
                 [("write_report", _p(data="/d/a.csv", path="/d/r1.txt"))]],
    ))
    T.append(Task(
        "t02", "Create a file, then read it",
        ["file_not_exists(/d/n.txt)"],
        ["file_read(/d/n.txt)"],
        {"path": ["/d/n.txt"], "content": ["hello"]},
        optimal=[[("create_file", _p(path="/d/n.txt", content="hello"))],
                 [("read_file", _p(path="/d/n.txt"))]],
    ))
    T.append(Task(
        "t03", "Move a file to a new path",
        ["file_exists(/d/old.txt)", "file_not_exists(/d/new.txt)"],
        ["file_exists(/d/new.txt)"],
        {"src": ["/d/old.txt"], "dst": ["/d/new.txt"], "path": ["/d/new.txt"]},
        optimal=[[("move_file", _p(src="/d/old.txt", dst="/d/new.txt"))]],
    ))
    T.append(Task(
        "t04", "Authenticate, load profile, send email",
        [],
        ["email_sent(boss@co.com)"],
        {"user": ["amy"], "to": ["boss@co.com"]},
        optimal=[[("authenticate", _p(user="amy"))],
                 [("fetch_profile", _p(user="amy"))],
                 [("send_email", _p(user="amy", to="boss@co.com"))]],
    ))
    T.append(Task(
        "t05", "CSV pipeline on a second dataset",
        ["file_exists(/d/b.csv)", "file_not_exists(/d/r2.txt)"],
        ["report_written(/d/r2.txt)"],
        {"path": ["/d/b.csv", "/d/r2.txt"], "table": ["/d/b.csv"],
         "predicate": ["y<5"], "data": ["/d/b.csv"]},
        optimal=[[("parse_csv", _p(path="/d/b.csv"))],
                 [("filter_rows", _p(table="/d/b.csv", predicate="y<5"))],
                 [("aggregate", _p(table="/d/b.csv"))],
                 [("finalize_table", _p(table="/d/b.csv"))],
                 [("write_report", _p(data="/d/b.csv", path="/d/r2.txt"))]],
    ))
    T.append(Task(
        "t06", "Create, read, then delete a file",
        ["file_not_exists(/d/t.txt)"],
        ["file_read(/d/t.txt)", "file_deleted(/d/t.txt)"],
        {"path": ["/d/t.txt"], "content": ["tmp"]},
        optimal=[[("create_file", _p(path="/d/t.txt", content="tmp"))],
                 [("read_file", _p(path="/d/t.txt"))],
                 [("delete_file", _p(path="/d/t.txt"))]],
    ))
    T.append(Task(
        "t07", "Join two tables and write a report",
        ["file_exists(/d/a.csv)", "file_exists(/d/b.csv)",
         "file_not_exists(/d/j.txt)"],
        ["report_written(/d/j.txt)"],
        {"path": ["/d/a.csv", "/d/b.csv", "/d/j.txt"],
         "t1": ["/d/a.csv"], "t2": ["/d/b.csv"],
         "data": ["join(/d/a.csv,/d/b.csv)"]},
        optimal=[[("parse_csv", _p(path="/d/a.csv"))],
                 [("parse_csv", _p(path="/d/b.csv"))],
                 [("join_tables", _p(t1="/d/a.csv", t2="/d/b.csv"))],
                 [("finalize_join", _p(t1="/d/a.csv", t2="/d/b.csv"))],
                 [("write_report", _p(data="join(/d/a.csv,/d/b.csv)",
                                      path="/d/j.txt"))]],
    ))
    T.append(Task(
        "t08", "Authenticate and pull order history",
        [],
        ["orders_loaded(amy)"],
        {"user": ["amy"]},
        optimal=[[("authenticate", _p(user="amy"))],
                 [("fetch_orders", _p(user="amy"))]],
    ))
    T.append(Task(
        "t09", "Create, move, then read a file",
        ["file_not_exists(/d/w.txt)", "file_not_exists(/d/v.txt)"],
        ["file_read(/d/v.txt)"],
        {"path": ["/d/w.txt", "/d/v.txt"], "content": ["data"],
         "src": ["/d/w.txt"], "dst": ["/d/v.txt"]},
        optimal=[[("create_file", _p(path="/d/w.txt", content="data"))],
                 [("move_file", _p(src="/d/w.txt", dst="/d/v.txt"))],
                 [("read_file", _p(path="/d/v.txt"))]],
    ))
    T.append(Task(
        "t10", "CSV pipeline on a third dataset",
        ["file_exists(/d/c.csv)", "file_not_exists(/d/r3.txt)"],
        ["report_written(/d/r3.txt)"],
        {"path": ["/d/c.csv", "/d/r3.txt"], "table": ["/d/c.csv"],
         "predicate": ["z=1"], "data": ["/d/c.csv"]},
        optimal=[[("parse_csv", _p(path="/d/c.csv"))],
                 [("filter_rows", _p(table="/d/c.csv", predicate="z=1"))],
                 [("aggregate", _p(table="/d/c.csv"))],
                 [("finalize_table", _p(table="/d/c.csv"))],
                 [("write_report", _p(data="/d/c.csv", path="/d/r3.txt"))]],
    ))

    # ---------------- parallelizable ----------------
    T.append(Task(
        "t11", "Load profile and orders in parallel after auth",
        [],
        ["profile_loaded(amy)", "orders_loaded(amy)"],
        {"user": ["amy"]},
        optimal=[[("authenticate", _p(user="amy"))],
                 [("fetch_profile", _p(user="amy")),
                  ("fetch_orders", _p(user="amy"))]],
    ))
    T.append(Task(
        "t12", "Parallel loads, then send email",
        [],
        ["email_sent(boss@co.com)", "orders_loaded(amy)"],
        {"user": ["amy"], "to": ["boss@co.com"]},
        optimal=[[("authenticate", _p(user="amy"))],
                 [("fetch_profile", _p(user="amy")),
                  ("fetch_orders", _p(user="amy"))],
                 [("send_email", _p(user="amy", to="boss@co.com"))]],
    ))
    T.append(Task(
        "t13", "Create two independent files",
        ["file_not_exists(/d/p.txt)", "file_not_exists(/d/q.txt)"],
        ["file_exists(/d/p.txt)", "file_exists(/d/q.txt)"],
        {"path": ["/d/p.txt", "/d/q.txt"], "content": ["x"]},
        optimal=[[("create_file", _p(path="/d/p.txt", content="x")),
                  ("create_file", _p(path="/d/q.txt", content="x"))]],
    ))
    T.append(Task(
        "t14", "Parse two CSVs in parallel, join, report",
        ["file_exists(/d/a.csv)", "file_exists(/d/b.csv)",
         "file_not_exists(/d/r4.txt)"],
        ["report_written(/d/r4.txt)"],
        {"path": ["/d/a.csv", "/d/b.csv", "/d/r4.txt"],
         "t1": ["/d/a.csv"], "t2": ["/d/b.csv"],
         "data": ["join(/d/a.csv,/d/b.csv)"]},
        optimal=[[("parse_csv", _p(path="/d/a.csv")),
                  ("parse_csv", _p(path="/d/b.csv"))],
                 [("join_tables", _p(t1="/d/a.csv", t2="/d/b.csv"))],
                 [("finalize_join", _p(t1="/d/a.csv", t2="/d/b.csv"))],
                 [("write_report", _p(data="join(/d/a.csv,/d/b.csv)",
                                      path="/d/r4.txt"))]],
    ))
    T.append(Task(
        "t15", "Read two files in parallel",
        ["file_exists(/d/m.txt)", "file_exists(/d/n2.txt)"],
        ["file_read(/d/m.txt)", "file_read(/d/n2.txt)"],
        {"path": ["/d/m.txt", "/d/n2.txt"]},
        optimal=[[("read_file", _p(path="/d/m.txt")),
                  ("read_file", _p(path="/d/n2.txt"))]],
    ))
    T.append(Task(
        "t16", "Two users: auth both, then load everything in parallel",
        [],
        ["profile_loaded(amy)", "orders_loaded(amy)",
         "profile_loaded(ben)", "orders_loaded(ben)"],
        {"user": ["amy", "ben"]},
        optimal=[[("authenticate", _p(user="amy")),
                  ("authenticate", _p(user="ben"))],
                 [("fetch_profile", _p(user="amy")),
                  ("fetch_orders", _p(user="amy")),
                  ("fetch_profile", _p(user="ben")),
                  ("fetch_orders", _p(user="ben"))]],
    ))
    T.append(Task(
        "t17", "Create two files, then read both in parallel",
        ["file_not_exists(/d/e.txt)", "file_not_exists(/d/f.txt)"],
        ["file_read(/d/e.txt)", "file_read(/d/f.txt)"],
        {"path": ["/d/e.txt", "/d/f.txt"], "content": ["z"]},
        optimal=[[("create_file", _p(path="/d/e.txt", content="z")),
                  ("create_file", _p(path="/d/f.txt", content="z"))],
                 [("read_file", _p(path="/d/e.txt")),
                  ("read_file", _p(path="/d/f.txt"))]],
    ))
    T.append(Task(
        "t18", "Two independent CSV pipelines interleaved",
        ["file_exists(/d/a.csv)", "file_exists(/d/b.csv)"],
        ["table_aggregated(/d/a.csv)", "table_aggregated(/d/b.csv)"],
        {"path": ["/d/a.csv", "/d/b.csv"],
         "table": ["/d/a.csv", "/d/b.csv"], "predicate": ["x>0"]},
        optimal=[[("parse_csv", _p(path="/d/a.csv")),
                  ("parse_csv", _p(path="/d/b.csv"))],
                 [("filter_rows", _p(table="/d/a.csv", predicate="x>0")),
                  ("filter_rows", _p(table="/d/b.csv", predicate="x>0"))],
                 [("aggregate", _p(table="/d/a.csv")),
                  ("aggregate", _p(table="/d/b.csv"))]],
    ))
    T.append(Task(
        "t19", "Move one file while creating another (independent)",
        ["file_exists(/d/s.txt)", "file_not_exists(/d/d.txt)",
         "file_not_exists(/d/g.txt)"],
        ["file_exists(/d/d.txt)", "file_exists(/d/g.txt)"],
        {"src": ["/d/s.txt"], "dst": ["/d/d.txt"],
         "path": ["/d/g.txt"], "content": ["g"]},
        optimal=[[("move_file", _p(src="/d/s.txt", dst="/d/d.txt")),
                  ("create_file", _p(path="/d/g.txt", content="g"))]],
    ))
    T.append(Task(
        "t20", "Auth, parallel loads, email (variant)",
        [],
        ["email_sent(ops@co.com)", "profile_loaded(ben)", "orders_loaded(ben)"],
        {"user": ["ben"], "to": ["ops@co.com"]},
        optimal=[[("authenticate", _p(user="ben"))],
                 [("fetch_profile", _p(user="ben")),
                  ("fetch_orders", _p(user="ben"))],
                 [("send_email", _p(user="ben", to="ops@co.com"))]],
    ))
    T.append(Task(
        "t21", "Create three files in parallel",
        ["file_not_exists(/d/1.txt)", "file_not_exists(/d/2.txt)",
         "file_not_exists(/d/3.txt)"],
        ["file_exists(/d/1.txt)", "file_exists(/d/2.txt)",
         "file_exists(/d/3.txt)"],
        {"path": ["/d/1.txt", "/d/2.txt", "/d/3.txt"], "content": ["c"]},
        optimal=[[("create_file", _p(path="/d/1.txt", content="c")),
                  ("create_file", _p(path="/d/2.txt", content="c")),
                  ("create_file", _p(path="/d/3.txt", content="c"))]],
    ))
    T.append(Task(
        "t22", "Delete two files in parallel",
        ["file_exists(/d/x1.txt)", "file_exists(/d/x2.txt)"],
        ["file_deleted(/d/x1.txt)", "file_deleted(/d/x2.txt)"],
        {"path": ["/d/x1.txt", "/d/x2.txt"]},
        optimal=[[("delete_file", _p(path="/d/x1.txt")),
                  ("delete_file", _p(path="/d/x2.txt"))]],
    ))

    # ---------------- conflict traps + conditionals ----------------
    T.append(Task(
        "t23", "Read then delete the same file (ordered, never parallel)",
        ["file_exists(/d/k.txt)"],
        ["file_read(/d/k.txt)", "file_deleted(/d/k.txt)"],
        {"path": ["/d/k.txt"]},
        optimal=[[("read_file", _p(path="/d/k.txt"))],
                 [("delete_file", _p(path="/d/k.txt"))]],
    ))
    T.append(Task(
        "t24", "Two reports, same output path: pick one (write-write conflict)",
        ["file_exists(/d/a.csv)", "file_exists(/d/b.csv)",
         "file_not_exists(/d/r.txt)"],
        ["report_written(/d/r.txt)"],
        {"path": ["/d/a.csv", "/d/b.csv", "/d/r.txt"],
         "table": ["/d/a.csv", "/d/b.csv"], "predicate": ["x>0"],
         "data": ["/d/a.csv", "/d/b.csv"]},
        optimal=[[("parse_csv", _p(path="/d/a.csv"))],
                 [("filter_rows", _p(table="/d/a.csv", predicate="x>0"))],
                 [("aggregate", _p(table="/d/a.csv"))],
                 [("finalize_table", _p(table="/d/a.csv"))],
                 [("write_report", _p(data="/d/a.csv", path="/d/r.txt"))]],
    ))
    T.append(Task(
        "t25", "Distractor: creating the same file twice is useless",
        ["file_not_exists(/d/dup.txt)"],
        ["file_exists(/d/dup.txt)"],
        {"path": ["/d/dup.txt"], "content": ["one", "two"]},
        optimal=[[("create_file", _p(path="/d/dup.txt", content="one"))]],
    ))
    T.append(Task(
        "t26", "Delete then recreate the same path (ordered)",
        ["file_exists(/d/rc.txt)"],
        ["file_exists(/d/rc.txt)", "file_deleted(/d/rc.txt)"],
        {"path": ["/d/rc.txt"], "content": ["new"]},
        optimal=[[("delete_file", _p(path="/d/rc.txt"))],
                 [("create_file", _p(path="/d/rc.txt", content="new"))]],
    ))
    T.append(Task(
        "t27", "Move then read at the destination (ordered)",
        ["file_exists(/d/o.txt)", "file_not_exists(/d/p2.txt)"],
        ["file_read(/d/p2.txt)"],
        {"src": ["/d/o.txt"], "dst": ["/d/p2.txt"], "path": ["/d/p2.txt"]},
        optimal=[[("move_file", _p(src="/d/o.txt", dst="/d/p2.txt"))],
                 [("read_file", _p(path="/d/p2.txt"))]],
    ))
    T.append(Task(
        "t28", "Distractor: fetch_orders looks relevant but email needs the profile",
        [],
        ["email_sent(boss@co.com)"],
        {"user": ["amy"], "to": ["boss@co.com"]},
        optimal=[[("authenticate", _p(user="amy"))],
                 [("fetch_profile", _p(user="amy"))],
                 [("send_email", _p(user="amy", to="boss@co.com"))]],
    ))
    T.append(Task(
        "t29", "Conditional effect: admin profile unlocks the admin panel",
        ["is_admin(root)"],
        ["admin_panel_loaded(root)"],
        {"user": ["root"]},
        optimal=[[("authenticate", _p(user="root"))],
                 [("fetch_profile", _p(user="root"))]],
    ))
    T.append(Task(
        "t30", "Flaky API: first profile fetch silently fails, executor must replan",
        [],
        ["profile_loaded(amy)"],
        {"user": ["amy"]},
        optimal=[[("authenticate", _p(user="amy"))],
                 [("fetch_profile", _p(user="amy"))],
                 [("fetch_profile", _p(user="amy"))]],  # retry after replan
        deviations={("fetch_profile", (("user", "amy"),)):
                    {"add": [], "delete": ["profile_loaded(amy)"]}},
    ))
    return T


def conflict_probes() -> list[tuple[tuple[str, dict], tuple[str, dict], bool]]:
    """Planted (call_a, call_b, should_be_compatible) pairs for the
    check_compatible() precision/recall test. Includes near-misses."""
    P = _p
    return [
        # true conflicts (must be flagged)
        ((("read_file", P(path="/d/k.txt"))), (("delete_file", P(path="/d/k.txt"))), False),
        ((("write_report", P(data="/d/a.csv", path="/d/r.txt"))),
         (("write_report", P(data="/d/b.csv", path="/d/r.txt"))), False),
        ((("create_file", P(path="/d/x.txt", content="1"))),
         (("create_file", P(path="/d/x.txt", content="2"))), False),
        ((("move_file", P(src="/d/a.txt", dst="/d/b.txt"))),
         (("create_file", P(path="/d/b.txt", content="z"))), False),
        ((("fetch_profile", P(user="amy"))),
         (("send_email", P(user="amy", to="t@co.com"))), False),
        ((("delete_file", P(path="/d/rc.txt"))),
         (("create_file", P(path="/d/rc.txt", content="n"))), False),
        # safe pairs (must NOT be flagged)
        ((("read_file", P(path="/d/m.txt"))),
         (("read_file", P(path="/d/n2.txt"))), True),
        ((("fetch_profile", P(user="amy"))),
         (("fetch_orders", P(user="ben"))), True),
        ((("create_file", P(path="/d/p.txt", content="x"))),
         (("delete_file", P(path="/d/x1.txt"))), True),
        ((("parse_csv", P(path="/d/a.csv"))),
         (("parse_csv", P(path="/d/b.csv"))), True),
        ((("authenticate", P(user="amy"))),
         (("authenticate", P(user="ben"))), True),
        ((("create_file", P(path="/d/1.txt", content="c"))),
         (("create_file", P(path="/d/2.txt", content="c"))), True),
    ]
