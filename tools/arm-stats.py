#!/usr/bin/env python3
"""arm-stats — totals for one batch of kanban work, for A/B comparisons.

A "batch" is every card created by the same session (`tasks.session_id`), which
is how one Hermes instance's work is identified. Give it a card-title prefix or
a session id and it prints tokens, calls and wall-clock per card and in total.

    arm-stats.py --title "Weather Map"
    arm-stats.py --session 20260912_105545_1a43fc
    arm-stats.py --title "Weather Map" --json

Read-only: every database is opened with mode=ro.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path

TASK_ID_RE = re.compile(r"\bt_[0-9a-f]{6,}\b")


def kanban_root() -> Path:
    import os
    override = os.environ.get("HERMES_KANBAN_HOME", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".hermes"


def ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    return conn


def session_tokens(root: Path) -> dict[str, list[tuple[float, int, int, int]]]:
    """{card: [(session start, input, output, calls), …]} across every profile.

    A card can be attempted more than once, under more than one profile, so the
    rows are kept per attempt and summed by the caller."""
    out: dict[str, list[tuple[float, int, int, int]]] = {}
    dbs = [root / "state.db"] + sorted(p / "state.db" for p in (root / "profiles").iterdir())
    for db in dbs:
        if not db.exists():
            continue
        try:
            conn = ro(db)
        except sqlite3.Error:
            continue
        try:
            rows = conn.execute(
                "select title, input_tokens, output_tokens, api_call_count, started_at "
                "from sessions where source = 'kanban'").fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()
        for title, inp, outp, calls, began in rows:
            match = TASK_ID_RE.search(title or "")
            if match:
                out.setdefault(match.group(0), []).append(
                    (began or 0.0, inp or 0, outp or 0, calls or 0))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="arm-stats")
    ap.add_argument("--title", help="card title prefix, e.g. 'Weather Map'")
    ap.add_argument("--session", help="creating session id")
    ap.add_argument("--board", default="kanban.db", help="board file under the Hermes root")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    if not args.title and not args.session:
        ap.error("give --title or --session")

    root = kanban_root()
    board = ro(root / args.board)
    if args.session:
        cards = board.execute(
            "select * from tasks where session_id = ? order by created_at", (args.session,)).fetchall()
    else:
        cards = board.execute(
            "select * from tasks where title like ? order by created_at", (args.title + "%",)).fetchall()
    if not cards:
        print("no cards matched")
        return 1

    tokens = session_tokens(root)
    now = time.time()
    rows, totals = [], {"input": 0, "output": 0, "calls": 0, "runtime": 0.0}
    for card in cards:
        attempts = tokens.get(card["id"], [])
        inp = sum(a[1] for a in attempts)
        outp = sum(a[2] for a in attempts)
        calls = sum(a[3] for a in attempts)
        started, ended = card["started_at"], card["completed_at"]
        runtime = ((ended or now) - started) if started else 0.0
        totals["input"] += inp
        totals["output"] += outp
        totals["calls"] += calls
        totals["runtime"] += runtime
        rows.append({"card": card["id"], "title": card["title"], "status": card["status"],
                     "profile": card["assignee"], "runtime_min": round(runtime / 60, 1),
                     "input": inp, "output": outp, "calls": calls,
                     "tokens_per_call": round(outp / calls) if calls else 0})

    started = [c["started_at"] for c in cards if c["started_at"]]
    wall = (now - min(started)) if started else 0.0
    done = sum(1 for c in cards if c["status"] == "done")
    summary = {"cards": len(cards), "done": done, "wall_clock_h": round(wall / 3600, 2),
               "worker_time_h": round(totals["runtime"] / 3600, 2), **totals,
               "tokens_per_call": round(totals["output"] / totals["calls"]) if totals["calls"] else 0,
               "output_per_min": round(totals["output"] / (totals["runtime"] / 60)) if totals["runtime"] else 0}

    if args.json:
        print(json.dumps({"cards": rows, "summary": summary}, indent=1))
        return 0

    print(f"{'card':10} {'status':9} {'profile':15} {'time':>9} {'in':>11} {'out':>9} "
          f"{'calls':>6} {'tok/call':>9}")
    for r in rows:
        print(f"{r['card'][2:10]:10} {r['status']:9} {r['profile'] or '—':15} "
              f"{r['runtime_min']:8.1f}m {r['input']:>11,} {r['output']:>9,} "
              f"{r['calls']:>6} {r['tokens_per_call']:>9,}")
    print(f"\ncards {done}/{summary['cards']} done · wall clock {summary['wall_clock_h']} h · "
          f"worker time {summary['worker_time_h']} h")
    print(f"tokens in {summary['input']:,} · out {summary['output']:,} · calls {summary['calls']} · "
          f"{summary['tokens_per_call']:,} tok/call · {summary['output_per_min']:,} out-tok/min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
