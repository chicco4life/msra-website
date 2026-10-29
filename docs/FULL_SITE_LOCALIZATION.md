# Full-site localization and prepared release — 29 October 2026

## Scope

All 31 current source identities have 18 editions: en, de, fr, it, es, nl, pl, sv, da, nb, fi, ja, pt-BR, pt-PT, ko, zh-Hans, ru and hi. There are 558 routes (540 HTML pages plus 18 RSS feeds), including 13 actual research/guide resources and 18 marketing/support/utility identities per edition. This adds 153 marketing documents to the earlier 374 translations: 527 non-English documents in total. No future backlog item is represented as a finished article.

The homepage, shop, six product detail pages, waitlist/contact copy, shared email-topic preview, navigation, privacy and error-page copy are translated. Scholarly publication titles, names, identifiers and source URLs retain their identity. Draft feeds remain empty. Kit collection and campaigns remain disabled under the existing independent email controls.

The owner explicitly requested preservation of the current lab/manufacturing wording and confirmed that a shareholder owns an operating laboratory and manufacturing facility. This records the owner's instruction, not an independent facility/certification audit. Product and research limitations are retained in every edition.

## Markets and keyword application

Growth's core investment order is English US/UK (CA/AU extensions), German, French, then Italian/Spanish and a focused Dutch rabbit-health audience. PL/SV and Nordic editions follow; JA, BR, KR, Simplified Chinese, Russian and Hindi require their own channel/editorial context. Hindi is not treated as the language of all India; the automatic selector respects a supported browser preference in multilingual markets. Portuguese BR/PT are separate editions. Shared-language English/French/German editions are not falsely described as separately researched copy for every country.

The frozen packet is `_data/full_site_keywords.json`, imported from the authorized Consumer Growth handoff. It contains 288 intent briefs, 960 editorial candidate phrases and 124 primary/context source URLs, retaining historical Google/Trends evidence and 62 new displayed Google product-feature observations. Publisher terminology, displayed search features, aggregated Trends wording and observed individual queries are different evidence classes. Ahrefs reported an insufficient plan and Semrush reported no API units; volume/KD/CPC are unknown, not zero. No ranking, demand, AI-citation or traffic guarantee is made.

`_data/localized_seo.json` maps each HTML page to its own title, description, intent and target terminology. The 144 page-specific research overrides preserve differences among a collection, summary, core review, individual trial, source index and blank record. Utility pages do not inherit clinical acquisition keywords. No hidden keyword blocks, invented FAQ answers or special AI-only content are added. Full readable bodies, preserved citations, clear headings and canonical language URLs serve both search and retrieval systems.

## Language selection

`assets/js/language-routing.js` uses complete static language URLs. A supported legacy `?lang=` selection is consumed and remembered; manual selection wins over inference. Explicit locale paths stay in that language. Otherwise a neutral English entry first uses the best supported browser-language match among actual editions, including English. Only when there is no supported browser match can it query the fixed `https://api.country.is/` endpoint in a production HTTPS page and use the country as a secondary hint. Unavailable, timed-out or unsupported country detection retains English. Explicit Traditional Chinese browser preferences are not silently relabelled as Simplified Chinese through the country fallback.

The service necessarily receives the requesting IP. Requests omit credentials/referrer and do not send email, page URL or query parameters; MSRA never stores/logs the returned IP. Every privacy edition explains this. One session attempt and redirect history prevent loops; blocked storage, missing variants, unknown fragments and navigation changes fail safely. Compatible fragments and other query parameters survive a same-content switch. Manual links work without JavaScript; local previews perform no country lookup.

The visible menu is shared across home/shop/research/library. It links real equivalents and saves a manual preference in `msra-language-choice-v1` until the visitor clears site storage. Routing events contain only status/reason/locale, with no IP/email/path/query values.

## Release and review states

`_config.yml` prepares public discovery and automatic routing with `localization_public_release` and `language_routing_enabled`. `_data/publication_manifest.json` freezes the current identities and exact variant hashes. New identities and changed/unprepared variants remain noindex and cannot be auto-selected. The manifest is a technical indexing candidate authorized by the owner's preparation request, not native editing or independent veterinary approval. Existing Draft/source-review labels and scientific limitations remain visible. No artificial publication dates are inserted.

The prepared sitemap has 486 indexable URLs with reciprocal hreflang and x-default. Updates pages, legacy remote-project viewers, feeds and error pages remain outside acquisition discovery. Each actual edition has its own canonical. Native editorial and independent veterinary review have not been credited as performed.

`.github/workflows/pages.yml` enforces source/registry/manifest freshness without regenerating or authorizing them in CI. It runs all source coverage and routing tests, builds real production Jekyll, checks the actual rendered site, then uploads/deploys only the checked artifact. PRs validate only. GitHub Pages must use the GitHub Actions publishing source; branch-based publishing bypasses this mandatory pre-build barrier. No new paid service or credentials are needed. The remote repository currently still uses branch-based publishing; select GitHub Actions as part of the publishing step before pushing this candidate. This local preparation has not changed the remote publishing source or deployed content.

## Future edits

1. Change the English source deliberately. Reconcile every affected research translation, including qualifiers, numbers, tables and citation links, before updating its source hash. A mere hash refresh is not reconciliation.
2. Update all 17 complete marketing dictionaries when shared/home/product copy changes. Preserve every English key, markup/link identity, units and evidence boundaries.
3. Render a fresh English source snapshot, regenerate static marketing bodies, then rebuild the registry and SEO map. The generator verifies the source fingerprint and records dictionary/template hashes.
4. Review the changed content and deliberately prepare a new publication candidate. This is never done automatically by deployment CI.
5. Run a real Jekyll production build and the rendered audits before pushing.

```sh
node tools/preview_library.mjs /private/tmp/msra-library-preview-full-site-source
python3 tools/prepare_marketing_localizations.py --built /private/tmp/msra-library-preview-full-site-source
python3 tools/prepare_localizations.py
python3 tools/import_full_site_keywords.py
python3 tools/import_full_site_keywords.py --check
python3 tools/import_full_site_keywords.py --self-test
python3 tools/prepare_publication_manifest.py
python3 tools/prepare_localizations.py --check
python3 tools/prepare_publication_manifest.py --check
python3 tools/verify_localizations.py --complete
node tools/test_language_routing.cjs
JEKYLL_ENV=production bundle exec jekyll build
python3 tools/verify_full_site.py --built _site --complete --release
```

The limited Node/Liquid/marked renderer is for design and source generation; it is not the production compiler or sitemap plugin. Development browser previews send neither GA4 nor country requests. Production output deliberately includes GA4 `G-R7JTFRCH80` exactly once per HTML page, including every real language URL. No additional GA4 account settings or real-time metrics are asserted here.

## Verification and delivery

Full reports, browser receipts and final screenshots are kept outside the deployable checkout in `../library-preview-2026-10-29/`. The release receipt distinguishes native production builds, source fidelity, routing fixtures, browser checks and live verification. A local build is not a GitHub Actions run or a live deployment. Search indexing/performance, live IP fallback behavior and analytics reception still require the post-push live check.
