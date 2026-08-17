"""Ingest documents into a per-benchmark OpenKB knowledge base.

Each benchmark dataset gets its own KB directory:
    kb_root/<dataset_name>/
        .openkb/
        wiki/
            sources/       ← pymupdf-extracted text (md or json)
            summaries/     ← PageIndex tree (long) or LLM summary (short)
            concepts/      ← LLM-generated
            entities/      ← LLM-generated
            index.md

Follows OpenKB's exact PDF ingestion logic:
  - Short PDF (<threshold pages): pymupdf → markdown → LLM compilation
  - Long PDF  (≥threshold pages): PageIndex tree indexing → LLM compilation
  - Text files (.md/.txt): treated as short docs → LLM compilation
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from typing import Literal

from openkb.agent.compiler import compile_long_doc, compile_short_doc
from openkb.config import resolve_concurrency, resolve_effective_config
from openkb.converter import get_pdf_page_count
from openkb.images import convert_pdf_with_images
from openkb.indexer import index_long_document
from openkb.locks import atomic_write_text
from openkb.schema import INDEX_SEED

logger = logging.getLogger(__name__)

DEFAULT_PAGEINDEX_THRESHOLD = 20
DEFAULT_COMPILE_CONCURRENCY = 4



# ---------------------------------------------------------------------------
# KB initialisation
# ---------------------------------------------------------------------------


def init_kb(kb_root: Path, dataset_name: str) -> Path:
    """Initialise a KB directory for a benchmark dataset. Returns kb_dir.

    Configure the model and concurrency in .openkb/config.yaml after init.
    """
    kb_dir = kb_root / dataset_name
    openkb_dir = kb_dir / ".openkb"
    if not openkb_dir.exists():
        kb_dir.mkdir(parents=True, exist_ok=True)
        openkb_dir.mkdir()
        wiki_dir = kb_dir / "wiki"
        wiki_dir.mkdir(exist_ok=True)
        (wiki_dir / "index.md").write_text(INDEX_SEED, encoding="utf-8")
    return kb_dir


# ---------------------------------------------------------------------------
# LLM compilation wrappers
# ---------------------------------------------------------------------------


def _compile_short(doc_name: str, source_path: Path, kb_dir: Path, model: str) -> None:
    config = resolve_effective_config(kb_dir)[0]
    concurrency = resolve_concurrency(config) or DEFAULT_COMPILE_CONCURRENCY
    asyncio.run(compile_short_doc(doc_name, source_path, kb_dir, model, max_concurrency=concurrency))


def _compile_long(
    doc_name: str, doc_id: str, kb_dir: Path, model: str, description: str = ""
) -> None:
    config = resolve_effective_config(kb_dir)[0]
    concurrency = resolve_concurrency(config) or DEFAULT_COMPILE_CONCURRENCY
    summary_path = kb_dir / "wiki" / "summaries" / f"{doc_name}.md"
    asyncio.run(
        compile_long_doc(
            doc_name, summary_path, doc_id, kb_dir, model,
            doc_description=description, max_concurrency=concurrency,
        )
    )


# ---------------------------------------------------------------------------
# Single-document ingestion
# ---------------------------------------------------------------------------


def ingest_pdf(
    pdf_path: Path,
    doc_name: str,
    kb_dir: Path,
    model: str,
    *,
    threshold: int = DEFAULT_PAGEINDEX_THRESHOLD,
) -> Literal["added", "failed"]:
    """Ingest a single PDF following OpenKB's short/long logic.

    Short (<threshold pages):
      pymupdf → wiki/sources/{doc}.md → compile_short_doc
    Long (≥threshold pages):
      index_long_document (PageIndex + pymupdf) → compile_long_doc
    """
    try:
        page_count = get_pdf_page_count(pdf_path)
        if page_count >= threshold:
            print(f"    long PDF ({page_count} pages) → PageIndex path")
            result = index_long_document(pdf_path, kb_dir, doc_name=doc_name)
            _compile_long(doc_name, result.doc_id, kb_dir, model, description=result.description)
        else:
            print(f"    short PDF ({page_count} pages) → direct path")
            sources_dir = kb_dir / "wiki" / "sources"
            sources_dir.mkdir(parents=True, exist_ok=True)
            images_dir = sources_dir / "images" / doc_name
            images_dir.mkdir(parents=True, exist_ok=True)
            markdown = convert_pdf_with_images(pdf_path, doc_name, images_dir)
            source_path = sources_dir / f"{doc_name}.md"
            atomic_write_text(source_path, markdown)
            _compile_short(doc_name, source_path, kb_dir, model)
        return "added"
    except Exception as exc:
        logger.error("ingestion failed for %s: %s", pdf_path.name, exc, exc_info=True)
        print(f"    FAILED: {exc}")
        return "failed"


def ingest_text(
    text_path: Path,
    doc_name: str,
    kb_dir: Path,
    model: str,
) -> Literal["added", "failed"]:
    """Ingest a text file (.md/.txt) as a short document."""
    try:
        sources_dir = kb_dir / "wiki" / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)
        content = text_path.read_text(encoding="utf-8")
        source_path = sources_dir / f"{doc_name}.md"
        atomic_write_text(source_path, content)
        _compile_short(doc_name, source_path, kb_dir, model)
        return "added"
    except Exception as exc:
        logger.error("ingestion failed for %s: %s", text_path.name, exc, exc_info=True)
        print(f"    FAILED: {exc}")
        return "failed"


# ---------------------------------------------------------------------------
# Batch ingestion
# ---------------------------------------------------------------------------


def ingest_all(
    doc_id_to_path: dict[str, Path],
    kb_dir: Path,
    model: str,
    *,
    threshold: int = DEFAULT_PAGEINDEX_THRESHOLD,
) -> dict[str, str]:
    """Ingest all documents into the KB. Returns {doc_id: outcome}.

    Accepts PDFs and text files. Skips documents whose summary already exists.
    """
    outcomes: dict[str, str] = {}
    total = len(doc_id_to_path)
    for i, (doc_id, path) in enumerate(doc_id_to_path.items(), 1):
        summary = kb_dir / "wiki" / "summaries" / f"{doc_id}.md"
        if summary.exists():
            print(f"  [{i}/{total}] {doc_id} already ingested, skipping")
            outcomes[doc_id] = "skipped"
            continue
        if not path.exists():
            print(f"  [{i}/{total}] {doc_id} file not found: {path}")
            outcomes[doc_id] = "failed"
            continue
        print(f"  [{i}/{total}] ingesting {doc_id} ...")
        if path.suffix.lower() == ".pdf":
            outcomes[doc_id] = ingest_pdf(path, doc_id, kb_dir, model, threshold=threshold)
        else:
            outcomes[doc_id] = ingest_text(path, doc_id, kb_dir, model)
    return outcomes
