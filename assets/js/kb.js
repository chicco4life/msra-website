/* MSRA Open Research client.
   The research pages read projects live from the knowledge base repository set in _config.yml.
   Each top-level folder there is one project: README.md (the report, in English) and
   sources/ (README.md + sources.csv). Publishing a project there updates this website with no rebuild. */
(function () {
  var M = window.MSRA || {};
  var cfg = M.kb || {};
  var REPO = cfg.repo || 'chicco4life/MSRA-Open-Research';
  var BR = cfg.branch || 'main';
  var RAW = 'https://raw.githubusercontent.com/' + REPO + '/' + BR + '/';
  var API = 'https://api.github.com/repos/' + REPO + '/contents?ref=' + encodeURIComponent(BR);
  var TREE = 'https://github.com/' + REPO + '/tree/' + BR + '/';
  var BLOB = 'https://github.com/' + REPO + '/blob/' + BR + '/';
  var HOME = 'https://github.com/' + REPO;
  var PAGE = (cfg.projectPage || '/research/project/') + '?p=';

  function T(key, en) { return M.t ? M.t(key, en) : en; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function onLang(fn) { document.addEventListener('msra:lang', fn); }

  function cacheGet(k) { try { var v = JSON.parse(sessionStorage.getItem(k)); if (v && Date.now() - v.t < 600000) return v.d; } catch (e) {} return null; }
  function cacheSet(k, d) { try { sessionStorage.setItem(k, JSON.stringify({ t: Date.now(), d: d })); } catch (e) {} }
  function fmtDate(d) { if (!d) return ''; if (d instanceof Date) return d.toISOString().slice(0, 10); return String(d).slice(0, 10); }
  function parseDoc(text) {
    var m = /^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/.exec(text);
    var meta = {}, body = text;
    if (m) { try { meta = window.jsyaml ? (jsyaml.load(m[1]) || {}) : {}; } catch (e) { meta = {}; } body = m[2]; }
    return { meta: meta, body: body };
  }

  function listProjects() {
    var c = cacheGet('msra-kb-projects-v2'); if (c) return Promise.resolve(c);
    return fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { if (!r.ok) throw new Error('list ' + r.status); return r.json(); })
      .then(function (items) {
        var dirs = items.filter(function (f) { return f.type === 'dir' && !/^[._]/.test(f.name); });
        return Promise.all(dirs.map(function (d) {
          return fetch(RAW + encodeURIComponent(d.name) + '/README.md').then(function (r) { if (!r.ok) throw 0; return r.text(); }).then(function (txt) {
            var m = parseDoc(txt).meta;
            return { dir: d.name, title: m.title || d.name, summary: m.summary || '',
                     date: fmtDate(m.date) || d.name.slice(0, 7), species: Array.isArray(m.species) ? m.species : [] };
          }).catch(function () { return null; });
        }));
      })
      .then(function (list) {
        list = list.filter(Boolean).sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; });
        cacheSet('msra-kb-projects-v2', list); return list;
      });
  }
  function loadSources(dir) {
    return fetch(RAW + encodeURIComponent(dir) + '/sources/sources.csv')
      .then(function (r) { if (!r.ok) return ''; return r.text(); })
      .then(function (txt) { return txt ? Papa.parse(txt.trim(), { header: true, skipEmptyLines: true }).data.filter(function (r) { return r.title; }) : []; });
  }
  function loadAllSources() {
    var c = cacheGet('msra-kb-sources-v2'); if (c) return Promise.resolve(c);
    return listProjects().then(function (projects) {
      return Promise.all(projects.map(function (p) { return loadSources(p.dir).then(function (rows) { return { p: p, rows: rows }; }); }));
    }).then(function (sets) {
      var byKey = {}, out = [];
      sets.forEach(function (s) {
        s.rows.forEach(function (r) {
          var key = (r.pmid || r.doi || r.title).toLowerCase();
          if (!byKey[key]) { byKey[key] = Object.assign({}, r, { projects: [] }); out.push(byKey[key]); }
          byKey[key].projects.push({ dir: s.p.dir, title: s.p.title });
        });
      });
      cacheSet('msra-kb-sources-v2', out); return out;
    });
  }
  function failHtml() {
    return '<p class="kb-state">' + esc(T('kb.fail', 'Could not reach the knowledge base just now.')) + ' ' +
      '<a href="' + HOME + '" target="_blank" rel="noopener">' + esc(T('kb.fail_link', 'Browse it on GitHub →')) + '</a></p>';
  }
  function studiesLine(rows) {
    var oa = rows.filter(function (r) { return r.pmc; }).length;
    return rows.length + ' ' + T('kb.studies', 'studies') + ' · ' + oa + ' ' + T('open.free_full_text', 'with free full text');
  }

  /* Home page cards */
  var latest = document.getElementById('kb-latest');
  if (latest) {
    listProjects().then(function (list) {
      var p = list[0]; if (!p) return;
      latest.removeAttribute('data-i18n'); latest.textContent = p.title;
      var meta = document.getElementById('kb-latest-meta');
      function paint() { meta.textContent = T('kb.published', 'Published') + ' ' + p.date; }
      meta.removeAttribute('data-i18n'); paint(); onLang(paint);
      latest.closest('a').href = PAGE + encodeURIComponent(p.dir);
    }).catch(function () {});
    loadAllSources().then(function (rows) {
      document.getElementById('kb-lib-count').textContent = rows.length;
      document.getElementById('kb-lib-oa').textContent = rows.filter(function (r) { return r.pmc; }).length;
    }).catch(function () {
      document.getElementById('kb-lib-count').textContent = '';
      document.getElementById('kb-lib-oa').textContent = '';
    });
  }

  /* Research projects: one card per project, one tap to the full report */
  var listEl = document.getElementById('kb-notes');
  if (listEl) {
    var data = null;
    var render = function () {
      if (!data) return;
      if (!data.list.length) { listEl.innerHTML = '<p class="kb-state">' + esc(T('kb.none', 'No projects yet.')) + '</p>'; return; }
      listEl.innerHTML = data.list.map(function (p) {
        var tags = p.species.map(function (s) { return '<i class="chip">' + esc(s) + '</i>'; }).join('');
        var rows = data.sources[p.dir] || [];
        return '<a class="rcard" href="' + PAGE + encodeURIComponent(p.dir) + '">' +
          '<span class="rc-top"><span class="rc-date">' + esc(p.date) + '</span><span class="rc-tags">' + tags + '</span></span>' +
          '<b class="rc-title">' + esc(p.title) + '</b>' +
          '<span class="rc-sum">' + esc(p.summary) + '</span>' +
          '<span class="rc-foot"><span class="rc-src">' + (rows.length ? esc(studiesLine(rows)) : '') + '</span>' +
          '<span class="rc-go">' + esc(T('kb.read', 'Read the report')) + ' →</span></span></a>';
      }).join('');
    };
    listProjects().then(function (list) {
      data = { list: list, sources: {} }; render();
      list.forEach(function (p) { loadSources(p.dir).then(function (rows) { data.sources[p.dir] = rows; render(); }).catch(function () {}); });
      onLang(render);
    }).catch(function () { listEl.innerHTML = failHtml(); });
  }

  /* Single project page: the report, then the way to every paper it used */
  var projEl = document.getElementById('kb-project');
  if (projEl) {
    var wrap = projEl.querySelector('.post-wrap');
    var state = projEl.querySelector('.kb-state');
    var dir = new URLSearchParams(location.search).get('p') || '';
    if (!/^[\w.\-]+$/.test(dir)) { state.outerHTML = failHtml(); }
    else {
      var base = RAW + encodeURIComponent(dir) + '/';
      var srcUrl = TREE + encodeURIComponent(dir) + '/sources';
      var holder = document.createElement('div');
      var proj = null;
      var renderProject = function () {
        if (!proj) return;
        var m = proj.meta, rows = proj.sources;
        var oa = rows.filter(function (r) { return r.pmc; }).length;
        var species = (Array.isArray(m.species) ? m.species : []).map(function (s) { return '<span class="chip">' + esc(s) + '</span>'; }).join('');
        var langNote = M.lang && M.lang() !== 'en' ? '<p class="lang-note">' + esc(T('kb.english_only', 'This report is published in English.')) + '</p>' : '';
        var head = '<div class="label">' + esc(T('kb.project', 'Research project')) + ' · ' + esc(fmtDate(m.date)) + '</div>' +
          '<h1 class="post-title">' + esc(m.title || dir) + '</h1>' + (m.summary ? '<p class="lead">' + esc(m.summary) + '</p>' : '') +
          '<div class="post-meta">' + (m.authors ? '<span>' + esc(m.authors) + '</span>' : '') + species +
          (rows.length ? '<a class="chip chip-link" href="#sources">' + esc(rows.length + ' ' + T('kb.studies', 'studies')) + '</a>' : '') + '</div>' + langNote;
        var srcPanel = '<aside class="src-panel" id="sources">' +
          '<div class="sp-text"><span class="label">' + esc(T('kb.src_label', 'The scientific publications')) + '</span>' +
          '<h2>' + esc(T('kb.src_h', 'Read every study this report used')) + '</h2>' +
          '<p>' + esc(T('kb.src_p', 'All the papers behind this report are listed in its sources folder on GitHub, with links to PubMed and to the free full text where one exists.')) + '</p>' +
          '<div class="sp-nums"><span><b>' + rows.length + '</b> ' + esc(T('kb.studies', 'studies')) + '</span><span><b>' + oa + '</b> ' + esc(T('open.free_full_text', 'with free full text')) + '</span></div></div>' +
          '<a class="btn btn-solid" href="' + srcUrl + '" target="_blank" rel="noopener">' +
          '<svg width="17" height="17" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>' +
          esc(T('kb.src_btn', 'Open the sources on GitHub')) + '</a></aside>';
        var foot = '<p class="post-source"><a href="' + TREE + encodeURIComponent(dir) + '" target="_blank" rel="noopener">' +
          esc(T('kb.history', 'View this project and its history on GitHub')) + '</a> · ' +
          '<a href="' + HOME + '/issues/new?title=' + encodeURIComponent('Correction: ' + (m.title || dir)) + '" target="_blank" rel="noopener">' + esc(T('kb.correct', 'Suggest a correction or a source')) + '</a></p>';
        holder.innerHTML = head + '<div class="prose" lang="en">' + proj.html + '</div>' + srcPanel + foot;
        // Relative links inside a report point at files in the project folder on GitHub.
        holder.querySelectorAll('.prose a[href]').forEach(function (a) {
          var h = a.getAttribute('href');
          if (!/^(https?:|mailto:|#)/i.test(h)) a.href = new URL(h, BLOB + dir + '/').href;
          if (/^https?:/i.test(a.href) && a.host !== location.host) { a.target = '_blank'; a.rel = 'noopener'; }
        });
        document.title = (m.title || dir) + ' · MSRA Open Research';
      };
      Promise.all([fetch(base + 'README.md').then(function (r) { if (!r.ok) throw new Error(); return r.text(); }),
                   loadSources(dir).catch(function () { return []; })])
        .then(function (res) {
          var d = parseDoc(res[0]);
          // The report repeats its title, summary and sources link at the top for GitHub readers; drop them here.
          var body = d.body.replace(/^\s*# [^\n]*\n+/, '').replace(/^\*[^\n]*\*\s*\n+/, '').replace(/^\[[^\n]*\]\([^)\n]*\)[^\n]*\n+/, '');
          proj = { meta: d.meta, sources: res[1], html: window.DOMPurify ? DOMPurify.sanitize(marked.parse(body)) : esc(body) };
          state.replaceWith(holder);
          renderProject(); onLang(renderProject);
        })
        .catch(function () { state.outerHTML = failHtml(); });
    }
  }

  /* Research library: every source cited across all projects */
  var rowsEl = document.getElementById('kb-lib-rows');
  if (rowsEl) {
    var all = null, filter = 'all';
    var renderLib = function () {
      if (!all) return;
      var n = 0;
      rowsEl.innerHTML = all.map(function (s) {
        var tags = String(s.tags || '').split(/\s*;\s*/).filter(Boolean);
        var show = filter === 'all' || tags.indexOf(filter) > -1;
        if (show) n++;
        var links = (s.pmc ? '<a href="https://pmc.ncbi.nlm.nih.gov/articles/' + esc(s.pmc) + '/" target="_blank" rel="noopener">' + esc(T('lib.full_text', 'Full text')) + '</a>' : '') +
          (s.pmid ? '<a href="https://pubmed.ncbi.nlm.nih.gov/' + esc(s.pmid) + '/" target="_blank" rel="noopener">PubMed ' + esc(s.pmid) + '</a>' : '') +
          (s.doi ? '<a href="https://doi.org/' + esc(s.doi) + '" target="_blank" rel="noopener">DOI</a>' : '');
        var access = s.pmc ? '<span class="pill live">' + esc(T('lib.open_access', 'Open access')) + '</span>' : '<span class="pill">' + esc(T('lib.subscription', 'Subscription')) + '</span>';
        var projects = s.projects.map(function (p) { return '<a href="' + PAGE + encodeURIComponent(p.dir) + '">' + esc(p.title) + '</a>'; }).join('<br>');
        return '<tr' + (show ? '' : ' hidden') + '><td class="lib-study"><b>' + esc(s.title) + '</b><span>' + esc(s.authors) + ' · ' + esc(s.journal) + ', ' + esc(s.year) +
          '</span><span class="lib-links">' + links + '</span></td><td>' + esc(s.studied_in) + '</td><td>' + esc(s.topic) + '</td><td>' + access + '</td><td class="lib-proj">' + projects + '</td></tr>';
      }).join('');
      document.getElementById('lib-count').textContent = n;
    };
    loadAllSources().then(function (rows) {
      all = rows.sort(function (a, b) { return (b.year || 0) - (a.year || 0); });
      renderLib(); onLang(renderLib);
      var filters = document.querySelectorAll('.filter[data-filter]');
      filters.forEach(function (b) {
        b.addEventListener('click', function () {
          filter = b.dataset.filter;
          filters.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
          renderLib();
        });
      });
    }).catch(function () {
      rowsEl.innerHTML = '<tr><td colspan="5">' + failHtml() + '</td></tr>';
    });
  }
})();
