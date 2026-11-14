import os
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('refresh',Path(os.environ.get('PROJECT_BRIEFING_TEST_PACKAGE', Path(__file__).parents[1]))/'skills/project-briefing/scripts/refresh.py')
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
    def test_actual_cli_baseline_and_delta_with_fake_gh(self):
        import os
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); binary=root/'gh'
            binary.write_text('#!/usr/bin/env python3\nimport json,sys\ne=sys.argv[2]\nprint(json.dumps({"total_count":0,"incomplete_results":False} if e.startswith("search/issues?") else {"default_branch":"main"} if e=="repos/org/a" else []))\n')
            binary.chmod(0o700)
            (root/'projects.json').write_text(json.dumps({'projects':[{'repo':'org/a','state_dir':'data/a'}]}))
            env=dict(os.environ,PATH=str(root)+os.pathsep+os.environ['PATH'])
            command=[sys.executable,r.__file__,'--workspace',str(root)]
            for number in (1,2):
                result=subprocess.run(command,env=env,check=True,capture_output=True,text=True)
                payload=json.loads(result.stdout)
                self.assertEqual(payload['projects'][0]['status'],'complete')
                self.assertEqual(payload['projects'][0]['run'],number)
                self.assertTrue((root/f'data/a/run-{number}.md').is_file())
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
