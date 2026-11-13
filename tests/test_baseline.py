"""First-scan planning through the real collector/refresh CLI with a fake gh."""
from contextlib import closing
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from unittest.mock import patch

ROOT = Path(os.environ.get("PROJECT_BRIEFING_TEST_PACKAGE", Path(__file__).parents[1]))
SCRIPTS = ROOT / "skills/project-briefing/scripts"
spec = importlib.util.spec_from_file_location("collect", SCRIPTS / "collect.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class BaselineTests(unittest.TestCase):
    def test_counted_choices_share_cutoff_and_do_not_guess_budgets(self):
        calls = []
        counts = iter([1052, 420, 60])
        def fetch(endpoint):
            calls.append(endpoint)
            return {"total_count": next(counts), "incomplete_results": False}
        with patch.object(c, "now", return_value="2026-11-13T12:00:00Z"):
            plan = c.baseline_plan("org/repo", fetch=fetch)
        self.assertEqual(plan["status"], "needs_scope")
        self.assertEqual(plan["options"], [
            {"days": 7, "estimated_prs": 1052, "max_prs": 1300},
            {"days": 3, "estimated_prs": 420, "max_prs": 600},
            {"days": 1, "estimated_prs": 60, "max_prs": 100}])
        for endpoint, date in zip(calls, ["2026-11-06", "2026-11-10", "2026-11-12"]):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(endpoint).query)
            self.assertEqual(query, {"q": [f"repo:org/repo is:pr updated:>={date}T12:00:00Z"], "per_page": ["1"]})

    def test_approved_budget_needs_only_one_count(self):
        calls = []
        def fetch(endpoint):
            calls.append(endpoint)
            return {"total_count": 1052, "incomplete_results": False}
        plan = c.baseline_plan("org/repo", max_prs=1500, fetch=fetch)
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(len(calls), 1)

    def test_incomplete_or_invalid_counts_cannot_authorize_collection(self):
        def fetch(endpoint):
            return {"total_count": 0, "incomplete_results": True}
        plan = c.baseline_plan("org/repo", days=2, fetch=fetch)
        self.assertEqual(plan["status"], "needs_scope")
        self.assertEqual([p["days"] for p in plan["estimates"]], [2, 1])
        self.assertEqual(plan["options"], [])
        for bad in ({}, [], {"total_count": True, "incomplete_results": False}):
            with self.assertRaisesRegex(RuntimeError, "no usable PR workload estimate"):
                c.baseline_plan("org/repo", fetch=lambda endpoint: bad)

    def workspace(self, root, counts=None, incomplete=False, discovered=0):
        (root / "counts.json").write_text(json.dumps({
            "counts": counts or {"7": 1052, "3": 420, "1": 60},
            "incomplete": incomplete, "discovered": discovered}))
        (root / "gh").write_text("""#!/usr/bin/env python3
import datetime as dt, json, pathlib, sys, urllib.parse
root = pathlib.Path(__file__).parent
endpoint = sys.argv[2]
with (root / "calls.jsonl").open("a") as log:
    log.write(json.dumps(endpoint) + "\\n")
config = json.loads((root / "counts.json").read_text())
if endpoint.startswith("search/issues?"):
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(endpoint).query)["q"][0]
    since = dt.datetime.fromisoformat(query.split("updated:>=")[1].replace("Z", "+00:00"))
    days = round((dt.datetime.now(dt.timezone.utc) - since).total_seconds() / 86400)
    result = {"total_count": config["counts"][str(days)], "incomplete_results": config["incomplete"]}
elif endpoint == "repos/org/repo":
    result = {"default_branch": "main"}
elif "/pulls?" in endpoint:
    result = [{"number": n, "updated_at": dt.datetime.now(dt.timezone.utc).isoformat()} for n in range(config["discovered"])]
else:
    result = []
print(json.dumps(result))
""")
        (root / "gh").chmod(0o700)
        config = root / "projects.json"
        config.write_text(json.dumps({"projects": [{"repo": "org/repo", "state_dir": "data/repo", "days": 7, "max_prs": 100}]}))
        env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"])
        return config, env

    def refresh(self, root, env):
        result = subprocess.run([sys.executable, str(SCRIPTS / "refresh.py"), "--workspace", str(root)],
                                capture_output=True, text=True, check=True, env=env)
        return json.loads(result.stdout)

    def calls(self, root):
        return [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]

    def test_initial_scope_blocks_then_both_approved_choices_work(self):
        for approved in ({"days": 7, "max_prs": 1300}, {"days": 1, "max_prs": 100}):
            with self.subTest(approved=approved), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config, env = self.workspace(root)
                before = config.read_bytes()
                result = self.refresh(root, env)
                self.assertEqual(result["projects"][0]["status"], "needs_scope")
                self.assertEqual(len(result["projects"][0]["options"]), 3)
                self.assertTrue(all(url.startswith("search/issues?") for url in self.calls(root)))
                with closing(sqlite3.connect(root / "data/repo/activity.sqlite")) as db:
                    self.assertEqual(db.execute("SELECT count(*) FROM runs").fetchone()[0], 0)
                    self.assertEqual(db.execute("SELECT count(*) FROM objects").fetchone()[0], 0)
                self.assertEqual(config.read_bytes(), before)
                self.assertEqual(self.refresh(root, env)["alerts"], [])
                saved = json.loads(config.read_text())
                saved["projects"][0].update(approved)
                config.write_text(json.dumps(saved))
                result = self.refresh(root, env)
                self.assertEqual(result["projects"][0]["status"], "complete")
                with closing(sqlite3.connect(root / "data/repo/activity.sqlite")) as db:
                    since = db.execute("SELECT since FROM runs").fetchone()[0]
                age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(since.replace("Z", "+00:00"))
                self.assertAlmostEqual(age.total_seconds() / 86400, approved["days"], places=2)
                (root / "calls.jsonl").write_text("")
                self.assertEqual(self.refresh(root, env)["projects"][0]["status"], "complete")
                self.assertFalse(any(url.startswith("search/issues?") for url in self.calls(root)))
                self.assertEqual(json.loads(config.read_text())["projects"][0], saved["projects"][0])

    def test_estimate_is_read_only_and_incomplete_counts_block_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, env = self.workspace(root, incomplete=True)
            state = root / "data/repo"
            result = subprocess.run([sys.executable, str(SCRIPTS / "collect.py"), "--repo", "org/repo",
                                     "--state-dir", str(state), "--estimate"],
                                    env=env, check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout)["status"], "needs_scope")
            self.assertFalse(state.exists())
            self.assertEqual(self.refresh(root, env)["projects"][0]["status"], "needs_scope")
            self.assertTrue(all(url.startswith("search/issues?") for url in self.calls(root)))

    def test_search_undercount_still_stops_before_conversation_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, env = self.workspace(root, counts={"7": 0}, discovered=3)
            saved = json.loads(config.read_text())
            saved["projects"][0]["max_prs"] = 2
            config.write_text(json.dumps(saved))
            result = self.refresh(root, env)
            self.assertEqual(result["projects"][0]["status"], "failed")
            self.assertIn("Read budget exceeded", result["projects"][0]["error"])
            self.assertFalse(any("/comments" in url or "/reviews" in url for url in self.calls(root)))
            with closing(sqlite3.connect(root / "data/repo/activity.sqlite")) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM runs WHERE status='complete'").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM objects").fetchone()[0], 0)
