import socket
import unittest
from unittest.mock import MagicMock, Mock, patch

from nbn import sources


class SourceFetchSafetyTests(unittest.TestCase):
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
