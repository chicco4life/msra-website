# msralab.com

The MSRA website. Hosted on GitHub Pages: **every change saved here goes live by itself in 1–2 minutes.**

Research is written in the open knowledge base, [chicco4life/MSRA-Open-Research](https://github.com/chicco4life/MSRA-Open-Research).
Each folder there is one project (a report plus a `sources/` folder). To publish research, add a project there (see its CONTRIBUTING.md).

`tools/sync_research.py` copies every project into this site, so each report is a real page at `/research/<folder>/`
that search engines and AI answer engines can read (they do not run JavaScript). Run it after publishing or correcting a project,
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

English, 日本語, Nederlands, Español and 中文, chosen from the globe menu (remembered per visitor; first visit follows the browser's language).
English text is written in the pages. Every translatable element carries `data-i18n="key"`, and the other languages
live in `assets/i18n/ja.json`, `nl.json`, `es.json` and `zh.json`, one line per key. A key missing from a language shows in English.

After changing English text, rebuild and run `python3 tools/i18n.py`: it refreshes `assets/i18n/en.json`
and lists the keys each language is missing. Research reports themselves are published in English.

## Google Analytics 4

The GA4 measurement ID is `G-R7JTFRCH80`, configured as `google_analytics` in `_config.yml`.
`_includes/analytics.html` loads the Google tag once in the shared `_layouts/default.html` head
on production builds, including GitHub Pages. Local development previews do not send analytics.

Tracking covers the home page, shop and products, open research hub, library, project fallback,
and every published research report. Future pages must use `layout: default` or a layout that inherits
from it. Jekyll blog posts in `_posts/` inherit `default` automatically; any custom blog layout
must also inherit it. There are currently no blog posts in this repository.

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
