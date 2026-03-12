"""Generate commit census records for fixed references + rolling history."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = Path(__file__).resolve().parent
CONFIG_PATH = MODELS_DIR / "reference_models.json"
RECORDS_DIR = MODELS_DIR / "records"
INDEX_PATH = MODELS_DIR / "INDEX.md"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitMeta:
    """Commit metadata used in generated records."""

    commit: str
    short: str
    date: str
    subject: str


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit_exists(commit: str) -> bool:
    try:
        _run_git("cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError:
        return False
    return True


def _meta(commit: str) -> CommitMeta:
    raw = _run_git(
        "show",
        "-s",
        "--format=%H%x1f%h%x1f%ad%x1f%s",
        "--date=short",
        commit,
    )
    full, short, date, subject = raw.split("\x1f", maxsplit=3)
    return CommitMeta(commit=full, short=short, date=date, subject=subject)


def _counts(commit: str, target_path: str) -> tuple[int, int]:
    files = _run_git("ls-tree", "-r", "--name-only", commit, "--", target_path).splitlines()
    total = len(files)
    py = sum(1 for file in files if file.endswith(".py"))
    return total, py


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _recent_commits(target_path: str) -> list[str]:
    out = _run_git("log", "--format=%H", "--", target_path)
    return [line for line in out.splitlines() if line]


def main() -> None:
    """Refresh reference and rolling commit census records."""

    config = _load_config()
    target_path = str(config["target_path"])
    rolling_limit = int(config["rolling_limit"])
    references: list[dict[str, str]] = list(config["references"])

    if len(references) != 5:
        raise SystemExit("Expected exactly 5 reference commits in reference_models.json")

    for ref in references:
        if not _commit_exists(ref["commit"]):
            raise SystemExit(f"Reference commit missing: {ref['commit']} ({ref['id']})")

    RECORDS_DIR.mkdir(parents=True, exist_ok=True)

    desired_files: set[str] = set()
    rendered_rows: list[tuple[str, str, str, str, int, int]] = []

    reference_shas: set[str] = set()

    for index, ref in enumerate(references, start=1):
        meta = _meta(ref["commit"])
        reference_shas.add(meta.commit)
        total_files, py_files = _counts(meta.commit, target_path)
        record = {
            "role": "reference",
            "reference_id": ref["id"],
            "label": ref["label"],
            **asdict(meta),
            "target_path": target_path,
            "total_files": total_files,
            "py_files": py_files,
        }
        filename = f"ref_{index:02d}_{meta.short}_{_slug(ref['id'])}.json"
        (RECORDS_DIR / filename).write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        desired_files.add(filename)
        rendered_rows.append(
            ("reference", ref["id"], ref["label"], meta.short, total_files, py_files)
        )

    rolling_commits: list[str] = []
    for commit in _recent_commits(target_path):
        if commit in reference_shas:
            continue
        rolling_commits.append(commit)
        if len(rolling_commits) >= rolling_limit:
            break

    for index, commit in enumerate(rolling_commits, start=1):
        meta = _meta(commit)
        total_files, py_files = _counts(meta.commit, target_path)
        record = {
            "role": "rolling",
            "rolling_index": index,
            **asdict(meta),
            "target_path": target_path,
            "total_files": total_files,
            "py_files": py_files,
        }
        filename = f"rolling_{index:02d}_{meta.short}.json"
        (RECORDS_DIR / filename).write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        desired_files.add(filename)
        rendered_rows.append(("rolling", str(index), "(latest)", meta.short, total_files, py_files))

    for existing in RECORDS_DIR.glob("*.json"):
        if existing.name not in desired_files:
            existing.unlink()

    lines = [
        "# Commit Models Index",
        "",
        f"Target path: `{target_path}`",
        "",
        "| role | id/index | label | short_commit | total_files | py_files |",
        "|---|---|---|---:|---:|---:|",
    ]
    for role, key, label, short, total, py in rendered_rows:
        lines.append(f"| {role} | {key} | {label} | `{short}` | {total} | {py} |")
    lines.append("")
    lines.append(
        "Generated by `docs/metrics/commit_models/update_commit_models.py`."
    )
    INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    LOGGER.info("Updated records in %s", RECORDS_DIR)
    LOGGER.info("Wrote %s", INDEX_PATH)


if __name__ == "__main__":
    main()
