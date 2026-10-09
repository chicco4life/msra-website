/* MSRA site behaviour: buy / pre-order links, inquiry form, language toggle, library filters. */
(function () {
  var M = window.MSRA || {};
  var shop = M.shop || {};
  var products = shop.products || {};
  var mail = M.mail || 'li@msralab.com';

  // 1. Buy buttons. A Shopify or Amazon link turns "Pre-order" into a real buy button.
  document.querySelectorAll('[data-shop]').forEach(function (a) {
    var p = products[a.dataset.shop] || {};
    var url = p.shopify || p.amazon;
    if (!url) return;                       // no store link yet: stays "Pre-order"
    a.href = url; a.target = '_blank'; a.rel = 'noopener';
    a.removeAttribute('data-inquire');
    if (p.shopify) { a.innerHTML = 'Buy now'; a.setAttribute('data-cn', '立即购买'); }
    else { a.innerHTML = 'Buy on Amazon'; a.setAttribute('data-cn', '在亚马逊购买'); }
  });
  var navShop = document.getElementById('nav-shop');
  if (navShop && shop.store) {
    navShop.href = shop.store; navShop.target = '_blank'; navShop.rel = 'noopener';
    navShop.innerHTML = 'Shop'; navShop.setAttribute('data-cn', '选购');
  }

  // 2. Pre-order / inquiry form.
  var form = document.getElementById('inq-form');
  var qtyField = document.getElementById('qty-field');
  function syncQty() {
    var pre = document.getElementById('type-preorder');
    if (qtyField && pre) qtyField.hidden = !pre.checked;
  }
  if (form) {
    form.querySelectorAll('input[name="type"]').forEach(function (r) { r.addEventListener('change', syncQty); });
    syncQty();
  }
  // Product buttons pre-fill the form.
  document.querySelectorAll('[data-inquire]').forEach(function (a) {
    a.addEventListener('click', function () {
      if (!form || !a.dataset.inquire) return;
      var sel = document.getElementById('inq-product');
      if (sel) sel.value = a.dataset.inquire;
      var t = document.getElementById(a.dataset.type === 'preorder' ? 'type-preorder' : 'type-question');
      if (t) t.checked = true;
      syncQty();
    });
  });
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var status = document.getElementById('inq-status');
      var cn = document.documentElement.lang === 'zh-CN';
      var email = document.getElementById('inq-email');
      if (!email.value || !email.checkValidity()) {
        status.textContent = cn ? '请填写有效的邮箱地址。' : 'Please enter a valid email address so we can reply.';
        email.focus(); return;
      }
      var type = (form.querySelector('input[name="type"]:checked') || {}).value || 'Question';
      var data = {
        type: type,
        product: document.getElementById('inq-product').value,
        quantity: type === 'Pre-order' ? document.getElementById('inq-qty').value : '',
        name: document.getElementById('inq-name').value,
        country: document.getElementById('inq-country').value,
        email: email.value,
        message: document.getElementById('inq-msg').value
      };
      var subject = type + ': ' + data.product;
      if (shop.form_endpoint) {
        var btn = document.getElementById('inq-send'); btn.disabled = true;
        fetch(shop.form_endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(Object.assign({ _subject: subject }, data))
        }).then(function (r) {
          if (!r.ok) throw new Error(r.status);
          form.reset(); syncQty();
          status.textContent = cn ? '已收到你的请求，我们会通过邮件回复。' : 'Thanks. We have your request and will reply by email.';
        }).catch(function () {
          status.textContent = cn ? '发送失败。请直接发邮件至 ' + mail : 'That did not send. Please email ' + mail + ' instead.';
        }).then(function () { btn.disabled = false; });
      } else {
        var body = [
          'Request: ' + data.type, 'Product: ' + data.product,
          data.quantity ? 'Quantity: ' + data.quantity : '',
          'Name: ' + data.name, 'Country: ' + data.country, 'Email: ' + data.email, '', data.message
        ].filter(function (l, i) { return l !== '' || i > 5; }).join('\n');
        window.location.href = 'mailto:' + mail + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
        status.textContent = cn ? '你的邮件应用会打开并自动填好内容。若没有打开，请直接发邮件至 ' + mail + '。'
                                : 'Your email app should open with the request filled in. If it does not, email ' + mail + '.';
      }
    });
  }

  // 3. Language toggle (EN / 中文) for every element that carries data-cn.
  var els = Array.prototype.slice.call(document.querySelectorAll('[data-cn]'));
  els.forEach(function (el) { el.dataset.en = el.innerHTML; });
  var bEn = document.getElementById('lang-en'), bCn = document.getElementById('lang-cn');
  function setLang(lang) {
    els.forEach(function (el) { el.innerHTML = lang === 'cn' ? el.dataset.cn : el.dataset.en; });
    document.documentElement.lang = lang === 'cn' ? 'zh-CN' : 'en';
    if (bEn) bEn.setAttribute('aria-pressed', String(lang !== 'cn'));
    if (bCn) bCn.setAttribute('aria-pressed', String(lang === 'cn'));
  }
  function choose(lang) { setLang(lang); try { localStorage.setItem('msra-lang', lang); } catch (e) {} }
  if (bEn) bEn.addEventListener('click', function () { choose('en'); });
  if (bCn) bCn.addEventListener('click', function () { choose('cn'); });
  var saved = null;
  try { saved = localStorage.getItem('msra-lang'); } catch (e) {}
  if (saved === 'cn' || (!saved && M.pageLang === 'zh')) setLang('cn');

  // 4. Research library filters.
  var filters = document.querySelectorAll('.filter[data-filter]');
  if (filters.length) {
    var rows = document.querySelectorAll('table.lib tbody tr');
    var count = document.getElementById('lib-count');
    filters.forEach(function (b) {
      b.addEventListener('click', function () {
        var f = b.dataset.filter, n = 0;
        filters.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        rows.forEach(function (r) {
          var show = f === 'all' || (' ' + r.dataset.tags + ' ').indexOf(' ' + f + ' ') > -1;
          r.hidden = !show; if (show) n++;
        });
        if (count) count.textContent = n;
      });
    });
  }
})();
