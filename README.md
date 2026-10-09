# msralab.com

The MSRA website: home page, research notes and research library.
It is hosted on GitHub Pages. **Every change you save here goes live by itself in 1–2 minutes.** Nothing to upload or re-host.

## Publish a research note

1. Open the `_posts` folder → **Add file** → **Create new file**.
2. Name the file `YYYY-MM-DD-short-title.md`, for example `2026-11-02-rabbit-gut-notes.md`
   (lowercase, hyphens, no spaces). For a Chinese version, end the name with `-zh`.
3. Copy everything from `docs/post-template.md`, paste it in, and fill it in.
4. Click **Commit changes**. The note appears at `msralab.com/research/` a minute or two later.
   Progress shows under the **Actions** tab; a red ✕ there means a typo in the top section of the file.

Or send the text to Claude and ask for a post file; paste what it gives you in step 3.

**Images:** upload them to `assets/img/posts/` (webp or jpg, under 500 KB), then write
`![What the image shows](/assets/img/posts/file-name.webp)` in the note.

## Add a study to the research library

Edit `_data/library.yml`, copy one block, change the details, commit.
Mark free full text with its `pmc:` ID so it shows as open access.

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

## Preview on your own computer (optional)

```
bundle install
bundle exec jekyll serve
```
Then open http://localhost:4000.

## Files

| Path | What it is |
|---|---|
| `index.html` | Home page |
| `_posts/` | Research notes, one file each |
| `research/` | Research list page and library page |
| `_data/library.yml` | Studies in the research library |
| `_data/shop.yml` | Buy links |
| `_layouts/`, `_includes/` | Page templates |
| `assets/` | Styles, script, images |
| `CNAME` | Tells GitHub Pages to serve msralab.com |
