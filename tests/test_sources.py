import json
import socket
import unittest
from unittest.mock import MagicMock, Mock, patch

from nbn import sources


class SourceFetchSafetyTests(unittest.TestCase):
    def test_bitcoin_news_guides_have_a_dedicated_watch_lane(self):
        joined = " ".join(sources.X_GUIDE_QUERIES)
        for handle in ("BitcoinNewsCom", "BitcoinArchive", "BitcoinMagazine", "TFTC21"):
            self.assertIn(f"from:{handle}", joined)
        self.assertNotIn("BitcoinNewsCom", " ".join(sources.X_DETECTOR_QUERIES))

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
        http.get.assert_called_once_with("https://public.example/start")

    def test_non_http_scheme_is_rejected(self):
        with self.assertRaises(sources.UnsafeSourceURL):
            sources._assert_public_http_url("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
