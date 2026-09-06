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

Shipped runtime commit `c581510`, pushed to main. Clean archive
`/tmp/nbn-identity-release.oNjy7c` passed **425 tests** on Python 3.12. Production backup:
`/data/backups/nbn-pre-source-policy-20260906T125747Z.db`.

Railway deployment `7e3b8a34-b3e8-492e-ad60-adb1f207ad22` is **SUCCESS**. Production
classification returns Bitcoin News for the guide even with its obsolete cached label,
and Bitcoin.com News for the separate domain. Both remain T3/discovery.
Local and public health/snapshot checks passed; unauthenticated snapshots returned 403.
The PDF hash is unchanged and SQLite quick_check returned `ok`. A natural cycle completed
at `1788699530.9991043`, after process start `1788699526.644911`, without a worker error.

No provider/model test calls, Typefully writes, forced editorial runs or historical-record
rewrites were made. Autopost remains OFF. Rolling audit remains ACTIVE. Existing draft
10650329 still contains the old attribution and remains for human review; this deploy does
not silently correct previously delivered copy. Rollback is the prior runtime `2d9dcad`.
