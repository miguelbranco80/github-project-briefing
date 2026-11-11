#!/usr/bin/env python3
"""Read-only GitHub collection; Python stdlib + authenticated gh."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import urllib.parse

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def api(endpoint):
    for attempt in range(3):
        p = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True, timeout=90)
        if p.returncode == 0:
            return json.loads(p.stdout)
        if not re.search(r"HTTP (429|5\d\d)", p.stderr) or attempt == 2:
            raise RuntimeError(f"GitHub read failed: {endpoint}: {p.stderr.strip()}")
        time.sleep(2 ** attempt)

def pages(endpoint, stop=None, fetch=api):
    result = []
    for page in range(1, 1001):
        sep = "&" if "?" in endpoint else "?"
        batch = fetch(f"{endpoint}{sep}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError(f"Expected a list: {endpoint}")
        for item in batch:
            if stop and stop(item):
                return result
            result.append(item)
        if len(batch) < 100:
            return result
    raise RuntimeError(f"Pagination safety limit reached: {endpoint}")

def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS runs(
      id INTEGER PRIMARY KEY, repo TEXT NOT NULL, started TEXT NOT NULL,
      finished TEXT, status TEXT NOT NULL, since TEXT NOT NULL, error TEXT);
    CREATE TABLE IF NOT EXISTS objects(
      repo TEXT, kind TEXT, key TEXT, digest TEXT NOT NULL, payload TEXT NOT NULL,
      PRIMARY KEY(repo,kind,key));
    CREATE TABLE IF NOT EXISTS changes(
      run_id INTEGER, kind TEXT, key TEXT, before_json TEXT, after_json TEXT,
      UNIQUE(run_id,kind,key));
    """)
    return db

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)

def save(db, run, repo, records):
    changed = 0
    for kind, key, payload in records:
        body = canonical(payload)
        digest = hashlib.sha256(body.encode()).hexdigest()
        old = db.execute("SELECT digest,payload FROM objects WHERE repo=? AND kind=? AND key=?",
                         (repo, kind, key)).fetchone()
        if old and old[0] == digest:
            continue
        db.execute("INSERT INTO changes VALUES(?,?,?,?,?)", (run, kind, key, old[1] if old else None, body))
        db.execute("INSERT OR REPLACE INTO objects VALUES(?,?,?,?,?)", (repo, kind, key, digest, body))
        changed += 1
    return changed

def collect(db, repo, since, until, reconcile=False, fetch=api, max_prs=100):
    base = f"repos/{repo}"
    metadata = fetch(base)
    # Complete open inventory plus updated closed/merged inventory; no Search API cap.
    opened = pages(f"{base}/pulls?state=open&sort=updated&direction=desc", fetch=fetch)
    recent = pages(f"{base}/pulls?state=closed&sort=updated&direction=desc",
                   stop=lambda p: p["updated_at"] < since, fetch=fetch)
    prs = {str(p["number"]): p for p in opened + recent}
    previous = {key: json.loads(body) for key, body in db.execute(
        "SELECT key,payload FROM objects WHERE repo=? AND kind='pr'", (repo,))}
    for key, old in previous.items():
        if key not in prs and old["pr"]["state"] == "open":
            prs[key] = fetch(f"{base}/pulls/{key}")

    def detail(pair):
        key, p = pair
        old = previous.get(key)
        if not reconcile and old and old["pr"]["updated_at"] == p["updated_at"] and old["pr"]["head"]["sha"] == p["head"]["sha"]:
            return "pr", key, old
        # Fetch detail first; activity arriving afterward is picked up by overlap next run.
        p = fetch(f"{base}/pulls/{key}")
        files = pages(f"{base}/pulls/{key}/files", fetch=fetch)
        if len(files) >= 3000:
            raise RuntimeError(f"PR {key}: GitHub file-list cap; cannot claim complete coverage")
        result = {"pr": p, "files": files,
                  "comments": pages(f"{base}/issues/{key}/comments", fetch=fetch),
                  "reviews": pages(f"{base}/pulls/{key}/reviews", fetch=fetch),
                  "review_comments": pages(f"{base}/pulls/{key}/comments", fetch=fetch)}
        return "pr", key, result

    if len(prs) > max_prs:
        raise RuntimeError(f"Preflight: {len(opened)} open PRs, {len(recent)} recently updated closed PRs; {len(prs)} unique PRs require coverage, above --max-prs {max_prs}. No PR conversations fetched. Narrow the project scope or explicitly raise --max-prs. No checkpoint advanced.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(detail, prs.items()))
    branch = urllib.parse.quote(metadata["default_branch"], safe="")
    commits = pages(f"{base}/commits?sha={branch}&since={since}&until={until}", fetch=fetch)
    records.extend(("commit", c["sha"], c) for c in commits)
    # Releases are not sorted by update time, so enumerate and filter locally.
    releases = pages(f"{base}/releases", fetch=fetch)
    records.extend(("release", str(r["id"]), r) for r in releases if r["created_at"] >= since or r.get("published_at", "") >= since)
    return records

def clean(value):
    return " ".join(str(value or "").replace("|", "/").split())

def render(db, run):
    row = db.execute("SELECT repo,started,finished,status,since,error FROM runs WHERE id=?", (run,)).fetchone()
    repo, started, finished, status, since, error = row
    prior = db.execute("SELECT count(*) FROM runs WHERE repo=? AND status='complete' AND id<?", (repo,run)).fetchone()[0]
    lines = [f"# {repo}: {'baseline' if not prior else 'changes'}", "",
             f"Run {run}; status: {status}; started: {started}; finished: {finished or 'not completed'}.",
             f"Window starts {since}. Includes all currently open PRs, recently updated closed PRs, default-branch commits and releases.",
             "PR issue comments, reviews, inline comments and changed paths are captured. GitHub Discussions, ordinary issues, CI, RFC file contents, and deployment proof are NOT covered.",
             "Incremental scans reuse unchanged PRs; use --reconcile to re-fetch all tracked open/recent PR conversations. GitHub is not a transactional snapshot.", ""]
    if status != "complete":
        return "\n".join(lines + [f"Coverage incomplete: {clean(error)}. Last successful checkpoint retained.", ""])
    groups = {"Merged PRs": [], "Open PRs / updates": [], "Closed without merge": [], "Default-branch commits": [], "Releases": []}
    for kind, key, before, after in db.execute("SELECT kind,key,before_json,after_json FROM changes WHERE run_id=? ORDER BY kind,key", (run,)):
        p = json.loads(after)
        if kind == "pr":
            pr = p["pr"]
            paths = [f["filename"] for f in p["files"]]
            rfc = any(re.search(r"(^|/)(rfcs?|proposals?)(/|[.-])", path, re.I) for path in paths)
            group = "Merged PRs" if pr.get("merged_at") else "Open PRs / updates" if pr["state"] == "open" else "Closed without merge"
            users = sorted({c.get("user", {}).get("login", "unknown") for name in ("comments","reviews","review_comments") for c in p[name] if c.get("user",{}).get("type") != "Bot"})
            tag = " **RFC/proposal paths touched; acceptance and implementation unverified.**" if rfc else ""
            previous = json.loads(before) if before else None
            if previous:
                old_ids = {(name,c["id"]): canonical(c) for name in ("comments","reviews","review_comments") for c in previous[name]}
                count = sum(old_ids.get((name,c["id"])) != canonical(c) for name in ("comments","reviews","review_comments") for c in p[name])
                delta = f"; {count} new/edited conversation entries"
            else:
                delta = "; first observed"
            groups[group].append(f"- [#{key}: {clean(pr['title'])}]({pr['html_url']}) — @{clean(pr['user']['login'])}; GitHub association: {clean(pr.get('author_association','unknown'))} (not verified maintainer role){delta}.{tag} Human participants: {', '.join('@'+clean(u) for u in users) or 'none captured'}.")
        elif kind == "commit":
            groups["Default-branch commits"].append(f"- [{key[:10]}]({p['html_url']}) {clean(p['commit']['message'].splitlines()[0])}")
        else:
            groups["Releases"].append(f"- [{clean(p['tag_name'])}]({p['html_url']}){' (draft)' if p['draft'] else ''}")
    total = sum(map(len, groups.values()))
    if not total:
        lines += ["No newly observed changes within the stated coverage.", ""]
    for title, entries in groups.items():
        if entries:
            lines += [f"## {title} ({len(entries)})", "", *entries, ""]
    lines += ["## Interpretation boundary", "", "This is a factual activity ledger, not a decision summary. Read the stored bodies and conversations before drawing conclusions. Merged code is not deployment proof; a merged proposal is not implementation.", ""]
    return "\n".join(lines)

def refresh(db, repo, days=7, reconcile=False, collector=collect):
    started = now()
    last = db.execute("SELECT started FROM runs WHERE repo=? AND status='complete' ORDER BY id DESC LIMIT 1", (repo,)).fetchone()
    anchor = dt.datetime.fromisoformat(last[0].replace("Z","+00:00")) if last else dt.datetime.now(dt.timezone.utc)
    since = (anchor - dt.timedelta(hours=24) if last else anchor - dt.timedelta(days=days)).isoformat(timespec="seconds").replace("+00:00","Z")
    run = db.execute("INSERT INTO runs(repo,started,status,since) VALUES(?,?,'running',?)", (repo,started,since)).lastrowid
    db.commit()
    try:
        records = collector(db, repo, since, started, reconcile)
        with db:
            count = save(db, run, repo, records)
            db.execute("UPDATE runs SET status='complete',finished=? WHERE id=?", (now(),run))
        return run, count
    except Exception as exc:
        db.rollback()
        with db:
            db.execute("UPDATE runs SET status='failed',finished=?,error=? WHERE id=?", (now(),str(exc),run))
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--max-prs", type=int, default=100, help="Stop before fetching conversations if the discovered PR inventory exceeds this count")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo) or args.days < 1 or args.max_prs < 1:
        parser.error("Use owner/repository and positive --days / --max-prs")
    args.state_dir.mkdir(parents=True, exist_ok=True)
    # One writer per state directory, including collection (prevents competing checkpoints).
    import fcntl
    with (args.state_dir / "collect.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(args.state_dir / "activity.sqlite")
        try:
            run, count = refresh(db, args.repo, args.days, args.reconcile,
                                 collector=lambda db, repo, since, until, reconcile: collect(
                                     db, repo, since, until, reconcile, max_prs=args.max_prs))
        except Exception:
            run = db.execute("SELECT max(id) FROM runs").fetchone()[0]
            report = args.state_dir / f"run-{run}.md"
            report.write_text(render(db,run))
            error = db.execute("SELECT error FROM runs WHERE id=?", (run,)).fetchone()[0]
            print(json.dumps({"run":run,"status":"failed","error":error,"report":str(report)}))
            raise SystemExit(1)
        report = args.state_dir / f"run-{run}.md"
        report.write_text(render(db,run))
        print(json.dumps({"run":run,"changed_records":count,"report":str(report),"status":"complete"}))

if __name__ == "__main__":
    main()
