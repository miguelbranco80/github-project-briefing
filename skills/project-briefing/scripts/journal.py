#!/usr/bin/env python3
"""Prepare and build a journal entry for an existing completed collection run."""
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

ENGINE = Path(__file__).resolve().parents[1] / "journal"


def article_metadata(repo, run, since, finished):
    return {
        "run": run, "source": repo, "date": finished[:10], "issue": str(run),
        "window": f"{since} → {finished} (UTC)",
        "title": "TODO: explain the engineering change",
        "description": "TODO: state the practical consequence",
        "cover": f"/assets/illustrations/run-{run}.png",
        "coverAlt": "TODO: describe the generated image",
        "coverCaption": "TODO: a short editorial caption",
        "topics": [{"label": "First story", "id": "the-first-engineering-change"}],
    }


def initialize(site, repo):
    if site.exists():
        return
    with tempfile.TemporaryDirectory(prefix=".journal-init-", dir=site.parent) as temporary:
        staged = Path(temporary) / "site"
        shutil.copytree(ENGINE, staged, ignore=shutil.ignore_patterns("node_modules", "_site", ".build-*", "__pycache__"))
        (staged / "src/_data").mkdir(exist_ok=True)
        (staged / "src/assets/illustrations").mkdir(exist_ok=True)
        (staged / "drafts").mkdir()
        (staged / "src/_data/site.json").write_text(json.dumps({
            "name": f"{repo} fieldnotes",
            "description": f"Engineering updates for {repo}.",
            "repositoryName": repo, "repository": f"https://github.com/{repo}",
        }, indent=2) + "\n")
        (staged / "image-prompts.json").write_text('{"images": []}\n')
        staged.rename(site)


def journal(workspace, repo, run, action):
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
            existing = db.execute("SELECT briefing_path,delivery_status FROM run_outputs WHERE run_id=?", (run,)).fetchone()
            if existing:
                return {"status": "recorded", "article": existing[0], "delivery_status": existing[1]}
            site = state / "journal"
            if not site.resolve().is_relative_to(state):
                raise ValueError("Journal must remain inside the project state directory")
            initialize(site, repo)
            metadata = article_metadata(repo, run, *evidence)
            filename = f"{metadata['date']}-run-{run}.md"
            published = site / "src/posts" / filename
            draft = site / "drafts" / filename
            article = published if published.exists() else draft
            result = {
                "status": "draft", "site_dir": str(site), "article": str(article),
                "cover": str(site / "src" / metadata["cover"].lstrip("/")),
                "prompts": str(site / "image-prompts.json"),
                "output_dir": str(site / "_site"),
                "post_url": f"/posts/{article.stem}/",
            }
            if action == "prepare":
                if not article.exists():
                    starter = (site / "templates/post.md").read_text().split("---", 2)[2].lstrip()
                    article.write_text("---\n" + json.dumps(metadata, indent=2) + "\n---\n\n" + starter)
                return result
            if not article.is_file():
                raise ValueError("Prepare the article before publishing")
            try:
                actual = json.loads(article.read_text().removeprefix("---\n").split("\n---\n", 1)[0])
            except (ValueError, IndexError) as error:
                raise ValueError("Keep the prepared JSON frontmatter; edit its values and the Markdown body") from error
            for key in ("run", "source", "date", "window"):
                if actual.get(key) != metadata[key]:
                    raise ValueError(f"Do not change the collector-derived {key}")
            images = json.loads((site / "image-prompts.json").read_text()).get("images", [])
            cover = "src" + actual.get("cover", "")
            if not any(image.get("post") == article.stem and image.get("asset") == cover
                       and image.get("prompt") and image.get("tool") for image in images):
                raise ValueError("Record the generated cover's post, asset, exact prompt and tool in image-prompts.json")
            if not (site / "node_modules/@11ty/eleventy/cmd.cjs").is_file():
                subprocess.run(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=site, check=True, timeout=180, stdout=sys.stderr)
            moved = article == draft
            if moved:
                draft.rename(published)
            try:
                subprocess.run([sys.executable, "build.py"], cwd=site, check=True, timeout=180, stdout=sys.stderr)
            except (OSError, subprocess.SubprocessError):
                if moved:
                    published.rename(draft)
                raise
            collect.record_output(db, repo, run, published, "pending")
            return {**result, "article": str(published), "cover": str(site / cover),
                    "status": "built", "delivery_status": "pending"}
        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "publish"])
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run", type=int, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(journal(args.workspace, args.repo, args.run, args.action)))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Journal update failed: {error}\n")


if __name__ == "__main__":
    main()
