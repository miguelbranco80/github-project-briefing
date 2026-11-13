"""Run the packaged journal commands against disposable, generic project data."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import unittest


ROOT = Path(os.environ.get("PROJECT_BRIEFING_TEST_PACKAGE", Path(__file__).resolve().parents[1])).resolve()
SKILL = ROOT / "skills/project-briefing"
SCRIPT = SKILL / "scripts/journal.py"


def snapshot(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()}


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="project-journal-test-")
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.state = self.workspace / "data/example--widgets"
        self.state.mkdir(parents=True)
        (self.workspace / "projects.json").write_text(json.dumps({"projects": [
            {"repo": "example/widgets", "state_dir": "data/example--widgets"}
        ]}))
        with sqlite3.connect(self.state / "activity.sqlite") as db:
            db.execute("CREATE TABLE runs(id INTEGER PRIMARY KEY,repo TEXT,started TEXT,finished TEXT,status TEXT,since TEXT,error TEXT)")
            db.executemany("INSERT INTO runs VALUES(?,?,?,?,?,?,NULL)", [
                (1, "example/widgets", "2026-11-10T12:00:00Z", "2026-11-10T12:01:00Z", "complete", "2026-11-03T12:00:00Z"),
                (2, "example/widgets", "2026-11-11T12:00:00Z", "2026-11-11T12:01:00Z", "complete", "2026-11-09T12:00:00Z"),
                (3, "example/widgets", "2026-11-12T12:00:00Z", None, "failed", "2026-11-10T12:00:00Z"),
            ])

    def command(self, action, run=1, succeeds=True, repo="example/widgets"):
        result = subprocess.run(["python3", str(SCRIPT), action, "--workspace", str(self.workspace),
                                 "--repo", repo, "--run", str(run)],
                                capture_output=True, text=True, timeout=60)
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def draft(self, run=1):
        result = self.command("prepare", run)
        site = Path(result["site_dir"])
        dependencies = SKILL / "journal/node_modules"
        self.assertTrue((dependencies / "@11ty/eleventy/cmd.cjs").is_file(),
                        "Run npm ci --prefix skills/project-briefing/journal before journal tests")
        if not (site / "node_modules").exists():
            (site / "node_modules").symlink_to(dependencies, target_is_directory=True)
        return result

    def author(self, run=1, artwork=False):
        result = self.draft(run)
        article = Path(result["article"])
        metadata = json.loads(article.read_text().split("---", 2)[1])
        metadata.update(title=f"Engineering update {run}", description="An evidence-linked update with literal --- punctuation.",
                        topics=[{"label": "Actual heading", "id": "actual-heading"}])
        if artwork:
            metadata.update(cover=f"/assets/illustrations/run-{run}.svg",
                            coverAlt="Disposable test fixture.", coverCaption="Test artwork fixture.")
        article.write_text("---\n" + json.dumps(metadata, indent=2) +
                           "\n---\n\n## Actual heading\n\nA [primary source](https://example.com/source).\n")
        if artwork:
            site = Path(result["site_dir"])
            (site / "src/assets/illustrations" / f"run-{run}.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="20"><rect width="30" height="20" fill="navy"/></svg>')
        return result

    def test_prepare_is_generic_and_never_overwrites_draft(self):
        draft = self.draft()
        article = Path(draft["article"])
        metadata = json.loads(article.read_text().split("---", 2)[1])
        self.assertEqual(metadata["window"], "2026-11-03T12:00:00Z → 2026-11-10T12:01:00Z (UTC)")
        self.assertNotIn("cover", metadata)
        self.assertNotIn("coverAlt", metadata)
        article.write_text(article.read_text() + "\nPreserve this draft.\n")
        before = article.read_bytes()
        self.command("prepare")
        self.assertEqual(article.read_bytes(), before)
        site = json.loads((Path(draft["site_dir"]) / "src/_data/site.json").read_text())
        self.assertEqual(site["repository"], "https://github.com/example/widgets")
        self.assertEqual(len(list(article.parent.glob("*.md"))), 1)

    def test_two_posts_archive_and_delivery_state_survive_retry(self):
        first = self.author(artwork=True)
        built = self.command("publish")
        self.assertEqual(built["status"], "built")
        article_hash = hashlib.sha256(Path(built["article"]).read_bytes()).hexdigest()
        art = Path(first["site_dir"]) / "src/assets/illustrations/run-1.svg"
        art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
        self.author(2)
        second = self.command("publish", 2)
        site = Path(second["site_dir"]) / "_site"
        homepage, archive = (site / "index.html").read_text(), (site / "archive/index.html").read_text()
        featured = homepage.split('class="featured-story text-only"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("<img", featured)
        self.assertIn("run-1.svg", homepage)
        second_html = (site / second["post_url"].lstrip("/") / "index.html").read_text()
        self.assertNotIn('class="article-cover"', second_html)
        self.assertNotIn('src=""', homepage + archive + second_html)
        self.assertIn("Engineering update 2", featured)
        for entry in (built, second):
            self.assertIn(entry["post_url"], archive)
            self.assertTrue((site / entry["post_url"].lstrip("/") / "index.html").is_file())
        self.assertEqual(hashlib.sha256(Path(built["article"]).read_bytes()).hexdigest(), article_hash)
        self.assertEqual(hashlib.sha256(art.read_bytes()).hexdigest(), art_hash)
        with sqlite3.connect(self.state / "activity.sqlite") as db:
            self.assertEqual(db.execute("SELECT briefing_path FROM run_outputs WHERE run_id=1").fetchone()[0], built["article"])
            db.execute("UPDATE run_outputs SET delivery_status='confirmed' WHERE run_id=1")
        before = snapshot(site)
        retry = self.command("publish")
        self.assertEqual(retry["status"], "recorded")
        self.assertEqual(retry["delivery_status"], "confirmed")
        self.assertEqual(retry["output_dir"], built["output_dir"])
        self.assertEqual(retry["post_url"], built["post_url"])
        self.assertEqual(snapshot(site), before)

    def test_starter_cannot_publish_with_only_metadata_filled(self):
        self.author()
        first = self.command("publish")
        previous = snapshot(Path(first["output_dir"]))
        draft = self.draft(2)
        article = Path(draft["article"])
        metadata, body = article.read_text().removeprefix("---\n").split("\n---\n", 1)
        metadata = json.loads(metadata)
        metadata.update(title="A finished headline", description="A finished description.")
        article.write_text("---\n" + json.dumps(metadata) + "\n---\n" + body)
        failed = self.command("publish", 2, succeeds=False)
        self.assertIn("Replace the article scaffold", failed.stderr)
        self.assertEqual(snapshot(Path(first["output_dir"])), previous)
        self.assertTrue(article.is_file())
        with sqlite3.connect(self.state / "activity.sqlite") as db:
            self.assertIsNone(db.execute("SELECT 1 FROM run_outputs WHERE run_id=2").fetchone())
        self.author(2)
        self.assertEqual(self.command("publish", 2)["status"], "built")

    def test_invalid_entry_retains_good_site_and_reporting_backlog(self):
        self.author()
        first = self.command("publish")
        previous = snapshot(Path(first["output_dir"]))
        draft = self.author(2)
        article = Path(draft["article"])
        good = article.read_text()
        variants = {
            "missing diagram": good + "\n![Request path](/assets/diagrams/absent.svg)\n",
            "missing optional cover": good.replace('"topics":', '"cover": "/assets/absent.png", "coverAlt": "Missing optional art", "topics":'),
            "cover without alt": good.replace('"topics":', '"cover": "/assets/favicon.svg", "topics":'),
            "broken anchor": good.replace('"id": "actual-heading"', '"id": "absent-heading"'),
            "broken link": good + "\n[Broken](/no-such-page/)\n",
            "placeholder": good.replace('"title": "Engineering update 2"', '"title": "TODO: headline"'),
            "changed evidence": good.replace("2026-11-09T12:00:00Z", "2020-01-01T00:00:00Z"),
        }
        for name, content in variants.items():
            with self.subTest(name=name):
                article.write_text(content)
                self.command("publish", 2, succeeds=False)
                self.assertEqual(snapshot(Path(first["output_dir"])), previous)
                with sqlite3.connect(self.state / "activity.sqlite") as db:
                    self.assertIsNone(db.execute("SELECT 1 FROM run_outputs WHERE run_id=2").fetchone())
        article.write_text(good)
        self.assertEqual(self.command("publish", 2)["status"], "built")

    def test_text_only_publication_needs_no_image_provenance(self):
        draft = self.author()
        Path(draft["prompts"]).unlink()
        built = self.command("publish")
        output = Path(built["output_dir"])
        for page in (output / "index.html", output / "archive/index.html",
                     output / built["post_url"].lstrip("/") / "index.html"):
            self.assertNotIn("<img", page.read_text())
        self.assertFalse(any((output / "assets/illustrations").glob("*")))

    def test_optional_diagram_is_copied_and_linked_without_cover(self):
        draft = self.author()
        diagram = Path(draft["site_dir"]) / "src/assets/diagrams/request-path.svg"
        diagram.parent.mkdir()
        diagram.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 40" '
                           'role="img" aria-label="Request path"><text x="5" y="25">'
                           'Browser → API → database</text></svg>')
        article = Path(draft["article"])
        with article.open("a") as output:
            output.write("\n![Request path](/assets/diagrams/request-path.svg)\n"
                         "\nDiagram source: [reviewed implementation](https://example.com/source).\n")
        built = self.command("publish")
        output = Path(built["output_dir"])
        html = (output / built["post_url"].lstrip("/") / "index.html").read_text()
        self.assertIn('src="/assets/diagrams/request-path.svg"', html)
        self.assertIn("https://example.com/source", html)
        self.assertEqual((output / "assets/diagrams/request-path.svg").read_bytes(), diagram.read_bytes())
        self.assertNotIn('class="article-cover"', html)

    def test_unfinished_draft_does_not_block_other_post(self):
        first = self.author()
        pending = self.draft(2)
        draft_bytes = Path(pending["article"]).read_bytes()
        self.assertEqual(self.command("publish")["status"], "built")
        self.assertEqual(Path(pending["article"]).read_bytes(), draft_bytes)
        site = Path(first["output_dir"])
        self.assertNotIn("run-2", (site / "archive/index.html").read_text())
        self.assertFalse((site / "drafts").exists())

    def test_reject_unconfigured_repository_and_failed_run(self):
        self.command("prepare", repo="other/project", succeeds=False)
        self.command("prepare", run=3, succeeds=False)
        self.assertFalse((self.state / "journal").exists())


class PackageSelectionTests(unittest.TestCase):
    def test_all_runtime_resources_selected_without_test_data(self):
        manifest = (ROOT / "CLAW.md").read_text()
        selected = re.findall(r"^    - source: (.+)$", manifest, re.MULTILINE)
        expected = {p.relative_to(ROOT).as_posix() for p in SKILL.rglob("*")
                    if p.is_file() and not any(part in {"node_modules", "__pycache__", "_site"} for part in p.parts)}
        self.assertEqual(set(selected), expected)
        self.assertEqual(len(selected), len(set(selected)))
        for name in selected:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())
                self.assertNotIn("/home/miguel/", (ROOT / name).read_text())
                self.assertNotIn("openclaw-enterprise", (ROOT / name).read_text())
        self.assertIn("scripts/journal.py", manifest)
        self.assertNotIn("image-prompts.json", selected)
        self.assertEqual(manifest.count("id: daily-project-briefing"), 1)


if __name__ == "__main__":
    unittest.main()
