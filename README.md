# msralab.com

The MSRA website. Hosted on GitHub Pages: **every change saved here goes live by itself in 1–2 minutes.**

Research content does **not** live here. The research pages (`/research/`, `/research/project/`, `/research/library/`)
read projects live from the open knowledge base, [chicco4life/MSRA-Open-Research](https://github.com/chicco4life/MSRA-Open-Research).
Each folder there is one project (a report plus a `sources/` folder). To publish research, add a project there (see its CONTRIBUTING.md).
It appears on the website within about five minutes, with no change to this repository.

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

## Files

| Path | What it is |
|---|---|
| `index.html` | Home page |
| `shop/` | Shop page and one page per product (`_layouts/product.html` draws them from `_data/products.yml`) |
| `research/` | Projects list, single project and library pages (content loaded from the knowledge base) |
| `_data/products.yml` | Everything shown about each product |
| `_data/shop.yml` | Where the waitlist and contact forms send requests |
| `assets/i18n/` | Translations: one file per language |
| `tools/i18n.py` | Lists missing translations |
| `_config.yml` | Site settings, including which repository the research comes from |
| `_layouts/`, `_includes/` | Page templates |
| `assets/` | Styles, scripts (`site.js`, `kb.js`), images |
| `CNAME` | Tells GitHub Pages to serve msralab.com |

## Preview on your own computer (optional)

```
bundle install
bundle exec jekyll serve
```
