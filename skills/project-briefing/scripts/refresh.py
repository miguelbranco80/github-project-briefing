#!/usr/bin/env python3
"""Refresh configured projects; no configuration means no collection."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

def projects(root):
    path = root / "projects.json"
    if not path.exists():
        return []
    config = json.loads(path.read_text())
    rows = config["projects"]
    if not isinstance(rows, list):
        raise ValueError("projects must be an array")
    seen = set()
    states = set()
    for row in rows:
        repo = row["repo"]
        state = (root / row["state_dir"]).resolve()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Use owner/repository")
        if not state.is_relative_to(root / "data") or state == root / "data":
            raise ValueError("state_dir must be a directory beneath workspace data/")
        if repo.lower() in seen or state in states:
            raise ValueError("Duplicate repository or state directory")
        seen.add(repo.lower())
        states.add(state)
        for field in ("days", "max_prs"):
            value = row.get(field, 7 if field == "days" else 100)
            if type(value) is not int or value < 1:
                raise ValueError(f"{field} must be a positive integer")
        for field in ("priorities", "watchlist"):
            if not isinstance(row.get(field, []), list) or not all(isinstance(v, str) for v in row.get(field, [])):
                raise ValueError(f"{field} must be an array of strings")
        if not isinstance(row.get("pr_filter", ""), str):
            raise ValueError("pr_filter must be a GitHub PR search string")
    return rows

def run(root, execute=subprocess.run):
    root = root.resolve()
    # A workspace-wide lock prevents concurrent daily jobs, not interactive edits.
    import fcntl
    with (root / "refresh.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "projects": [], "alerts": []}
        db = sqlite3.connect(root / "refresh.sqlite")
        db.execute("CREATE TABLE IF NOT EXISTS blockers(key TEXT PRIMARY KEY,error TEXT)")
        alerts = []
        def health(key, error):
            old = db.execute("SELECT error FROM blockers WHERE key=?", (key,)).fetchone()
            if error:
                signature = re.sub(r"\?[^\s;]+", "", error)
                if not old or old[0] != signature:
                    alerts.append({"project": key, "error": error})
                db.execute("INSERT OR REPLACE INTO blockers VALUES(?,?)", (key, signature))
            elif old:
                db.execute("DELETE FROM blockers WHERE key=?", (key,))
                alerts.append({"project": key, "recovered": True})
            db.commit()
        try:
            rows = projects(root)
        except (ValueError, KeyError, TypeError) as exc:
            health("configuration", f"Invalid projects.json: {exc}")
            db.close()
            return {"status": "blocked", "projects": [], "alerts": alerts}
        health("configuration", None)
        results = []
        for row in rows:
            command = [sys.executable, str(Path(__file__).with_name("collect.py")),
                       "--repo", row["repo"], "--state-dir", str(root / row["state_dir"]),
                       "--days", str(row.get("days", 7)), "--max-prs", str(row.get("max_prs", 100))]
            if row.get("pr_filter", "").strip():
                command.append("--pr-filter=" + row["pr_filter"].strip())
            result = execute(command, capture_output=True, text=True)
            try:
                payload = json.loads(result.stdout)
            except ValueError:
                payload = {"status": "failed", "error": "Collector did not complete; inspect local state and execution-host access"}
            error = payload.get("error", "Collection failed") if result.returncode else None
            health(row["repo"], error)
            results.append({"repo": row["repo"], **payload})
        db.close()
        return {"status": "complete" if rows else "unconfigured", "projects": results, "alerts": alerts}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    print(json.dumps(run(parser.parse_args().workspace)))
