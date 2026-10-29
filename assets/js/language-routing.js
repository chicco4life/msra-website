/* Same-content language URLs. No IP, URL, query or country is stored or logged.
   Country.is is a third-party hint; explicit choices and explicit URLs win. */
(function (scope, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else {
    scope.MSRALanguageRouting = api;
    if (scope.document) api.install(scope);
  }
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  var ENDPOINT = 'https://api.country.is/';
  var PREFERENCE = 'msra-language-choice-v1';
  var ATTEMPT = 'msra-language-auto-attempted-v1';
  var REDIRECTS = 'msra-language-redirects-v1';
  var COUNTRIES = {
    DE:'de', AT:'de', FR:'fr', IT:'it', ES:'es', MX:'es', AR:'es', CL:'es', CO:'es',
    PE:'es', EC:'es', UY:'es', PY:'es', BO:'es', VE:'es', CR:'es', PA:'es', GT:'es',
    HN:'es', SV:'es', NI:'es', DO:'es', CU:'es', NL:'nl', PL:'pl', SE:'sv', JP:'ja',
    BR:'pt-BR', KR:'ko', CN:'zh-Hans', PT:'pt-PT', DK:'da', NO:'nb', FI:'fi',
    RU:'ru', IN:'hi'
  };
  function locale(value, locales) {
    if (typeof value !== 'string') return null;
    var key = value.toLowerCase().replace(/_/g, '-');
    if (key === 'cn' || key === 'zh' || key === 'zh-cn' || key === 'zh-sg') key = 'zh-hans';
    if (key === 'no') key = 'nb';
    return Object.keys(locales || {}).find(function (name) { return name.toLowerCase() === key; }) || null;
  }
  function browserCandidate(language, locales) {
    var exact = locale(language, locales);
    if (exact) return exact;
    var code = String(language).toLowerCase().replace(/_/g, '-');
    if (/^zh-(?:hans|cn|sg)(?:-|$)/.test(code)) return locale('zh-Hans', locales);
    // Do not silently convert traditional Chinese into the Simplified edition.
    if (/^zh(?:-|$)/.test(code)) return null;
    if (/^pt(?:-|$)/.test(code)) return locale('pt-PT', locales) || locale('pt-BR', locales);
    return locale(code.split('-')[0], locales);
  }
  function supportedBrowserLocale(languages, locales) {
    for (var language of languages || []) {
      var candidate = browserCandidate(language, locales);
      if (candidate) return candidate;
    }
    return null;
  }
  function browserLocale(languages, locales) {
    return supportedBrowserLocale(languages, locales) || 'en';
  }
  function countryLocale(country, locales, languages) {
    var markets = { CH:['de','fr','it'], BE:['nl','fr','de'], CA:['en','fr'], IN:['en','hi'], SG:['en','zh-Hans'] };
    if (markets[country]) {
      for (var language of languages || []) {
        var candidate = browserCandidate(language, locales);
        if (candidate && markets[country].indexOf(candidate) !== -1) return candidate;
      }
      return 'en';
    }
    return locale(COUNTRIES[country], locales) || 'en';
  }
  function isBot(agent) {
    return /bot\b|crawler|spider|slurp|facebookexternalhit|whatsapp|telegrambot|chatgpt-user|claude-user|perplexity-user|google-inspectiontool|googleother|preview\b/i.test(agent || '');
  }
  function isLocal(host) {
    host = String(host || '').toLowerCase();
    return host === 'localhost' || host === '::1' || host === '[::1]' || /^(?:127\.|0\.0\.0\.0$)/.test(host) || /\.(?:localhost|local|test|invalid)$/.test(host);
  }
  function read(storage, key) { try { return storage && storage.getItem(key); } catch (error) { return null; } }
  function write(storage, key, value) { try { storage.setItem(key, value); return true; } catch (error) { return false; } }
  function preference(storage, locales) {
    return locale(read(storage, PREFERENCE), locales) || locale(read(storage, 'msra-lang'), locales);
  }
  function fragmentFits(hash, variant) {
    if (!hash) return true;
    var id;
    try { id = decodeURIComponent(hash.slice(1)); } catch (error) { return false; }
    return Array.isArray(variant.fragmentIds) && variant.fragmentIds.indexOf(id) !== -1;
  }
  function preservedSearch(current, locales) {
    if (!locale(current.searchParams.get('lang'), locales)) return current.search;
    // Consume the reserved legacy selector without re-encoding other query values.
    var parts = current.search.slice(1).split('&').filter(function (part) {
      try { return decodeURIComponent(part.split('=')[0].replace(/\+/g, ' ')) !== 'lang'; }
      catch (error) { return true; }
    });
    return parts.length ? '?' + parts.join('&') : '';
  }
  function destination(config, chosen, current, manual) {
    var variant = (config.variants || {})[chosen];
    if (!variant || typeof variant.url !== 'string' || !/^\/(?!\/)/.test(variant.url) || /[\s\\?#]/.test(variant.url)) return { reason:'missing-variant' };
    var target;
    try { target = new URL(variant.url, current.origin); } catch (error) { return { reason:'invalid-variant' }; }
    if (target.origin !== current.origin) return { reason:'invalid-variant' };
    var compatible = fragmentFits(current.hash, variant);
    if (!compatible && !manual) return { reason:'incompatible-fragment' };
    target.search = preservedSearch(current, config.locales);
    target.hash = compatible ? current.hash : '';
    return { url:target.href, locale:chosen, fragmentPreserved:compatible, reason:target.href === current.href ? 'same-url' : 'ready' };
  }
  function fetchCountry(env, timeout) {
    return new Promise(function (resolve) {
      var settled = false;
      var controller = env.AbortController ? new env.AbortController() : null;
      var timer;
      function finish(result) {
        if (settled) return;
        settled = true;
        env.clearTimeout(timer);
        resolve(result);
      }
      timer = env.setTimeout(function () {
        finish({ reason:'country-timeout' });
        if (controller) controller.abort();
      }, timeout);
      Promise.resolve().then(function () {
        return env.fetch(ENDPOINT, { method:'GET', mode:'cors', credentials:'omit',
          referrerPolicy:'no-referrer', cache:'no-store', signal:controller ? controller.signal : undefined });
      }).then(function (response) {
        if (!response.ok) throw new Error('country-http');
        return response.json();
      }).then(function (payload) {
        // The service returns an IP field too. It is deliberately never read.
        var country = payload && payload.country;
        finish(typeof country === 'string' && /^[A-Z]{2}$/.test(country) ? { country:country } : { reason:'country-invalid' });
      }).catch(function () { finish({ reason:'country-unavailable' }); });
    });
  }
  function guarded(config, env, current, queryChoice) {
    if (!config.enabled && !queryChoice) return 'disabled';
    if (isLocal(current.hostname) || current.protocol !== 'https:') return 'local-or-insecure';
    var production;
    try { production = new URL(config.siteUrl); } catch (error) { return 'invalid-site'; }
    if (current.hostname !== production.hostname && current.hostname !== 'www.' + production.hostname) return 'nonproduction-host';
    if (isBot(env.userAgent)) return 'bot';
    if (!config.resourceKey || !config.variants || !config.variants.en) return 'unregistered-route';
    if (config.currentLocale !== 'en' || current.pathname !== config.sourceRoute) return 'explicit-or-unmatched-route';
    return null;
  }
  async function run(config, env) {
    var current = new URL(env.url);
    function done(reason, chosen, target) {
      var result = { status:target ? 'redirect' : 'stay', reason:reason, locale:chosen || config.currentLocale || 'en' };
      if (target) result.url = target;
      if (env.status) env.status({ status:result.status, reason:result.reason, locale:result.locale });
      return result;
    }
    var queryChoice = locale(current.searchParams.get('lang'), config.locales);
    var skip = guarded(config, env, current, queryChoice);
    if (skip) return done(skip);
    if (queryChoice) write(env.localStorage, PREFERENCE, queryChoice);
    var chosen = queryChoice || preference(env.localStorage, config.locales);
    var explicit = Boolean(chosen);
    // If session storage is unavailable, keep the current page instead of risking a loop.
    if (!write(env.sessionStorage, 'msra-language-session-v1', '1')) return done('session-storage-unavailable');
    if (!chosen) {
      if (read(env.sessionStorage, ATTEMPT)) return done('session-attempted');
      write(env.sessionStorage, ATTEMPT, '1');
      var availableLocales = {};
      Object.keys(config.variants).forEach(function (name) {
        if (config.locales[name]) availableLocales[name] = config.locales[name];
      });
      // Playbook rule 3: a supported browser choice, including English, wins
      // before a country lookup. Only actual same-content editions are eligible.
      chosen = supportedBrowserLocale(env.languages, availableLocales);
      if (!chosen) {
        if (config.countryEndpoint !== ENDPOINT) return done('invalid-country-endpoint');
        var result = await fetchCountry(env, Math.max(100, Math.min(Number(config.timeoutMs) || 1200, 2000)));
        if (env.manualChoice && env.manualChoice()) return done('manual-choice-in-progress');
        // An explicit choice made in another tab while lookup was pending wins.
        chosen = preference(env.localStorage, config.locales);
        explicit = Boolean(chosen);
        if (!chosen) {
          // An unavailable Traditional Chinese edition is not permission to
          // substitute Simplified Chinese merely because of a country hint.
          if ((env.languages || []).some(function (name) { return /^zh-(?:hant|tw|hk|mo)(?:-|$)/i.test(String(name).replace(/_/g, '-')); })) {
            delete availableLocales['zh-Hans'];
          }
          chosen = result.country ? countryLocale(result.country, availableLocales, env.languages) : 'en';
        }
      }
    }
    if (chosen === 'en') return done(queryChoice ? 'query-english' : explicit ? 'preference-english' : 'resolved-english', 'en');
    var live = env.currentUrl ? new URL(env.currentUrl()) : current;
    if (live.origin !== current.origin || live.pathname !== current.pathname) return done('navigation-changed', chosen);
    var target = destination(config, chosen, live, false);
    if (!target.url || target.reason === 'same-url') return done(target.reason, chosen);
    var attempts;
    try { attempts = JSON.parse(read(env.sessionStorage, REDIRECTS) || '[]'); } catch (error) { attempts = []; }
    if (!Array.isArray(attempts)) attempts = [];
    var token = config.resourceKey + '::' + chosen;
    // A newly opened legacy selector is explicit intent, like a menu choice.
    // Its consumed lang parameter cannot replay on the target. Keep the token
    // so any later implicit/preference bounce is still stopped.
    if (!queryChoice && attempts.indexOf(token) !== -1) return done('redirect-already-attempted', chosen);
    if (attempts.indexOf(token) === -1) attempts.push(token);
    if (!write(env.sessionStorage, REDIRECTS, JSON.stringify(attempts))) return done('session-storage-unavailable', chosen);
    return done(queryChoice ? 'query' : explicit ? 'preference' : 'automatic-hint', chosen, target.url);
  }
  function install(win) {
    var doc = win.document;
    var node = doc.getElementById('msra-language-routing');
    if (!node || node.dataset.initialized) return;
    node.dataset.initialized = 'true';
    var config;
    try { config = JSON.parse(node.textContent); } catch (error) { return; }
    var local, session;
    try { local = win.localStorage; } catch (error) { local = null; }
    try { session = win.sessionStorage; } catch (error) { session = null; }
    var manuallyChosen = false;
    function status(detail) { doc.dispatchEvent(new win.CustomEvent('msra:language-routing', { detail:detail })); }
    doc.querySelectorAll('[data-language-choice], a[data-source-edition]').forEach(function (link) {
      var menuChoice = link.getAttribute('data-language-choice');
      var chosen = locale(menuChoice || 'en', config.locales);
      if (!chosen) return;
      if (menuChoice) {
        var target = destination(config, chosen, new URL(win.location.href), true);
        if (!target.url) return;
        link.href = target.url;
      }
      function choose(event) {
        if (event.defaultPrevented || (event.button !== undefined && event.button !== 0 && event.button !== 1)) return;
        // Source-edition links can intentionally name a different ?p= project.
        // Keep those authored hrefs; only the same-content menu inherits this URL.
        if (menuChoice) {
          var latest = destination(config, chosen, new URL(win.location.href), true);
          if (!latest.url) return;
          link.href = latest.url;
        }
        manuallyChosen = true;
        var saved = write(local, PREFERENCE, chosen);
        // A new explicit choice starts a fresh preference route history.
        write(session, REDIRECTS, '[]');
        status({ status:'manual-choice', reason:saved ? 'preference-saved' : 'preference-storage-unavailable', locale:chosen });
        // Native anchors also support modified clicks, new tabs and JavaScript-free pages.
      }
      link.addEventListener('click', choose);
      link.addEventListener('auxclick', choose);
    });
    var env = { url:win.location.href, userAgent:win.navigator.userAgent,
      languages:win.navigator.languages || [win.navigator.language], localStorage:local, sessionStorage:session,
      fetch:win.fetch ? win.fetch.bind(win) : function () { return Promise.reject(new Error('unavailable')); },
      AbortController:win.AbortController, setTimeout:win.setTimeout.bind(win), clearTimeout:win.clearTimeout.bind(win),
      manualChoice:function () { return manuallyChosen; }, currentUrl:function () { return win.location.href; }, status:status };
    run(config, env).then(function (result) {
      if (result.status !== 'redirect' || manuallyChosen) return;
      var initial = new URL(env.url), live = new URL(win.location.href);
      if (live.origin !== initial.origin || live.pathname !== initial.pathname) return;
      var latest = destination(config, result.locale, live, false);
      if (latest.url && latest.reason !== 'same-url') win.location.replace(latest.url);
    }).catch(function () { status({ status:'stay', reason:'routing-unavailable', locale:config.currentLocale || 'en' }); });
  }
  return { endpoint:ENDPOINT, keys:{ preference:PREFERENCE, attempt:ATTEMPT, redirects:REDIRECTS },
    locale:locale, browserLocale:browserLocale, countryLocale:countryLocale, isBot:isBot,
    fragmentFits:fragmentFits, destination:destination, fetchCountry:fetchCountry, run:run, install:install };
});
