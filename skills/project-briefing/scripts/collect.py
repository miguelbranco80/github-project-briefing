#!/usr/bin/env python3
"""Collect a bounded set of GitHub story candidates; keep snapshots and review history."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import urllib.parse


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def api(endpoint):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GH_DEBUG")}
    env.update(GH_PROMPT_DISABLED="1", GH_PAGER="cat", NO_COLOR="1")
    for attempt in range(3):
        result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True,
                                timeout=90, env=env)
        if result.returncode == 0:
            return json.loads(result.stdout)
        if not re.search(r"HTTP (429|5\d\d)", result.stderr) or attempt == 2:
            status = re.search(r"HTTP (\d{3})", result.stderr)
            raise RuntimeError(f"GitHub read failed: {endpoint}: {status.group(0) if status else 'check gh access'}")
        time.sleep(2 ** attempt)


def sample(endpoint, limit, fetch=api, stop=None, search=False):
    """Return candidates plus an explicit coverage note; never paginate beyond the budget."""
    items = []
    page = 1
    incomplete = False
    while len(items) <= limit:
        size = min(100, limit)
        sep = "&" if "?" in endpoint else "?"
        result = fetch(f"{endpoint}{sep}per_page={size}&page={page}")
        total = None
        if search:
            if (not isinstance(result, dict) or type(result.get("total_count")) is not int
                    or result["total_count"] < 0 or type(result.get("incomplete_results")) is not bool):
                raise ValueError("GitHub returned an invalid search response")
            total = result["total_count"]
            incomplete = incomplete or result["incomplete_results"]
            result = result.get("items")
        if not isinstance(result, list):
            raise ValueError(f"Expected a list from {endpoint}")
        for item in result:
            if stop and stop(item):
                return items, {"count": len(items), "limited": incomplete}
            if len(items) == limit:
                return items, {"count": len(items), "limited": True}
            items.append(item)
        if len(result) < size or (total is not None and len(items) >= total):
            return items, {"count": len(items), "limited": incomplete or (total is not None and len(items) < total)}
        page += 1
    return items, {"count": len(items), "limited": True}


def pr_query(repo, since, pr_filter):
    if re.search(r"\b(?:repo|org|user|is|type|updated)\s*:|\bOR\b", pr_filter, re.I):
        raise ValueError("pr_filter accepts labels, authors and keywords; repository, type and window are supplied automatically")
    return f"repo:{repo} is:pr updated:>={since} {pr_filter}".strip()


def estimate(repo, since, max_prs=100, pr_filter="", fetch=api):
    query = urllib.parse.urlencode({"q": pr_query(repo, since, pr_filter), "per_page": 1})
    result = fetch(f"search/issues?{query}")
    if (type(result.get("total_count")) is not int or result["total_count"] < 0
            or type(result.get("incomplete_results")) is not bool):
        raise ValueError("GitHub returned an invalid workload estimate")
    limit = min(max_prs, 1000) if pr_filter else max_prs
    return {"estimated": result["total_count"], "limit": limit,
            "limited": result["incomplete_results"] or result["total_count"] > limit}


def collect(repo, since, until, max_prs=100, max_commits=100, pr_filter="", fetch=api):
    workload = estimate(repo, since, max_prs, pr_filter, fetch)
    if workload["limited"]:
        return [], {"prs": {"count": 0, **workload}}
    base = f"repos/{repo}"
    if pr_filter:
        query = urllib.parse.urlencode({"q": pr_query(repo, since, pr_filter), "sort": "updated", "order": "desc"})
        prs, coverage = sample(f"search/issues?{query}", min(max_prs, 1000), fetch, search=True)
    else:
        prs, coverage = sample(f"{base}/pulls?state=all&sort=updated&direction=desc", max_prs,
                               fetch, stop=lambda pr: pr["updated_at"] < since)
    # An updated PR can move between pages while GitHub serves the sample.
    prs = list({pr["number"]: pr for pr in prs}.values())
    coverage["count"] = len(prs)
    records = [("pr", str(pr["number"]), {"pr": pr}) for pr in prs]
    coverage = {"prs": {**workload, **coverage}}
    if not pr_filter:
        branch = urllib.parse.quote(fetch(base)["default_branch"], safe="")
        commits, coverage["commits"] = sample(f"{base}/commits?sha={branch}&since={since}&until={until}", max_commits, fetch)
        coverage["commits"]["limit"] = max_commits
        releases, coverage["releases"] = sample(f"{base}/releases", 100, fetch)
        records.extend(("commit", commit["sha"], commit) for commit in commits)
        records.extend(("release", str(release["id"]), release) for release in releases)
    return records, coverage


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS runs(
      id INTEGER PRIMARY KEY, repo TEXT NOT NULL, started TEXT NOT NULL,
      finished TEXT, status TEXT NOT NULL, since TEXT NOT NULL, error TEXT,
      pr_filter TEXT NOT NULL DEFAULT '', coverage TEXT NOT NULL DEFAULT '{}',
      article_path TEXT, review_reason TEXT, days INTEGER NOT NULL DEFAULT 7);
    CREATE TABLE IF NOT EXISTS objects(
      repo TEXT, kind TEXT, key TEXT, digest TEXT NOT NULL, payload TEXT NOT NULL,
      PRIMARY KEY(repo,kind,key));
    CREATE TABLE IF NOT EXISTS changes(
      run_id INTEGER, kind TEXT, key TEXT, before_json TEXT, after_json TEXT,
      UNIQUE(run_id,kind,key));
    """)
    return db


def save(db, run, repo, records):
    changed = 0
    for kind, key, payload in records:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(body.encode()).hexdigest()
        old = db.execute("SELECT digest,payload FROM objects WHERE repo=? AND kind=? AND key=?",
                         (repo, kind, key)).fetchone()
        if old and old[0] == digest:
            continue
        db.execute("INSERT INTO changes VALUES(?,?,?,?,?)", (run, kind, key, old[1] if old else None, body))
        db.execute("INSERT OR REPLACE INTO objects VALUES(?,?,?,?,?)", (repo, kind, key, digest, body))
        changed += 1
    return changed


def scan_since(db, repo, days, pr_filter, started):
    last = db.execute("SELECT started,pr_filter FROM runs WHERE repo=? AND status='complete' ORDER BY id DESC LIMIT 1", (repo,)).fetchone() if db else None
    if last and last[1] == pr_filter:
        anchor, overlap = last[0], dt.timedelta(hours=24)
    else:
        attempt = db.execute("SELECT since,pr_filter,days FROM runs WHERE repo=? ORDER BY id DESC LIMIT 1", (repo,)).fetchone() if db else None
        if attempt and attempt[1:] == (pr_filter, days):
            return attempt[0]
        anchor, overlap = started, dt.timedelta(days=days)
    return (dt.datetime.fromisoformat(anchor.replace("Z", "+00:00")) - overlap).isoformat(timespec="seconds").replace("+00:00", "Z")


def refresh(db, repo, days=7, max_prs=100, pr_filter="", collector=collect, max_commits=100):
    started = now()
    since = scan_since(db, repo, days, pr_filter, started)
    run = db.execute("INSERT INTO runs(repo,started,status,since,pr_filter,days) VALUES(?,?,'running',?,?,?)",
                     (repo, started, since, pr_filter, days)).lastrowid
    db.commit()
    try:
        records, coverage = collector(repo, since, started, max_prs=max_prs, max_commits=max_commits, pr_filter=pr_filter)
        limited = [kind for kind in ("prs", "commits") if coverage.get(kind, {}).get("limited")]
        if limited:
            with db:
                db.execute("UPDATE runs SET status='needs_scope',finished=?,coverage=?,error=? WHERE id=?",
                           (now(), json.dumps(coverage), "Collection incomplete: " + ", ".join(limited) + ". Review scope or budgets; checkpoint retained.", run))
            return run, 0
        with db:
            count = save(db, run, repo, records)
            db.execute("UPDATE runs SET status='complete',finished=?,coverage=? WHERE id=?",
                       (now(), json.dumps(coverage), run))
        return run, count
    except Exception as error:
        db.rollback()
        with db:
            db.execute("UPDATE runs SET status='failed',finished=?,error=? WHERE id=?", (now(), str(error), run))
        raise


def read_run(db, repo, run):
    fields = ("run", "since", "finished", "status", "error", "pr_filter", "coverage", "article", "review_reason")
    row = db.execute("""SELECT id,since,finished,status,error,pr_filter,coverage,article_path,review_reason
                        FROM runs WHERE id=? AND repo=?""", (run, repo)).fetchone()
    if row is None:
        raise ValueError("Run does not belong to this repository")
    result = dict(zip(fields, row))
    result["coverage"] = json.loads(result["coverage"])
    result["candidates"] = []
    for kind, key, before, body in db.execute("SELECT kind,key,before_json,after_json FROM changes WHERE run_id=? ORDER BY kind,key", (run,)):
        payload = json.loads(body)
        item = payload["pr"] if kind == "pr" else payload
        title = item.get("title") or item.get("tag_name") or item.get("commit", {}).get("message", key).splitlines()[0]
        result["candidates"].append({"kind": kind, "key": key, "title": " ".join(str(title).split()),
                                     "url": item.get("html_url"), "change": "updated" if before else "new"})
    return result


def pending_runs(db, repo):
    return [run for (run,) in db.execute("""
        SELECT id FROM runs WHERE repo=? AND status='complete'
        AND article_path IS NULL AND review_reason IS NULL ORDER BY id
    """, (repo,))]


def record_review(db, repo, run, article=None, reason=None):
    if (article is None) == (reason is None):
        raise ValueError("Provide an article or a reason for not publishing")
    if article is not None and (not article.is_file() or not article.read_text().strip()):
        raise ValueError("A saved article is required")
    if reason is not None and not reason.strip():
        raise ValueError("Explain why no article is needed")
    with db:
        result = db.execute("""UPDATE runs SET article_path=?,review_reason=?
            WHERE id=? AND repo=? AND status='complete' AND article_path IS NULL AND review_reason IS NULL""",
            (str(article.resolve()) if article else None, reason.strip() if reason is not None else None, run, repo))
        if result.rowcount != 1:
            raise ValueError("Run must be completed, unreviewed and belong to this repository")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--max-prs", type=int, default=100)
    parser.add_argument("--max-commits", type=int, default=100)
    parser.add_argument("--pr-filter", default="")
    reads = parser.add_mutually_exclusive_group()
    reads.add_argument("--estimate", action="store_true", help="Count PR workload without collecting or creating project state")
    reads.add_argument("--pending", action="store_true", help="List unreviewed runs without accessing GitHub")
    reads.add_argument("--run", type=int, help="Read a saved run and its candidates without accessing GitHub")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo) or min(args.days, args.max_prs, args.max_commits) < 1:
        parser.error("Use owner/repository and positive days/max-prs/max-commits")
    args.pr_filter = args.pr_filter.strip()
    try:
        pr_query(args.repo, now(), args.pr_filter)
    except ValueError as error:
        parser.error(str(error))
    if (args.pending or args.run is not None) and not (args.state_dir / "activity.sqlite").is_file():
        parser.error("No collection database exists for this project")
    if args.estimate:
        db = connect(args.state_dir / "activity.sqlite") if (args.state_dir / "activity.sqlite").is_file() else None
        try:
            since = scan_since(db, args.repo, args.days, args.pr_filter, now())
            print(json.dumps({"since": since, **estimate(args.repo, since, args.max_prs, args.pr_filter)}))
        finally:
            if db is not None:
                db.close()
        return
    args.state_dir.mkdir(parents=True, exist_ok=True)
    import fcntl
    with (args.state_dir / "collect.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(args.state_dir / "activity.sqlite")
        try:
            if args.pending:
                result = {"pending_runs": pending_runs(db, args.repo)}
            elif args.run is not None:
                result = read_run(db, args.repo, args.run)
            else:
                run, count = refresh(db, args.repo, args.days, args.max_prs, args.pr_filter, max_commits=args.max_commits)
                status, coverage, error = db.execute("SELECT status,coverage,error FROM runs WHERE id=?", (run,)).fetchone()
                coverage = json.loads(coverage)
                result = {"status": status, "run": run, "changed_records": count,
                          "coverage": coverage, "pending_runs": pending_runs(db, args.repo)}
                if error:
                    result["error"] = error
            print(json.dumps(result))
            if result.get("status") == "needs_scope":
                raise SystemExit(1)
        except Exception as error:
            print(json.dumps({"status": "failed", "error": str(error)}))
            raise SystemExit(1)
        finally:
            db.close()


if __name__ == "__main__":
    main()
