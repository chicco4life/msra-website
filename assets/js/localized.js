/* Progressive enhancement for complete static translation drafts. No requests,
   provider code, analytics, signup submission, or client-side body translation. */
(function () {
  'use strict';
  var node = document.getElementById('localized-ui-data');
  var ui;
  try { ui = JSON.parse(node.textContent); } catch (error) { return; }
  var body = document.querySelector('[data-localized-body]');
  if (!body) return;

  // The static CSS label remains visible without JS. Add actual text for
  // assistive technology when enhancement is available.
  body.querySelectorAll('a[data-fallback-label]').forEach(function (link) {
    var label = document.createElement('span');
    label.className = 'localized-language-label';
    label.textContent = ' (' + link.getAttribute('data-fallback-label') + ')';
    link.appendChild(label);
    link.setAttribute('data-fallback-enhanced', 'true');
  });

  var print = document.querySelector('[data-localized-print]');
  if (print) print.addEventListener('click', function () { window.print(); });
  var copy = document.querySelector('[data-localized-copy]');
  var copyStatus = document.querySelector('[data-localized-copy-status]');
  if (copy) copy.addEventListener('click', function () {
    if (!navigator.clipboard || !window.isSecureContext) {
      if (copyStatus) copyStatus.textContent = ui.copy_error;
      return;
    }
    navigator.clipboard.writeText(body.innerText).then(function () {
      if (copyStatus) copyStatus.textContent = ui.copy_success;
    }).catch(function () {
      if (copyStatus) copyStatus.textContent = ui.copy_error;
    });
  });

  if (body.getAttribute('data-public-copy-id') !== 'S00') return;
  function topChild(element) {
    while (element && element.parentNode !== body) element = element.parentNode;
    return element;
  }
  var anchors = Array.from(body.querySelectorAll('a[id]')).filter(function (anchor) {
    return /^ref-\d+$/.test(anchor.id);
  });
  anchors.forEach(function (anchor, index) {
    var start = topChild(anchor);
    var lastBoundary = body.querySelector('#supplementary-guidance');
    var end = index + 1 < anchors.length ? topChild(anchors[index + 1]) : topChild(lastBoundary);
    var card = document.createElement('section');
    card.className = 'localized-source-card';
    start.before(card);
    var current = start;
    while (current && current !== end) {
      if (current.nodeType === 1 && current.id === 'supplementary-guidance') break;
      var next = current.nextSibling;
      card.appendChild(current);
      current = next;
    }
  });
  var filter = document.querySelector('[data-localized-source-filter]');
  var query = document.querySelector('[data-localized-source-query]');
  var status = document.querySelector('[data-localized-source-status]');
  var cards = Array.from(body.querySelectorAll('.localized-source-card'));
  if (!filter || !query || !cards.length) return;
  filter.hidden = false;
  function filterSources() {
    var term = query.value.trim().toLocaleLowerCase(document.documentElement.lang);
    var shown = 0;
    cards.forEach(function (card) {
      var visible = !term || card.textContent.toLocaleLowerCase(document.documentElement.lang).indexOf(term) !== -1;
      card.hidden = !visible;
      if (visible) shown++;
    });
    if (status) status.textContent = ui.source_search_results.replace('{shown}', String(shown)).replace('{total}', String(cards.length));
  }
  query.addEventListener('input', filterSources);
  function revealFragment() {
    if (!/^#ref-\d+$/.test(location.hash)) return;
    var target = document.getElementById(location.hash.slice(1));
    if (!target) return;
    query.value = '';
    filterSources();
    window.requestAnimationFrame(function () { target.scrollIntoView({ block:'start' }); });
  }
  window.addEventListener('hashchange', revealFragment);
  filterSources();
  revealFragment();
})();

// Native selector with stable project fragments and a complete no-JavaScript list.
document.querySelectorAll('[data-localized-project-browser]').forEach(function(browser) {
  var select = browser.querySelector('[data-localized-project-select]');
  var panels = Array.from(browser.querySelectorAll('[data-localized-project]'));
  if (!select || !panels.length) return;
  function showProject(updateHash) {
    var chosen = panels.find(function(panel) { return panel.dataset.localizedProject === select.value; });
    if (!chosen) return;
    panels.forEach(function(panel) { panel.hidden = panel !== chosen; });
    if (updateHash) history.replaceState(null, '', '#project-' + select.value);
  }
  function fromHash() {
    var id = location.hash.replace(/^#project-/, '');
    if (panels.some(function(panel) { return panel.dataset.localizedProject === id; })) select.value = id;
    showProject(false);
  }
  select.addEventListener('change', function() { showProject(true); });
  window.addEventListener('hashchange', fromHash);
  fromHash();
});
