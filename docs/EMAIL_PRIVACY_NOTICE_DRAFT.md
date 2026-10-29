# MSRA research email privacy notice — local draft

Prepared 29 October 2026. This repository document is excluded from the website build by `_config.yml`; it is not a published privacy page or an activation instruction. A reader-facing local preview is prepared at [`privacy/index.html`](../privacy/index.html), with permalink `/privacy/`, `noindex`, `sitemap: false` and `publication_state: editorial-draft`. Neither file activates collection or establishes deployment.

The page uses explicit semantic HTML so both Jekyll and the existing limited design renderer can render its content. The renderer now includes `privacy/**/*.{html,md}`. A focused isolated-browser check verified one main heading, five section headings, 14 paragraphs, the supplied operator/contact, Kit links, noindex, modeled sitemap exclusion, a 780-pixel reading column and no JavaScript errors or page overflow. See the [local preview check](../../library-preview-2026-10-29/email-privacy-preview-qa-2026-10-29.json) and [screenshot](../../library-preview-2026-10-29/email-privacy-preview-2026-10-29.png). This remains a design preview, not a Jekyll build or deployment.

## Current implementation state

- The owner selected Kit. The account now shows **MSRA Lab <federico@msralab.com>** as **Confirmed** and **Default**, and a green verification check for the `msralab.com` sending domain. The website's existing public contact remains **li@msralab.com**.
- The owner supplied **Future Foundry Limited, a Hong Kong entity**, as the responsible operator, and **federico@msralab.com** as the business and subscription contact. No physical address was supplied. This document and the preview do not use Kit's postal address as the operator's address.
- Kit has a published public form with an email field and three topic checkboxes. The website integration is prepared but disabled: `enabled`, `account_checks_verified` and `signup.topic_choices_verified` are false, and `privacy_url` is empty. Website collection being disabled does not disable Kit's separately published form.
- The latest owner-requested website presentation is a local email-entry bar opening one shared topic dialog. In disabled mode these unnamed local inputs demonstrate the flow without saving or sending them; the dialog's final action remains disabled. The earlier no-email-input preview rule is superseded by this request. The genuine Kit Form remains behind the existing release gates.
- Three Topics of Interest are configured using the existing form tags. An owner-controlled test selected Feline urinary health and New research launches. The owner clicked the confirmation email, and the actual Kit profile was then observed as **Confirmed**, with exactly tags `25146776` and `25146779`; the unselected Rabbit digestive health tag `25146778` was absent. The initial unconfirmed record was not observed. The test address and subscriber identifier are not recorded here.
- The observed form requires email confirmation: confirmation email on, automatic confirmation off. Subscriber data in the thank-you URL is off. The controlled result above verifies the confirmed profile and those selected tags. The email-footer profile link was subsequently opened and used to change and restore the topic choices; this verified the preference method described in the preview. The email-footer unsubscribe page's actual **Unsubscribe from all** button was then used: the reader-facing page confirmed successful unsubscribe, and the actual Kit profile showed **Unsubscribed**. The controlled record remains unsubscribed.
- The intended ongoing operation is manually prepared, topic-filtered Kit Broadcasts compatible with Kit Free. A website publication or build does not automatically send email. No campaign send is recorded by this document.

## Proposed notice text

### Research email updates

MSRA is operated by **Future Foundry Limited, a Hong Kong entity**. The business and subscription contact is **federico@msralab.com**.

MSRA uses Kit to manage research email subscriptions. You can choose **Feline urinary health**, **Rabbit digestive health** and **New research launches**, in any combination. We use your email address and chosen topics to send the research updates you request. The first two topics cover relevant guides, research and substantive evidence updates; New research launches covers new projects and questions across species.

Signing up for these research updates does not sign you up for product promotions. You can read our guides and research, and use the blank vet-visit record, without subscribing.

### Information used for the subscription

The signup form asks for your email address and research-topic choices. Kit keeps the subscription record, including confirmation and subscription status, topic tags and email activity associated with that record. We use these records to manage the list, select the relevant audience and handle delivery or subscription requests. Kit's subscriber records can include delivery, open and link-click activity. [Kit's subscriber-record documentation](https://help.kit.com/en/articles/2502651-the-subscriber-profile-page-and-status)

The subscription form does not ask for your pet's symptoms, diagnosis, treatment, clinical records or a completed vet-visit record. Please do not submit that information for a mailing-list signup. Choosing a research topic is an expression of interest, not a statement about your or your pet's health.

On the MSRA website, a topic link may suggest a checkbox based on the page you came from. You can change that selection before submitting. Opening a page or selecting a checkbox alone does not subscribe you or confirm your address.

### Confirmation and messages

After submitting the form, use the link in Kit's confirmation email to confirm your address. Submitting the form and confirming the email are separate steps. Research messages will come from **MSRA Lab <federico@msralab.com>** and will be selected using your current topic choices.

### Kit and email activity

Kit receives the information submitted to its form and provides the storage, confirmation, delivery and subscription-management service. Its service also uses technical information and tracking technologies; the applicable provider terms are in [Kit's Data Processing Addendum](https://kit.com/dpa). The provider's general [Privacy Policy](https://kit.com/privacy) covers its own service interactions and directs readers to the addendum for newsletter-subscriber processing.

Email-open and link-click records can be affected by mail apps and automated security checks, so they do not reliably establish that a person read or clicked a message. [Kit's explanation of automatic email activity](https://help.kit.com/en/articles/3643376-why-are-my-emails-being-automatically-opened-or-clicked)

### Unsubscribe, preferences and contact

Use the **Unsubscribe** link in a research email to stop receiving research emails. Unsubscribing stops further sends; it does not by itself erase the historical subscriber record in Kit. [Kit's subscription-status documentation](https://help.kit.com/en/articles/2502651-the-subscriber-profile-page-and-status)

Use **Update your profile** in the email footer to change topic preferences, then save your changes. The controlled profile check verified changing and restoring the selected topics.

For help changing your topics, correcting your email address, or requesting access to or deletion of subscription information, contact **federico@msralab.com**.

## Record handling and activity wording

The preview explains that an unsubscribed record may remain in Kit and provides a contact for access, correction and deletion requests. No fixed retention duration or deletion deadline has been established, and none is promised. The preview does not assert a country of storage or a sale/sharing policy.

The preview transparently describes Kit's possible processing of delivery, open and click activity as applicable, rather than asserting that tracking is disabled or promising a future account setting. The email-footer unsubscribe result is verified as recorded above. Deletion-request handling has not been tested by this task.

## Website analytics boundary

`_includes/analytics.html` loads Google Analytics 4 only in a production build when `site.google_analytics` is set; `_config.yml` currently specifies `G-R7JTFRCH80`. The include invokes the standard `gtag('config', ...)` call. The subscription JavaScript inspected for this draft does not send entered email addresses, subscriber IDs or clinical information to GA4; its local topic suggestions are not saved subscription records.

This email notice is not a complete website analytics or cookies notice. It does not claim that the website is cookie-free, that analytics are anonymous, that a consent gate has been configured, or that provider data stays in a particular country. A future website-wide notice should describe the actual deployed analytics and consent behavior after inspection.

## Source record

Local implementation checked: `_data/subscriptions.yml`, `_includes/kit-research-form.html`, `_includes/analytics.html`, `assets/js/subscriptions.js`, `_config.yml`, and `docs/KIT_CONNECTION_STATUS_2026-10-29.md`. The latest setup handover and human-supplied operator identity supersede earlier pending sender-verification, preference-configuration, controlled-test and operator-identity wording. No subscriber addresses, private postal details or credentials are included in this document.

Official provider references were checked on 29 October 2026. [Kit's topic-preference documentation](https://help.kit.com/en/articles/6082488-managing-subscriber-preferences-in-kit) establishes the provider's intended tag-based preference feature; the account configuration and controlled-test results are recorded separately above. A configured preference topic alone does not establish that a subscriber's preference change or unsubscribe has been tested.

The completed signup, confirmation, preferences and unsubscribe evidence is recorded without subscriber information in the [controlled-flow audit](../../library-preview-2026-10-29/kit-controlled-signup-check-2026-10-29.json) and [unsubscribe-success screenshot](../../library-preview-2026-10-29/kit-unsubscribe-success-2026-10-29.jpg). No research campaign was sent during these checks.
