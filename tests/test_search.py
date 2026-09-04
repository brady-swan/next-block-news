import logging
import unittest
from unittest.mock import Mock, patch

from nbn import search


class SearchTests(unittest.TestCase):
    def test_unconfigured_search_is_a_noop(self):
        with (
            patch("nbn.search.config.SERPAPI_KEY", ""),
            patch("nbn.search.httpx.get") as get,
        ):
            self.assertEqual(search.google("Bitcoin policy"), [])
        get.assert_not_called()

    def test_google_shapes_only_public_organic_results(self):
        response = Mock(is_success=True, status_code=200)
        response.json.return_value = {
            "search_metadata": {"status": "Success"},
            "organic_results": [
                {
                    "position": 1,
                    "title": "Release",
                    "link": "https://sec.gov/release",
                    "source": "SEC",
                    "snippet": "Official release",
                },
                {"position": 2, "title": "Unsafe", "link": "javascript:alert(1)"},
                {
                    "position": 3,
                    "title": "Report",
                    "link": "https://reuters.com/report",
                },
            ],
        }
        with (
            patch("nbn.search.config.SERPAPI_KEY", "secret"),
            patch("nbn.search.httpx.get", return_value=response) as get,
        ):
            results = search.google("Bitcoin policy", max_results=5)
        self.assertEqual([row["rank"] for row in results], [1, 3])
        self.assertEqual(results[1]["outlet"], "reuters.com")
        self.assertEqual(get.call_args.kwargs["timeout"], 15.0)
        self.assertEqual(get.call_args.kwargs["params"]["q"], "Bitcoin policy")

    def test_provider_error_is_typed_without_response_body(self):
        response = Mock(is_success=False, status_code=429)
        with (
            patch("nbn.search.config.SERPAPI_KEY", "secret"),
            patch("nbn.search.httpx.get", return_value=response),
            self.assertRaisesRegex(search.SearchError, "HTTP 429") as raised,
        ):
            search.google("Bitcoin policy")
        self.assertEqual(raised.exception.kind, "provider_error")

    def test_quota_error_and_retry_after_are_typed(self):
        response = Mock(is_success=False, status_code=429)
        response.headers = {"retry-after": "99999"}
        response.json.return_value = {"error": "Your account has run out of searches."}
        with patch("nbn.search.config.SERPAPI_KEY", "secret"), \
                patch("nbn.search.httpx.get", return_value=response):
            with self.assertRaises(search.SearchError) as raised:
                search.google("Bitcoin policy")
        self.assertEqual(raised.exception.kind, "quota_exhausted")
        self.assertEqual(raised.exception.retry_after_seconds, 3600)

    def test_account_status_returns_allowlisted_capacity_without_identity_or_key(self):
        response = Mock(is_success=True, status_code=200)
        response.json.return_value = {
            "api_key": "secret", "account_id": "identity", "account_email": "x@example.com",
            "plan_name": "Developer Plan", "plan_renewal_date": "2026-09-06",
            "searches_per_month": 5000, "this_month_usage": 1000,
            "total_searches_left": 4000, "this_hour_searches": 3,
            "last_hour_searches": 2, "account_rate_limit_per_hour": 1000,
        }
        with patch("nbn.search.config.SERPAPI_KEY", "secret"), \
                patch("nbn.search.httpx.get", return_value=response):
            result = search.account_status()
        self.assertEqual(result["state"], "healthy")
        self.assertEqual(result["total_searches_left"], 4000)
        self.assertNotIn("api_key", result)
        self.assertNotIn("account_id", result)
        self.assertNotIn("account_email", result)
        self.assertNotIn("secret", repr(result))

    def test_httpx_logging_level_is_restored_after_search(self):
        response = Mock(is_success=True, status_code=200)
        response.json.return_value = {
            "search_metadata": {"status": "Success"},
            "organic_results": [],
        }
        logger = logging.getLogger("httpx")
        prior_level = logger.level
        logger.setLevel(logging.INFO)
        try:
            with (
                patch("nbn.search.config.SERPAPI_KEY", "secret"),
                patch("nbn.search.httpx.get", return_value=response),
            ):
                search.google("Bitcoin policy")
            self.assertEqual(logger.level, logging.INFO)
        finally:
            logger.setLevel(prior_level)


if __name__ == "__main__":
    unittest.main()
