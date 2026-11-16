import os
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('refresh',Path(os.environ.get('GITHUB_PROJECT_BRIEFING_TEST_PACKAGE', Path(__file__).parents[1]))/'skills/github-project-briefing/scripts/refresh.py')
r=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class RefreshTests(unittest.TestCase):
    def test_unconfigured_does_not_collect(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=r.run(Path(tmp),execute=lambda *a,**k:self.fail('unexpected collection'))
            self.assertEqual(result['status'],'unconfigured')
            self.assertEqual(result['alerts'],[])
    def test_invalid_configuration_warns_once_and_preserves_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/'projects.json'; path.write_text('{broken')
            self.assertEqual(len(r.run(root)['alerts']),1)
            self.assertEqual(r.run(root)['alerts'],[])
            self.assertEqual(path.read_text(),'{broken')
            path.write_text('{"projects":[]}')
            self.assertTrue(r.run(root)['alerts'][0]['recovered'])
    def test_paths_and_budgets_are_validated_before_any_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for state,budget in [('../escape',100),('data/x',0),('data/x',True)]:
                (root/'projects.json').write_text(json.dumps({'projects':[{'repo':'org/repo','state_dir':state,'max_prs':budget}]}))
                self.assertEqual(r.run(root,execute=lambda *a,**k:self.fail('invalid config collected'))['status'],'blocked')
    def test_filter_validation_and_forwarding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "projects.json"
            row = {"repo": "org/repo", "state_dir": "data/repo", "pr_filter": ["not a query"]}
            path.write_text(json.dumps({"projects": [row]}))
            self.assertEqual(r.run(root, execute=lambda *a, **k: self.fail("invalid filter collected"))["status"], "blocked")
            row["pr_filter"] = "-label:docs"
            path.write_text(json.dumps({"projects": [row]}))
            def execute(cmd, **kwargs):
                self.assertIn("--pr-filter=-label:docs", cmd)
                return subprocess.CompletedProcess(cmd, 0, '{"status":"complete"}')
            self.assertEqual(r.run(root, execute)["projects"][0]["status"], "complete")
            self.assertEqual(json.loads(path.read_text())["projects"][0], row)

    def test_project_directories_cannot_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for states in (("data/a", "data/a"), ("data/a", "data/a/b"), ("data/a/b", "data/a")):
                (root / "projects.json").write_text(json.dumps({"projects": [
                    {"repo": "org/a", "state_dir": states[0]}, {"repo": "org/b", "state_dir": states[1]}]}))
                result = r.run(root, execute=lambda *a, **k: self.fail("Overlapping projects collected"))
                self.assertEqual(result["status"], "blocked")

    def test_one_failure_does_not_block_other_repo_and_recovery_is_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'projects.json').write_text(json.dumps({'projects':[{'repo':'org/a','state_dir':'data/a'},{'repo':'org/b','state_dir':'data/b'}]}))
            failing=True
            calls=[]
            def execute(cmd,**kwargs):
                calls.append(cmd)
                fail=failing and cmd[cmd.index('--repo')+1]=='org/a'
                return subprocess.CompletedProcess(cmd,int(fail),json.dumps({'error':'HTTP 403'} if fail else {'status':'complete'}))
            self.assertEqual(len(r.run(root,execute)['alerts']),1)
            self.assertEqual(r.run(root,execute)['alerts'],[])
            self.assertEqual(len(calls),4)
            failing=False
            self.assertTrue(r.run(root,execute)['alerts'][0]['recovered'])
            self.assertEqual(r.run(root,execute)['alerts'],[])
    def test_overlapping_refresh_is_busy(self):
        import fcntl
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with (root/'refresh.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertEqual(r.run(root)['status'],'busy')
    def test_cli_collect_save_update_and_skip(self):
        import datetime as dt
        import sqlite3
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            binary = root / "gh"
            binary.write_text("#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\nfrom urllib.parse import urlsplit,parse_qs\n"
                              "responses=json.loads(Path(__file__).with_name('responses.json').read_text())\n"
                              "url=urlsplit(sys.argv[2]); query=parse_qs(url.query); data=responses[url.path]\n"
                              "if isinstance(data,list):\n"
                              "    size=int(query.get('per_page',['100'])[0]); page=int(query.get('page',['1'])[0]); data=data[(page-1)*size:page*size]\n"
                              "print(json.dumps(data))\n")
            binary.chmod(0o700)
            # Only the repository is required. State location and budgets have defaults.
            (root / "projects.json").write_text(json.dumps({"projects": [{"repo": "org/a"}, {"repo": "org/b"}]}))
            stamp = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            pr = {"number": 7, "title": "Cancel disconnected requests", "body": "Initial proposal",
                  "updated_at": stamp, "html_url": "https://github.com/org/a/pull/7"}
            responses = {"search/issues": {"total_count": 1, "incomplete_results": False}, "repos/org/a": {"default_branch": "main"}, "repos/org/a/pulls": [pr],
                         "repos/org/a/commits": [], "repos/org/a/releases": []}
            responses.update({"repos/org/b": {"default_branch": "main"},
                              "repos/org/b/pulls": [{**pr, "title": "A separate project change", "html_url": "https://github.com/org/b/pull/7"}],
                              "repos/org/b/commits": [], "repos/org/b/releases": []})
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"])
            scripts = Path(r.__file__).parent
            def invoke(script, *args):
                result = subprocess.run([sys.executable, str(scripts / script), *args],
                                        env=env, check=True, capture_output=True, text=True, timeout=60)
                return json.loads(result.stdout)
            (root / "responses.json").write_text(json.dumps(responses))
            estimate = invoke("collect.py", "--repo", "org/a", "--state-dir", str(root / "data/org--a"), "--estimate")
            self.assertEqual(estimate["estimated"], 1)
            self.assertFalse((root / "data").exists())
            first = None
            for number in (1, 2, 3):
                if number == 2:
                    pr["body"] = "Revised cancellation mechanism"
                (root / "responses.json").write_text(json.dumps(responses))
                payload = invoke("refresh.py", "--workspace", str(root))
                self.assertEqual(payload["status"], "complete")
                result = payload["projects"][0]
                self.assertEqual(result["changed_records"], 0 if number == 3 else 1)
                self.assertEqual(result["pending_runs"], [number])
                saved = invoke("collect.py", "--repo", "org/a", "--state-dir", result["state_dir"], "--run", str(number))
                self.assertEqual(len(saved["candidates"]), 0 if number == 3 else 1)
                if number < 3:
                    self.assertEqual(saved["candidates"][0]["title"], "Cancel disconnected requests")
                if number == 3:
                    invoke("collect.py", "--repo", "org/a", "--state-dir", result["state_dir"],
                           "--run", str(number), "--reason", "Reviewed sample; no further change.")
                    continue
                article = Path(result["state_dir"]) / "articles" / f"{stamp[:10]}-run-{number}.md"
                article.parent.mkdir(exist_ok=True)
                article.write_text(f"# Cancellation update {number}\n\n{pr['body']}\n\n"
                                   "[Proposal](https://github.com/org/a/pull/7)\n\n"
                                   "```yaml\ntoken: ${{ secrets.GITHUB_TOKEN }}\n```\n")
                saved = invoke("collect.py", "--repo", "org/a", "--state-dir", result["state_dir"],
                               "--run", str(number), "--article", str(article))
                self.assertEqual(saved["article"], str(article))
                if number == 1:
                    first = (article, article.read_bytes())
            self.assertEqual(first[0].read_bytes(), first[1])
            state = Path(result["state_dir"])
            self.assertEqual(list(state.glob("*.md")), [])
            articles = sorted((state / "articles").glob("*.md"))
            self.assertEqual(len(articles), 2)
            self.assertIn("Cancellation update 2", articles[1].read_text())
            self.assertEqual(invoke("collect.py", "--repo", "org/a", "--state-dir", str(state),
                                    "--pending")["pending_runs"], [])
            with sqlite3.connect(state / "activity.sqlite") as db:
                before, after = db.execute("SELECT before_json,after_json FROM changes WHERE run_id=2").fetchone()
                self.assertEqual(json.loads(before)["pr"]["body"], "Initial proposal")
                self.assertEqual(json.loads(after)["pr"]["body"], "Revised cancellation mechanism")
            other = root / "data/org--b"
            pending = invoke("collect.py", "--repo", "org/b", "--state-dir", str(other), "--pending")
            self.assertEqual(pending["pending_runs"], [1, 2, 3])
            original = {p.relative_to(state): p.read_bytes() for p in state.rglob("*") if p.is_file()}
            article = other / "articles" / f"{stamp[:10]}-run-1.md"
            article.parent.mkdir()
            article.write_text("# A separate project change\n\nIndependent project coverage.\n")
            saved = invoke("collect.py", "--repo", "org/b", "--state-dir", str(other),
                           "--run", "1", "--article", str(article))
            self.assertEqual(saved["article"], str(article))
            self.assertEqual({p.relative_to(state): p.read_bytes() for p in state.rglob("*") if p.is_file()}, original)
            self.assertEqual(invoke("collect.py", "--repo", "org/b", "--state-dir", str(other), "--pending")["pending_runs"], [2, 3])
            with sqlite3.connect(other / "activity.sqlite") as db:
                self.assertEqual(db.execute("SELECT DISTINCT repo FROM objects").fetchall(), [("org/b",)])
            # The normal daily caller reports overflow, then honors the saved budget.
            responses["search/issues"]["total_count"] = 150
            responses["repos/org/a/pulls"] = [{**pr, "number": n} for n in range(150)]
            (root / "responses.json").write_text(json.dumps(responses))
            blocked = invoke("refresh.py", "--workspace", str(root))
            self.assertEqual(blocked["status"], "partial")
            self.assertEqual(blocked["projects"][0]["status"], "needs_scope")
            self.assertEqual(blocked["projects"][0]["pending_runs"], [])
            (root / "projects.json").write_text(json.dumps({"projects": [
                {"repo": "org/a", "max_prs": 200}, {"repo": "org/b", "max_prs": 200}]}))
            resumed = invoke("refresh.py", "--workspace", str(root))
            self.assertEqual(resumed["status"], "complete")
            self.assertEqual(resumed["projects"][0]["changed_records"], 149)
            with sqlite3.connect(state / "activity.sqlite") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM objects WHERE kind='pr'").fetchone()[0], 150)
                self.assertEqual(db.execute("SELECT count(DISTINCT since) FROM runs WHERE id IN (4,5)").fetchone()[0], 1)

    def test_blocker_signature_ignores_changing_request_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'projects.json').write_text(json.dumps({'projects':[{'repo':'org/a','state_dir':'data/a'}]}))
            counter=0
            def execute(cmd,**kwargs):
                nonlocal counter
                counter+=1
                error=f'GitHub read failed: repos/org/a/commits?since=old&until=2026-11-11T00:00:0{counter}Z: HTTP 403'
                return subprocess.CompletedProcess(cmd,1,json.dumps({'error':error}))
            self.assertEqual(len(r.run(root,execute)['alerts']),1)
            self.assertEqual(r.run(root,execute)['alerts'],[])
