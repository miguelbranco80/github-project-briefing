#!/usr/bin/env python3
"""Publish an article or record why a collected run needs none."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import collect
from refresh import projects

ENGINE = Path(__file__).resolve().parents[1] / "assets/journal"


def article_metadata(repo, run, since, finished):
    return {
        "run": run, "source": repo, "date": finished[:10], "issue": str(run),
        "window": f"{since} → {finished} (UTC)",
        "title": "TODO: explain the engineering change",
        "description": "TODO: state the practical consequence",
    }


def initialize(site, repo):
    if site.exists():
        return
    with tempfile.TemporaryDirectory(prefix=".journal-init-", dir=site.parent) as temporary:
        staged = Path(temporary) / "site"
        shutil.copytree(ENGINE / "src", staged / "src", ignore=shutil.ignore_patterns(".DS_Store"))
        (staged / "src/_data").mkdir(exist_ok=True)
        (staged / "src/assets/illustrations").mkdir(exist_ok=True)
        (staged / "drafts").mkdir()
        (staged / "src/_data/site.json").write_text(json.dumps({
            "name": f"{repo} fieldnotes",
            "description": f"Engineering updates for {repo}.",
            "repositoryName": repo, "repository": f"https://github.com/{repo}",
        }, indent=2) + "\n")
        staged.rename(site)


def journal(workspace, repo, run, action, reason=None):
    workspace = workspace.resolve()
    row = next((p for p in projects(workspace) if p["repo"].lower() == repo.lower()), None)
    if row is None:
        raise ValueError("Repository is not configured in projects.json")
    repo = row["repo"]
    state = (workspace / row["state_dir"]).resolve()
    if not (state / "activity.sqlite").is_file():
        raise ValueError("Collect project evidence before preparing an entry")
    with (state / "collect.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = collect.connect(state / "activity.sqlite")
        try:
            evidence = db.execute("SELECT since,finished FROM runs WHERE id=? AND repo=? AND status='complete'", (run, repo)).fetchone()
            if not evidence or not evidence[1]:
                raise ValueError("Entry must reference a completed run for this repository")
            site = state / "journal"
            article_path, review_reason = db.execute("SELECT article_path,review_reason FROM runs WHERE id=?", (run,)).fetchone()
            if article_path is not None or review_reason is not None:
                result = {"status": "reviewed", "run": run, "article": article_path, "review_reason": review_reason}
                article = Path(article_path) if article_path else None
                if article is not None and article.parent == site / "src/posts":
                    result.update(site_dir=str(site), output_dir=str(site / "_site"),
                                  reader=str(site / "_site/reader.html"),
                                  html=str(site / "_site/posts" / article.stem / "index.html"),
                                  post_url=f"/posts/{article.stem}/")
                return result
            if not site.resolve().is_relative_to(state):
                raise ValueError("Journal must remain inside the project state directory")
            if action == "skip":
                collect.record_review(db, repo, run, reason=reason)
                return {"status": "reviewed", "run": run, "article": None, "review_reason": reason.strip()}
            initialize(site, repo)
            metadata = article_metadata(repo, run, *evidence)
            filename = f"{metadata['date']}-run-{run}.md"
            published = site / "src/posts" / filename
            draft = site / "drafts" / filename
            article = published if published.exists() else draft
            result = {
                "status": "draft", "site_dir": str(site), "article": str(article),
                "output_dir": str(site / "_site"),
                "reader": str(site / "_site/reader.html"),
                "html": str(site / "_site/posts" / article.stem / "index.html"),
                "post_url": f"/posts/{article.stem}/",
            }
            if action == "prepare":
                if not article.exists():
                    article.write_text("---\n" + json.dumps(metadata, indent=2) + "\n---\n\n")
                return result
            if not article.is_file():
                raise ValueError("Prepare the article before publishing")
            try:
                header, body = article.read_text().removeprefix("---\n").split("\n---\n", 1)
                actual = json.loads(header)
                if not isinstance(actual, dict):
                    raise ValueError("Frontmatter must be an object")
            except ValueError as error:
                raise ValueError("Keep the prepared JSON frontmatter and write the article below it") from error
            if not body.strip() or "<!-- project-briefing: draft -->" in body:
                raise ValueError("Write the article before publishing")
            for key in ("run", "source", "date", "window"):
                if actual.get(key) != metadata[key]:
                    raise ValueError(f"Do not change the collector-derived {key}")
            if not (ENGINE / "node_modules/@11ty/eleventy/cmd.cjs").is_file():
                subprocess.run(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=ENGINE, check=True, timeout=180, stdout=sys.stderr)
            moved = article == draft
            if moved:
                draft.rename(published)
            try:
                subprocess.run([sys.executable, str(ENGINE / "build.py"), str(site)], cwd=site, check=True, timeout=180, stdout=sys.stderr)
            except (OSError, subprocess.SubprocessError):
                if moved:
                    published.rename(draft)
                raise
            collect.record_review(db, repo, run, article=published)
            return {**result, "article": str(published),
                    "status": "built"}
        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "publish", "skip"])
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--reason", help="Why this run needs no article (required for skip)")
    args = parser.parse_args()
    try:
        print(json.dumps(journal(args.workspace, args.repo, args.run, args.action, args.reason)))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Journal update failed: {error}\n")


if __name__ == "__main__":
    main()
