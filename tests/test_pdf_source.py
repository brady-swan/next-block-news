"""Real local Poppler extraction plus offline newsroom integration (no network/models)."""
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import httpx

from nbn import pdf_source, sources, store
from tests.support import temporary_store
from tests.test_editorial_v2 import candidate
from tests.test_reporter_writer import session


def pdf_bytes(pages):
    """Minimal text-layer PDF fixture; no extra PDF-authoring dependency in the test suite."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        page_id, stream_id = len(objects) + 1, len(objects) + 2
        kids.append(f"{page_id} 0 R")
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
        objects.extend([
            (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
             f"/Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>").encode(),
            f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
        ])
    objects[1] = f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(kids)}] >>".encode()
    result = b"%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(result)
    result += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return result + (f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
                     f"startxref\n{xref}\n%%EOF\n").encode()


class PdfSourceTests(unittest.TestCase):
    def test_real_text_and_page_boundaries_with_honest_limits(self):
        result = pdf_source.extract_text(pdf_bytes(["DRAFT: Payment controls.", "Bitcoin firms are included."]))
        self.assertEqual(result["outcome"], "ok")
        self.assertIn("[PDF page 1]\nDRAFT: Payment controls.", result["text"])
        self.assertIn("[PDF page 2]\nBitcoin firms are included.", result["text"])
        self.assertNotIn("%PDF", result["text"])
        self.assertIn("Scanned pages", result["limitations"])
        self.assertIn("publication date", result["limitations"])

    def test_real_page_cap_excludes_later_pages(self):
        result = pdf_source.extract_text(pdf_bytes([f"Page {i} text" for i in range(1, 23)]))
        self.assertIn("Page 20 text", result["text"])
        self.assertNotIn("Page 21 text", result["text"])
        self.assertIn("first 20 pages", result["limitations"])

    def test_character_cap_is_visible_not_a_full_document_claim(self):
        result = pdf_source.extract_text(pdf_bytes(["A report with several important sentences."] * 3), limit=60)
        self.assertEqual(len(result["text"]), 60)
        self.assertIn("Excerpt clipped", result["limitations"])
        self.assertIn("unread remainder is not evidence", result["limitations"])

    def test_empty_or_broken_document_is_not_evidence(self):
        for content, kind in [(pdf_bytes([""]), "pdf_no_text"),
                              (b"%PDF-1.7 broken", "pdf_extraction_failed")]:
            with self.subTest(kind=kind):
                result = pdf_source.extract_text(content)
                self.assertEqual(result["outcome"], "evidence_failed")
                self.assertEqual(result["error_kind"], kind)
                self.assertEqual(result["text"], "")

    def test_oversized_input_is_not_parsed(self):
        with patch.object(pdf_source, "MAX_INPUT_BYTES", 2), patch.object(pdf_source.subprocess, "run") as run:
            result = pdf_source.extract_text(b"123")
        run.assert_not_called()
        self.assertEqual(result["error_kind"], "pdf_too_large")

    def test_no_text_allowance_does_not_parse(self):
        with patch.object(pdf_source.subprocess, "run") as run:
            result = pdf_source.extract_text(b"pdf", limit=0)
        run.assert_not_called()
        self.assertEqual(result["error_kind"], "pdf_text_limit")

    def test_page_marker_only_excerpts_cannot_become_evidence(self):
        content = pdf_bytes(["Original report."])
        url = "https://example.com/source.pdf"
        response = httpx.Response(200, content=content, headers={"content-type": "application/pdf"},
                                  request=httpx.Request("GET", url))
        for limit in (1, 8, 12, 13):
            with self.subTest(limit=limit), temporary_store() as con:
                desk = session(con)
                with patch.object(sources, "_assert_public_http_url"), patch.object(sources.httpx, "Client") as client:
                    client.return_value.__enter__.return_value.get.return_value = response
                    result = desk._fetch(url, char_limit=limit, intake={"url_hash": "pdf"})
                self.assertFalse(result["ok"])
                self.assertEqual(result["error_kind"], "pdf_text_limit")
                self.assertEqual(desk.fetches, {})
                self.assertEqual(desk.fetch_by_url, {})
                self.assertEqual(desk.fetch_chars, 0)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM writer_artifacts").fetchone()[0], 0)

    def test_deadline_is_checked_immediately_before_spawn(self):
        with patch.object(pdf_source.time, "monotonic", return_value=100), \
                patch.object(pdf_source.subprocess, "run") as run:
            result = pdf_source.extract_text(b"pdf", deadline=99)
        run.assert_not_called()
        self.assertEqual(result["error_kind"], "pdf_extraction_timeout")

    def test_subprocess_failures_discard_output_and_clean_files(self):
        for error, kind in [(subprocess.TimeoutExpired("pdftotext", 2), "pdf_extraction_timeout"),
                            (subprocess.CalledProcessError(1, "pdftotext"), "pdf_extraction_failed"),
                            (FileNotFoundError(), "pdf_reader_unavailable")]:
            paths = []
            def failed(argv, **kwargs):
                paths.extend([Path(argv[-2]), Path(argv[-1])])
                self.assertEqual(argv[:7], ["pdftotext", "-f", "1", "-l", "20", "-enc", "UTF-8"])
                self.assertEqual(kwargs["timeout"], 2)
                self.assertNotIn("shell", kwargs)
                self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
                paths[-1].write_text("Partial output must not become evidence.")
                raise error
            with self.subTest(kind=kind), patch.object(pdf_source.time, "monotonic", return_value=100), \
                    patch.object(pdf_source.subprocess, "run", side_effect=failed):
                result = pdf_source.extract_text(b"pdf", deadline=102)
            self.assertEqual(result["error_kind"], kind)
            self.assertEqual(result["text"], "")
            self.assertTrue(all(not path.exists() for path in paths))

    def test_success_uses_ten_second_ceiling_and_cleans_files(self):
        paths = []
        def extracted(argv, **kwargs):
            paths.extend([Path(argv[-2]), Path(argv[-1])])
            self.assertEqual(kwargs["timeout"], 10)
            paths[-1].write_text("Source paragraph.\n\nAnother paragraph.\fSecond page.")
        with patch.object(pdf_source.subprocess, "run", side_effect=extracted):
            result = pdf_source.extract_text(b"pdf")
        self.assertIn("Source paragraph.\n\nAnother paragraph.", result["text"])
        self.assertTrue(all(not path.exists() for path in paths))

    def test_successful_pdf_routing_preserves_actual_url_not_metadata_dates(self):
        for mime in ("application/pdf", "Application/PDF; charset=binary", "text/html", "application/octet-stream"):
            start, target = "https://example.com/release", "https://example.com/original.pdf"
            responses = [httpx.Response(302, headers={"location": target}, request=httpx.Request("GET", start)),
                         httpx.Response(200, content=pdf_bytes(["Original statement."]),
                                        headers={"content-type": mime}, request=httpx.Request("GET", target))]
            with self.subTest(mime=mime), patch.object(sources, "_assert_public_http_url"), \
                    patch.object(sources.httpx, "Client") as client:
                client.return_value.__enter__.return_value.get.side_effect = responses
                result = sources.fetch_article(start)
            self.assertEqual(result["outcome"], "ok")
            self.assertEqual(result["final_url"], target)
            self.assertEqual(result["canonical_url"], target)
            self.assertEqual(result["redirect_chain"], [start, target])
            self.assertEqual(result["published_at"], "")
            self.assertEqual(result["byline"], "")

    def test_pdf_limits_survive_receipt_artifact_attempt_pool_and_next_session(self):
        url = "https://www.sec.gov/example/circular.pdf"
        response = httpx.Response(200, content=pdf_bytes(["Draft Bitcoin payment controls."]),
            headers={"content-type": "application/pdf"}, request=httpx.Request("GET", url))
        with temporary_store() as con:
            desk = session(con)
            with patch.object(sources, "_assert_public_http_url"), patch.object(sources.httpx, "Client") as client:
                client.return_value.__enter__.return_value.get.return_value = response
                result = desk._fetch(url, intake={"url_hash": candidate()["url_hash"]})
            self.assertTrue(result["ok"])
            self.assertEqual(desk.fetch_chars, len(result["text"]))
            artifact = con.execute("SELECT payload_json FROM writer_artifacts WHERE kind='receipt'").fetchone()[0]
            self.assertIn("Scanned pages", artifact)
            fid, row = result["fetch_id"], candidate()
            with patch("nbn.store.validate_newsroom_run"):
                outcome = desk._validate_and_convert_v2({
                    "stories": [{"story_id": "pdf", "story_key": "payment-controls",
                        "member_candidate_ids": [row["url_hash"]], "post": "Draft Bitcoin payment controls.",
                        "selected_fetch_id": fid, "evidence_fetch_ids": [fid]}],
                    "decisions": [{"candidate_id": row["url_hash"], "story_id": "pdf", "disposition": "publish"}]})
            attempt = outcome.story_attempts[0]
            self.assertEqual(attempt["evidence"][0]["limitations"], result["limitations"])
            store.save_newsroom_story_attempt(con, "payment-controls", "research_pending", attempt)
            pool = store.newsroom_story_memories(con)[0]["evidence_pool"]
            self.assertEqual(pool[0]["limitations"], result["limitations"])
            with patch("nbn.newsroom._cached_url_is_public", return_value=True):
                next_desk = session(con)
            rec = next(r for r in next_desk.fetches.values() if r.fetch_id.startswith("memory_"))
            self.assertEqual(rec.limitations, result["limitations"])
            self.assertEqual(next_desk._fetch_payload(rec, cached=True)["limitations"], result["limitations"])
            reusable = next_desk.continuity_cards[0]["reusable_evidence"][0]
            self.assertEqual(reusable["limitations"], result["limitations"])
            self.assertEqual(rec.retrieval_kind, "direct_fetch")


if __name__ == "__main__":
    unittest.main()
