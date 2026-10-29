# Research language editions — earlier implementation record

**Superseded for current scope and release behavior by [FULL_SITE_LOCALIZATION.md](FULL_SITE_LOCALIZATION.md).** This record describes the earlier research-only draft stage; home/shop localization and a real production build are now included.

All three requested implementation stages are prepared locally: consumer titles and pinned reviews/topic menus; reconciliation with the Consumer Growth scientific packet; full research-language editions and their keyword mappings. This is a source and preview handoff, not a deployment, native-language review or clinical approval.

## Actual inventory

English plus `de`, `fr`, `it`, `es`, `nl`, `pl`, `sv`, `da`, `nb`, `fi`, `ja`, `pt-BR`, `pt-PT`, `ko`, `zh-Hans`, `ru`, `hi` covers all 18 editions named in Growth's expanded handoff. URL prefixes are lowercase (`/pt-br/`, `/pt-pt/`, `/zh-hans/`); HTML language identifiers retain their declared casing. Bokmål and Hindi remain the commissioning choices recorded in the handoff, not evidence that every Norwegian/Indian language was researched.

Each edition has the 13 actual source destinations: G01–G05, E09, V25, H00, O00, S00, T24, R00 and the existing rabbit review. Rabbit's implementation key is `research:2026-09-rabbit-digestion-weather`; Growth's `RABBIT-CORE` is its inventory alias, not a new English content ID. The 9 utilities are library home, cat index, methods/corrections, research updates, research hub, publication library, remote-project bridge, privacy and the empty draft RSS feed. There are 234 content/locale pairs and 162 utility/locale pairs, of which 374 are new non-English documents.

The English scientific files and canonical routes are unchanged. Consumer titles are presentation overrides in `_data/library.json` and the research/project data, reused by H1, title/social tags, schema, menu links and cards. The core review is a highlighted clickable item above a flat seven-article table. Rabbit honestly has zero separate articles. No comprehensive/systematic-review completion claim was added.

## Sources and coordination

The owner authorized coordination with **【MSRA】Consumer Growth**. Its expanded local handoff is `growth-research/full-localization-handover-2026-10-29/` in the shared workspace. The latest scientific manuscript packet remains feline v2; all ten prepared bodies were already integrated and match that packet. E09, V25 and the rabbit report are also retained. No newer scientific body was fabricated or appended.

The full commissioning matrix supersedes the historical six-resource German/French pilot. `_data/localization_plan.json` is the repository-contained snapshot of inventory aliases, per-page/locale keyword evidence and source hashes. It preserves observed phrases, normalized candidates and unobserved AI editorial seeds as different evidence classes. Monthly search volume, keyword difficulty and CPC are unknown, not zero. Native keyword fieldwork was not supplied for several named markets; translated wording does not establish that research was performed. These drafts cannot promise rankings or traffic.

Growth supplied the complete PL/SV/DA/NB/FI/PT-BR/PT-PT/KO/RU/HI manuscript packets in `growth-research/localization-body-drafts-2026-10-29/`. Their manifests were hash-checked before import. Other editions were written in the website checkout from the same current English files. Import receipts and independent source/semantic/numeric checks are outside the checkout in `MSRA网站/library-preview-2026-10-29/`. Import normalization preserves scientific bodies while aligning implementation identity, lowercase URL prefixes, source-date provenance and `.xml` feed extensions. Explicit translation corrections are recorded in the QA artifacts.

## Safe maintenance

1. Edit an English scientific source deliberately, preserving its stable ID/route and real review state. Locally adapted copies remain protected from synchronizer overwrite by `frontend_edited: true`.
2. Reconcile the complete affected translation, including methods, tables, uncertainty, source-access notes, citation targets and reference IDs. Refresh its English whole-file hash only after that reconciliation. A changed hash intentionally stops registry generation.
3. Preserve original third-party publication titles/authors/DOI/PMID and bibliography numbering. Translated MSRA narrative is separate from the original publications; no full third-party paper translation is included.
4. Update all 38 shared UI strings and 20 support labels when their schemas change. Shared navigation/selector/filter/copy behavior has no language-specific clinical-text regex.
5. Regenerate and verify the registry, then render the design preview and run the complete rendered checks. Do not publish unreviewed drafts by flipping a global flag.

```sh
python3 tools/prepare_localizations.py
python3 tools/verify_localizations.py --complete
/Users/work/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/preview_library.mjs
python3 tools/verify_localizations.py --built /private/tmp/msra-library-preview --complete
python3 tools/verify_library_presentation.py --built /private/tmp/msra-library-preview
python3 tools/verify_feline_v2.py --built /private/tmp/msra-library-preview
python3 tools/verify_knowledge.py --kb ../../msra-open-research --built /private/tmp/msra-library-preview --source-root .
```

The registry records source hashes, actual routes, drafted/missing status, native review, clinical review, release and live verification separately. The label “Source date” describes an existing source preparation/date field; it is not a new translation publication date. Plain navigation/privacy does not require veterinary clearance merely because it is near clinical content. No unperformed native or clinical review is credited.

## Rendering and release boundary

The local preview renders 405 documents using a limited Liquid subset and `marked`; it is **not Jekyll**. It does not run Jekyll plugins or prove the production build. The previously aborted native dependency installation was not repeated. A real Jekyll build and production-equivalent review remain necessary before deployment.

All new language documents remain `noindex`, outside public sitemaps and with empty draft feeds. They have self-canonicals and actual same-content language choices; no live reciprocal `hreflang` discovery is asserted for unpublished drafts. No IP/browser-language redirect changes the research body. The architecture uses separate language URLs and full translated content, consistent with [Google's multilingual-site guidance](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites) and [localized-version guidance](https://developers.google.com/search/docs/specialty/international/localized-versions).

`_layouts/localized.html` deliberately includes the shared GA4 include exactly once, behind the existing production gate. The development preview sends no analytics. No additional GA4 account settings or unrelated SEO campaign were changed.

Kit's account/domain and owner-controlled lifecycle tests were completed earlier. Website collection remains disabled; translated email/privacy information preserves that state. This work sent no campaign, activated no subscription provider, made no paid change and pushed no deployment. Original brand-homepage and shop/product body localization is outside the research-content commission; English destinations are labelled where used.
