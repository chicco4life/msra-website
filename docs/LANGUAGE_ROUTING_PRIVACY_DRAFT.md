# Language routing: implementation and privacy insertion draft

Prepared for parent integration. This file does not publish a notice or assert legal review.

## Suggested public notice text

### Language choices and approximate country

You can choose the language of the page from the language menu. We save that explicit choice in your browser's local storage without an expiry date, until you change it or clear the site's stored data. This preference is separate from research email subscriptions and does not subscribe you to anything.

On a first eligible visit to an English page, when there is no explicit language choice, the website first chooses the first supported browser language among the available, released editions of the same content. English counts as a supported language. If a supported browser language is found, no country lookup is made. Only when no browser language has a supported edition may the website request an approximate country from **Country.is** at `https://api.country.is/`. The request goes directly from your browser to that third-party service, which therefore receives your network IP address and ordinary network request information. We omit credentials, cookies and the page referrer and do not send the page URL, search parameters, fragment, email address or other form data in the lookup. The service response includes an IP address and country code; the MSRA routing code reads only the country code, does not retain the response, and does not store or log the IP address or country.

The country is only a fallback language hint. It may be wrong, including when a VPN is in use, and a country can have several languages. If the lookup is unavailable, fails or is slow, the page stays in English. A country without an available, supported default also keeps English. Traditional Chinese browser preferences (`Hant`, `TW`, `HK` or `MO`) do not trigger a Simplified Chinese edition through country fallback when no other supported browser language matches. A saved explicit choice takes priority over automatic browser or country selection. A page URL that already identifies a language stays in that language.

Temporary session storage records that an automatic lookup or same-page redirect was attempted, to prevent repeated lookups and redirect loops. It contains only a flag and language/content identifiers, not IP addresses or country codes. Language switching keeps the page's search parameters, except that a supported legacy `lang` language selector is consumed and removed so it cannot undo a later manual choice. Other query values keep their encoding. A fragment is kept only when the target edition has that anchor; an incompatible fragment prevents an automatic redirect, while an explicit manual switch opens the chosen edition without that fragment. Without JavaScript the menu still links to the actual equivalent page, but it cannot save a preference or carry the current query and fragment dynamically. If browser storage is blocked or cleared, persistence cannot be guaranteed; automatic redirects are disabled when session storage is unavailable.

This routing does not send signup data, activate email capture, or report lookup results to analytics.

## Service evidence and limitations

- [Official Country.is documentation](https://country.is/): free commercial use, no account/key or ordinary quota; abuse limit 10 requests per second per client IP.
- [Official OpenAPI](https://api.country.is/openapi.json): the default response contains `ip` and `country`; `country` may be null. Additional `fields` cannot remove the default IP field.
- [Official implementation](https://github.com/lineofflight/country/blob/main/src/app.ts): CORS is enabled. Documentation says requests are not logged, but the implementation includes error-response logging. No separate retention/privacy policy was located in the official material reviewed. Do not promise that the provider never logs requests or IP information.

No provider account, secret, attribution token or paid plan was created. The code uses a 1.2-second timeout, credentials omitted, `no-referrer`, and `no-store`. A shared NAT IP may encounter abuse limits. Service availability and CORS remain external dependencies; lookup failures keep English. Browser language is checked before any lookup, and supported browser-language selection makes no country request. All lookup tests use injected fake responses and do not look up an owner's IP.

## Integration contract

Include `{% include language-routing.html %}` once near the end of each HTML layout. The include emits inert JSON and the deferred local script. It requires `localization_registry.by_route`, `resources[*].variants`, and `locales`. Each variant's optional `fragment_ids` array lists actual compatible HTML IDs; absent lists are treated conservatively. No locale URL is synthesized by adding a prefix.

The saved preference key is `msra-language-choice-v1`; a valid legacy `msra-lang` preference is respected if no newer preference exists. A supported legacy `?lang=` selector on a neutral English public URL is an explicit choice: it wins over a saved preference, saves the selected language, makes no country request, and works independently of the automatic release setting. `cn` and `zh` map to `zh-Hans`; unknown selectors are ignored and preserved. An explicit locale path remains stronger than the query selector. Manual links carry `data-language-choice`; the English source-edition link also counts as an explicit English choice. Status events are named `msra:language-routing` and contain only finite status/reason labels and a locale—never IP, country, URL, query or form values.

Automatic routing is off by default. It requires an explicit `language_routing_enabled: true` site setting, a production build, and the configured HTTPS production host. The parent should enable it only when the intended locale editions are ready for public routing; merely pushing drafts must not turn it on. Localhost, local/preview hosts, nonproduction builds, bots, unregistered routes, and explicit locale routes make no lookup request. The default English layout should set `data-content-locale="en"` to keep the retained legacy dictionary module from relabelling full English content. The parent owns that layout integration.
