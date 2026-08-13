"""Ingest prepared markdown documents into an OpenKB knowledge base."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

def init_kb(kb_dir: Path) -> None:
    """Initialize a fresh KB if not already present."""
    openkb_dir = kb_dir / ".openkb"
    if openkb_dir.exists():
        return
    # Inline the essential init logic to avoid Click context dependency.
    from openkb.schema import INDEX_SEED

    kb_dir.mkdir(parents=True, exist_ok=True)
    openkb_dir.mkdir()
    wiki_dir = kb_dir / "wiki"
    wiki_dir.mkdir(exist_ok=True)
    (wiki_dir / "index.md").write_text(INDEX_SEED, encoding="utf-8")


def ingest_one(md_path: Path, kb_dir: Path) -> Literal["added", "skipped", "failed"]:
    """Ingest a single markdown file into the KB.

    Calls the real OpenKB add_single_file (conversion → compilation → mutation).
    """
    from openkb.cli import add_single_file

    return add_single_file(md_path, kb_dir)


def ingest_all(uuid_to_md: dict[str, Path], kb_dir: Path) -> dict[str, str]:
    """Ingest all documents. Returns {uuid: outcome}.

    Skips documents whose summary page already exists.
    """
    init_kb(kb_dir)
    outcomes: dict[str, str] = {}
    total = len(uuid_to_md)
    for i, (uid, md_path) in enumerate(uuid_to_md.items(), 1):
        summary = kb_dir / "wiki" / "summaries" / f"{md_path.stem}.md"
        if summary.exists():
            print(f"  [{i}/{total}] {uid} already ingested, skipping")
            outcomes[uid] = "skipped"
            continue
        print(f"  [{i}/{total}] ingesting {uid} ...")
        outcomes[uid] = ingest_one(md_path, kb_dir)
    return outcomes
