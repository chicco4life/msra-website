# msralab.com

The MSRA website. Hosted on GitHub Pages: **every change saved here goes live by itself in 1–2 minutes.**

Research content does **not** live here. The research pages (`/research/`, `/research/library/`) read notes and studies
live from the open knowledge base, [chicco4life/msra](https://github.com/chicco4life/msra). To publish research,
add it there (see that repository's CONTRIBUTING.md). It appears on the website within about five minutes, with no change to this repository.

## Turn on buy buttons

Edit `_data/shop.yml` and paste the product's Shopify or Amazon link between the quotes.
With no link, the button says "Pre-order" and opens the pre-order / inquiry form on the home page.

## Pre-order and inquiry form

By default the form opens the visitor's email app with the request filled in, addressed to li@msralab.com.
To receive submissions directly instead, create a free form at formspree.io and paste its endpoint
into `form_endpoint` in `_data/shop.yml`.

## Edit the home page

`index.html`. English text sits between the tags; the Chinese version of the same text sits in the
`data-cn="…"` attribute beside it. Change both.

## Files

| Path | What it is |
|---|---|
| `index.html` | Home page |
| `research/` | Research list, single note and library pages (content loaded from the knowledge base) |
| `_data/shop.yml` | Buy links and the form endpoint |
| `_config.yml` | Site settings, including which repository the research comes from |
| `_layouts/`, `_includes/` | Page templates |
| `assets/` | Styles, scripts (`site.js`, `kb.js`), images |
| `CNAME` | Tells GitHub Pages to serve msralab.com |

## Preview on your own computer (optional)

```
bundle install
bundle exec jekyll serve
```
