# Updating library wording and navigation

The Pet Health Library keeps its species/condition architecture and canonical routes. Growth and the dedicated feline research thread own owner-query evidence, selected targets, briefs and scientific wording. Website changes remain with the website implementation thread.

## What changes where

`_data/library.json` owns curated shelf selection and card-only presentation. It is separate from generated `_data/knowledge.json` and from the provisional growth order. A manual navigation choice is not a measured demand ranking.

- `topics.feline-urinary.overview_id` pins O00 as the central orientation card.
- `guide_ids` selects the five existing guides; `featured_ids` selects the library entry cards.
- `related_ids` provides up to three available related guides, excluding the current article. `study_ids` selects existing study explanations.
- `tool_id` resolves the public record T24.
- `cards.<content_id>.title`, `summary` and `label` override only the card. Empty strings use the actual source title/summary/label. Card destinations always come from the matching source document; this file cannot invent or override a URL.

For example, an approved shorter G04 card title belongs at `cards.G04.title`. It changes the card wording across the library, hub and related-reading shelves while preserving G04's canonical URL and full article title. Treat current wording as working editorial copy until owner-query and source checks support a revision.

The whole article title is already data in that article's front matter. An approved article-title change belongs in `title`; review `seo_title` and description at the same time. The article heading, social metadata and Article/Breadcrumb metadata read the same source fields. Keep `content_id`, `permalink`, source links, actual authorship and review status intact. Never derive a new slug from a revised title.

## Receiving research work

Read the selected targets/briefs saved under `growth-research/feline-urinary/` in the shared MSRA folder. The current priority note and `PROVISIONAL_CONTENT_PRIORITY.json` are editorial hypotheses, not verified search-volume data. No brief or priority file is imported or published automatically.

Resolve a brief by stable content ID first. Reuse the existing destination when the owner task is the same. The 26-record evidence map includes sections, reference material and conditional candidates; it is not a page-creation queue. A selected section does not receive a new route merely because its acquisition attention changes. O00 and T24 remain useful navigation infrastructure regardless of their promotion rank. Unknown IDs are rejected by the presentation verifier until there is an actual substantive source document and deliberate route decision.

If source text is later regenerated, carry its stable `content_id` and approved existing `permalink` into the source record. Locally adapted copies remain protected by `frontend_edited: true`; reconcile them deliberately rather than clearing that guard for an automatic sync.

## Verify a wording change

From the website checkout:

```sh
python3 tools/verify_library_presentation.py
```

After rendering the local design preview or a real build:

```sh
python3 tools/verify_library_presentation.py --built /private/tmp/msra-library-preview
python3 tools/verify_knowledge.py --kb ../../msra-open-research --built /private/tmp/msra-library-preview
```

The presentation check validates real IDs/routes, card order, title fallbacks/overrides and canonical identity. The broader check verifies links, fragments, Article metadata and draft exclusions. The existing local preview renderer is not a Jekyll build; a production Jekyll build and the recorded editorial release checks remain separate requirements. No wording or shelf edit activates Kit or changes GA4.
