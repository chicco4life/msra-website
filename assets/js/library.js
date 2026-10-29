/* Local reading tools only. No search text or completed veterinary record is sent. */
(function () {
  'use strict';
  // Keep the project choice local; every project and its links exist without JS.
  var picker = document.querySelector('[data-library-project-picker]');
  if (picker) {
    var panels = Array.from(document.querySelectorAll('[data-library-project]'));
    var projectIds = panels.map(function (panel) { return panel.dataset.libraryProject; });
    var announcement = document.querySelector('[data-library-project-status]');
    function projectFromHash() {
      var id = window.location.hash.replace(/^#project-/, '');
      return projectIds.indexOf(id) !== -1 ? id : null;
    }
    function showProject(id) {
      if (projectIds.indexOf(id) === -1) id = picker.options[0].value;
      picker.value = id;
      panels.forEach(function (panel) { panel.hidden = panel.dataset.libraryProject !== id; });
      var label = picker.options[picker.selectedIndex].textContent;
      if (announcement) announcement.textContent = label + ' selected.';
    }
    showProject(projectFromHash() || picker.value);
    document.querySelector('[data-library-project-enhanced]').hidden = false;
    document.querySelector('[data-library-project-fallback]').hidden = true;
    picker.addEventListener('change', function () {
      showProject(picker.value);
      // A project ID is navigation state, never an email address or consent.
      window.history.replaceState(null, '', '#project-' + picker.value);
    });
    window.addEventListener('hashchange', function () {
      var id = projectFromHash();
      if (id) showProject(id);
    });
  }
  document.querySelectorAll('[data-print-record]').forEach(function (button) {
    button.addEventListener('click', function () { window.print(); });
  });
  document.querySelectorAll('[data-copy-record]').forEach(function (button) {
    button.addEventListener('click', function () {
      var record = document.querySelector('[data-public-copy-id="T24"]');
      var status = document.querySelector('[data-copy-record-status]');
      if (!record || !status) return;
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        status.textContent = 'Select the record text to copy it, or use Print. Nothing is saved or sent.';
        return;
      }
      navigator.clipboard.writeText(record.innerText).then(function () {
        status.textContent = 'Blank record copied. Paste it into your own notes; nothing was uploaded or sent to MSRA.';
      }).catch(function () {
        status.textContent = 'Copy was not available. Select the record text to copy it, or use Print.';
      });
    });
  });

  document.querySelectorAll('[data-public-copy-id]').forEach(function (body) {
    var paragraphs = Array.from(body.querySelectorAll(':scope > p'));
    var urgent = paragraphs.find(function (p) {
      return p.querySelector('strong') && /(?:little or no urine|little or no urinary|uncertain.*urine|urine.*uncertain)/i.test(p.textContent) && /(?:contact|call)/i.test(p.textContent);
    });
    if (!urgent) return;
    urgent.classList.add('knowledge-urgent');
    var grid = body.closest('.knowledge-packet__grid');
    if (!grid) return;
    function placeNavigation() {
      var bottom = urgent.getBoundingClientRect().bottom - grid.getBoundingClientRect().top;
      grid.style.setProperty('--packet-urgent-offset', Math.max(0, Math.ceil(bottom) + 24) + 'px');
    }
    placeNavigation();
    window.addEventListener('resize', placeNavigation);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(placeNavigation);
  });

  // Progressive enhancement: the full source manuscript works without JavaScript.
  // Group its actual ref-N anchors for local filtering without rewriting prose.
  var sourceBody = document.querySelector('[data-public-copy-id="S00"]');
  if (sourceBody) {
    function topChild(node) {
      while (node && node.parentNode !== sourceBody) node = node.parentNode;
      return node;
    }
    var anchors = Array.from(sourceBody.querySelectorAll('a[id]')).filter(function (a) { return /^ref-\d+$/.test(a.id); });
    anchors.forEach(function (anchor, index) {
      var start = topChild(anchor);
      var end = index + 1 < anchors.length ? topChild(anchors[index + 1]) : topChild(sourceBody.querySelector('#supplementary-guidance'));
      var card = document.createElement('article');
      card.className = 'knowledge-source-card';
      start.before(card);
      var node = start;
      while (node && node !== end) {
        if (node.nodeType === 1 && /^(additional-context|supplementary-guidance)$/.test(node.id)) break;
        var next = node.nextSibling;
        card.appendChild(node);
        node = next;
      }
    });
    var filter = document.querySelector('[data-packet-source-filter]');
    if (filter && anchors.length === 41) filter.hidden = false;
  }
  var search = document.querySelector('[data-source-search]');
  if (!search) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll('.knowledge-source-card'));
  var status = document.querySelector('[data-source-search-status]');
  function filterSources() {
    var query = search.value.trim().toLocaleLowerCase();
    var found = 0;
    cards.forEach(function (card) {
      var show = !query || card.textContent.toLocaleLowerCase().indexOf(query) !== -1;
      card.hidden = !show;
      if (show) found += 1;
    });
    if (status) status.textContent = found + ' of ' + cards.length + ' source records shown.';
  }
  search.addEventListener('input', filterSources);
  function revealLinkedSource() {
    if (!sourceBody || !/^#ref-(?:[1-9]|[1-3]\d|4[01])$/.test(window.location.hash)) return;
    var target = document.getElementById(window.location.hash.slice(1));
    if (!target) return;
    search.value = '';
    filterSources();
    window.requestAnimationFrame(function () { target.scrollIntoView({ block: 'start' }); });
  }
  window.addEventListener('hashchange', revealLinkedSource);
  filterSources();
  revealLinkedSource();
})();
