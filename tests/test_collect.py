import importlib.util
from pathlib import Path
import tempfile
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
    def test_open_inventory_and_closed_reconciliation(self):
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
        self.assertEqual(records[0][2]["pr"]["state"],"closed")
        self.assertTrue(any("/pulls/1/comments" in url for url in called))

if __name__ == "__main__":
    unittest.main()
