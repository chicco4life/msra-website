/* MSRA open knowledge base client.
   Research pages read notes (notes/*.md) and studies (library/studies.csv) live from the
   GitHub repository set in _config.yml, so anything published there shows up here
   without rebuilding the website. */
(function () {
  var M = window.MSRA || {};
  var cfg = M.kb || {};
  var REPO = cfg.repo || 'chicco4life/msra';
  var BR = cfg.branch || 'main';
  var RAW = 'https://raw.githubusercontent.com/' + REPO + '/' + BR + '/';
  var API = 'https://api.github.com/repos/' + REPO + '/contents/notes?ref=' + encodeURIComponent(BR);
  var BLOB = 'https://github.com/' + REPO + '/blob/' + BR + '/';
  var EDIT = 'https://github.com/' + REPO + '/edit/' + BR + '/';
  var HOME = 'https://github.com/' + REPO;
  var NOTE = (cfg.notePage || '/research/note/') + '?f=';

  function cn() { return document.documentElement.lang === 'zh-CN'; }
  function t(en, zh) { return cn() ? zh : en; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  // Set bilingual content so the EN / 中文 toggle keeps working on live content.
  function bi(el, en, zh) { if (!el) return; el.dataset.en = en; el.dataset.cn = zh; el.innerHTML = cn() ? zh : en; }

  function cacheGet(k) { try { var v = JSON.parse(sessionStorage.getItem(k)); if (v && Date.now() - v.t < 600000) return v.d; } catch (e) {} return null; }
  function cacheSet(k, d) { try { sessionStorage.setItem(k, JSON.stringify({ t: Date.now(), d: d })); } catch (e) {} }

  function fmtDate(d) { if (!d) return ''; if (d instanceof Date) return d.toISOString().slice(0, 10); return String(d).slice(0, 10); }
  function parseNote(text) {
    var m = /^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/.exec(text);
    var meta = {}, body = text;
    if (m) { try { meta = window.jsyaml ? (jsyaml.load(m[1]) || {}) : {}; } catch (e) { meta = {}; } body = m[2]; }
    return { meta: meta, body: body };
  }

  function listNotes() {
    var c = cacheGet('msra-kb-notes'); if (c) return Promise.resolve(c);
    return fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { if (!r.ok) throw new Error('list ' + r.status); return r.json(); })
      .then(function (files) {
        files = files.filter(function (f) { return f.type === 'file' && /\.md$/i.test(f.name) && !/^(_|readme)/i.test(f.name); });
        return Promise.all(files.map(function (f) {
          return fetch(RAW + 'notes/' + encodeURIComponent(f.name)).then(function (r) { return r.text(); }).then(function (txt) {
            var p = parseNote(txt), m = p.meta;
            return { file: f.name, title: m.title || f.name, summary: m.summary || '', date: fmtDate(m.date) || f.name.slice(0, 10),
                     lang: m.lang || 'en', species: Array.isArray(m.species) ? m.species : [], translation: m.translation || '' };
          }).catch(function () { return null; });
        }));
      })
      .then(function (list) {
        list = list.filter(Boolean).sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; });
        cacheSet('msra-kb-notes', list); return list;
      });
  }
  function loadStudies() {
    var c = cacheGet('msra-kb-studies'); if (c) return Promise.resolve(c);
    return fetch(RAW + 'library/studies.csv')
      .then(function (r) { if (!r.ok) throw new Error('csv ' + r.status); return r.text(); })
      .then(function (txt) {
        var rows = Papa.parse(txt.trim(), { header: true, skipEmptyLines: true }).data.filter(function (r) { return r.title; });
        cacheSet('msra-kb-studies', rows); return rows;
      });
  }
  function failNote(el, what) {
    if (!el) return;
    el.innerHTML = '<p class="kb-state">' + esc(t('Could not reach the knowledge base just now. ', '暂时无法连接开放知识库。')) +
      '<a href="' + HOME + '" target="_blank" rel="noopener">' + esc(t('Browse ' + what + ' on GitHub →', '前往 GitHub 浏览 →')) + '</a></p>';
  }

  // Home page: open-research cards
  var latest = document.getElementById('kb-latest');
  if (latest) {
    listNotes().then(function (list) {
      var en = list.filter(function (n) { return n.lang !== 'zh'; })[0] || list[0];
      var zh = list.filter(function (n) { return n.lang === 'zh'; })[0] || en;
      if (!en) return;
      bi(latest, esc(en.title), esc(zh.title));
      bi(document.getElementById('kb-latest-meta'), 'Latest · ' + esc(en.date), '最新 · ' + esc(zh.date));
    }).catch(function () {});
    loadStudies().then(function (rows) {
      document.getElementById('kb-lib-count').textContent = rows.length;
      document.getElementById('kb-lib-oa').textContent = rows.filter(function (r) { return r.pmc; }).length;
    }).catch(function () {
      document.getElementById('kb-lib-count').textContent = '';
      document.getElementById('kb-lib-oa').textContent = '';
    });
  }

  // Research list page
  var listEl = document.getElementById('kb-notes');
  if (listEl) {
    listNotes().then(function (list) {
      if (!list.length) { listEl.innerHTML = '<p class="kb-state">' + esc(t('No notes yet.', '暂无笔记。')) + '</p>'; return; }
      listEl.innerHTML = list.map(function (n) {
        var tags = (n.lang === 'zh' ? '<i class="chip">中文</i>' : '') + n.species.map(function (s) { return '<i class="chip">' + esc(s) + '</i>'; }).join('');
        return '<a class="post-row" href="' + NOTE + encodeURIComponent(n.file) + '"' + (n.lang === 'zh' ? ' lang="zh-CN"' : '') + '>' +
          '<span class="pr-date">' + esc(n.date) + '</span>' +
          '<span class="pr-main"><b>' + esc(n.title) + '</b><span>' + esc(n.summary) + '</span><span class="pr-tags">' + tags + '</span></span>' +
          '<span class="pr-go" aria-hidden="true">→</span></a>';
      }).join('');
    }).catch(function () { failNote(listEl, 'the notes'); });
  }

  // Single note page
  var noteEl = document.getElementById('kb-note');
  if (noteEl) {
    var wrap = noteEl.querySelector('.post-wrap');
    var state = wrap.querySelector('.kb-state');
    var f = new URLSearchParams(location.search).get('f') || '';
    if (!/^[\w.\-]+\.md$/.test(f)) { failNote(state, 'the notes'); }
    else {
      fetch(RAW + 'notes/' + encodeURIComponent(f))
        .then(function (r) { if (!r.ok) throw new Error('note ' + r.status); return r.text(); })
        .then(function (txt) {
          var p = parseNote(txt), m = p.meta, zh = m.lang === 'zh';
          if (zh) noteEl.setAttribute('lang', 'zh-CN');
          document.title = (m.title || f) + ' · MSRA Research';
          var species = (Array.isArray(m.species) ? m.species : []).map(function (s) { return '<span class="chip">' + esc(s) + '</span>'; }).join('');
          var head = '<div class="label">' + esc(zh ? '研究笔记' : 'Research note') + ' · ' + esc(fmtDate(m.date)) + '</div>' +
            '<h1 class="post-title">' + esc(m.title || f) + '</h1>' +
            (m.summary ? '<p class="lead">' + esc(m.summary) + '</p>' : '') +
            '<div class="post-meta">' + (m.authors ? '<span>' + esc(m.authors) + '</span>' : '') + species +
            (m.translation ? '<a class="chip chip-link" href="' + NOTE + encodeURIComponent(m.translation) + '">' + (zh ? 'English version' : '中文版') + '</a>' : '') +
            '</div>';
          var html = window.DOMPurify ? DOMPurify.sanitize(marked.parse(p.body)) : esc(p.body);
          var foot = '<p class="post-source"><a href="' + BLOB + 'notes/' + encodeURIComponent(f) + '" target="_blank" rel="noopener">' +
            esc(zh ? '在 GitHub 上查看此笔记及修改记录' : 'View this note and its history on GitHub') + '</a> · ' +
            '<a href="' + EDIT + 'notes/' + encodeURIComponent(f) + '" target="_blank" rel="noopener">' + esc(zh ? '建议修改' : 'Suggest an edit') + '</a></p>';
          state.outerHTML = head + '<div class="prose">' + html + '</div>' + foot;
          // Relative links inside a note point at files in the knowledge base.
          noteEl.querySelectorAll('.prose a[href]').forEach(function (a) {
            var h = a.getAttribute('href');
            if (!/^(https?:|mailto:|#)/i.test(h)) a.href = new URL(h, BLOB + 'notes/').href;
            if (/\/library\/(studies\.csv)?$/.test(a.href) && a.href.indexOf(BLOB) === 0) a.href = (cfg.libraryPage || '/research/library/');
            if (/^https?:/i.test(a.href) && a.host !== location.host) { a.target = '_blank'; a.rel = 'noopener'; }
          });
        })
        .catch(function () { failNote(state, 'this note'); });
    }
  }

  // Library page
  var rowsEl = document.getElementById('kb-lib-rows');
  if (rowsEl) {
    loadStudies().then(function (rows) {
      rows.sort(function (a, b) { return (b.year || 0) - (a.year || 0); });
      rowsEl.innerHTML = rows.map(function (s) {
        var tags = String(s.tags || '').split(/\s*;\s*/).filter(Boolean).join(' ');
        var links = (s.pmc ? '<a href="https://pmc.ncbi.nlm.nih.gov/articles/' + esc(s.pmc) + '/" target="_blank" rel="noopener">Full text</a>' : '') +
          (s.pmid ? '<a href="https://pubmed.ncbi.nlm.nih.gov/' + esc(s.pmid) + '/" target="_blank" rel="noopener">PMID ' + esc(s.pmid) + '</a>' : '') +
          (s.doi ? '<a href="https://doi.org/' + esc(s.doi) + '" target="_blank" rel="noopener">DOI</a>' : '');
        var access = s.pmc ? '<span class="pill live">' + esc(t('Open access', '开放获取')) + '</span>' : '<span class="pill">' + esc(t('Subscription', '需订阅')) + '</span>';
        return '<tr data-tags="' + esc(tags) + '"><td class="lib-study"><b>' + esc(s.title) + '</b><span>' + esc(s.authors) + ' · ' + esc(s.journal) + ', ' + esc(s.year) +
          '</span><span class="lib-links">' + links + '</span></td><td>' + esc(s.studied_in) + '</td><td>' + esc(s.topic) + '</td><td>' + access + '</td><td>' + esc(s.relevant_to) + '</td></tr>';
      }).join('');
      var count = document.getElementById('lib-count');
      count.textContent = rows.length;
      var filters = document.querySelectorAll('.filter[data-filter]');
      filters.forEach(function (b) {
        b.addEventListener('click', function () {
          var fl = b.dataset.filter, n = 0;
          filters.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
          rowsEl.querySelectorAll('tr').forEach(function (r) {
            var show = fl === 'all' || (' ' + r.dataset.tags + ' ').indexOf(' ' + fl + ' ') > -1;
            r.hidden = !show; if (show) n++;
          });
          count.textContent = n;
        });
      });
    }).catch(function () {
      rowsEl.innerHTML = '<tr><td colspan="5"></td></tr>';
      failNote(rowsEl.querySelector('td'), 'the library');
    });
  }
})();
