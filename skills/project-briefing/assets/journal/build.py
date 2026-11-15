#!/usr/bin/env python3
"""Build and check the static journal before replacing the last good preview."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                raise ValueError(f"duplicate HTML id: {attrs['id']}")
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])


def check_site(root):
    root = root.resolve()
    pages = {p.resolve(): Page(p.read_text()) for p in root.rglob("*.html")}
    for required in ("index.html", "archive/index.html"):
        if root / required not in pages:
            raise ValueError(f"missing required page: {required}")
    checked = 0
    for page, parsed in pages.items():
        for link in parsed.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (root / unquote(url.path).lstrip("/") if url.path.startswith("/")
                      else page.parent / unquote(url.path) if url.path else page).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"{page.relative_to(root)}: link escapes site: {link}")
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                raise ValueError(f"{page.relative_to(root)}: missing target: {link}")
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError(f"{page.relative_to(root)}: missing heading: {link}")
            checked += 1
    return len(pages), checked


def build(site):
    site = site.resolve()
    command = ROOT / "node_modules/@11ty/eleventy/cmd.cjs"
    if not command.is_file():
        raise ValueError("Run npm ci before building the journal.")
    with tempfile.TemporaryDirectory(prefix=".build-", dir=site) as temporary:
        temporary = Path(temporary)
        staged = temporary / "site"
        subprocess.run(["node", str(command), f"--config={ROOT / 'eleventy.config.cjs'}", f"--output={staged}"], cwd=site, check=True, timeout=120)
        pages, links = check_site(staged)
        subprocess.run(["node", str(ROOT / "reader.cjs"), str(staged)], check=True, timeout=120)
        output, previous = site / "_site", temporary / "previous"
        if output.exists():
            output.rename(previous)
        try:
            staged.rename(output)
        except OSError:
            if previous.exists():
                previous.rename(output)
            raise
    print(f"Built {pages} pages; checked {links} local links and assets.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    try:
        build(parser.parse_args().site)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Blog build failed; previous site retained: {error}") from error
