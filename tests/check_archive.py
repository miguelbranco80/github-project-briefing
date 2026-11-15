"""Verify archive contents and run the tests against its packaged scripts."""
import argparse
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

SOURCE = Path(__file__).resolve().parents[1]


def check(artifact):
    with tempfile.TemporaryDirectory(prefix="briefing-archive-") as temporary:
        temporary = Path(temporary).resolve()
        with tarfile.open(artifact) as archive:
            archive.extractall(temporary, filter="data")
            files = {m.name for m in archive.getmembers() if m.isfile()}
        package = temporary / "package"
        selected = subprocess.check_output(
            ["git", "ls-files", "--", "skills/project-briefing"], cwd=SOURCE, text=True,
        ).splitlines()
        expected = {"package/" + name for name in selected}
        expected.update({"package/CLAW.md", "package/BOOTSTRAP.md", "package/package.json", "package/LICENSE"})
        if files != expected:
            raise ValueError(f"Archive selection mismatch: {files ^ expected}")
        env = dict(os.environ, PROJECT_BRIEFING_TEST_PACKAGE=str(package))
        subprocess.run(["python3", "-m", "unittest", "discover", "-s", str(SOURCE / "tests"),
                        "-v"], env=env, check=True, timeout=180)
        print(f"Verified {len(files)} archive files and the briefing workflow from extracted package code.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    check(parser.parse_args().artifact)
