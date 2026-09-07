import json
import socket
import unittest
from unittest.mock import MagicMock, Mock, patch

import httpx

from nbn import sources


class SourceFetchSafetyTests(unittest.TestCase):
    def test_bitcoin_news_guides_have_a_dedicated_watch_lane(self):
        joined = " ".join(sources.X_GUIDE_QUERIES)
        for handle in ("BitcoinNewsCom", "BitcoinArchive", "BitcoinMagazine", "TFTC21",
                       "SimplyBitcoin"):
            self.assertIn(f"from:{handle}", joined)
        self.assertNotIn("BitcoinNewsCom", " ".join(sources.X_DETECTOR_QUERIES))

    def test_blockworks_is_in_detector_lane(self):
        self.assertIn("from:Blockworks_", " ".join(sources.X_DETECTOR_QUERIES))

    def test_guide_post_stays_distinct_and_carries_format_and_link_context(self):
        client = MagicMock()
        http = client.return_value.__enter__.return_value

        def result_for(_url, params):
            response = Mock()
            response.raise_for_status.return_value = None
            if params["query"] in sources.X_GUIDE_QUERIES:
                response.json.return_value = {
                    "meta": {"newest_id": "42"},
                    "includes": {"users": [{
                        "id": "7", "username": "BitcoinArchive", "verified": True,
                    }]},
                    "data": [{
                        "id": "42", "author_id": "7", "created_at": "2026-09-01T12:00:00Z",
                        "text": "JUST IN: A Bitcoin policy claim",
                        "public_metrics": {"like_count": 10, "retweet_count": 3},
                        "entities": {"urls": [{
                            "expanded_url": "https://example.com/primary",
                        }]},
                    }],
                }
            else:
                response.json.return_value = {"meta": {}, "includes": {"users": []}, "data": []}
            return response

        http.get.side_effect = result_for
        with patch.object(sources.config, "X_BEARER_TOKEN", "test"), \
                patch.object(sources.config, "X_POLL_SECONDS", 0), \
                patch.object(sources.config, "X_LIST_ID", ""), \
                patch.object(sources, "_last_x_poll", 0), \
                patch.object(sources.httpx, "Client", client):
            rows = sources.fetch_x()
        guide = next(row for row in rows if row["source"] == "X guide @BitcoinArchive")
        self.assertEqual(guide["url"], "https://x.com/BitcoinArchive/status/42")
        context = json.loads(guide["discovery_context"])
        signal = context["guide_signal"]
        self.assertEqual(signal["version"], "guide-signal-v1")
        self.assertEqual(signal["outbound_urls"], ["https://example.com/primary"])
        self.assertEqual(signal["metrics"]["likes"], 10)

    def test_kobeissi_letter_is_in_direct_research_watch(self):
        self.assertTrue(any("from:KobeissiLetter" in query
                            for query in sources.X_STATIC_QUERIES))

    def test_barchart_is_in_direct_research_watch(self):
        self.assertTrue(any("from:Barchart" in query
                            for query in sources.X_STATIC_QUERIES))

    def test_private_literal_is_rejected_before_request(self):
        client = MagicMock()
        http = client.return_value.__enter__.return_value
        with patch.object(sources.httpx, "Client", client):
            result = sources.fetch_article("http://127.0.0.1/admin")
        self.assertEqual(result["text"], "")
        http.get.assert_not_called()

    def test_redirect_hop_is_revalidated_before_private_request(self):
        response = Mock()
        response.is_redirect = True
        response.headers = {"location": "http://169.254.169.254/latest/meta-data"}
        response.url = "https://public.example/start"
        client = MagicMock()
        http = client.return_value.__enter__.return_value
        http.get.return_value = response
        public_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "",
                       ("93.184.216.34", 443))]
        with patch.object(sources.socket, "getaddrinfo", return_value=public_dns), \
                patch.object(sources.httpx, "Client", client):
            result = sources.fetch_article("https://public.example/start")
        self.assertEqual(result["text"], "")
        http.get.assert_called_once_with("https://public.example/start", timeout=20)

    def test_non_http_scheme_is_rejected(self):
        with self.assertRaises(sources.UnsafeSourceURL):
            sources._assert_public_http_url("file:///etc/passwd")

    def test_pdf_is_not_reported_as_successful_article_text(self):
        cases = [
            ("Application/PDF; charset=binary", b"%PDF-1.7\n1 0 obj\n<<>>\nendobj"),
            ("application/octet-stream", b" \n%PDF-1.7\n1 0 obj\n<<>>\nendobj"),
            ("text/html", b"%PDF-1.7\nmislabelled document"),
            ("application/pdf", b"broken PDF content without its signature"),
        ]
        for content_type, body in cases:
            with self.subTest(content_type=content_type, body=body):
                response = httpx.Response(200, content=body,
                    headers={"content-type": content_type},
                    request=httpx.Request("GET", "https://example.com/source"))
                with patch.object(sources, "_assert_public_http_url"), \
                        patch.object(sources.httpx, "Client") as client:
                    client.return_value.__enter__.return_value.get.return_value = response
                    result = sources.fetch_article("https://example.com/source")
                self.assertEqual(result["outcome"], "evidence_failed")
                self.assertEqual(result["error_kind"], "unsupported_document")
                self.assertEqual(result["text"], "")
                self.assertEqual(result["published_at"], "")
                self.assertIn("no document text was inspected", result["error_message"])

    def test_pdf_redirect_keeps_source_provenance_without_a_receipt(self):
        start = "https://example.com/release"
        target = "https://example.com/circular.pdf"
        responses = [httpx.Response(302, headers={"location": target},
                                   request=httpx.Request("GET", start)),
                     httpx.Response(200, content=b"%PDF-1.7", headers={"content-type": "application/pdf"},
                                    request=httpx.Request("GET", target))]
        with patch.object(sources, "_assert_public_http_url") as safe, \
                patch.object(sources.httpx, "Client") as client:
            client.return_value.__enter__.return_value.get.side_effect = responses
            result = sources.fetch_article(start)
        self.assertEqual(result["redirect_chain"], [start, target])
        self.assertEqual(result["final_url"], target)
        self.assertEqual(result["canonical_url"], target)
        self.assertEqual(result["outcome"], "evidence_failed")
        self.assertEqual([c.args[0] for c in safe.call_args_list], [start, target])

    def test_html_is_not_rejected_just_because_url_ends_in_pdf(self):
        url = "https://example.com/circular.pdf"
        response = httpx.Response(200, text="<p>Readable public consultation notice.</p>",
                                  headers={"content-type": "text/html"},
                                  request=httpx.Request("GET", url))
        with patch.object(sources, "_assert_public_http_url"), \
                patch.object(sources.httpx, "Client") as client:
            client.return_value.__enter__.return_value.get.return_value = response
            result = sources.fetch_article(url)
        self.assertEqual(result["outcome"], "ok")
        self.assertEqual(result["text"], "Readable public consultation notice.")


if __name__ == "__main__":
    unittest.main()
