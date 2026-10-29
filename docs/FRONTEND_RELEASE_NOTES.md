# Pet Health Library implementation and release checks

Local implementation note — 29 October 2026. This records front-end safeguards, not publication approval, a successful Jekyll build or clinical validation. The research knowledge base was not changed by these tooling updates.

## Editorial preview is the default

`tools/sync_articles.py` treats source `publication_state: ready` as generation eligibility. A source-checked eligible record is emitted with:

```yaml
source_publication_state: ready
publication_state: editorial-draft
release_approved: false
robots: noindex
sitemap: false
```

The source's authorship and actual clinical-review status are preserved. Ineligible source drafts are not generated. The release gate does not independently verify a source, reviewer identity or medical claim; those remain editorial responsibilities.

A record becomes published only with explicit source `release_approved: true`, ready/source-checked status and `release_scope` of `literature-interpretation` or `clinical-guidance`. A literature interpretation can retain the truthful `not-independently-reviewed` status; approval must not be used to misclassify clinical instructions as an interpretation. Clinical guidance requires `clinical_review_status: independently-reviewed` plus the real `clinical_reviewer`, `clinical_review_scope` and ISO `clinical_review_date`. Do not add those fields unless that review actually occurred. Claiming an independent review without the required details is rejected even for a preview.

A released article cannot link through a relative source `.md` link to an unapproved article. Source dates must be valid ISO dates, and the update date cannot precede the article date.

## Preserve local adaptations

Mark a website article that has been independently adapted:

```yaml
frontend_edited: true
```

The synchronizer inspects planned overwrites and generated-file removals before writing any articles or knowledge data. A marked adaptation stops the batch with its path and a reconciliation instruction. It is not silently replaced or deleted, even if its source slug changes or its source disappears. Reconcile the source/body/metadata deliberately, then remove the protection flag only when regeneration is intended. Unmarked generated files remain managed output and can be overwritten by a later authorized sync.

Do not run a production sync merely to test these checks. `tools/verify_knowledge.py` creates its own temporary knowledge base and site, never generating into the actual checkout during its gate test.

## Verification commands and scope

From the website checkout:

```sh
python3 tools/verify_knowledge.py --kb ../../msra-open-research
```

This verifies default noindex previews, withheld ineligible drafts, rejected unchecked/unscoped releases, truthful review metadata, an explicitly approved literature interpretation, preservation of marked local edits on overwrite/removal, and unchanged output after a rejected batch.

When a matching rendered site exists:

```sh
python3 tools/verify_knowledge.py --kb ../../msra-open-research --built /absolute/path/to/rendered-site
```

Use `--source-root /absolute/path/to/matching/site-sources` if the rendered output belongs to a separate fixture/checkout. The output must be built from those matching sources.

The output verifier checks every owner HTML page for a self-canonical, one main heading, rendered Liquid and working internal links/fragment targets. Article checks compare visible titles/authors and dated time elements with source metadata, Article JSON-LD and social metadata. Structured breadcrumbs must match visible parent links and end at the article's canonical URL. The RSS feed must contain exactly explicitly released articles, with no duplicates; noindex pages must be absent from RSS and sitemap. It uses the actual inventory rather than an assumed five-article count.

A rendered-output pass does not establish that Jekyll produced the output: report the renderer and full Jekyll build separately. The known missing local Ruby/native dependencies and the previously aborted install must not be represented as a successful build or retried without the user's authorization.

## Current validation and activation

Temporary publication-gate checks passed after these changes. No generation was run into the real `_articles` or `_data/knowledge.json` by this tooling task. Full-site rendering and responsive checks are reported by the overall front-end implementation.

Kit remains disabled pending a genuine central public Form/Share URL, published privacy notice and account-owner confirmation of sender/domain, confirmation, topic preference and unsubscribe tests. Persistent local topic presets additionally need the real Form HTML and verified topic-checkbox mapping; a hosted Share URL requires topic reconfirmation. See [mailing-list setup](MAILING_LIST_SETUP.md). No message sending, outreach or paid-product launch is included.

## Implemented collection and source corrections

The front end now follows Pet Health Library → Cats → Urinary health. A prominent central owner overview leads five substantial guide drafts (urgent signs; after a blockage; food/water; diagnostic terms; medicines/supplements), an ungated printable record, the retained 2021 prazosin interpretation and one complete source index. The existing Maine Coon draft is retained at its old local URL as a conditional, unindexed resource, with relevant-reading context on the hub; no breed predisposition is inferred. No pages were manufactured for the 26-item backlog.

The index preserves all public references 1–40, original DOI/PMID identities and study years, and labels local guideline addition 41 separately. Sources show population/outcome, access and actual audit checking status as separate fields. Source references link both ways between the index and MSRA explanations. Search filters the local page only; it sends no query or medical information.

The local technical report and relevant owner copy apply the supplied audit: source 8 is 17 complete dissolutions among 21 cats; source 33 has 14 unique cats and crossover exposure denominators; source 31's difficult-case prescribing explanation is removed; source 36's episode-rate comparison is between groups; source 26 retains support for environmental management and therapeutic diets with evidence limits. Source 11's 11/37 versus 5/28 counts remain. Source 34's allocation/masking and procedural/safety limitations are qualified. The unverified numerical urine-concentration target and universal water-intake target are removed. Universal original-full-paper fact-checking and verified PRISMA adherence are not claimed. These are targeted source-audit corrections, not independent clinical validation.

The research source repository is preserved. The local report has frontend_edited:true and tools/sync_research.py now stops before overwriting it; reconcile these corrections into the source project before a future sync or release. Existing GA4 include contents are byte-for-byte unchanged from HEAD; no duplicate tag or email-signup success instrumentation was added. The design preview disables analytics.

## Reviewable preview and verified limits

The actual preview is served at http://127.0.0.1:8768/learn/cats/urinary-health/ from /private/tmp/msra-library-preview. The renderer and its preview-manifest.json explicitly identify a limited Liquid/Markdown design preview, not Jekyll. Preview-only sitemap.xml is labelled as a model of draft exclusions. Local Jekyll is unavailable (Ruby 2.6 with missing Jekyll/native dependencies; previous native installation incomplete). The aborted dependency installation was not retried. A real Jekyll build on an available build host/CI remains required before release.

Rendered-output checks passed for 15 library pages and eight Article/Breadcrumb graphs: self-canonicals, visible/schema authors and dates, 249 internal fragment links, zero broken internal links, and zero draft entries in RSS or the preview sitemap. The browser sweep checked all 15 pages at 1440, 390 and 320 pixels: all HTTP200, one H1, no horizontal overflow or JavaScript errors. Source filtering returned 4 prazosin matches, 5 matches for 2021, 0 unmatched, and all 41 after clearing. With JavaScript off, all 41 sources and honest inactive email copy remain available; no email field or active signup link appears. The Print button invoked printing once, and print media hid navigation/subscription while retaining the blank record. Browser screenshots used fallback fonts because external resources were blocked during QA.

No website commit, push, deployment, email send, outreach, preorder activation or funding launch was performed for this library implementation. All library resources remain editorial drafts/noindex. Kit collection remains disabled until the real central public form, published privacy notice and verified account configuration are supplied. The activation gates require `enabled: true`, `account_checks_verified: true`, `signup.topic_choices_verified: true`, a nonempty `privacy_url` and a valid approved-host URL in the configured hosted-reconfirm mode. These flags do not establish persistent topic presets without the genuine embed and field mapping.

## Editorial-priority handoff refinement

The provisional growth note does not set the frontend build queue or establish keyword demand. Dedicated `_data/library.json` now selects cards by stable content ID, with editable card title/summary/label overrides that fall back to the real source metadata. O00 and T24 have explicit stable IDs. Overview/tool destinations resolve from their actual pages, and guide/study/related-reading shelves resolve actual source articles. No URL or content identity can be changed by a card override. Whole-article headings and metadata remain driven by front matter.

The current owner shelf reads urgent signs, food/water, after treatment, diagnosis, then medicines. Its configuration is separate from the provisional acquisition rank and from generated `_data/knowledge.json`. No acquisition rank is imported automatically, and none of the 26 planning records or newer keyword hypotheses produced placeholder pages. Inherited quoted boolean/integer article metadata and the generated knowledge registry types were normalized for consistent selection. Routes, clinical bodies, author/review status, GA4 and Kit activation are unchanged by this refinement. See docs/LIBRARY_EDITORIAL_HANDOFF.md for the validated-wording handoff procedure.

The presentation refinement passed configuration and actual-preview checks for 36 rendered cards and nine source canonicals. A temporary copy rendered with a changed G04 card title/summary proved that the home/hub card copy changes while the article H1, URL and canonical remain unchanged. Four desktop/mobile browser checks passed with the configured shelf order and complete overview/tool destinations. A preview-only missing site.pages collection was fixed. The 15-page/8-Article/249-fragment broader check still passes; the local renderer remains explicitly non-Jekyll.

## Single primary navigation

The owner's navigation review replaces the duplicate top CTA buttons and secondary link row with one shared primary navigation: Pet Health Library, Open Research and Shop. The current section is underlined. At narrow widths, one Menu button reveals that same list; there is no duplicate set of links. Language selection remains a utility where translations are available. Cats, methods, source browsing and topic follow remain inside their respective sections instead of adding another global navigation row.

The shared Shop navigation link is distinct from a checkout prompt in owner content. Rendered verification continues to reject local shop/checkout links inside the editorial main content while allowing the owner's requested global navigation.

Navigation verification passed on research and owner-hub pages at 1440, 900, 390 and 320 pixels: one three-link primary navigation, correct active section, no duplicate CTA/second row, no page overflow or JavaScript errors. Enter/Space, Tab order, Escape with focus return, outside click and resize behavior passed. Without JavaScript, the same three links remain available. The current in-app research preview was refreshed and visually confirmed. Changes remain local.

## Central research subscription preview

The latest direction adds one homepage research-updates CTA and contextual entry points across the homepage, Pet Health Library, collection, Open Research hub and reports. Every entry leads to `/learn/updates/`; feline/rabbit content suggests its own topic, and the research hub suggests `new-research`. The center permits multiple choices across feline urinary health, rabbit digestive health and new MSRA project/question launches. These are local preview selections, not saved preferences or consent. All collection switches remain off, the public URL is blank, and no address is collected.

Local `?topic=` and `?topics=` suggestions are checked against the actual catalog. They are not forwarded to Kit. The active hosted-only fallback must visibly ask visitors to choose topics again on the real form; seamless persistence is pending the genuine public Form HTML and topic-field mapping. The prior normally-monthly promise is superseded by publication updates: manual topic broadcasts after approved releases on Kit Free, with one union audience for overlapping interests. Automatic RSS/sequence delivery is not configured or promised. Public resources remain ungated.

This central-flow change is independent of the earlier preview-check counts recorded above. Its actual rendered/browser results are reported with the current website verification. No live signup, provider lifecycle test or publication email delivery is established by the front-end preview.

Current subscription verification passed 16 desktop/mobile chooser cases, editable/keyboard choices, seven entry-page destinations, known report-topic mappings and no-JavaScript behavior at 1440/390/320 pixels. The disabled chooser exposed no email input, provider link, POST, provider request or capture/handoff event. Ten temporary design-render fixtures exercised activation flags, missing privacy/topic verification, invalid modes and rejected URL hosts/protocols/userinfo/ports; only the fully configured approved-host hosted fallback appeared, with explicit topic reconfirmation. No real provider was contacted. Local script checks also covered no query propagation and no false signup event.

The final design render still passes the library checks: 15 owner pages, eight Article graphs, 250 internal fragment links, zero broken links and zero draft RSS/sitemap entries; presentation checks pass 36 cards and nine source canonicals. These are design-preview/browser checks, not a Jekyll production build. Screenshots and browser results are saved outside the source checkout in `../library-preview-2026-10-29/subscription-*`. No commit, push, deployment, provider activation or email send occurred.

## Feline packet v2 local preparation

The ten prepared public bodies from `growth-research/feline-urinary/publication-prep-v2` replace H00, G01–G05, O00, T24, S00 and R00 at their retained URLs. Four page sources move from `index.html` to `index.md` while keeping explicit permalinks. The manuscript H1 is rendered once from selected metadata; public body text, all 185 external href occurrences and review/AI footers remain intact. R00 replaces the earlier local report body; its original 20 August history remains visible, while the current revision is labelled a local draft. Eight heading fragments were verified on the live historical report and retained as explicit aliases, alongside layout `#report` and `#sources`. E09/V25 source bytes and rendered clinical bodies remain unchanged.

`_data/feline_packet.json` owns selected asset metadata and mapped navigation, while `_data/library.json` keeps presentation separate from demand evidence. The featured owner promotion order is G02 → G04 → G03, followed by O00 for the roundup. The hub's five guide choices retain their owner-task order. The source index preserves `ref-1` through `ref-41` and supplementary guidance, with local progressive filtering that never sends queries. The record has 35 blank writing lines and local copy/print actions, without inputs, upload, score or signup gate.

All ten pages explicitly remain editorial drafts/noindex and out of preview discovery; the ten prepared bodies have no email CTA or provider connection. Prepared dates are labelled as preparation, with no invented publication or modification date in schema/social metadata. Editorial proofreading is complete; qualified veterinary/clinical-nutrition review remains unperformed. No clinician/reviewer identity or `reviewedBy` claim was added. At the time of this implementation, email provider selection/setup was on hold; no Kit requirement, account/form activation, broadcast or publication-triggered send was introduced.

### Latest owner direction: Kit and follow-up sequence

The owner subsequently chose Kit, where they already have an account. After the remaining marketing-content handoffs and integration, provide the practical Kit setup walkthrough. The actual account plan, public form, topic-field mapping and account checks remain unverified; collection and sending stay disabled. The next general SEO and GA4 optimization round follows email setup and awaits further owner instructions. This decision changes documentation only, with no provider connection, campaign send, paid upgrade or SES setup.

Rendered checks pass the ten-body parity/metadata/citation/fragment suite and broader library safeguards. The output remains a limited Liquid/marked design preview, not a successful Jekyll build. The prior aborted dependency installation was not retried. Qualified review of the actionable owner wording and a real Jekyll build remain required before release, followed by truthful actual release dates and discovery entries for only released pages. This preparation does not create an additional generic owner-approval step. No commit, push, deployment or source-packet modification was performed.

## Current email-bar and topic-popup preview — 29 October 2026

Reusable email-entry bars now open one shared topic dialog with editable context suggestions. The current browser audit records **20 CUA cases**: eight routes at 390 pixels, the homepage/library/research hubs at 320 and 1440, active blocked-provider fixtures at 390/320, topic and email validation, allowlisted multiple-topic queries, focus boundaries and Escape. Email transfer was confirmed visually; redacted CUA value reads were not treated as evidence of an empty field. The bibliography shows 81 entries across the 40-paper rabbit and 41-publication feline groups, with working details toggles and no mobile page overflow. See the [current browser audit](../../library-preview-2026-10-29/subscription-popup-browser-qa-2026-10-29.json).

The [dialog static audit](../../library-preview-2026-10-29/subscription-modal-static-qa-2026-10-29.json) and [active-fixture refresh](../../library-preview-2026-10-29/subscription-modal-active-refresh-qa-2026-10-29.json) preserve the genuine Kit markup and test disabled, active, hosted and negative-config states. Active browser fixtures use temporary CSP to block provider scripts, connections and form submissions. Earlier central-page/no-email-field results above are historical. The separately authorized real hosted-provider lifecycle verified confirmation, selected tags, preference changes/restoration and full unsubscribe; that record remains Unsubscribed. Website flags remain off, the privacy notice remains a local preview, and no deployment, website capture activation or research campaign send occurred. These UI checks use the limited local renderer, not Jekyll.

## Current project-based library index — 29 October 2026

The Pet Health Library now uses one project selector, the selected project's actual core review and a flat article table. `_data/library_projects.json` owns this mapping: feline urinary health has seven actual article destinations, while rabbit digestion and weather has its existing core review and an honest zero-article state. The Cats index reuses the pinned feline panel. H00's extra overview/study/Maine Coon/related card stacks are removed; its exact prepared body, urgent guidance, sidebar and compatibility anchors remain intact.

Source and [rendered presentation checks](../../library-preview-2026-10-29/library-project-index-static-qa-2026-10-29.json) pass, including canonical destinations and rejection of [duplicate or misdirected rows](../../library-preview-2026-10-29/library-project-index-negative-qa-2026-10-29.json). All ten prepared bodies, 185 external citation links and 41 source anchors remain preserved in the [packet parity audit](../../library-preview-2026-10-29/feline-v2-library-project-qa-2026-10-29.json). The [11-case browser audit](../../library-preview-2026-10-29/library-project-index-browser-qa-2026-10-29.json) passes desktop/mobile selection, empty state, deep links, keyboard order, pinned Cats view, preserved H00 and shared topic popup checks without page overflow. Clinical-review and release gates remain unchanged, email capture stays disabled, and no deployment or campaign send occurred. The preview remains a limited local renderer; a real Jekyll build is still required before release.
