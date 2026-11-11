import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location("collect", Path(__file__).parents[1] / "skills/project-briefing/scripts/collect.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = c.connect(Path(self.tmp.name) / "test.sqlite")
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def test_pagination_and_overlap_boundary(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return [{"n": i} for i in range(100)] if url.endswith("&page=1") else [{"n":100}]
        self.assertEqual(len(c.pages("items", fetch=fetch)), 101)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(c.pages("items", stop=lambda x:x["n"]>20, fetch=fetch)),21)
    def test_duplicate_refresh_retains_one_change(self):
        def collector(*args):
            return [("commit","abc",{"sha":"abc"})]
        first, count = c.refresh(self.db,"org/repo",collector=collector)
        second, again = c.refresh(self.db,"org/repo",collector=collector)
        self.assertEqual((count,again),(1,0))
        self.assertEqual(self.db.execute("SELECT count(*) FROM changes").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0],1)
    def test_failed_collection_preserves_checkpoint_and_objects(self):
        c.refresh(self.db,"org/repo",collector=lambda *a:[("commit","a",{})])
        before = self.db.execute("SELECT started FROM runs WHERE status='complete'").fetchone()[0]
        def failed(*args):
            raise RuntimeError("page 2 unavailable")
        with self.assertRaises(RuntimeError):
            c.refresh(self.db,"org/repo",collector=failed)
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT started FROM runs WHERE status='complete'").fetchone()[0],before)
        report = c.render(self.db,2)
        self.assertIn("Coverage incomplete",report)
        self.assertNotIn("No newly observed changes",report)
    def test_atomic_rollback_if_saving_fails(self):
        def broken(*args):
            return [("commit","a",{}),("commit","a",{"changed":True})]
        with self.assertRaises(Exception):
            c.refresh(self.db,"org/repo",collector=broken)
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT status FROM runs").fetchone()[0],"failed")
    def test_edits_retain_before_and_after_evidence(self):
        c.refresh(self.db,"org/repo",collector=lambda *a:[("pr","1",{"body":"proposed"})])
        c.refresh(self.db,"org/repo",collector=lambda *a:[("pr","1",{"body":"revised"})])
        row=self.db.execute("SELECT before_json,after_json FROM changes WHERE run_id=2").fetchone()
        self.assertEqual(c.json.loads(row[0])["body"],"proposed")
        self.assertEqual(c.json.loads(row[1])["body"],"revised")
    def test_repository_checkpoints_are_independent(self):
        c.refresh(self.db,"org/one",collector=lambda *a:[("commit","a",{})])
        seen=[]
        def collect_two(db,repo,since,until,reconcile):
            seen.append(since)
            return [("commit","a",{})]
        _,count=c.refresh(self.db,"org/two",days=30,collector=collect_two)
        self.assertEqual(count,1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0],2)
        age=c.dt.datetime.now(c.dt.timezone.utc)-c.dt.datetime.fromisoformat(seen[0].replace("Z","+00:00"))
        self.assertGreater(age.days,28)
    def test_closed_proposal_not_claimed_implemented(self):
        record = {"pr":{"title":"Proposal","html_url":"https://github.com/org/repo/pull/1",
            "state":"closed","merged_at":"2026-11-11T00:00:00Z","user":{"login":"author"}},
            "files":[{"filename":"specs/rfcs/test.md"}],"comments":[],"reviews":[],"review_comments":[]}
        run,_ = c.refresh(self.db,"org/repo",collector=lambda *a:[("pr","1",record)])
        report = c.render(self.db,run)
        self.assertIn("Merged PRs",report)
        self.assertIn("acceptance and implementation unverified",report)
        self.assertIn("not verified maintainer",report)
    def test_oversized_inventory_stops_before_conversation_reads(self):
        requested=[]
        def fetch(url):
            requested.append(url)
            if url=="repos/org/repo": return {"default_branch":"main"}
            if "/pulls?state=all" in url:
                return [{"number":n,"updated_at":"2026-11-11T00:00:00Z"} for n in range(3)]
            return []
        with self.assertRaisesRegex(RuntimeError,"Read budget exceeded.*more than 2 records"):
            c.collect(self.db,"org/repo","2026-11-10T00:00:00Z","2026-11-11T00:00:00Z",fetch=fetch,max_prs=2)
        self.assertFalse(any("/comments" in url or "/files" in url or "/reviews" in url for url in requested))
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0],0)
    def test_discovery_stops_at_old_pr_without_reading_dormant_backlog(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if url == "repos/org/repo": return {"default_branch": "main"}
            if "/pulls?" in url:
                return [{"number": n, "updated_at": "2020-01-01T00:00:00Z"} for n in range(100)]
            return []
        records = c.collect(self.db, "org/repo", "2026-11-10T00:00:00Z",
                            "2026-11-11T00:00:00Z", fetch=fetch)
        self.assertEqual(records, [])
        self.assertEqual(len([url for url in calls if "/pulls?" in url]), 1)
        self.assertFalse(any("/pulls/" in url for url in calls))

    def test_paginated_evidence_overflow_is_not_silently_truncated(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return [{"id": n} for n in range(100)]
        with self.assertRaisesRegex(RuntimeError, "Read budget exceeded"):
            c.pages("comments", fetch=fetch)
        self.assertEqual(len(calls), 11)

    def test_old_draft_and_edited_release_survive_incremental_windows(self):
        release = {"id": 1, "created_at": "2020-01-01T00:00:00Z",
                   "published_at": None, "body": "draft"}
        def fetch(url):
            if url == "repos/org/repo": return {"default_branch": "main"}
            if "/releases?" in url: return [dict(release)]
            return []
        def collector(db, repo, since, until, reconcile):
            return c.collect(db, repo, since, until, reconcile, fetch=fetch)
        _, count = c.refresh(self.db, "org/repo", collector=collector)
        self.assertEqual(count, 1)
        release.update(published_at="2020-01-02T00:00:00Z", body="edited notes")
        _, changed = c.refresh(self.db, "org/repo", collector=collector)
        self.assertEqual(changed, 1)
        _, duplicate = c.refresh(self.db, "org/repo", collector=collector)
        self.assertEqual(duplicate, 0)

    def test_unbriefed_run_survives_no_change_refresh_and_delivery_uncertainty(self):
        collector = lambda *a: [("commit", "abc", {"sha": "abc"})]
        first, _ = c.refresh(self.db, "org/repo", collector=collector)
        c.refresh(self.db, "org/repo", collector=collector)
        self.assertIn(first, [p["run"] for p in c.pending_outputs(self.db, "org/repo")])
        self.assertEqual(c.pending_outputs(self.db, "org/other"), [])
        briefing = Path(self.tmp.name) / "briefing.md"
        briefing.write_text("Meaningful change with evidence.")
        c.record_output(self.db, "org/repo", first, briefing, "uncertain")
        self.assertNotIn(first, [p["run"] for p in c.pending_outputs(self.db, "org/repo")])
        self.assertEqual(c.delivery_outputs(self.db, "org/repo")[0]["delivery_status"], "uncertain")
        c.record_output(self.db, "org/repo", first, briefing, "confirmed")
        self.assertNotIn(first, [p["run"] for p in c.pending_outputs(self.db, "org/repo")])
        with self.assertRaises(ValueError):
            c.record_output(self.db, "org/other", first, briefing, "confirmed")
        with self.assertRaises(ValueError):
            c.record_output(self.db, "org/repo", first, briefing.with_name("missing"), "confirmed")

    def test_pending_cli_repairs_interrupted_ledger_without_network(self):
        root = Path(self.tmp.name)
        db = c.connect(root / "activity.sqlite")
        run, _ = c.refresh(db, "org/repo", collector=lambda *a: [
            ("commit", "abc", {"html_url": "https://github.com/org/repo/commit/abc",
                              "commit": {"message": "A meaningful change"}})])
        db.close()
        ledger = root / f"run-{run}.md"
        for partial in ("", "# org/repo: base"):
            ledger.write_text(partial)
            result = subprocess.run([sys.executable, c.__file__, "--repo", "org/repo",
                                     "--state-dir", str(root), "--pending"],
                                    check=True, capture_output=True, text=True)
            self.assertIn("A meaningful change", ledger.read_text())
            self.assertEqual(c.json.loads(result.stdout)["pending_outputs"][0]["run"], run)

    def test_dormant_tracked_pr_requires_explicit_reconciliation(self):
        old = {"pr":{"state":"open","updated_at":"old","head":{"sha":"a"}}}
        c.refresh(self.db,"org/repo",collector=lambda *a:[("pr","1",old)])
        closed = {"number":1,"state":"closed","updated_at":"new","head":{"sha":"b"}}
        called=[]
        def fetch(url):
            called.append(url)
            if url=="repos/org/repo": return {"default_branch":"main"}
            if url=="repos/org/repo/pulls/1": return closed
            return []
        records=c.collect(self.db,"org/repo","2026-11-10T00:00:00Z","2026-11-11T00:00:00Z",fetch=fetch)
        self.assertEqual(records, [])
        self.assertNotIn("repos/org/repo/pulls/1", called)
        records=c.collect(self.db,"org/repo","2026-11-10T00:00:00Z","2026-11-11T00:00:00Z",reconcile=True,fetch=fetch)
        self.assertEqual(records[0][2]["pr"]["state"],"closed")
        self.assertTrue(any("/issues/1/comments" in url for url in called))

if __name__ == "__main__":
    unittest.main()

class LightweightTests(unittest.TestCase):
    def test_no_file_or_diff_reads_and_legacy_cache_is_refetched(self):
        with tempfile.TemporaryDirectory() as root:
            db = c.connect(Path(root) / 'test.sqlite')
            pr = {'number':1,'state':'open','updated_at':'2026-11-11T00:00:00Z','head':{'sha':'a'}}
            c.refresh(db,'org/repo',collector=lambda *a:[('pr','1',{'pr':pr,'files':[{'patch':'old'}]})])
            calls=[]
            def fetch(url):
                calls.append(url)
                if url=='repos/org/repo': return {'default_branch':'main'}
                if '/pulls?' in url: return [pr]
                if url=='repos/org/repo/pulls/1': return pr
                return []
            records=c.collect(db,'org/repo','2026-11-10','2026-11-12',fetch=fetch)
            self.assertNotIn('files',records[0][2])
            self.assertFalse(any('/files' in url or '/pulls/1/comments' in url for url in calls))
            self.assertTrue(any('/reviews?' in url for url in calls))
            db.close()

class BriefingPathTests(unittest.TestCase):
    def test_reserved_ledger_name_rejected_and_legacy_briefing_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); db=c.connect(root/'activity.sqlite')
            run,_=c.refresh(db,'org/repo',collector=lambda *a:[])
            path=root/f'run-{run}.md'; path.write_text('Interpretive briefing')
            with self.assertRaisesRegex(ValueError,'reserved'):
                c.record_output(db,'org/repo',run,path,'pending')
            db.execute('INSERT INTO run_outputs VALUES(?,?,?)',(run,str(path),'pending'))
            db.commit()
            c.write_ledger(db,run,path)
            self.assertEqual(path.read_text(),'Interpretive briefing')
            db.close()
