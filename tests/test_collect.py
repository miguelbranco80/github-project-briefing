import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(os.environ.get("PROJECT_BRIEFING_TEST_PACKAGE", Path(__file__).parents[1]))
SCRIPT = ROOT / "skills/project-briefing/scripts/collect.py"
spec = importlib.util.spec_from_file_location("collect", SCRIPT)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def candidates(records, coverage=None):
    return lambda *args, **kwargs: (records, coverage or {})


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.db = c.connect(self.root / "activity.sqlite")
        self.addCleanup(self.db.close)

    def test_sample_is_bounded_and_labels_coverage(self):
        calls = []
        def fetch(endpoint):
            calls.append(endpoint)
            page = int(parse_qs(urlsplit(endpoint).query)["page"][0])
            return [{"id": n} for n in range((page - 1) * 100, page * 100)]
        items, coverage = c.sample("items", 150, fetch)
        self.assertEqual([p["id"] for p in items], list(range(150)))
        self.assertEqual(len(calls), 2)
        self.assertTrue(coverage["limited"])
        items, coverage = c.sample("items", 100, lambda endpoint: [{"id": 1}])
        self.assertEqual(items, [{"id": 1}])
        self.assertFalse(coverage["limited"])

    def test_old_pr_boundary_stops_discovery(self):
        prs = [{"updated_at": "2026-11-15"}, {"updated_at": "2020-01-01"}]
        items, scope = c.sample("pulls", 100, lambda endpoint: prs,
                                stop=lambda pr: pr["updated_at"] < "2026-11-01")
        self.assertEqual(items, prs[:1])
        self.assertFalse(scope["limited"])

    def test_search_reports_incomplete_or_capped_samples(self):
        for total, incomplete, limited in ((1, False, False), (1, True, True), (2000, False, True)):
            with self.subTest(total=total, incomplete=incomplete):
                items, scope = c.sample("search/issues?q=test", 1,
                    lambda endpoint: {"total_count": total, "incomplete_results": incomplete, "items": [{"number": 7}]}, search=True)
                self.assertEqual(items, [{"number": 7}])
                self.assertEqual(scope["limited"], limited)
        with self.assertRaises(ValueError):
            c.sample("search/issues?q=test", 100, lambda endpoint: {}, search=True)

    def test_large_release_history_cannot_block_candidate_collection(self):
        calls = []
        pr = {"number": 7, "title": "Fix cancellation", "updated_at": "2026-11-15T09:00:00Z",
              "body": "Cancel the backend request when a client disconnects.", "html_url": "https://github.com/org/repo/pull/7"}
        def fetch(endpoint):
            calls.append(endpoint)
            if endpoint.startswith("search/issues?"): return {"total_count": 1, "incomplete_results": False}
            if endpoint.startswith("repos/org/repo/pulls?"): return [pr]
            if endpoint == "repos/org/repo": return {"default_branch": "main"}
            if "/commits?" in endpoint: return []
            if "/releases?" in endpoint:
                if parse_qs(urlsplit(endpoint).query)["page"] == ["2"]: return [{"id": 101}]
                return [{"id": n, "tag_name": f"v{n}", "html_url": f"https://example.com/releases/{n}"} for n in range(100)]
            self.fail(f"Unexpected detail or preflight request: {endpoint}")
        run, count = c.refresh(self.db, "org/repo", collector=lambda *args, **kwargs: c.collect(*args, fetch=fetch, **kwargs))
        self.assertEqual(count, 101)
        status, coverage = self.db.execute("SELECT status,coverage FROM runs WHERE id=?", (run,)).fetchone()
        self.assertEqual(status, "complete")
        self.assertTrue(json.loads(coverage)["releases"]["limited"])
        self.assertTrue(c.read_run(self.db, "org/repo", run)["coverage"]["releases"]["limited"])
        self.assertEqual(len(calls), 6)

    def test_filtered_discovery_reads_only_matching_pr_metadata(self):
        calls = []
        def fetch(endpoint):
            calls.append(endpoint)
            self.assertTrue(endpoint.startswith("search/issues?"))
            query = parse_qs(urlsplit(endpoint).query)["q"][0]
            self.assertEqual(query, "repo:org/repo is:pr updated:>=2026-11-14 label:security")
            return {"total_count": 2, "incomplete_results": False,
                    "items": [{"number": 7, "title": "Security change", "body": body}
                              for body in ("Initial proposal", "Proposal")]}
        records, coverage = c.collect("org/repo", "2026-11-14", "2026-11-15", pr_filter="label:security", fetch=fetch)
        self.assertEqual(records[0][:2], ("pr", "7"))
        self.assertEqual(records[0][2]["pr"]["body"], "Proposal")
        self.assertEqual(len(records), 1)
        self.assertEqual(coverage["prs"]["count"], 1)
        self.assertEqual(set(coverage), {"prs"})
        self.assertEqual(len(calls), 2)

    def test_snapshot_deltas_and_unchanged_refresh(self):
        c.refresh(self.db, "org/repo", collector=candidates([("pr", "7", {"body": "proposed"})]))
        c.refresh(self.db, "org/repo", collector=candidates([("pr", "7", {"body": "revised"})]))
        _, count = c.refresh(self.db, "org/repo", collector=candidates([("pr", "7", {"body": "revised"})]))
        before, after = self.db.execute("SELECT before_json,after_json FROM changes WHERE run_id=2").fetchone()
        self.assertEqual(json.loads(before)["body"], "proposed")
        self.assertEqual(json.loads(after)["body"], "revised")
        self.assertEqual(count, 0)

    def test_failed_collection_and_save_keep_previous_checkpoint(self):
        c.refresh(self.db, "org/repo", collector=candidates([("commit", "a", {})]))
        checkpoint = self.db.execute("SELECT started FROM runs WHERE status='complete'").fetchone()[0]
        def failed(*args, **kwargs):
            raise RuntimeError("GitHub unavailable")
        for collector in (failed, candidates([("commit", "b", {}), ("commit", "b", {"changed": True})])):
            with self.assertRaises(Exception):
                c.refresh(self.db, "org/repo", collector=collector)
            self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0], 1)
            self.assertEqual(self.db.execute("SELECT started FROM runs WHERE status='complete'").fetchone()[0], checkpoint)
        self.assertEqual(self.db.execute("SELECT count(*) FROM runs WHERE status='failed'").fetchone()[0], 2)

    def test_actual_checkpoint_window_survives_downtime(self):
        with patch.object(c, "now", return_value="2026-11-01T09:00:00Z"):
            c.refresh(self.db, "org/repo", collector=candidates([]))
        observed = []
        def collect(repo, since, until, **kwargs):
            observed.append(since)
            return [], {"prs": {"count": 0, "limited": False}}
        with patch.object(c, "now", return_value="2026-11-15T09:00:00Z"):
            run, _ = c.refresh(self.db, "org/repo", days=1, collector=collect)
        self.assertEqual(observed, ["2026-10-31T09:00:00Z"])
        self.assertEqual(c.read_run(self.db, "org/repo", run)["since"], observed[0])

    def test_filter_changes_rebaseline_without_removing_old_evidence(self):
        with patch.object(c, "now", return_value="2026-11-01T09:00:00Z"):
            c.refresh(self.db, "org/repo", collector=candidates([("commit", "a", {})]))
        observed = []
        with patch.object(c, "now", return_value="2026-11-15T09:00:00Z"):
            c.refresh(self.db, "org/repo", days=7, pr_filter="label:security",
                      collector=lambda repo, since, until, **kwargs: (observed.append(since) or [], {}))
        self.assertEqual(observed, ["2026-11-08T09:00:00Z"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0], 1)

    def test_offline_queue_and_review_keep_unreviewed_runs(self):
        run, _ = c.refresh(self.db, "org/repo", collector=candidates([
            ("commit", "abc", {"html_url": "https://github.com/org/repo/commit/abc", "commit": {"message": "Cancel stale work"}})]))
        c.refresh(self.db, "org/repo", collector=candidates([]))
        command = [sys.executable, str(SCRIPT), "--repo", "org/repo", "--state-dir", str(self.root)]
        result = subprocess.run(command + ["--pending"], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["pending_runs"], [1, 2])
        result = subprocess.run(command + ["--run", str(run)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["candidates"], [{"kind": "commit", "key": "abc",
            "title": "Cancel stale work", "url": "https://github.com/org/repo/commit/abc", "change": "new"}])
        self.assertEqual(list(self.root.glob("*.md")), [])
        article = self.root / "article.md"
        article.write_text("A reviewed article")
        c.record_review(self.db, "org/repo", run, article=article)
        self.assertEqual(c.pending_runs(self.db, "org/repo"), [2])
        with self.assertRaises(ValueError):
            c.record_review(self.db, "org/repo", run, reason="Already reviewed")
        for repo, number, reason in (("other/repo", 2, "Nothing relevant"),
                                     ("org/repo", 99, "Missing run"), ("org/repo", 2, "  ")):
            with self.assertRaises(ValueError):
                c.record_review(self.db, repo, number, reason=reason)
        with self.assertRaises(ValueError):
            c.read_run(self.db, "other/repo", run)
        self.assertEqual(c.pending_runs(self.db, "org/repo"), [2])

    def test_busy_repo_retries_original_window_after_budget_agreement(self):
        calls = []
        prs = [{"number": n, "title": f"Change {n}", "updated_at": "2026-11-01T08:00:00Z"} for n in range(150)]
        def fetch(endpoint):
            calls.append(endpoint)
            query = parse_qs(urlsplit(endpoint).query)
            if endpoint.startswith("search/issues?"):
                return {"total_count": len(prs), "incomplete_results": False}
            if "/pulls?" in endpoint:
                size, page = int(query["per_page"][0]), int(query["page"][0])
                return prs[(page - 1) * size:page * size]
            if endpoint == "repos/org/repo": return {"default_branch": "main"}
            return []
        collector = lambda *a, **kw: c.collect(*a, **kw, fetch=fetch)
        with patch.object(c, "now", return_value="2026-11-01T09:00:00Z"):
            run, count = c.refresh(self.db, "org/repo", collector=collector)
        blocked = c.read_run(self.db, "org/repo", run)
        self.assertEqual(blocked["status"], "needs_scope")
        self.assertEqual(blocked["coverage"]["prs"]["estimated"], 150)
        self.assertEqual(count, 0)
        self.assertEqual(len(calls), 1)  # Count only; no bulk reads before agreement.
        self.assertEqual(c.pending_runs(self.db, "org/repo"), [])
        self.assertEqual(self.db.execute("SELECT count(*) FROM objects").fetchone()[0], 0)
        with patch.object(c, "now", return_value="2026-11-05T09:00:00Z"):
            run, count = c.refresh(self.db, "org/repo", max_prs=200, collector=collector)
        completed = c.read_run(self.db, "org/repo", run)
        self.assertEqual(completed["status"], "complete")
        self.assertEqual(completed["since"], blocked["since"])
        self.assertEqual(count, 150)
        self.assertEqual(len(completed["candidates"]), 150)
        self.assertEqual(c.pending_runs(self.db, "org/repo"), [run])

    def test_actual_pr_and_commit_overflow_preserve_completed_checkpoint(self):
        for kind in ("pr", "commit"):
            with self.subTest(kind=kind):
                db = c.connect(":memory:")
                try:
                    with patch.object(c, "now", return_value="2026-11-01T09:00:00Z"):
                        c.refresh(db, "org/repo", collector=candidates([]))
                    items = ([{"number": n, "updated_at": "2026-11-02T00:00:00Z"} for n in range(101)]
                             if kind == "pr" else [{"sha": str(n)} for n in range(101)])
                    def fetch(endpoint):
                        query = parse_qs(urlsplit(endpoint).query)
                        # An estimate can lag live PR activity.
                        if endpoint.startswith("search/issues?"):
                            return {"total_count": 0, "incomplete_results": False}
                        if endpoint == "repos/org/repo": return {"default_branch": "main"}
                        if (kind == "pr" and "/pulls?" in endpoint) or (kind == "commit" and "/commits?" in endpoint):
                            size, page = int(query["per_page"][0]), int(query["page"][0])
                            return items[(page - 1) * size:page * size]
                        return []
                    collector = lambda *a, **kw: c.collect(*a, **kw, fetch=fetch)
                    with patch.object(c, "now", return_value="2026-11-03T09:00:00Z"):
                        run, count = c.refresh(db, "org/repo", collector=collector)
                    blocked = c.read_run(db, "org/repo", run)
                    self.assertEqual(blocked["status"], "needs_scope")
                    self.assertEqual(count, 0)
                    with patch.object(c, "now", return_value="2026-11-06T09:00:00Z"):
                        run, count = c.refresh(db, "org/repo", max_prs=101, max_commits=101, collector=collector)
                    completed = c.read_run(db, "org/repo", run)
                    self.assertEqual(completed["status"], "complete")
                    self.assertEqual(completed["since"], "2026-10-31T09:00:00Z")
                    self.assertEqual(count, 101)  # Exactly the agreed limit is allowed.
                finally:
                    db.close()

    def test_incomplete_estimate_and_search_ceiling_require_scope(self):
        for total, incomplete in ((1, True), (1001, False)):
            calls = []
            def fetch(endpoint):
                calls.append(endpoint)
                return {"total_count": total, "incomplete_results": incomplete}
            records, coverage = c.collect("org/repo", "2026-11-01", "2026-11-15", max_prs=2000,
                                          pr_filter="label:bug", fetch=fetch)
            self.assertEqual(records, [])
            self.assertTrue(coverage["prs"]["limited"])
            self.assertEqual(coverage["prs"]["limit"], 1000)
            self.assertEqual(len(calls), 1)

    def test_filters_cannot_change_repository_or_time_window(self):
        for value in ("repo:other/repo", "org:other", "user:other", "is:issue", "type:issue", "updated:>2020-01-01", "label:bug OR repo:other/repo"):
            with self.assertRaises(ValueError):
                c.pr_query("org/repo", "2026-11-10", value)


if __name__ == "__main__":
    unittest.main()
