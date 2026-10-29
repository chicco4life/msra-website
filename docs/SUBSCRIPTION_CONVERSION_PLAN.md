# Research subscription pipeline

Implementation decision note — 29 October 2026. The latest user direction is one research-updates conversion path, multiple contextual entry points, a central choice of followed topics, and email notices for new posts/research. This replaces the earlier monthly-only promise. This note does not create a Kit account, activate collection or send email.

Latest provider decision: the owner chose Kit and authorized actual browser/account setup. The genuine multi-topic Form, sender/domain verification and topic preferences are complete. The controlled hosted signup, confirmation, selected tags, preference change/restoration and full unsubscribe passed; the test record remains Unsubscribed. The latest website direction is reusable email-entry bars opening one shared topic dialog. The privacy notice and website integration remain local previews with collection disabled. See the [current connection receipt](KIT_CONNECTION_STATUS_2026-10-29.md). The subsequent general SEO/GA4 round awaits further human instructions.

## Concrete website flow

Reuse one shared **research-topic dialog** on each page. Entry bars ask for an email address and show **Receive research updates**; submitting a bar opens that dialog with editable email/topic choices. Repeat the same component at relevant points on the homepage, library, collection, Open Research hub and reports. **`/learn/updates/`** remains the fallback entry page. Ordinary reading/navigation links remain available. Entry-bar values stay in browser memory and are not sent, stored, put in URLs or included in analytics events by opening the dialog.

| Entry point | Shared-dialog context |
|---|---|
| Homepage and library root | Choose from the configured available topics; no implied follow-all choice |
| Open Research hub | Suggest `new-research` for new project/question launches |
| Feline collection, feline guides and feline report | Suggest feline urinary research |
| Rabbit research report | Suggest rabbit digestive research; local selection remains a preview while collection is disabled |
| A resource spanning topics | Suggest the relevant available topics together; allow changes |

The site may use its **own** URL such as `/learn/updates/?topic=feline-urinary` or `/learn/updates/?topics=feline-urinary,new-research` to set visible topic suggestions. Support `topic` for one public catalog ID and `topics` for a comma-separated set. Accept only configured stable IDs; ignore unknown IDs. Keep the canonical as `/learn/updates/`. Do not put an email address, medical record or subscriber identifier in this URL, and do not forward inbound queries to Kit.

The public catalog has three choices:

| Public ID | Configuration key | Scope |
|---|---|---|
| `feline-urinary` | `feline_urinary` | New guides, published research and substantive updates within feline urinary health |
| `rabbit-gut` | `rabbit_gut` | New guides, published research and substantive updates within rabbit digestive health |
| `new-research` | `new_research` | New MSRA projects and research questions across species; not every minor edit |

All three current choices are **local preview selections**, not stored consent. Show a topic checklist, an accurate notification promise and clear status. Context is a convenience: a checked suggestion is not a subscription. The visitor can change it before the explicit subscription step. Keep product messages and research participation outside this editorial choice. No topic becomes active collection merely because its CTA or preview checkbox exists.

Proposed copy:

> Choose the research topics you follow. Confirm your email, then receive updates about new articles and research we publish in those topics. Change topics or unsubscribe at any time.

Do not promise instant delivery or a welcome sequence. The current Free-plan workflow prepares publication notices manually. The notification step follows approved publication rather than waiting for an arbitrary monthly date.

## What Kit officially supports

Kit uses one subscriber list, organized by tags/segments; a person can follow several topics without separate mailing lists. [Subscriber organization](https://help.kit.com/en/articles/2502716-how-subscriber-organization-works-in-kit)

Forms and landing pages can offer **Tag checkboxes** for multiple choices. Configure each public topic label against its genuine Kit tag, then use those same tags for subscriber preferences. [Tag checkboxes](https://help.kit.com/en/articles/3317488-adding-tag-dropdowns-checkboxes-to-kit-forms)

Preference changes add/remove the corresponding tags. Broadcast audiences should follow current tags, not historical form membership. [Subscriber preferences](https://help.kit.com/en/articles/6082488-managing-subscriber-preferences-in-kit)

The Free plan includes forms/landing pages, broadcasts, tagging and segmentation. Its current limits exclude visual automations, sequences, rules and RSS campaigns. This establishes the proposed platform fit; actual account behavior still needs controlled checks. [Kit Free](https://help.kit.com/en/articles/16627071-the-kit-free-plan)

**Hosted-page preselection is unverified.** The official form, tag-checkbox, landing-page and embedding documentation checked here does not document a Share-URL parameter for preselecting tag checkboxes. This is a limit of the evidence found, not proof that no such feature exists. Never invent `tags=`, `topics=` or checkbox/tag IDs on a Kit URL. A generic hosted URL does not by itself preserve a checklist selected on MSRA.

## Connection model

**Preferred activation: one genuine Kit Form inside the shared MSRA dialog.** The real account's saved public HTML supplies its actual action, identity, fields and tag-checkbox options. `_layouts/default.html` includes `_includes/subscription-modal.html` once; reusable bars and contextual CTA wrappers open it. Keep submission and email storage with Kit; no server/API secret is needed on GitHub Pages. Preserve the provider's working controls, confirmation and error handling. `signup.mode: inline` continues to describe this genuine embedded Form, despite its placement inside the dialog.

Kit officially offers editable raw HTML embeds for Forms; that code must be recopied after relevant provider changes. A Landing Page is a separate hosted page and cannot be substituted as an embedded Form. Context-aware checkbox initialization is an MSRA implementation inference using the actual form markup, not an official hosted-URL contract; test real selected tags, deselection and repeat subscribers before activation. [Embedding options and HTML limitations](https://help.kit.com/en/articles/4009572-form-embedding-basics)

Do not precheck a separate consent checkbox or treat a default topic as permission. Require clear affirmative subscription and the configured confirmation click. Kit's own guidance distinguishes topic tagging from affirmative consent; any enabled provider consent controls remain under the visitor's control. [Kit consent FAQ](https://help.kit.com/en/articles/2502571-gdpr-faq)

**Hosted fallback (`signup.mode: hosted-reconfirm`):** one genuine multi-topic public Share URL is sufficient for a provider-hosted checklist. Label the handoff **Choose topics and subscribe on Kit**. If MSRA has shown a local selection, explicitly say **Choose your topics again on the signup form; these choices have not been sent.** Do not claim that MSRA selections persist. The genuine Share URL is now recorded in `signup.hosted_form_url`; the preferred configured mode is `inline`, and both branches remain disabled by the global activation gates.

**While website collection is disabled:** the owner-requested local email bars and topic popup may demonstrate the flow. Their email inputs are unnamed, the modal preview form uses `method="dialog"`, the final action is disabled, and the dialog says email and choices are not saved or sent. Render no provider form, behavior script or provider handoff. Keep all activation flags false and preserve the published privacy-notice requirement. Public guides, urgent direction and the blank record stay ungated.

## Publication-to-notification operation on Free

1. Approve and publish the actual article/research release; confirm its canonical public URL. Website drafts, a build, card reordering or a source-file `ready` flag do not trigger a subscriber notice.
2. Record the released item in a lightweight editorial send queue: stable content/research ID, canonical URL, title, topic keys, release/version date and pending/sent status. Keep subscriber data out. A future queue implementation is separate from this note.
3. Prepare a short manual Kit Broadcast describing what is new and linking to the public source. Select **confirmed subscribers matching any of the current topic tags for that notice** and honor full unsubscribe/suppression. For a combined multi-topic release, use one union audience so a subscriber with overlapping interests receives one email for that release. Preview the recipient filters explicitly; do not leave the default All Subscribers audience selected. The `new-research` choice covers a genuine project/question launch, not every subsequent item or minor edit.
4. Test the actual broadcast, send/schedule it through the authorized editorial operation, then record its provider message ID/date against the queue item. Do not mark it sent merely because the website published. Closely related items released together can share one notice without reverting to a monthly-only cadence.

Broadcasts are manually authored one-off messages; Kit permits filtering recipients and scheduling sends. [Broadcast workflow](https://help.kit.com/en/articles/2934648-creating-sending-and-publishing-broadcasts) Tag/segment filters support matching any/all/none, so a combined audience can express the topic union; validate the actual recipient preview before a send. [Segment filters](https://help.kit.com/en/articles/2577659-how-to-create-a-segment)

Kit has an RSS-to-Broadcast workflow, but RSS campaigns require a paid plan under the current Free terms—even if automatic sending is turned off and RSS only prepares drafts. Do not describe a Free account as automatically notifying on every GitHub/Jekyll publication. No paid upgrade, custom delivery backend or sending is authorized by this note. [RSS workflow](https://help.kit.com/en/articles/2502636-how-to-connect-your-rss-feed-to-kit)

## Minimum real connection information

For the preferred seamless flow, supply **the genuine inline Form HTML embed** with topic-tag checkboxes and **its public Share URL as the fallback**. The public embed normally contains the needed form/field/tag identifiers; verify the exact labels-to-topic mapping rather than asking for an API key. For a hosted-only start, supply just the genuine **central multi-topic Share URL** and confirmation that its checkbox tags map to the intended topics; accept the preselection limitation above. Separate per-topic public URLs are not required for a single multi-topic form.

Also needed before public collection: the real **published MSRA privacy-notice path/URL** and account-owner confirmation that sender/domain authentication, required confirmation, topic preferences, unsubscribe/suppression and controlled submission tests pass. No Kit password, SMTP password, API key, subscriber export or private test address belongs in the public repository or chat.

## Acceptance for the actual connection

- Test no context, each available topic, multiple topics, changed/deselected topics, and unknown local keys. Inspect actual submitted tags and confirmation status in Kit; a handoff click is not a signup.
- Test an existing subscriber adding and removing topics, including full unsubscribe. A topic removed through preferences must be excluded from the next recipient preview even if its signup form appears in history.
- Keep provider redirects free of subscriber name/email/ID and analytics free of those values. Leave Kit's optional subscriber-data-in-thank-you-URL feature off. [Form settings](https://help.kit.com/en/articles/2502640-the-kit-form-builder)
- Measure central visits and neutral handoffs separately from provider submissions, confirmations and actual publication-message sends. Report provider outcomes only from provider records; neither a thank-you redirect nor a confirmation-page visit proves a stored state.
- Verify the rendered site, mobile/keyboard behavior, canonical URLs and honest inactive state. No campaign is sent as part of front-end deployment.

## Current state

The genuine Form and topic mapping are prepared, and the verified hosted-provider lifecycle is recorded in the [connection receipt](KIT_CONNECTION_STATUS_2026-10-29.md). The website now uses local email-entry bars and one shared dialog; earlier central-inline-page fixture results predate this presentation change. Collection and verification flags remain false and `privacy_url` is empty while the privacy page and website release remain local. The controlled record is Unsubscribed, and no campaign was sent. Fresh local dialog checks remain distinct from a deployed Jekyll build or an actual MSRA-to-Kit signup test.
