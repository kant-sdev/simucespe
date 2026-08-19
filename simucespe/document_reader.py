from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class DocumentText:
    text: str
    source_format: str
    page_count: int


def read_structured_document(path: Path) -> DocumentText:
    """Read the CEBRASPE source, preferring the ZIP+manifest format.

    The current local corpus is made of real PDFs, but the ingestion contract
    requires trying the ZIP package format first. The PDF fallback uses only the
    embedded text layer; it does not perform OCR.
    """

    try:
        return _read_zip_manifest(path)
    except zipfile.BadZipFile:
        return _read_pdf_text(path)
    except KeyError as exc:
        raise ValueError(f"{path} is a ZIP, but it does not contain the expected manifest/text paths") from exc


def _read_zip_manifest(path: Path) -> DocumentText:
    with zipfile.ZipFile(path) as package:
        manifest = json.loads(package.read("manifest.json"))
        pages = sorted(manifest["pages"], key=lambda page: page.get("number", page.get("page", 0)))
        texts: list[str] = []
        for page in pages:
            text_path = page.get("text_path") or page.get("text")
            if not text_path:
                raise KeyError("text_path")
            texts.append(package.read(text_path).decode("utf-8", errors="replace"))
        return DocumentText(text="\n".join(texts), source_format="zip_manifest", page_count=len(pages))


def _read_pdf_text(path: Path) -> DocumentText:
    reader = PdfReader(str(path))
    texts = [page.extract_text() or "" for page in reader.pages]
    return DocumentText(text="\n".join(texts), source_format="pdf_text_fallback", page_count=len(reader.pages))

