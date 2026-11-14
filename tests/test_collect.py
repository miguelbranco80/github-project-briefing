import os
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location("collect", Path(os.environ.get("PROJECT_BRIEFING_TEST_PACKAGE", Path(__file__).parents[1])) / "skills/project-briefing/scripts/collect.py")
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


    def test_filtered_collection_does_not_fetch_unrelated_streams_or_tracked_prs(self):
        pr = {"number": 7, "state": "open", "updated_at": "2026-11-11T00:00:00Z",
              "head": {"sha": "a"}, "title": "Fix sessions",
              "html_url": "https://github.com/org/repo/pull/7", "user": {"login": "dev"}}
        c.refresh(self.db, "org/repo", collector=lambda *a: [
            ("pr", "1", {"pr": dict(pr, number=1)})])
        calls = []
        def fetch(url):
            calls.append(url)
            if url.startswith("search/issues?"):
                query = c.urllib.parse.parse_qs(c.urllib.parse.urlsplit(url).query)["q"][0]
                self.assertEqual(query, 'repo:org/repo is:pr updated:>=2026-11-10 label:"agent runtime"')
                return {"total_count": 1, "incomplete_results": False, "items": [{"number": 7}]}
            if url == "repos/org/repo/pulls/7": return pr
            if "/issues/7/comments?" in url or "/pulls/7/reviews?" in url: return []
            self.fail(f"Unexpected out-of-scope read: {url}")
        records = c.collect(self.db, "org/repo", "2026-11-10", "2026-11-12",
                            reconcile=True, fetch=fetch, pr_filter='label:"agent runtime"')
        self.assertEqual([(kind, key) for kind, key, _ in records], [("pr", "7")])
        c.refresh(self.db, "org/repo", collector=lambda *a: records, pr_filter='label:"agent runtime"')
        report = c.render(self.db, 2)
        self.assertIn('PR-only coverage', report)
        self.assertIn('label:"agent runtime"', report)
        self.assertIn("commits and releases are NOT collected", report)
        calls.clear()
        self.assertEqual(c.collect(self.db, "org/repo", "2026-11-10", "2026-11-12",
                                   fetch=fetch, pr_filter='label:"agent runtime"'), records)
        self.assertEqual(len(calls), 2)  # Search + PR metadata; unchanged discussions reused.

    def test_search_paginates_and_stops_at_exact_thousand_without_page_eleven(self):
        for total in (101, 1000):
            calls = []
            def fetch(url):
                calls.append(url)
                start = (int(c.urllib.parse.parse_qs(c.urllib.parse.urlsplit(url).query)["page"][0]) - 1) * 100
                return {"total_count": total, "incomplete_results": False,
                        "items": [{"number": n} for n in range(start, min(start + 100, total))]}
            result = c.pages("search/issues?q=test", fetch=fetch, max_items=1000, search=True)
            self.assertEqual(len(result), total)
            self.assertEqual(len(calls), (total + 99) // 100)

    def test_unsafe_search_results_stop_before_any_conversation_read(self):
        for result in (
            {"total_count": 1, "incomplete_results": True, "items": []},
            {"total_count": 3, "incomplete_results": False, "items": []},
            {"total_count": 2, "incomplete_results": False, "items": [{"number": 1}]},
            {"total_count": 1, "incomplete_results": False,
             "items": [{"number": n} for n in range(3)]},
        ):
            calls = []
            def fetch(url):
                calls.append(url)
                return result
            with self.assertRaises(RuntimeError):
                c.collect(self.db, "org/repo", "2026-11-10", "2026-11-12",
                          fetch=fetch, max_prs=2, pr_filter="label:security")
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0].startswith("search/issues?"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0], 0)

    def test_changed_or_removed_filter_rebaselines_and_preserves_history(self):
        previous = None
        for pr_filter in ("", "label:security", "label:security", ""):
            observed = []
            def collector(db, repo, since, until, reconcile):
                observed.append(since)
                return []
            run, _ = c.refresh(self.db, "org/repo", days=7, collector=collector, pr_filter=pr_filter)
            since = c.dt.datetime.fromisoformat(observed[0].replace("Z", "+00:00"))
            if previous and previous[1] == pr_filter:
                self.assertEqual(since, previous[0] - c.dt.timedelta(hours=24))
            else:
                age = c.dt.datetime.now(c.dt.timezone.utc) - since
                self.assertAlmostEqual(age.total_seconds() / 86400, 7, places=2)
            started, saved_filter = self.db.execute("SELECT started,pr_filter FROM runs WHERE id=?", (run,)).fetchone()
            self.assertEqual(saved_filter, pr_filter)
            previous = (c.dt.datetime.fromisoformat(started.replace("Z", "+00:00")), pr_filter)
        self.assertIn("default-branch commits in the window", c.render(self.db, 1))
        self.assertIn("label:security", c.render(self.db, 2))
        self.assertEqual(self.db.execute("SELECT count(*) FROM runs").fetchone()[0], 4)

    def test_legacy_runs_gain_empty_filter_without_losing_checkpoint(self):
        path = Path(self.tmp.name) / "legacy.sqlite"
        old = c.sqlite3.connect(path)
        old.execute("CREATE TABLE runs(id INTEGER PRIMARY KEY,repo TEXT,started TEXT,finished TEXT,status TEXT,since TEXT,error TEXT)")
        old.execute("INSERT INTO runs VALUES(1,'org/repo','2026-11-01','2026-11-01','complete','2026-10-25',NULL)")
        old.commit()
        old.close()
        db = c.connect(path)
        self.assertEqual(db.execute("SELECT started,pr_filter FROM runs").fetchone(), ("2026-11-01", ""))
        db.close()

    def test_filter_cannot_override_repository_type_or_window(self):
        for value in ('repo:other/repo', 'org:other', 'user:other', 'is:issue',
                      'type:issue', 'updated:>2020-01-01', 'label:bug OR repo:other/repo'):
            with self.assertRaisesRegex(ValueError, "pr_filter accepts"):
                c.pr_query("org/repo", "2026-11-10", value)
        self.assertEqual(c.pr_query("org/repo", "2026-11-10", '"session resume" in:title,body -label:docs'),
                         'repo:org/repo is:pr updated:>=2026-11-10 "session resume" in:title,body -label:docs')


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
