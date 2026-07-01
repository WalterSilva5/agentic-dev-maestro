"""Extração de texto de arquivos para gerar planos de estudo.

Suporta txt/md, PDF, DOCX e EPUB. Degrada com elegância: se a lib do formato
não estiver disponível ou o parse falhar, tenta decodificar como texto puro.
"""
from __future__ import annotations

import io
import logging
import os
import tempfile

logger = logging.getLogger("maestro.study.ingest")

# Limite bruto de caracteres extraídos (ebooks podem ser enormes).
MAX_CHARS = 200_000

SUPPORTED_EXTS = (".txt", ".md", ".markdown", ".rst", ".pdf", ".docx", ".epub")


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", "ignore")


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    total = 0
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            txt = ""
        parts.append(txt)
        total += len(txt)
        if total > MAX_CHARS:
            break
    return "\n".join(parts)


def _from_docx(data: bytes) -> str:
    import docx
    doc = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def _from_epub(data: bytes) -> str:
    import ebooklib
    from bs4 import BeautifulSoup
    from ebooklib import epub

    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tf:
        tf.write(data)
        path = tf.name
    try:
        book = epub.read_epub(path)
        parts: list[str] = []
        total = 0
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(" ", strip=True)
            parts.append(text)
            total += len(text)
            if total > MAX_CHARS:
                break
        return "\n".join(parts)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def extract_text(data: bytes, filename: str = "") -> str:
    """Extrai texto de `data` conforme a extensão de `filename`."""
    ext = os.path.splitext(filename or "")[1].lower()
    try:
        if ext == ".pdf":
            text = _from_pdf(data)
        elif ext == ".docx":
            text = _from_docx(data)
        elif ext == ".epub":
            text = _from_epub(data)
        else:
            text = _decode(data)
    except Exception as e:  # noqa: BLE001
        logger.warning("Falha ao extrair %s (%s); tentando texto puro.", filename, e)
        text = _decode(data)
    text = (text or "").strip()
    return text[:MAX_CHARS]
