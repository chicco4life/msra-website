# MSRA research subscriptions: Kit Free connection

> Latest owner direction, 29 October 2026: **use Kit**, since the owner already has an account. Sending-domain and sender-email verification, the three preference topics, and the controlled hosted signup, confirmation, tag changes and full unsubscribe are complete. The website now uses reusable email-entry bars opening one shared topic dialog. Collection stays disabled while the privacy page and website connection remain local previews. No campaign send, paid upgrade or SES setup is requested. See the [observed connection receipt](KIT_CONNECTION_STATUS_2026-10-29.md).

Updated **29 October 2026**. **Kit Free is owner-approved.** The current user direction is a central mailing-list signup, selectable research topics, contextual topic suggestions and notifications about new posts/research. This supersedes the earlier monthly-only digest plan.

The website's shared topic dialog is the central subscription interface; **`/learn/updates/`** remains a fallback entry page. The catalog offers **feline urinary health**, **rabbit digestive health** and **new research launches**. While collection is disabled, unnamed local email fields and topic choices demonstrate the flow without saving or sending them. The genuine Kit form is rendered once inside the shared dialog only after the existing release gates pass. The controlled hosted-provider lifecycle is verified and its test record was left **Unsubscribed**. That account test is distinct from a deployed MSRA signup test. The MSRA [privacy notice](../privacy/index.html) is prepared locally but not yet public; no campaign was sent. See [the conversion architecture and verified limitations](SUBSCRIPTION_CONVERSION_PLAN.md).

## Owner promise and delivery

> Choose the research topics you follow. Confirm your email, then receive updates about new articles and research we publish in those topics. Change topics or unsubscribe at any time.

Notifications follow approved publication, with manually prepared topic broadcasts on Free. Do not promise instant automatic delivery or a welcome sequence. Guides, urgent direction and the blank vet-visit record remain free without email. Editorial topic choices do not imply product consent or research participation.

Kit currently provides one subscriber list organized by tags/segments. [Subscriber organization](https://help.kit.com/en/articles/2502716-how-subscriber-organization-works-in-kit) Free includes forms, broadcasts and tagging/segmentation; sequences, rules, visual automations and RSS campaigns require a paid plan. [Free-plan terms](https://help.kit.com/en/articles/16627071-the-kit-free-plan)

## Create one genuine multi-topic Form

These are account-owner actions, not actions performed by the static website:

1. Confirm the intended Free-plan transition. The observed account currently has a 14-day Creator Monthly trial with cancellation at trial end; do not treat that trial as a paid upgrade or rely on trial-only features. Set the actual sender/reply identity and required postal details. The corrected sender `MSRA Lab <federico@msralab.com>` is verified and Default; the Form's actual confirmation-email From dropdown shows that verified sender. Sending-domain authentication is complete after the owner-authorized 101domain DNS changes. See the receipt for evidence. Keep account credentials private. Turn unrelated Creator Network recommendations off initially.
2. Create an **inline Form** under **Audience growth → Landing Pages & Forms**. Use clear subscription wording, email, the available research-topic choices and MSRA's published privacy/contact link. Do not ask for clinical records.
3. Configure the choices as **Tag checkboxes**, using the actual website topic catalog. Use the same tags for subscriber preferences so later topic changes affect recipients. Do not create separate mailing lists or depend on paid rules to assign the selected tags. [Multi-select tag fields](https://help.kit.com/en/articles/3317488-adding-tag-dropdowns-checkboxes-to-kit-forms)
4. Require the confirmation click: turn **Send confirmation email ON** and leave **Auto-confirm new subscribers OFF**. These are the current documented labels and the settings observed on the published Form. [Confirmation settings](https://help.kit.com/en/articles/2502655-the-confirmation-email)
5. Publish the Form. Supply its genuine **HTML embed** and **public Share URL**. Preserve the form/action/input/tag identifiers from that real artifact; do not invent submission fields. A hosted Landing Page can provide a Share URL but is not the embeddable Form required for seamless local topic suggestions. [Form embed options](https://help.kit.com/en/articles/4009572-form-embedding-basics)
6. Set up current-topic preference/unsubscribe behavior and verify the broadcast recipient filters. Use the visitor's current topic tags, rather than original form membership. [Subscriber preferences](https://help.kit.com/en/articles/6082488-managing-subscriber-preferences-in-kit)

No API key, SMTP password, Kit password or private subscriber export is needed for this static Form integration. Its public form/field/tag IDs are account-specific configuration, not API credentials.

## Context suggestions and actual stored choices

Contextual website links use MSRA's own **`?topic=<single-id>`** or **`?topics=<comma-separated-ids>`** on `/learn/updates/`. Whitelist the actual public catalog IDs: `feline-urinary`, `rabbit-gut`, `new-research`; ignore unknown values. These parameters are website presentation state and must not be forwarded to Kit. The central page's canonical URL excludes them. The first two topics cover new guides, published research and substantive updates within that question; `new-research` covers new projects/questions across species, not every minor edit.

Reusable entry bars pass the entered email and allowlisted topic context to the shared dialog in browser memory. Email is not placed in a URL, storage or an analytics event. The user can change the visible email and topic selections before the final subscription action. With the genuine HTML Form active, the suggested topic maps to that Form's real visible checkbox. Verify this website-to-provider path after activation; the completed hosted test does not establish a deployed MSRA form submission. Kit's official hosted-page documentation checked here does **not** establish a Share-URL mechanism for preselecting tag checkboxes.

For an active **hosted-only fallback**, use the real central multi-topic Share URL and tell the visitor to **choose topics again on Kit**. Do not append invented `topics=`, `tags=` or tag IDs, and do not say a local selection has been saved or transferred. A generic hosted URL does not fulfill seamless persistence of local presets.

The owner requested visible email-entry bars and a topic popup even during preview. Local email fields are allowed for that demonstration, but the disabled dialog must show a clear **not saved or sent** notice, keep its final action disabled, and render no provider form, behavior script or handoff. Topic suggestions never replace an affirmative subscription action, the required confirmation click or any separate consent control; leave actual consent checkboxes unchecked. [Kit consent guidance](https://help.kit.com/en/articles/2502571-gdpr-faq)

## Public configuration and missing inputs

`_data/subscriptions.yml` owns the public catalog and connection state. The preferred branch remains `signup.mode: inline`: this refers to the genuine embedded Kit Form, now enclosed in `_includes/subscription-modal.html`. The default layout includes that shared dialog once on each page; `_includes/subscription-bar.html` supplies reusable entry bars. `_includes/kit-research-form.html` remains byte-identical to `docs/kit-form-public-2026-10-29.html`. The dialog renders that vendor form only when every gate passes, with no duplicate local chooser. The genuine `signup.hosted_form_url` remains available for `signup.mode: hosted-reconfirm`. All collection/verification flags remain false and `privacy_url` remains empty. Keep the complete configuration rather than replacing it with an incomplete example.

Before collection, all of the following must be true: `enabled`, `account_checks_verified`, a nonempty published `privacy_url`, and a verified genuine central provider form. Any embed-readiness status must remain pending until the actual public HTML and topic mapping are connected and tested. No form URL or flag alone proves that local topic presets persist.

The remaining connection work is:

- **Preferred seamless flow:** verify the final email-bar/dialog integration locally, then check the deployed MSRA-to-Kit path when its release conditions are satisfied. The real hosted form's confirmation, stored tags, preference changes and unsubscribe are already verified. No API key is needed.
- **Hosted-only alternative:** the genuine **central multi-topic Share URL** is available in the receipt. No separate public URL per topic is required; local presets would need reconfirmation on the provider form. It remains disabled in source.
- **Before either activates:** publish the MSRA **privacy-notice URL/path** and complete the website deployment/activation decision. Sender-email, sending-domain, preferences and the controlled hosted lifecycle are complete. Keep source flags off while the website feature remains on hold.

Do not commit subscriber addresses, test addresses, contact exports or private account credentials. Permit only verified HTTPS provider hosts. Inspect the actual embed's action/script hosts when it is supplied; do not guess domains or add shorteners.

## Publication notification operation

After an approved article/research release is publicly available, prepare a short Kit Broadcast for confirmed subscribers matching its current topic tags. For a combined release, use one audience union so overlapping interests receive one email for that release. Explicitly inspect the audience filter; the provider's default All Subscribers setting is not topic targeting. Record the release/version, canonical URL and provider send identifier in the editorial operation, without subscriber data in the repository. [Manual Broadcast workflow](https://help.kit.com/en/articles/2934648-creating-sending-and-publishing-broadcasts)

No notification is triggered by an editorial preview, `publication_state: ready`, card changes or a build. Free does not provide the proposed automatic RSS publication workflow; even using RSS to create unsent drafts is an RSS campaign feature. [RSS workflow](https://help.kit.com/en/articles/2502636-how-to-connect-your-rss-feed-to-kit) The website integration and deployment do not send a campaign.

## Controlled acceptance checks

Use authorized controlled addresses outside the repository:

- Test generic entry, every available context, multiple topics, deselection and unknown keys. Inspect real submitted tags and the initial unconfirmed state; verify confirmation only after the required email click.
- Test an existing subscriber changing topics, removing a preference and fully unsubscribing. Ensure the next broadcast preview respects current choices even if an old form subscription remains in history.
- For an embed, verify exact topic-field mapping, mobile/keyboard behavior, errors and the no-JavaScript outcome. For hosted fallback, verify the visible reconfirmation message and actual hosted choices.
- The current native Kit HTML permits no topic selection. MSRA JavaScript adds an at-least-one-topic check inside the active dialog. Without JavaScript, a ready site exposes the genuine hosted Share URL outside the closed dialog; visitors choose their email/topics there. Entry-bar GET fallbacks contain no named email control and do not transfer the entered address. Do not claim that local choices persist through the hosted fallback.
- Keep optional subscriber-data-in-thank-you-URL settings off, so name/email/ID do not enter URLs or analytics. [Form settings](https://help.kit.com/en/articles/2502640-the-kit-form-builder)
- Confirm sender authentication, inbox delivery, published privacy/contact information, spam protection, unsubscribe/suppression and provider access/export/deletion handling.
- Measure central visits and neutral handoffs separately from provider submissions, confirmations and publication-message sends. A click, redirect or page visit is not signup success; the provider record is authoritative.

Existing GA4 and its consent behavior remain in place. Do not send email addresses, clinical history, full form URLs/queries or subscriber IDs to analytics. Static frontend work does not complete MSRA's actual privacy/account setup.

## State of this implementation

The [29 October connection receipt](KIT_CONNECTION_STATUS_2026-10-29.md) records the genuine Form, verified sender/domain, observed settings, trial status, applied DNS and completed controlled hosted lifecycle. The current local architecture uses entry bars and one shared topic dialog; earlier central-inline-page fixture results remain historical evidence. The updated source, disabled-render, active-inline, hosted and two negative-config checks pass in the [dialog static audit](../../library-preview-2026-10-29/subscription-modal-static-qa-2026-10-29.json). All global collection switches remain off while privacy and the website release remain local. The renderer is not Jekyll, and local fixtures do not establish a deployed MSRA signup or a delivered publication alert.

## Owner-requested next steps

1. Complete local email-bar/dialog verification and publish/connect the prepared privacy notice when the website feature is released. Verify the actual deployed MSRA signup path then; the hosted provider lifecycle has already passed. Keep subscriber/test addresses and credentials out of the repository. The intended no-cost operation uses manual topic broadcasts; native RSS automation must not be promised on Free.
2. Complete the email setup before beginning the next general SEO and GA4 optimization round. The owner will supply further instructions for that round; record it as queued and awaiting scope, rather than starting a new audit or implementation now.

Authorization to perform account setup is separate from approval to send a campaign. No campaign send or paid plan change is implied by this sequence.
