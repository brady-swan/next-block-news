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
                self.assertEqual(result["error_kind"], "pdf_extraction_failed")
                self.assertEqual(result["text"], "")
                self.assertEqual(result["published_at"], "")
                self.assertIn("could not be read", result["error_message"])

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

    def test_article_body_precedes_navigation_before_text_and_link_caps(self):
        for marker in ('class="RichTextStoryBody RichTextBody"',
                       'class="article-body"', 'itemprop="articleBody"',
                       'class="td-post-content tagdiv-type"'):
            with self.subTest(marker=marker):
                url = "https://example.com/news/hearing"
                # Real AP/Fox pages put long div-based menus before their story body.
                menu = '<div>' + ('Menu and unrelated headline ' * 400) + ''.join(
                    f'<a href="/menu/{i}">Menu {i}</a>' for i in range(30)) + '</div>'
                body = ('<title>Hearing report</title>'
                        '<link rel="canonical" href="https://example.com/hearing">'
                        '<meta name="author" content="Reporter">'
                        '<meta property="article:published_time" content="2026-09-07">'
                        + menu + f'<div {marker}><p>A hearing is scheduled Tuesday.</p>'
                        '<div><p>Nested article paragraph &amp; context.</p></div>'
                        '<a href="/original?x=1&amp;y=2">Original record</a>'
                        '<script>not source text</script></div><div>Related headlines</div>')
                response = httpx.Response(200, text=body,
                    request=httpx.Request("GET", url))
                with patch.object(sources, "_assert_public_http_url"), \
                        patch.object(sources.httpx, "Client") as client:
                    client.return_value.__enter__.return_value.get.return_value = response
                    result = sources.fetch_article(url, limit=220)
                self.assertIn("A hearing is scheduled Tuesday.", result["text"])
                self.assertIn("Nested article paragraph & context.", result["text"])
                self.assertIn("Hearing report", result["text"])
                self.assertNotIn("Menu", result["text"])
                self.assertNotIn("Related headlines", result["text"])
                self.assertNotIn("not source text", result["text"])
                self.assertLessEqual(len(result["text"]), 220)
                self.assertEqual(result["links"], [{"text": "Original record",
                    "url": "https://example.com/original?x=1&y=2"}])
                self.assertEqual(result["byline"], "Reporter")
                self.assertEqual(result["published_at"], "2026-09-07")
                self.assertEqual(result["canonical_url"], "https://example.com/hearing")
                self.assertEqual(result["redirect_chain"], [url])

    def test_ambiguous_article_bodies_keep_whole_page_fallback(self):
        url = "https://example.com/collection"
        body = ('<p>Collection introduction.</p>'
                '<div class="article-body">First article.</div>'
                '<div class="article-body">Second article.</div>')
        response = httpx.Response(200, text=body, request=httpx.Request("GET", url))
        with patch.object(sources, "_assert_public_http_url"), \
                patch.object(sources.httpx, "Client") as client:
            client.return_value.__enter__.return_value.get.return_value = response
            result = sources.fetch_article(url)
        self.assertEqual(result["text"], "Collection introduction. First article. Second article.")

    def test_explicit_header_report_survives_chrome_cleanup_and_caps(self):
        url = "https://www.btcpolicy.org/articles/data-center-dividends"
        body = ('<title>Data Center Dividends</title>'
                '<link rel="canonical" href="https://example.com/report">'
                '<meta name="author" content="Report author">'
                '<header>Site navigation</header><div>' + 'Menu ' * 400 + ''.join(
                    f'<a href="/menu/{i}">Menu {i}</a>' for i in range(30)) + '</div>'
                '<header class="section_blog-post2-content"><div>'
                '<h1>Data Center Dividends</h1><p>September 9, 2026</p>'
                '<a href="/report.pdf">Download report</a>'
                '<div class="text-rich-text w-richtext">'
                '<p>Conditional household estimates use existing revenue.</p>'
                '<header>Nested navigation</header><p>Services are funded first.</p>'
                '<a href="/methodology">Methodology</a><script>Script noise</script>'
                '</div></div></header><footer>Footer noise</footer>')
        response = httpx.Response(200, text=body, request=httpx.Request("GET", url))
        with patch.object(sources, "_assert_public_http_url"), \
                patch.object(sources.httpx, "Client") as client:
            client.return_value.__enter__.return_value.get.return_value = response
            result = sources.fetch_article(url, limit=240)
        self.assertIn("Conditional household estimates", result["text"])
        self.assertIn("Services are funded first.", result["text"])
        self.assertIn("September 9, 2026", result["text"])
        for noise in ("Site navigation", "Menu", "Nested navigation", "Script noise", "Footer noise"):
            self.assertNotIn(noise, result["text"])
        self.assertLessEqual(len(result["text"]), 240)
        self.assertEqual(result["links"], [
            {"text": "Download report", "url": "https://www.btcpolicy.org/report.pdf"},
            {"text": "Methodology", "url": "https://www.btcpolicy.org/methodology"}])
        self.assertEqual(result["canonical_url"], "https://example.com/report")
        self.assertEqual(result["byline"], "Report author")

    def test_ambiguous_header_reports_do_not_select_one(self):
        body = ('<p>Collection introduction.</p>'
                '<header class="section_blog-post2-content">First report.</header>'
                '<header class="section_blog-post2-content">Second report.</header>')
        self.assertEqual(sources._article_markup(body), body)

    def test_unmarked_header_remains_chrome(self):
        url = "https://example.com/news"
        body = '<header>Site menu</header><p>Actual article text.</p>'
        response = httpx.Response(200, text=body, request=httpx.Request("GET", url))
        with patch.object(sources, "_assert_public_http_url"), \
                patch.object(sources.httpx, "Client") as client:
            client.return_value.__enter__.return_value.get.return_value = response
            result = sources.fetch_article(url)
        self.assertEqual(result["text"], "Actual article text.")


if __name__ == "__main__":
    unittest.main()
