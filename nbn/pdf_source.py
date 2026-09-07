"""Text-only PDF receipts within the existing source-fetch budget. No OCR or network."""
from pathlib import Path
import re
import subprocess
import tempfile
import time


MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_PAGES = 20
MAX_SECONDS = 10
MAX_TEXT_CHARS = 32000
LIMITATIONS = (
    "PDF text only, from at most the first 20 pages; the document may continue beyond them. "
    "Scanned pages and images/charts were not read; table layout is not verified. "
    "Extraction does not establish publication date."
)


def _failed(kind: str, message: str) -> dict:
    return {"text": "", "outcome": "evidence_failed", "error_kind": kind,
            "error_message": message, "limitations": "PDF not read. " + message}


def extract_text(content: bytes, limit: int = 8000, *, deadline: float | None = None) -> dict:
    """Reject unreadable documents instead of storing binary or partial-error output."""
    limit = max(0, min(int(limit), MAX_TEXT_CHARS))
    if not limit:
        return _failed("pdf_text_limit", "No text allowance remains.")
    if len(content) > MAX_INPUT_BYTES:
        return _failed("pdf_too_large", "Document exceeds the 10 MiB PDF parser-input limit.")
    try:
        with tempfile.TemporaryDirectory(prefix="nbn-pdf-") as directory:
            source = Path(directory) / "source.pdf"
            output = Path(directory) / "text.txt"
            source.write_bytes(content)
            # Recheck immediately before spawn; extraction must not steal finalization time.
            timeout = MAX_SECONDS if deadline is None else min(MAX_SECONDS, deadline - time.monotonic())
            if timeout <= 0:
                return _failed("pdf_extraction_timeout", "Research deadline reached before PDF extraction.")
            subprocess.run(
                ["pdftotext", "-f", "1", "-l", str(MAX_PAGES), "-enc", "UTF-8",
                 "-eol", "unix", str(source), str(output)],
                check=True, timeout=timeout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            # Poppler writes to a temporary file. Only a bounded excerpt enters Python/context.
            read_limit = min(MAX_TEXT_CHARS * 4, max(4096, limit * 4))
            with output.open(encoding="utf-8", errors="replace") as stream:
                raw = stream.read(read_limit + 1)
            clipped = len(raw) > read_limit
            raw = raw[:read_limit]
            pages = []
            for number, page in enumerate(raw.split("\f"), 1):
                page = re.sub(r"[^\S\n]+", " ", page).strip()
                page = re.sub(r"\n{3,}", "\n\n", page)
                if any(char.isalnum() for char in page):
                    pages.append(f"[PDF page {number}]\n{page}")
            text = "\n\n".join(pages)
            if not text:
                return _failed("pdf_no_text", "No readable text extracted; image-only/scanned pages require another route.")
            # A tiny remaining allowance must not register our page marker as source evidence.
            first_body = pages[0].split("\n", 1)[1]
            body_allowance = max(0, limit - (len(pages[0]) - len(first_body)))
            if not any(char.isalnum() for char in first_body[:body_allowance]):
                return _failed("pdf_text_limit", "Text allowance is too small to include readable PDF source text.")
            clipped = clipped or len(text) > limit
            return {"text": text[:limit], "outcome": "ok", "error_kind": "", "error_message": "",
                    "limitations": ("Excerpt clipped to the source-text allowance; unread remainder is not evidence. "
                                    if clipped else "") + LIMITATIONS}
    except subprocess.TimeoutExpired:
        # subprocess.run kills and reaps the child before raising; temp files are then removed.
        return _failed("pdf_extraction_timeout", "PDF text extraction exceeded its time allowance.")
    except FileNotFoundError:
        return _failed("pdf_reader_unavailable", "PDF text extractor is unavailable.")
    except subprocess.CalledProcessError:
        return _failed("pdf_extraction_failed", "PDF could not be read (invalid, protected or unsupported document).")
    except OSError:
        return _failed("pdf_extraction_failed", "PDF text extraction could not complete.")
