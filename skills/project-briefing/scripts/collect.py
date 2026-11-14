#!/usr/bin/env python3
"""Read-only GitHub collection; Python stdlib + authenticated gh."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def api(endpoint):
    for attempt in range(3):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GH_DEBUG")}
        env.update(GH_PROMPT_DISABLED="1", GH_PAGER="cat", NO_COLOR="1")
        p = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True, timeout=90, env=env)
        if p.returncode == 0:
            return json.loads(p.stdout)
        if not re.search(r"HTTP (429|5\d\d)", p.stderr) or attempt == 2:
            status = re.search(r"HTTP (\d{3})", p.stderr)
            raise RuntimeError(f"GitHub read failed: {endpoint}: {status.group(0) if status else 'check gh authentication and repository access'}")
        time.sleep(2 ** attempt)

def pages(endpoint, stop=None, fetch=api, max_items=1000, search=False):
    result = []
    for page in range(1, 1001):
        sep = "&" if "?" in endpoint else "?"
        batch = fetch(f"{endpoint}{sep}per_page=100&page={page}")
        if search:
            if (not isinstance(batch, dict) or batch.get("incomplete_results") is not False
                    or type(batch.get("total_count")) is not int or batch["total_count"] < 0
                    or batch["total_count"] > min(max_items, 1000)):
                raise RuntimeError("PR search is incomplete or exceeds the collection/search limit; narrow pr_filter and try an estimate. No checkpoint advanced.")
            total = batch["total_count"]
            batch = batch.get("items")
        if not isinstance(batch, list):
            raise RuntimeError(f"Expected a list: {endpoint}")
        for item in batch:
            if stop and stop(item):
                return result
            if len(result) >= max_items:
                raise RuntimeError(f"Read budget exceeded: {endpoint}; more than {max_items} records. PR discovery uses --max-prs; other evidence streams have a fixed cap. No checkpoint advanced.")
            result.append(item)
        if search and len(batch) < 100 and len(result) < total:
            raise RuntimeError("PR search returned fewer matches than reported; no checkpoint advanced.")
        if len(batch) < 100 or (search and len(result) >= total):
            return result
    raise RuntimeError(f"Pagination safety limit reached: {endpoint}")

def pr_query(repo, since, pr_filter=""):
    if (not isinstance(pr_filter, str) or re.search(r"\b(?:repo|org|user|is|type|updated)\s*:|\bOR\b", pr_filter, re.I)):
        raise ValueError("pr_filter accepts GitHub PR search terms (labels, authors, keywords), not repo/org/user/is/type/updated qualifiers or OR")
    return f"repo:{repo} is:pr updated:>={since} {pr_filter}".strip()

def baseline_plan(repo, days=7, max_prs=100, fetch=api, pr_filter=""):
    """Count indexed PRs before an uncached scan; never read conversations here."""
    observed = now()
    anchor = dt.datetime.fromisoformat(observed.replace("Z", "+00:00"))
    def estimate(window):
        since = (anchor - dt.timedelta(days=window)).isoformat(timespec="seconds").replace("+00:00", "Z")
        query = urllib.parse.urlencode({"q": pr_query(repo, since, pr_filter), "per_page": 1})
        result = fetch(f"search/issues?{query}")
        if (not isinstance(result, dict) or type(result.get("total_count")) is not int
                or result["total_count"] < 0 or type(result.get("incomplete_results")) is not bool):
            raise RuntimeError("GitHub returned no usable PR workload estimate; no scan started.")
        return {"days": window, "since": since, "estimated_prs": result["total_count"],
                "incomplete_results": result["incomplete_results"]}

    estimates = [estimate(days)]
    first = estimates[0]
    limit = min(max_prs, 1000) if pr_filter else max_prs
    needs_scope = first["incomplete_results"] or first["estimated_prs"] > limit
    if needs_scope:
        estimates.extend(estimate(window) for window in (3, 1) if window < days)
    options = []
    if needs_scope:
        for row in estimates:
            # An incomplete count cannot justify a sufficient budget.
            if row["incomplete_results"] or (pr_filter and row["estimated_prs"] > 1000):
                continue
            count = row["estimated_prs"]
            budget = max_prs
            if count > budget:
                budget = ((count + (count + 4) // 5 + 99) // 100) * 100
            if pr_filter:
                budget = min(budget, 1000)
            options.append({"days": row["days"], "estimated_prs": count, "max_prs": budget})
    plan = {"status": "needs_scope" if needs_scope else "ready", "observed_at": observed,
            "requested_days": days, "configured_max_prs": max_prs, "pr_filter": pr_filter,
            "estimates": estimates, "options": options,
            "note": "GitHub search estimates may lag live activity; PR counts are not runtime estimates. Collection still enforces the approved limit. Raised options target 20% headroom rounded up to 100, capped at 1,000 for filtered search."}
    if needs_scope:
        plan["error"] = "Initial scan needs a scope choice: try a narrower pr_filter, or change days/max_prs using the counted options. Filtered search is capped at 1,000 PRs. No scan started."
    return plan

def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS runs(
      id INTEGER PRIMARY KEY, repo TEXT NOT NULL, started TEXT NOT NULL,
      finished TEXT, status TEXT NOT NULL, since TEXT NOT NULL, error TEXT);
    CREATE TABLE IF NOT EXISTS run_outputs(
      run_id INTEGER PRIMARY KEY, briefing_path TEXT NOT NULL,
      delivery_status TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS objects(
      repo TEXT, kind TEXT, key TEXT, digest TEXT NOT NULL, payload TEXT NOT NULL,
      PRIMARY KEY(repo,kind,key));
    CREATE TABLE IF NOT EXISTS changes(
      run_id INTEGER, kind TEXT, key TEXT, before_json TEXT, after_json TEXT,
      UNIQUE(run_id,kind,key));
    """)
    if "pr_filter" not in {row[1] for row in db.execute("PRAGMA table_info(runs)")}:
        db.execute("ALTER TABLE runs ADD COLUMN pr_filter TEXT NOT NULL DEFAULT ''")
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

def collect(db, repo, since, until, reconcile=False, fetch=api, max_prs=100, pr_filter=""):
    base = f"repos/{repo}"
    # Updated order lets discovery stop at the window boundary or budget,
    # without enumerating the repository's dormant open backlog.
    if pr_filter:
        query = urllib.parse.urlencode({"q": pr_query(repo, since, pr_filter), "sort": "updated", "order": "desc"})
        recent = pages(f"search/issues?{query}", fetch=fetch, max_items=max_prs, search=True)
    else:
        recent = pages(f"{base}/pulls?state=all&sort=updated&direction=desc",
                       stop=lambda p: p["updated_at"] < since,
                       fetch=fetch, max_items=max_prs)
    prs = {str(p["number"]): p for p in recent}
    previous = {key: json.loads(body) for key, body in db.execute(
        "SELECT key,payload FROM objects WHERE repo=? AND kind='pr'", (repo,))}
    if reconcile and not pr_filter:
        for key, old in previous.items():
            if key not in prs and old["pr"]["state"] == "open":
                if len(prs) >= max_prs:
                    raise RuntimeError(f"Reconciliation exceeds --max-prs {max_prs}. No conversations fetched; no checkpoint advanced.")
                prs[key] = fetch(f"{base}/pulls/{key}")

    def detail(pair):
        key, p = pair
        old = previous.get(key)
        if pr_filter:
            p = fetch(f"{base}/pulls/{key}")
        if not reconcile and old and old["pr"]["updated_at"] == p["updated_at"] and old["pr"]["head"]["sha"] == p["head"]["sha"] and "files" not in old:
            return "pr", key, old
        # Fetch detail first; activity arriving afterward is picked up by overlap next run.
        if not pr_filter:
            p = fetch(f"{base}/pulls/{key}")
        result = {"pr": p,
                  "comments": pages(f"{base}/issues/{key}/comments", fetch=fetch),
                  "reviews": pages(f"{base}/pulls/{key}/reviews", fetch=fetch),
                  "review_comments": []}
        return "pr", key, result

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(detail, prs.items()))
    if pr_filter:
        return records
    metadata = fetch(base)
    branch = urllib.parse.quote(metadata["default_branch"], safe="")
    commits = pages(f"{base}/commits?sha={branch}&since={since}&until={until}", fetch=fetch)
    records.extend(("commit", c["sha"], c) for c in commits)
    # Releases are not sorted by update time, so enumerate and filter locally.
    releases = pages(f"{base}/releases", fetch=fetch)
    # Already enumerated: retain all releases so old edits and nullable draft dates work.
    records.extend(("release", str(r["id"]), r) for r in releases)
    return records

def clean(value):
    return " ".join(str(value or "").replace("|", "/").split())

def render(db, run):
    row = db.execute("SELECT repo,started,finished,status,since,error,pr_filter FROM runs WHERE id=?", (run,)).fetchone()
    repo, started, finished, status, since, error, pr_filter = row
    prior = db.execute("SELECT count(*) FROM runs WHERE repo=? AND status='complete' AND id<?", (repo,run)).fetchone()[0]
    coverage = f"Window starts {since}. Includes PRs updated in the window (not the entire open backlog), default-branch commits in the window, and current releases. Reconciliation may also revisit previously tracked open PRs."
    discovery = "Incremental scans reuse unchanged PRs; use --reconcile to re-fetch recent and previously tracked open PR conversations. Each paginated evidence stream is limited to 1,000 records; exceeding a limit fails the scan. GitHub is not a transactional snapshot."
    if pr_filter:
        coverage = f"Window starts {since}. PR-only coverage using GitHub search filter: {clean(pr_filter)}. Repository-wide commits and releases are NOT collected."
        discovery = "GitHub search is indexed, may lag live activity and is capped at 1,000 matches. Reconciliation re-reads matching PRs in this window only. Unchanged conversations are reused. Each conversation stream is capped at 1,000 records. Incomplete/oversized searches fail without advancing the checkpoint."
    lines = [f"# {repo}: {'baseline' if not prior else 'changes'}", "",
             f"Run {run}; status: {status}; started: {started}; finished: {finished or 'not completed'}.",
             coverage,
             "PR descriptions, issue comments and review summaries are captured; patches, changed files and inline diff comments are not fetched by default. GitHub Discussions, ordinary issues, CI, RFC file contents, and deployment proof are NOT covered.",
             discovery, ""]
    if status != "complete":
        return "\n".join(lines + [f"Coverage incomplete: {clean(error)}. Last successful checkpoint retained.", ""])
    groups = {"Merged PRs": [], "Open PRs / updates": [], "Closed without merge": [], "Default-branch commits": [], "Releases": []}
    for kind, key, before, after in db.execute("SELECT kind,key,before_json,after_json FROM changes WHERE run_id=? ORDER BY kind,key", (run,)):
        p = json.loads(after)
        if kind == "pr":
            pr = p["pr"]
            paths = [f["filename"] for f in p.get("files", [])]
            rfc = bool(re.search(r"\b(rfc|proposal|design)\b", pr["title"], re.I)) or any(re.search(r"(^|/)(rfcs?|proposals?)(/|[.-])", path, re.I) for path in paths)
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

def refresh(db, repo, days=7, reconcile=False, collector=None, pr_filter=""):
    started = now()
    last = db.execute("SELECT started,pr_filter FROM runs WHERE repo=? AND status='complete' ORDER BY id DESC LIMIT 1", (repo,)).fetchone()
    if last and last[1] != pr_filter:
        last = None
    anchor = dt.datetime.fromisoformat(last[0].replace("Z","+00:00")) if last else dt.datetime.now(dt.timezone.utc)
    since = (anchor - dt.timedelta(hours=24) if last else anchor - dt.timedelta(days=days)).isoformat(timespec="seconds").replace("+00:00","Z")
    run = db.execute("INSERT INTO runs(repo,started,status,since,pr_filter) VALUES(?,?,'running',?,?)", (repo,started,since,pr_filter)).lastrowid
    db.commit()
    try:
        records = (collect(db, repo, since, started, reconcile, pr_filter=pr_filter)
                   if collector is None else collector(db, repo, since, started, reconcile))
        with db:
            count = save(db, run, repo, records)
            db.execute("UPDATE runs SET status='complete',finished=? WHERE id=?", (now(),run))
        return run, count
    except Exception as exc:
        db.rollback()
        with db:
            db.execute("UPDATE runs SET status='failed',finished=?,error=? WHERE id=?", (now(),str(exc),run))
        raise

def write_ledger(db, run, path):
    # Preserve briefing paths registered by older versions, even ledger names.
    if any(Path(saved).resolve() == path.resolve() for (saved,) in
           db.execute("SELECT briefing_path FROM run_outputs")):
        return
    body = render(db, run)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp:
        temp_path = Path(temp.name)
        try:
            temp.write(body)
            temp.close()
            temp_path.replace(path)
        finally:
            temp_path.unlink(missing_ok=True)

def pending_outputs(db, repo):
    return [{"run": run, "briefing_path": path, "delivery_status": status or "pending"}
            for run, path, status in db.execute("""
              SELECT r.id, o.briefing_path, o.delivery_status FROM runs r
              LEFT JOIN run_outputs o ON o.run_id=r.id
              WHERE r.repo=? AND r.status='complete'
                AND o.run_id IS NULL
              ORDER BY r.id""", (repo,))]

def delivery_outputs(db, repo):
    return [{"run": run, "briefing_path": path, "delivery_status": status}
            for run, path, status in db.execute("""
              SELECT r.id,o.briefing_path,o.delivery_status FROM runs r
              JOIN run_outputs o ON o.run_id=r.id WHERE r.repo=?
              AND o.delivery_status IN ('pending','uncertain') ORDER BY r.id""", (repo,))]

def record_output(db, repo, run, path, delivery_status):
    if delivery_status not in {"pending", "confirmed", "uncertain", "not_needed"}:
        raise ValueError("Invalid delivery status")
    row = db.execute("SELECT status FROM runs WHERE id=? AND repo=?", (run, repo)).fetchone()
    if not row or row[0] != "complete":
        raise ValueError("Output must reference a complete run for this repository")
    if re.fullmatch(r"run-\d+\.md", path.name):
        raise ValueError("run-N.md filenames are reserved for activity ledgers; save briefing-N.md instead")
    if not path.is_file() or not path.read_text().strip():
        raise ValueError("A nonempty saved briefing is required")
    with db:
        db.execute("INSERT OR REPLACE INTO run_outputs VALUES(?,?,?)",
                   (run, str(path.resolve()), delivery_status))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--max-prs", type=int, default=100, help="Maximum recently updated PRs; discovery stops on overflow before conversation reads")
    parser.add_argument("--pr-filter", default="", help="Optional GitHub PR search terms; matching PRs only, excluding repository-wide commits/releases")
    parser.add_argument("--estimate", action="store_true", help="Read first-scan PR counts and scope options without creating local state")
    parser.add_argument("--pending", action="store_true", help="Recover ledgers and list separate writing and delivery queues offline")
    parser.add_argument("--record-output", type=int, metavar="RUN", help="Record a saved briefing and its observed delivery status")
    parser.add_argument("--briefing-path", type=Path)
    parser.add_argument("--delivery-status", choices=["pending", "confirmed", "uncertain", "not_needed"], default="pending")
    args = parser.parse_args()
    if sum((args.pending, args.estimate, args.record_output is not None)) > 1:
        parser.error("--pending, --estimate and --record-output are mutually exclusive")
    if args.record_output is not None and args.briefing_path is None:
        parser.error("--record-output requires --briefing-path")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo) or args.days < 1 or args.max_prs < 1:
        parser.error("Use owner/repository and positive --days / --max-prs")
    args.pr_filter = args.pr_filter.strip()
    try:
        pr_query(args.repo, now(), args.pr_filter)
    except ValueError as exc:
        parser.error(str(exc))
    if args.estimate:
        print(json.dumps(baseline_plan(args.repo, args.days, args.max_prs, pr_filter=args.pr_filter)))
        return
    args.state_dir.mkdir(parents=True, exist_ok=True)
    # One writer per state directory, including collection (prevents competing checkpoints).
    import fcntl
    with (args.state_dir / "collect.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = connect(args.state_dir / "activity.sqlite")
        if args.record_output is not None:
            path = args.briefing_path.resolve()
            if not path.is_relative_to(args.state_dir.resolve()):
                parser.error("--briefing-path must be inside --state-dir")
            record_output(db, args.repo, args.record_output, path, args.delivery_status)
            print(json.dumps({"pending_outputs": pending_outputs(db, args.repo), "delivery_outputs": delivery_outputs(db, args.repo)}))
            return
        # Restore missing ledgers before a new scan; collection success is not delivery.
        for (complete_run,) in db.execute("SELECT id FROM runs WHERE repo=? AND status='complete'", (args.repo,)):
            ledger = args.state_dir / f"run-{complete_run}.md"
            if not ledger.exists() or ledger.read_text() != render(db, complete_run):
                write_ledger(db, complete_run, ledger)
        if args.pending:
            print(json.dumps({"pending_outputs": pending_outputs(db, args.repo), "delivery_outputs": delivery_outputs(db, args.repo)}))
            return
        last = db.execute("SELECT pr_filter FROM runs WHERE repo=? AND status='complete' ORDER BY id DESC LIMIT 1", (args.repo,)).fetchone()
        if not last or last[0] != args.pr_filter:
            try:
                plan = baseline_plan(args.repo, args.days, args.max_prs, pr_filter=args.pr_filter)
            except Exception as exc:
                print(json.dumps({"status": "failed", "error": str(exc)}))
                raise SystemExit(1)
            if plan["status"] == "needs_scope":
                print(json.dumps(plan))
                raise SystemExit(1)
        try:
            run, count = refresh(db, args.repo, args.days, args.reconcile,
                                 collector=lambda db, repo, since, until, reconcile: collect(
                                     db, repo, since, until, reconcile, max_prs=args.max_prs, pr_filter=args.pr_filter),
                                 pr_filter=args.pr_filter)
        except Exception:
            run = db.execute("SELECT max(id) FROM runs").fetchone()[0]
            report = args.state_dir / f"run-{run}.md"
            write_ledger(db, run, report)
            error = db.execute("SELECT error FROM runs WHERE id=?", (run,)).fetchone()[0]
            print(json.dumps({"run":run,"status":"failed","error":error,"report":str(report)}))
            raise SystemExit(1)
        report = args.state_dir / f"run-{run}.md"
        write_ledger(db, run, report)
        print(json.dumps({"run":run,"changed_records":count,"report":str(report),"status":"complete", "pending_outputs":pending_outputs(db, args.repo), "delivery_outputs":delivery_outputs(db, args.repo)}))

if __name__ == "__main__":
    main()
