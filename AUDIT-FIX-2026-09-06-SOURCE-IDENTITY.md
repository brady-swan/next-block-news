# Audit repair: Bitcoin News source identity

## Evidence and scope

On September 6, production draft 10650329 attributed an inspected @BitcoinNewsCom post to
"Bitcoin.com News". The configured source entry incorrectly combined that guide handle with
bitcoin.com/news.bitcoin.com, supplying the wrong label to the editor. The fetched X page itself
identified the account as Bitcoin News.

Bitcoin News's [own newsletter](https://bitcoinnews.com/p/out-of-the-frying-pan-into-the-fire)
explicitly identifies @BitcoinNewsCom as its Twitter account. Its [about page](https://bitcoinnews.com/about-us)
identifies the Bitcoin-only publication; [Bitcoin.com News](https://news.bitcoin.com/) is a
separate branded site. This is an exact source-identity defect, not editorial source weighting.

## Small repair

- Preserve the guide's existing source ID and handle; correct its display name and identity.
- Retain the existing Bitcoin.com domains in a separate entry, with their existing identity key.
- Preserve T3/discovery capability for both, the guide roster, model roster, prompts and cadence.
- Do not add Bitcoin News's website to the registry or follow any new handle in this repair.
- URL classification overrides obsolete cached labels. Historical records and Typefully copy
  remain unchanged; there is no data migration, restaging, retry or publisher mutation.

## Verification and release

Focused source-policy/newsroom suite: 45 tests passed. Working-tree Python 3.12 suite:
427 tests passed, including two pre-existing unreleased evaluator tests. No runtime prompt
or code logic changed. URL-based reclassification in the existing event-memory reader also
recomputes the corrected label rather than trusting the stored historical label.

Pending: full clean-release suite, production backup, clean-archive deployment,
direct classification and HTTP smoke, natural worker cycle.
Autopost remains OFF. Rolling audit remains ACTIVE.
