# msralab.com

## Pet Health Library — editorial implementation, 29 October 2026

`/learn/` opens an **ongoing-project selector → core review → flat article table**. Feline urinary health has seven articles and guides; rabbit digestion and weather links to its existing core review and honestly shows no separate articles yet. `/learn/cats/` is pinned to the same feline review and seven-row table. Supporting overview, source-index and printable-record links remain available. The Maine Coon draft remains conditional, with no breed-specific risk or treatment claim. The 26-record backlog includes sections and future candidates; it is not 26 finished pages.

The library preserves its source-checking and independent veterinary-review labels. The prepared public indexing candidate is separate from scientific review: current verified language URLs have self-canonicals, reciprocal language links and sitemap entries when the release switches are on. No publication dates or clinical approvals are invented; draft RSS feeds stay empty. New or changed editions require fresh checks and a deliberate candidate update.

`_data/library_projects.json` drives the project/core/article mapping and supporting resource links. Curated copy and retained card configuration live in `_data/library.json`. These are independent of provisional acquisition priorities and survive article-data generation. Keep stable IDs and routes when validated wording changes; see [the editorial handoff](docs/LIBRARY_EDITORIAL_HANDOFF.md).

Owner source articles live in `MSRA-Open-Research/content/articles/`. The synchronizers now protect locally adapted website copies with `frontend_edited: true`; reconcile the audited changes into their sources before resync. Source `publication_state: ready` means generation eligibility, not release clearance. See [release notes](docs/FRONTEND_RELEASE_NOTES.md) for the explicit publication gate and safe verification commands.

A dependency-free design preview can use the existing bundled runtime:

```sh
/Users/work/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/preview_library.mjs
python3 -m http.server 8768 --bind 127.0.0.1 --directory /private/tmp/msra-library-preview
```

Open `/learn/` on that local server. The retained feline collection is at `/learn/cats/urinary-health/`. This uses a limited Liquid/Markdown preview renderer; **it is not a Jekyll build**. A real Jekyll 3.10 production build is also verified for this implementation. Use the real build and rendered audit below before deploying subsequent changes.

Topic subscriptions use local email-entry bars and one shared topic dialog, with the genuine Kit form behind release gates in `_data/subscriptions.yml`. See [docs/MAILING_LIST_SETUP.md](docs/MAILING_LIST_SETUP.md) and the [current connection receipt](docs/KIT_CONNECTION_STATUS_2026-10-29.md). Collection and verification flags remain off and the privacy URL remains empty; preview email entries and choices are not saved or sent. Sender/domain verification, topic preferences and the controlled hosted signup, confirmation, tag changes and unsubscribe are complete. The privacy notice and website connection remain local previews pending publication and deployment.

The owner editorial layout removes product checkout prompts and records research versus commercial scope. The existing shop/contact forms remain a separate implementation.

The MSRA website is hosted on GitHub Pages. The checked workflow in `.github/workflows/pages.yml` validates committed translation/allowlist snapshots, builds Jekyll and audits the result before deploying a push to `main`. Pull requests validate without deploying. Pages must use **GitHub Actions** as its publishing source; changing this setting does not publish these local files.

Research is written in the open knowledge base, [chicco4life/MSRA-Open-Research](https://github.com/chicco4life/MSRA-Open-Research).
Each folder there is one project (a report plus a `sources/` folder). To publish research, add a project there (see its CONTRIBUTING.md).

`tools/sync_research.py` copies every project into this site, so each report is a real page at `/research/<folder>/`
that crawlers and retrieval tools can read without running JavaScript. Run it after publishing or correcting a project,
then commit `_research/` and `_data/research.json`:

```
python3 tools/sync_research.py
```

Until the next sync, a newly published project still shows on `/research/` (added in the browser by `assets/js/kb.js`)
and opens at `/research/project/?p=<folder>`, a fallback page kept out of search results. Old `?p=` links to synced
projects forward to the new address.

## Shop and products

`/shop/` lists the six products; each has its own page at `/shop/<product>/`.
All product text (problem, research, ingredients, evidence, limits, references) lives in `_data/products.yml`.
Edit it there and the shop, the product pages and the home page update together.
Fill a product's `price` to show it; set `status` to `preorder`, `next` or `dev` to change its label.

Every product's button says "Pre-order" and opens a waitlist form (email, optional country).

## Waitlist and contact forms

By default both forms open the visitor's email app with the request filled in, addressed to li@msralab.com.
To collect sign-ups directly instead, create a free form at formspree.io and paste its endpoint
into `form_endpoint` in `_data/shop.yml`.

## Languages

The entire current website has complete static editions in English, German, French, Italian, Spanish, Dutch, Polish, Swedish, Danish, Norwegian Bokmål, Finnish, Japanese, Brazilian Portuguese, European Portuguese, Korean, Simplified Chinese, Russian and Hindi. There are **31 page identities × 18 editions = 558 routes**: 540 HTML pages and 18 RSS feeds. The 17 non-English editions are 527 saved documents, including home, shop, all six product pages, research, guides, utilities, forms and error-page copy. Original bibliographic titles/DOIs remain in their source language.

Full translated bodies live in `_localized/<locale>/`. Marketing dictionaries in `assets/i18n/` each contain all 367 keys and are materialized into HTML by `tools/prepare_marketing_localizations.py`; browser JavaScript does not replace these static bodies. English URLs stay unchanged. The shared header menu switches between actual same-content URLs, remembers explicit choices and preserves compatible deep links. Production automatic selection first matches a supported browser language and uses Country.is IP-country lookup only as a secondary fallback; unavailable or unsupported detection retains English. Explicit language URLs and saved choices win; localhost previews never request a country.

`_data/full_site_keywords.json` freezes Growth’s 288 regional intent briefs and source provenance. `_data/localized_seo.json` applies distinct page titles, descriptions and keyword targets. The current list contains 960 proposed phrases informed by primary local wording and observed Google features; it is not 960 measured user queries. Keyword volume, difficulty and CPC remain unknown because provider access was unavailable. Core market order and all evidence limits are in [the full-site handoff](docs/FULL_SITE_LOCALIZATION.md).

The two production switches are `localization_public_release` and `language_routing_enabled`. The frozen `_data/publication_manifest.json` restricts discoverability and automatic routing to the prepared identities and exact edition hashes. Unlisted, changed or missing editions fail closed; the checked deployment requires source/registry/manifest freshness before building. Indexing preparation does not claim native-language or veterinary approval. Email collection remains separately disabled.

The [SEO/GEO verification pass](docs/SEO_GEO_VERIFICATION.md) records the keyword-evidence audit, playbook fixes and outstanding regional Planner validation.

For future edits, follow [the regeneration and production checks](docs/FULL_SITE_LOCALIZATION.md). Do not refresh manuscript hashes or the publication candidate to bypass missing translation reconciliation.

## Google Analytics 4

The GA4 measurement ID is `G-R7JTFRCH80`, configured as `google_analytics` in `_config.yml`.
`_includes/analytics.html` loads the Google tag once in the shared `_layouts/default.html` head
on production builds, including GitHub Pages. The standalone `_layouts/localized.html` and `_layouts/localized-marketing.html` include the same production-gated tag once. Local development previews do not send analytics.

Tracking covers the home page, shop and products, open research hub, library, project fallback,
and every published research report, including actual localized research URLs when released. Future pages must use `layout: default` or a layout that inherits
from it. Jekyll blog posts in `_posts/` inherit `default` automatically; any custom blog layout
must also inherit it or deliberately include the shared production-gated tag once, as the localized layout does. There are currently no blog posts in this repository.

The source files and scientific evidence viewed on github.com are outside this site's tracking;
the published reports on msralab.com are tracked.

To check a deployment, visit the live site and its research reports, then check this property's
Realtime report in Google Analytics. Ad blockers or browser privacy settings may prevent collection.
To preview the production tag locally, use `JEKYLL_ENV=production bundle exec jekyll serve`.

## Files

| Path | What it is |
|---|---|
| `index.html` | Home page |
| `shop/` | Shop page and one page per product (`_layouts/product.html` draws them from `_data/products.yml`) |
| `research/` | Projects hub, library and the `?p=` fallback page |
| `_research/`, `_data/research.json` | Reports and sources copied from the knowledge base by `tools/sync_research.py` (do not edit by hand) |
| `_layouts/report.html` | The research report page |
| `_includes/seo.html`, `_includes/schema.html` | Browser-tab titles, descriptions, canonical and social tags; structured data |
| `_includes/analytics.html` | Shared GA4 tag, enabled for production builds |
| `_data/products.yml` | Everything shown about each product |
| `_data/shop.yml` | Where the waitlist and contact forms send requests |
| `assets/i18n/` | Translations: one file per language |
| `tools/i18n.py` | Lists missing translations |
| `tools/sync_research.py` | Copies research projects from the knowledge base into the site |
| `_config.yml` | Site settings, including which repository the research comes from |
| `_layouts/`, `_includes/` | Page templates |
| `assets/` | Styles, scripts (`site.js`, `kb.js`), images |
| `CNAME` | Tells GitHub Pages to serve msralab.com |

## Preview on your own computer (optional)

```
bundle install
bundle exec jekyll serve
```
