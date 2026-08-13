"""Convert BenchDocuments to markdown files for OpenKB ingestion."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.schema import BenchDocument


def doc_to_markdown(doc: BenchDocument) -> str:
    """Render a BenchDocument as a markdown string."""
    parts = [f"# {doc.title}\n"]

    for field_name, text in doc.content_fields.items():
        parts.append(f"## {field_name}\n\n{text}\n")

    if doc.metadata:
        parts.append("## Metadata\n")
        for k, v in doc.metadata.items():
            rendered = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            parts.append(f"**{k}:** {rendered}\n")

    return "\n".join(parts)


def prepare_all(docs: dict[str, BenchDocument], md_dir: Path) -> dict[str, Path]:
    """Write each document as a .md file. Returns {uuid: md_path}.

    Skips docs already written to md_dir.
    """
    md_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    for uid, doc in docs.items():
        md_path = md_dir / f"{uid}.md"
        if not md_path.exists():
            md_path.write_text(doc_to_markdown(doc), encoding="utf-8")
        result[uid] = md_path
    return result
