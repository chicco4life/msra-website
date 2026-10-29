# Kit connection status — 29 October 2026

This receipt records the account and public-form details observed during the owner-authorized browser setup. It supersedes the earlier deferred-walkthrough-only status. The owner authorized actual setup; this does not authorize a campaign send or paid upgrade. No subscriber data, private postal details or credentials are recorded here.

## Account and sender

- The account currently shows a **14-day Creator Monthly trial**. Billing explicitly says it **cancels at the end of the trial**; no paid upgrade was requested or completed.
- The intended ongoing operation is Kit Free with manually prepared, topic-filtered Broadcasts. Trial access does not establish that paid features will remain available on Free.
- The human corrected the intended sender to **MSRA Lab <federico@msralab.com>** and clicked its verification email. Kit now shows this address as **confirmed and Default**. The actual Form confirmation-email From dropdown also shows this verified sender. The mistaken pending `li@msralab.com` sender row was deleted and confirmed absent. The website's public contact email remains `li@msralab.com`.
- The Subscribers page initially showed **0 subscribers**, with the preferences control absent from that empty state. The three topic preferences were subsequently configured using the existing Form tags: **Feline urinary health**, **Rabbit digestive health**, **New research launches**. See the [actual Kit preferences screenshot](../../library-preview-2026-10-29/kit-topic-preferences-2026-10-29.jpg). A controlled preference change and restoration have now been verified against the actual subscriber's stored tags, as recorded below.

## Genuine published public Form

| Item | Observed value |
|---|---|
| Editor | <https://app.kit.com/forms/designers/10113119/edit?iframe=false> |
| Form ID | `10113119` |
| Form UID | `924e9b0702` |
| Public Share URL | <https://msra.kit.com/924e9b0702> |
| Submission method and action | `POST https://app.kit.com/forms/10113119/subscriptions` |
| Email input name | `email_address` |
| Topic input name | `tags[]` |

The title and subscription copy were published, and the actual **Follow MSRA research** header and three topic fields were verified in the final [saved public HTML](kit-form-public-2026-10-29.html). The genuine JavaScript embed is:

```html
<script async data-uid="924e9b0702" src="https://msra.kit.com/924e9b0702/index.js"></script>
```

The saved/published Form editor and exported raw HTML include **Future Foundry Limited (Hong Kong)** as operator and **federico@msralab.com** for privacy and subscription enquiries. The final saved HTML and `_includes/kit-research-form.html` are byte-identical, with SHA-256 `672da947e4549cc28bd381d43b3f193f28eebb133b81e3615339f9b1577c3460`. However, the latest reload of the public hosted Share page still shows the prior disclaimer without that operator/contact copy. The updated copy is therefore verified in the editor/raw artifacts, but **not yet verified on the hosted page**; a refreshed hosted-page check remains pending. The cause of this difference has not been established.

The observed public topic-checkbox mapping is:

| Website topic ID | Kit `tags[]` value |
|---|---|
| `feline-urinary` | `25146776` |
| `rabbit-gut` | `25146778` |
| `new-research` | `25146779` |

These identifiers are public form configuration. `_includes/kit-research-form.html` preserves the final saved vendor HTML byte-for-byte, including its actual POST action, names, checkbox IDs, branding, script, styles and response behavior. The latest local presentation uses email-entry bars opening one shared topic dialog. Once release gates pass, that dialog includes the genuine Form and maps allowlisted context to editable visible `tags[]` inputs. An entered bar email can move into the dialog in browser memory; it is not stored, placed in a URL or reported as a confirmed subscription. Collection remains disabled.

The initial genuine hosted-form inspection entered no email and submitted nothing. Evidence: [public hosted-form screenshot](../../library-preview-2026-10-29/kit-form-live-2026-10-29.jpg) and [observed topic-checkbox checks](../../library-preview-2026-10-29/kit-form-topic-checks-2026-10-29.json). These show form presentation and mapping. A subsequent authorized controlled submission is recorded below; neither artifact establishes stored subscription, confirmation or delivery.

## Observed form settings

- **Send confirmation email: ON.**
- **Auto-confirm new subscribers: OFF.** A new subscriber must click the confirmation link.
- **Subscriber data in the thank-you URL: OFF.**
- Kit's working confirmation template was retained, with subject **Confirm your MSRA research updates**.
- Subscriber preference topics are configured with the same existing topic tags. The controlled hosted signup's confirmation, selected tags, preference changes and full end-user unsubscribe behavior have all been verified. The test record is now **Unsubscribed**.

## Controlled hosted-form check — provider lifecycle verified

The owner-authorized test submitted the hosted Form with **feline urinary health** and **new research launches** selected. It displayed the configured **check your inbox** message. The test address is not recorded in this repository or these artifacts.

The owner then confirmed the test subscription email. The actual Kit Subscriber Profile now shows **Confirmed**, with **Feline urinary health (`25146776`)** and **New research launches (`25146779`)** present. **Rabbit digestive health (`25146778`) is absent**, as intended. The email activity row shows the subject **Confirm your MSRA research updates**. See the [PII-free controlled-signup audit](../../library-preview-2026-10-29/kit-controlled-signup-check-2026-10-29.json).

The initial unconfirmed record was **not observed**: the earlier UI query showed no matching unconfirmed record. The evidence therefore establishes completed email confirmation and correct stored selected tags, without claiming that a pre-click inactive state was directly inspected.

The owner opened the personal profile link from the confirmation email footer. Its initial checkboxes correctly showed **Feline + New research checked, Rabbit unchecked**. The controlled preference-change test then:

1. Selected **Rabbit + New research**, removed Feline, and saved **Update profile**. The actual Kit subscriber tag links became `25146778` and `25146779`; Feline (`25146776`) was absent.
2. Restored **Feline + New research** through the same profile page and saved. The actual Kit subscriber tag links returned to `25146776` and `25146779`; Rabbit (`25146778`) was absent.

The [same PII-free audit](../../library-preview-2026-10-29/kit-controlled-signup-check-2026-10-29.json) records the verified preference-change test. The original Feline + New research topics were restored before the final unsubscribe test.

The owner then opened the personal email footer's **Unsubscribe** link in Chrome. The actual reader page offered **Unsubscribe from all** and the same three topic checkboxes. After **Unsubscribe from all** was clicked, it displayed **You have been successfully unsubscribed**; see the [actual unsubscribe-success screenshot](../../library-preview-2026-10-29/kit-unsubscribe-success-2026-10-29.jpg). The actual Kit Subscriber Profile now shows **Unsubscribed**, and the PII-free audit records that result.

The controlled test record was deliberately left **Unsubscribed**, so it is not sendable. Its historical Feline + New research tags remain; those tags do not override the unsubscribed status or authorize future messages. The hosted provider lifecycle checks are complete. No campaign was sent and no paid upgrade was made.

## DNS applied; sending domain verified

The owner identified **101domain** and explicitly authorized DNS setup. These exact records were saved there with a **30-minute TTL**, then verified in the DNS editor. The baseline had nine records and no existing Kit records or `_dmarc` record; all baseline records were preserved. Kit validation then succeeded: the warning and Validate control disappeared, and a green check appeared next to `msralab.com` under **Verified sending domains**. The separate sender-email verification is also now complete, as recorded above.

| Type | Name | Value |
|---|---|---|
| CNAME | `ckespa` | `spf.dm-1a379071.sg3.convertkit.com` |
| CNAME | `cka._domainkey` | `dkim.dm-0c1d882d.sg3.convertkit.com` |
| CNAME | `cka2._domainkey` | `dkim2.dm-9689e094.sg3.convertkit.com` |
| TXT | `_dmarc` | `v=DMARC1; p=none;` |

Evidence: [DNS before](../../library-preview-2026-10-29/kit-dns-before-2026-10-29.json), [DNS after](../../library-preview-2026-10-29/kit-dns-after-2026-10-29.json), [saved DNS rows](../../library-preview-2026-10-29/kit-dns-records-2026-10-29.jpg) and [Kit verified-domain screenshot](../../library-preview-2026-10-29/kit-domain-verified-2026-10-29.jpg). The change check records `all_original_rows_preserved: true`, the exact four added records and no removed rows.

For future changes, inspect existing DNS first. **Do not replace an existing stronger DMARC policy with `p=none`, and do not add a second conflicting DMARC record.** No stronger or pre-existing DMARC record was replaced in this setup.

## Website activation remains blocked

The MSRA privacy notice is **not yet publicly deployed**. Its reader notice is prepared locally at **[http://127.0.0.1:8768/privacy/](http://127.0.0.1:8768/privacy/)**, using the owner-supplied business identity and contact. This local noindex preview does not satisfy public-launch readiness. Source configuration remains `enabled: false`, `account_checks_verified: false`, `signup.topic_choices_verified: false`, with an empty `privacy_url`. These switches remain off for the overall feature hold even though the hosted provider lifecycle checks are complete. The genuine Share URL and fixed inline mapping are stored in public configuration, with `signup.mode: inline`, but **no website capture has been activated**.

Both inline and hosted branches require all three verification flags and a nonempty privacy URL. The inline branch additionally checks the exact fixed provider/action/UID/field/mapping contract; mismatches fail closed to the unavailable local preview. Hosted fallback remains supported as `signup.mode: hosted-reconfirm` and requires an allowed HTTPS Kit Share URL. Hosted fallback asks visitors to choose topics again; it does not transfer local selections.

If activated, the shared dialog renders the genuine native Form; context suggestions and MSRA's at-least-one-topic validation require JavaScript. The native markup itself permits zero topic selections. Because a closed dialog needs JavaScript to open, a ready site also exposes the genuine hosted Share URL in a `noscript` fallback outside the dialog. Visitors choose their email and topics there; local bar values are not forwarded. No page visit, submit event or frontend message is treated as confirmed subscription evidence.

Earlier central-inline-page verification passed for the disabled render, an isolated inline fixture, hosted fallback and 13 invalid configurations. Those browser fixtures passed 43 checks, including known/unknown/multiple suggestions, editable choices, invalid runtime mapping, disabled/no-JavaScript states and widths 1440/900/390/320. All external requests were blocked; no email was entered and no actual form submission occurred. See the historical [static QA](../../library-preview-2026-10-29/kit-inline-static-qa-2026-10-29.json) and [browser QA](../../library-preview-2026-10-29/kit-inline-browser-qa-2026-10-29.json). These predate the shared-dialog architecture and use the local Liquid-subset renderer, **not Jekyll or a deployed site**. The separately completed real hosted-provider lifecycle is recorded above.

Before the later dialog presentation change, the operator-copy preview was rebuilt with **31 pages**, including `privacy/index.html`. At that point the disabled signup page had zero forms or email fields, and the source/rendered verifier passed against the final byte-identical vendor HTML. That historical zero-email assertion is superseded by the owner's request for local email bars and a topic popup. The updated verifier permits unnamed local demonstration fields while requiring zero provider forms, scripts and handoffs, one shared dialog, and a disabled final preview action. Fresh dialog-render checks must use the new verifier. All of these remain local design checks, not a Jekyll build or public deployment.

The shared-dialog source and fresh disabled render now pass the updated verifier. Isolated active-inline and hosted fixtures also pass, while missing-privacy and wrong-topic-mapping fixtures correctly remain disabled. The active fixture preserves the exact saved Kit markup once inside the dialog. Its temporary HTML applies a fixture-only Content Security Policy that blocks external scripts, network connections and all form submissions; the current source configuration is unchanged. See the [dialog static audit](../../library-preview-2026-10-29/subscription-modal-static-qa-2026-10-29.json). The [matching feline-content audit](../../library-preview-2026-10-29/feline-v2-subscription-modal-qa-2026-10-29.json) preserves all ten prepared bodies, 185 external source links, 41 anchors and the E09/V25 bodies. These static checks do not send email or establish a deployed signup.

Public launch remains pending the reviewed privacy notice's actual publication and the website deployment/activation decision. Sender-email, sending-domain verification, the three preference-topic definitions, and the controlled hosted test's confirmed status, selected tags, preference change, restoration and full unsubscribe outcome are complete. The local inline fixture checks remain distinct from a deployed MSRA signup test. Keep all activation flags off and `privacy_url` empty until the privacy notice is actually public and the owner-approved launch conditions are satisfied. See [the setup guide](MAILING_LIST_SETUP.md) for the integration and acceptance criteria.

No campaign send is authorized by this receipt. General SEO/GA4 work remains queued for further human instructions.

## Current shared-dialog browser verification — 29 October 2026

The [final browser audit](../../library-preview-2026-10-29/subscription-popup-browser-qa-2026-10-29.json) records 20 CUA cases covering the shared dialog across eight mobile routes, 320/1440-pixel hub layouts, blocked-provider active fixtures at 390/320, required email/topic validation, allowlisted multi-topic context, keyboard focus boundaries and Escape. Email transfer was confirmed visually; redacted value reads were not used to claim a failed transfer. The same audit records 81 bibliography entries, working group toggles and no mobile overflow.

The [static dialog checks](../../library-preview-2026-10-29/subscription-modal-static-qa-2026-10-29.json) and [active-fixture refresh](../../library-preview-2026-10-29/subscription-modal-active-refresh-qa-2026-10-29.json) use isolated local renders; fixture-only CSP blocks provider scripts, connections and form submissions. Historical central-page checks, the current UI fixtures and the real hosted-provider lifecycle recorded above establish separate results. Current source activation flags remain false and `privacy_url` remains empty. The privacy page and website connection remain local previews; no deployment, website capture activation or research campaign send occurred.
