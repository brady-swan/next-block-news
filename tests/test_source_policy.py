import tempfile
import unittest
from pathlib import Path

from nbn import source_policy


class SourcePolicyTests(unittest.TestCase):
    def test_requested_outlets_have_expected_tiers(self):
        cases = {
            "https://cryptoslate.com/story": ("cryptoslate", "t3"),
            "https://x.com/BitcoinNewsCom/status/1": ("bitcoin-news-com", "t3"),
            "https://x.com/BitcoinArchive/status/1": ("bitcoin-archive", "t3"),
            "https://x.com/BitcoinMagazine/status/1": ("bitcoin-magazine", "t2"),
            "https://x.com/coindesk/status/1": ("coindesk", "t2"),
            "https://www.btcpolicy.org/research/report": ("bitcoin-policy-institute", "t2"),
            "https://x.com/KobeissiLetter/status/1": ("kobeissi-letter", "t2"),
            "https://www.thekobeissiletter.com/p/markets": ("kobeissi-letter", "t2"),
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                ref = source_policy.classify(url)
                self.assertEqual((ref.source_id, ref.tier), expected)

    def test_handle_classifies_x_url(self):
        ref = source_policy.classify(
            "https://x.com/BitcoinArchive/status/1", "X detector @BitcoinArchive")
        self.assertEqual(ref.source_id, "bitcoin-archive")
        self.assertEqual(ref.matched_by, "handle")

    def test_x_url_path_handle_overrides_spoofed_source_label(self):
        ref = source_policy.classify(
            "https://x.com/BitcoinArchive/status/1", "X @coinbase")
        self.assertEqual(ref.source_id, "bitcoin-archive")
        self.assertEqual(ref.tier, "t3")

    def test_outbound_link_uses_receipt_domain_not_account_handle(self):
        ref = source_policy.classify(
            "https://coindesk.com/story", "X @BlackRock")
        self.assertEqual(ref.source_id, "coindesk")
        self.assertEqual(ref.matched_by, "domain")

    def test_subdomain_and_mobile_normalization(self):
        self.assertEqual(source_policy.classify("https://www.reuters.com/a").source_id, "reuters")
        self.assertEqual(source_policy.classify("https://m.reuters.com/a").source_id, "reuters")

    def test_unknown_fails_closed(self):
        ref = source_policy.classify("https://unrated.example/story", "Unrated")
        self.assertEqual(ref.tier, "unknown")
        self.assertFalse(ref.base_receipt_eligible)

    def test_untrusted_host_cannot_borrow_privileged_alias(self):
        ref = source_policy.classify("https://untrusted.example/story", "SEC")
        self.assertEqual(ref.tier, "unknown")
        self.assertFalse(ref.official)

    def test_url_prefix_match_requires_path_boundary(self):
        good = source_policy.classify("https://github.com/bitcoin/bitcoin/releases/tag/v1")
        hostile = source_policy.classify("https://github.com/bitcoin/bitcoin-evil")
        self.assertEqual(good.source_id, "bitcoin-core")
        self.assertEqual(hostile.tier, "unknown")

    def test_root_url_prefix_allows_paths_only_on_exact_origin(self):
        valid = source_policy.classify("https://bitcoincore.org/en/releases/30.0/")
        lookalike = source_policy.classify("https://evilbitcoincore.org/en/releases/30.0/")
        suffix = source_policy.classify("https://bitcoincore.org.evil.example/en/releases/30.0/")
        self.assertEqual(valid.source_id, "bitcoin-core")
        self.assertEqual(lookalike.tier, "unknown")
        self.assertEqual(suffix.tier, "unknown")

    def test_fred_graph_query_is_scoped_official_artifact_prefix(self):
        ref = source_policy.classify("https://fred.stlouisfed.org/graph/?g=abc123")
        self.assertEqual(ref.source_id, "federal-reserve")
        self.assertEqual(ref.matched_by, "url_prefix")

    def test_official_handle_and_website_share_owner(self):
        account = source_policy.classify("https://x.com/coinbase/status/1")
        website = source_policy.classify("https://coinbase.com/institutional/research")
        self.assertEqual(account.ownership_key, website.ownership_key)

    def test_content_fingerprint_collapses_formatting(self):
        self.assertEqual(source_policy.content_fingerprint("Bitcoin, rose 2%."),
                         source_policy.content_fingerprint(" bitcoin rose 2 "))

    def test_content_fingerprint_collapses_boilerplate_modified_copy(self):
        body = ("Reuters reported that the Securities and Exchange Commission approved "
                "the Bitcoin exchange traded fund after commissioners voted on the "
                "proposed rule change. The order becomes effective immediately and "
                "applies to the named exchange.")
        wrapper = ("Subscribe to our newsletter for daily updates. " + body +
                   " Copyright 2026 Example Media. All rights reserved.")
        self.assertTrue(source_policy.content_fingerprints_match(
            source_policy.content_fingerprint(body),
            source_policy.content_fingerprint(wrapper)))

    def test_malformed_and_duplicate_policy_are_rejected(self):
        duplicate = """
version = 1
[[sources]]
id="a"
display_name="A"
tier="t1"
category="reporting"
independence_key="a"
receipt_role="reporting"
domains=["same.example"]
aliases=[]
handles=[]
[[sources]]
id="b"
display_name="B"
tier="t2"
category="reporting"
independence_key="b"
receipt_role="reporting"
domains=["same.example"]
aliases=[]
handles=[]
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.toml"
            path.write_text(duplicate)
            with self.assertRaisesRegex(source_policy.PolicyError, "duplicate domain"):
                source_policy.SourcePolicy.from_path(path)
            path.write_text("version = 2\n")
            with self.assertRaisesRegex(source_policy.PolicyError, "version"):
                source_policy.SourcePolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
