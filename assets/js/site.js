/* MSRA site behaviour: languages, pre-order waitlist, shop filters, contact form. */
(function () {
  var M = window.MSRA = window.MSRA || {};
  var shop = M.shop || {};
  var mail = M.mail || 'li@msralab.com';
  var root = document.documentElement;

  /* ── 1. Languages ─────────────────────────────────────────────
     English is written in the HTML. Every translatable element carries data-i18n="key";
     translations live in /assets/i18n/<lang>.json. A missing key falls back to English. */
  var LANGS = { en: { code: 'EN', html: 'en' }, ja: { code: 'JA', html: 'ja' }, nl: { code: 'NL', html: 'nl' },
                es: { code: 'ES', html: 'es' }, zh: { code: '中文', html: 'zh-CN' } };
  var dicts = { en: {} };
  var cur = 'en';
  function t(key, en) { var d = dicts[cur] || {}; return (cur !== 'en' && d[key]) || en; }
  function apply(scope) {
    var d = dicts[cur] || {};
    (scope || document).querySelectorAll('[data-i18n]').forEach(function (el) {
      if (el.__en === undefined) el.__en = el.innerHTML;
      var v = cur !== 'en' ? d[el.getAttribute('data-i18n')] : null;
      el.innerHTML = v || el.__en;
    });
    (scope || document).querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      el.__enAttr = el.__enAttr || {};
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var i = pair.indexOf(':'); if (i < 0) return;
        var attr = pair.slice(0, i).trim(), key = pair.slice(i + 1).trim();
        if (!(attr in el.__enAttr)) el.__enAttr[attr] = el.getAttribute(attr) || '';
        var v = cur !== 'en' ? d[key] : null;
        el.setAttribute(attr, v || el.__enAttr[attr]);
      });
    });
  }
  function load(lang) {
    if (dicts[lang]) return Promise.resolve(dicts[lang]);
    return fetch((M.i18n || '/assets/i18n/') + lang + '.json?v=' + (M.v || ''))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { dicts[lang] = j; return j; });
  }
  function jpFonts() {
    if (document.getElementById('jp-fonts')) return;
    var l = document.createElement('link'); l.id = 'jp-fonts'; l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600&family=Noto+Serif+JP:wght@500;600&display=swap';
    document.head.appendChild(l);
  }
  function ready() { root.classList.remove('i18n-wait'); }
  function setLang(lang, save) {
    if (!LANGS[lang]) lang = 'en';
    if (lang === 'ja') jpFonts();
    return load(lang).catch(function () { lang = 'en'; }).then(function () {
      cur = lang;
      root.lang = LANGS[lang].html;
      root.setAttribute('data-lang', lang);
      apply(document);
      var c = document.getElementById('lang-cur'); if (c) c.textContent = LANGS[lang].code;
      document.querySelectorAll('#lang-list [data-lang]').forEach(function (b) { b.setAttribute('aria-checked', String(b.dataset.lang === lang)); });
      if (save) { try { localStorage.setItem('msra-lang', lang); } catch (e) {} }
      ready();
      document.dispatchEvent(new CustomEvent('msra:lang', { detail: lang }));
    });
  }
  M.t = t; M.applyI18n = apply; M.lang = function () { return cur; }; M.setLang = setLang;

  // Language menu
  var btn = document.getElementById('lang-btn'), list = document.getElementById('lang-list');
  function openMenu(open) {
    if (!btn || !list) return;
    list.hidden = !open; btn.setAttribute('aria-expanded', String(open));
    if (open) { var on = list.querySelector('[aria-checked="true"]') || list.querySelector('button'); if (on) on.focus(); }
  }
  if (btn && list) {
    btn.addEventListener('click', function (e) { e.stopPropagation(); openMenu(list.hidden); });
    list.addEventListener('click', function (e) {
      var b = e.target.closest('[data-lang]'); if (!b) return;
      openMenu(false); btn.focus(); setLang(b.dataset.lang, true);
    });
    list.addEventListener('keydown', function (e) {
      var items = Array.prototype.slice.call(list.querySelectorAll('button')), i = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
    });
    document.addEventListener('click', function (e) { if (!list.hidden && !e.target.closest('#lang-menu')) openMenu(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !list.hidden) { openMenu(false); btn.focus(); } });
  }

  // Start in the language chosen before paint (saved choice, ?lang=, or the browser's language).
  setTimeout(ready, 2500); // never leave text hidden if a translation file fails to load
  var start = root.getAttribute('data-lang') || 'en';
  var fromUrl = new URLSearchParams(location.search).get('lang');
  setLang(start, !!(fromUrl && LANGS[fromUrl]));

  /* ── 2. Pre-order waitlist ─────────────────────────────────── */
  var dlg = document.getElementById('waitlist');
  var wlForm = document.getElementById('wl-form'), wlDone = document.getElementById('wl-done');
  var wlStatus = document.getElementById('wl-status'), wlSlug = '';
  function productName(slug) { return (M.products || {})[slug] || slug; }
  function openWaitlist(slug) {
    if (!dlg) return;
    wlSlug = slug;
    document.getElementById('wl-product').textContent = productName(slug);
    document.getElementById('wl-done-product').textContent = productName(slug);
    wlForm.hidden = false; wlDone.hidden = true; wlStatus.textContent = '';
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
    setTimeout(function () { document.getElementById('wl-email').focus(); }, 30);
  }
  function closeWaitlist() { if (!dlg) return; if (dlg.close) dlg.close(); else dlg.removeAttribute('open'); }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-preorder]');
    if (b) { e.preventDefault(); openWaitlist(b.getAttribute('data-preorder')); }
  });
  if (dlg) {
    document.getElementById('wl-close').addEventListener('click', closeWaitlist);
    document.getElementById('wl-done-close').addEventListener('click', function () {
      closeWaitlist();
      if (!/\/shop\/?$/.test(location.pathname) && M.shopPage && /\/shop\//.test(location.pathname)) location.href = M.shopPage;
    });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) closeWaitlist(); }); // click on the backdrop
    wlForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var email = document.getElementById('wl-email');
      if (!email.value || !email.checkValidity()) {
        wlStatus.textContent = t('wl.err_email', 'Please enter a valid email address.'); email.focus(); return;
      }
      var name = productName(wlSlug);
      var data = { type: 'Waitlist', product: name, email: email.value,
                   country: document.getElementById('wl-country').value,
                   other_launches: document.getElementById('wl-news').checked ? 'yes' : 'no',
                   language: cur, page: location.href };
      var subject = 'Waitlist: ' + name;
      if (shop.form_endpoint) {
        var send = document.getElementById('wl-send'); send.disabled = true;
        fetch(shop.form_endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                                    body: JSON.stringify(Object.assign({ _subject: subject }, data)) })
          .then(function (r) { if (!r.ok) throw new Error(r.status); wlForm.reset(); wlForm.hidden = true; wlDone.hidden = false; })
          .catch(function () { wlStatus.textContent = t('wl.err_send', 'That did not send. Please email us at') + ' ' + mail; })
          .then(function () { send.disabled = false; });
      } else {
        var body = ['Please add me to the waitlist.', '', 'Product: ' + name, 'Email: ' + data.email,
                    'Country: ' + data.country, 'Tell me about other MSRA launches: ' + data.other_launches].join('\n');
        window.location.href = 'mailto:' + mail + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
        wlStatus.textContent = t('wl.mailto', 'Your email app should open with the request filled in. Send it to join the waitlist.');
      }
    });
  }

  /* ── 3. Shop filters ───────────────────────────────────────── */
  var grid = document.getElementById('pgrid');
  var shopFilters = document.querySelectorAll('.filter[data-group]');
  shopFilters.forEach(function (b) {
    b.addEventListener('click', function () {
      shopFilters.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      grid.querySelectorAll('.pcard').forEach(function (c) { c.hidden = !(b.dataset.group === 'all' || c.dataset.group === b.dataset.group); });
    });
  });

  /* ── 4. Questions and partnerships form ────────────────────── */
  var form = document.getElementById('inq-form');
  if (form) {
    var ask = new URLSearchParams(location.search).get('ask');
    if (ask && (M.products || {})[ask]) document.getElementById('inq-product').value = M.products[ask];
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var status = document.getElementById('inq-status');
      var email = document.getElementById('inq-email');
      if (!email.value || !email.checkValidity()) {
        status.textContent = t('ask.err_email', 'Please enter a valid email address so we can reply.'); email.focus(); return;
      }
      var type = (form.querySelector('input[name="type"]:checked') || {}).value || 'Question';
      var data = { type: type, product: document.getElementById('inq-product').value,
                   name: document.getElementById('inq-name').value, country: document.getElementById('inq-country').value,
                   email: email.value, message: document.getElementById('inq-msg').value, language: cur };
      var subject = type + ': ' + data.product;
      if (shop.form_endpoint) {
        var b = document.getElementById('inq-send'); b.disabled = true;
        fetch(shop.form_endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                                    body: JSON.stringify(Object.assign({ _subject: subject }, data)) })
          .then(function (r) { if (!r.ok) throw new Error(r.status); form.reset(); status.textContent = t('ask.sent', 'Thanks. We have your message and will reply by email.'); })
          .catch(function () { status.textContent = t('wl.err_send', 'That did not send. Please email us at') + ' ' + mail; })
          .then(function () { b.disabled = false; });
      } else {
        var body = ['Request: ' + data.type, 'Product: ' + data.product, 'Name: ' + data.name, 'Country: ' + data.country,
                    'Email: ' + data.email, '', data.message].join('\n');
        window.location.href = 'mailto:' + mail + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
        status.textContent = t('ask.mailto', 'Your email app should open with your message filled in. If it does not, email us directly.');
      }
    });
  }
})();
