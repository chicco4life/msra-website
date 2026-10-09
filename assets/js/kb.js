/* MSRA Open Research client.
   The research pages read projects live from the knowledge base repository set in _config.yml.
   Each top-level folder there is one project: README.md (report), optional README.zh.md,
   and sources/sources.csv. Publishing a project there updates this website with no rebuild. */
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

  function cn() { return document.documentElement.lang === 'zh-CN'; }
  function t(en, zh) { return cn() ? zh : en; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  // Bilingual live content: keeps the EN / 中文 toggle working.
  function bi(el, en, zh) { if (!el) return; el.dataset.en = en; el.dataset.cn = zh; el.innerHTML = cn() ? zh : en; }

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
    var c = cacheGet('msra-kb-projects'); if (c) return Promise.resolve(c);
    return fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { if (!r.ok) throw new Error('list ' + r.status); return r.json(); })
      .then(function (items) {
        var dirs = items.filter(function (f) { return f.type === 'dir' && !/^[._]/.test(f.name); });
        return Promise.all(dirs.map(function (d) {
          return fetch(RAW + encodeURIComponent(d.name) + '/README.md').then(function (r) { if (!r.ok) throw 0; return r.text(); }).then(function (txt) {
            var m = parseDoc(txt).meta;
            return { dir: d.name, title: m.title || d.name, title_zh: m.title_zh || m.title || d.name,
                     summary: m.summary || '', summary_zh: m.summary_zh || m.summary || '',
                     date: fmtDate(m.date) || d.name.slice(0, 7), species: Array.isArray(m.species) ? m.species : [] };
          }).catch(function () { return null; });
        }));
      })
      .then(function (list) {
        list = list.filter(Boolean).sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; });
        cacheSet('msra-kb-projects', list); return list;
      });
  }
  function loadSources(dir) {
    return fetch(RAW + encodeURIComponent(dir) + '/sources/sources.csv')
      .then(function (r) { if (!r.ok) return ''; return r.text(); })
      .then(function (txt) { return txt ? Papa.parse(txt.trim(), { header: true, skipEmptyLines: true }).data.filter(function (r) { return r.title; }) : []; });
  }
  function loadAllSources() {
    var c = cacheGet('msra-kb-sources'); if (c) return Promise.resolve(c);
    return listProjects().then(function (projects) {
      return Promise.all(projects.map(function (p) { return loadSources(p.dir).then(function (rows) { return { p: p, rows: rows }; }); }));
    }).then(function (sets) {
      var byKey = {}, out = [];
      sets.forEach(function (s) {
        s.rows.forEach(function (r) {
          var key = (r.pmid || r.doi || r.title).toLowerCase();
          if (!byKey[key]) { byKey[key] = Object.assign({}, r, { projects: [] }); out.push(byKey[key]); }
          byKey[key].projects.push({ dir: s.p.dir, title: s.p.title, title_zh: s.p.title_zh });
        });
      });
      cacheSet('msra-kb-sources', out); return out;
    });
  }
  function fail(el, what) {
    if (!el) return;
    el.innerHTML = '<p class="kb-state">' + esc(t('Could not reach the knowledge base just now. ', '暂时无法连接开放知识库。')) +
      '<a href="' + HOME + '" target="_blank" rel="noopener">' + esc(t('Browse ' + what + ' on GitHub →', '前往 GitHub 浏览 →')) + '</a></p>';
  }

  // Home page cards
  var latest = document.getElementById('kb-latest');
  if (latest) {
    listProjects().then(function (list) {
      var p = list[0]; if (!p) return;
      bi(latest, esc(p.title), esc(p.title_zh));
      bi(document.getElementById('kb-latest-meta'), 'Published ' + esc(p.date), '发布于 ' + esc(p.date));
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

  // Research projects list
  var listEl = document.getElementById('kb-notes');
  if (listEl) {
    listProjects().then(function (list) {
      if (!list.length) { listEl.innerHTML = '<p class="kb-state">' + esc(t('No projects yet.', '暂无研究项目。')) + '</p>'; return; }
      listEl.innerHTML = list.map(function (p) {
        var tags = p.species.map(function (s) { return '<i class="chip">' + esc(s) + '</i>'; }).join('');
        return '<a class="post-row" href="' + PAGE + encodeURIComponent(p.dir) + '">' +
          '<span class="pr-date">' + esc(p.date) + '</span>' +
          '<span class="pr-main"><b data-kb-en="' + esc(p.title) + '" data-kb-cn="' + esc(p.title_zh) + '">' + esc(cn() ? p.title_zh : p.title) + '</b>' +
          '<span data-kb-en="' + esc(p.summary) + '" data-kb-cn="' + esc(p.summary_zh) + '">' + esc(cn() ? p.summary_zh : p.summary) + '</span>' +
          '<span class="pr-tags">' + tags + '</span></span><span class="pr-go" aria-hidden="true">→</span></a>';
      }).join('');
      // follow the language toggle
      ['lang-en', 'lang-cn'].forEach(function (id) {
        var b = document.getElementById(id); if (!b) return;
        b.addEventListener('click', function () {
          listEl.querySelectorAll('[data-kb-en]').forEach(function (el) { el.textContent = id === 'lang-cn' ? el.dataset.kbCn : el.dataset.kbEn; });
        });
      });
    }).catch(function () { fail(listEl, 'the projects'); });
  }

  // Single project page
  var projEl = document.getElementById('kb-project');
  if (projEl) {
    var state = projEl.querySelector('.kb-state');
    var q = new URLSearchParams(location.search);
    var dir = q.get('p') || '';
    var wantZh = q.get('lang') === 'zh' || (q.get('lang') !== 'en' && cn());
    if (!/^[\w.\-]+$/.test(dir)) { fail(state, 'the projects'); }
    else {
      var base = RAW + encodeURIComponent(dir) + '/';
      var getReport = wantZh
        ? fetch(base + 'README.zh.md').then(function (r) { if (!r.ok) throw 0; return r.text().then(function (x) { return { txt: x, zh: true }; }); })
            .catch(function () { return fetch(base + 'README.md').then(function (r) { if (!r.ok) throw new Error(); return r.text().then(function (x) { return { txt: x, zh: false }; }); }); })
        : fetch(base + 'README.md').then(function (r) { if (!r.ok) throw new Error(); return r.text().then(function (x) { return { txt: x, zh: false }; }); });
      Promise.all([getReport, loadSources(dir).catch(function () { return []; }),
                   fetch(base + 'README.zh.md', { method: 'HEAD' }).then(function (r) { return r.ok; }).catch(function () { return false; })])
        .then(function (res) {
          var rep = res[0], sources = res[1], hasZh = res[2];
          var d = parseDoc(rep.txt), m = d.meta, zh = rep.zh;
          if (zh) projEl.setAttribute('lang', 'zh-CN'); else projEl.removeAttribute('lang');
          var title = zh ? (m.title_zh || m.title) : m.title;
          var summary = zh ? (m.summary_zh || m.summary) : m.summary;
          document.title = (title || dir) + ' · MSRA Open Research';
          // The report repeats its title, summary and language links at the top for GitHub readers; drop them here.
          var body = d.body.replace(/^\s*# [^\n]*\n+/, '').replace(/^\*[^\n]*\*\s*\n+/, '').replace(/^\[[^\n]*\]\([^)\n]*\)[^\n]*\n+/, '');
          var species = (Array.isArray(m.species) ? m.species : []).map(function (s) { return '<span class="chip">' + esc(s) + '</span>'; }).join('');
          var other = hasZh ? '<a class="chip chip-link" href="' + PAGE + encodeURIComponent(dir) + '&lang=' + (zh ? 'en' : 'zh') + '">' + (zh ? 'English version' : '中文版') + '</a>' : '';
          var oa = sources.filter(function (r) { return r.pmc; }).length;
          var head = '<div class="label">' + esc(zh ? '研究项目' : 'Research project') + ' · ' + esc(fmtDate(m.date)) + '</div>' +
            '<h1 class="post-title">' + esc(title || dir) + '</h1>' + (summary ? '<p class="lead">' + esc(summary) + '</p>' : '') +
            '<div class="post-meta">' + (m.authors ? '<span>' + esc(m.authors) + '</span>' : '') + species + other + '</div>';
          var srcBox = '<aside class="src-box"><div><span class="label">' + esc(zh ? '本项目的文献' : 'Sources for this project') + '</span>' +
            '<b>' + sources.length + ' ' + esc(zh ? '项研究' : 'studies') + '</b><span>' + oa + ' ' + esc(zh ? '项可免费阅读全文' : 'with free full text') + '</span></div>' +
            '<a class="btn btn-line btn-sm" href="' + TREE + encodeURIComponent(dir) + '/sources" target="_blank" rel="noopener">' + esc(zh ? '查看文献文件夹' : 'Open the sources folder') + '</a></aside>';
          var html = window.DOMPurify ? DOMPurify.sanitize(marked.parse(body)) : esc(body);
          var foot = '<p class="post-source"><a href="' + TREE + encodeURIComponent(dir) + '" target="_blank" rel="noopener">' +
            esc(zh ? '在 GitHub 上查看此项目及修改记录' : 'View this project and its history on GitHub') + '</a> · ' +
            '<a href="' + HOME + '/issues/new?title=' + encodeURIComponent('Correction: ' + (m.title || dir)) + '" target="_blank" rel="noopener">' + esc(zh ? '指出错误或补充文献' : 'Suggest a correction or a source') + '</a></p>';
          state.outerHTML = head + srcBox + '<div class="prose">' + html + '</div>' + foot;
          // Relative links inside a report point at files in the project folder on GitHub.
          projEl.querySelectorAll('.prose a[href]').forEach(function (a) {
            var h = a.getAttribute('href');
            if (!/^(https?:|mailto:|#)/i.test(h)) a.href = new URL(h, BLOB + dir + '/').href;
            if (/^https?:/i.test(a.href) && a.host !== location.host) { a.target = '_blank'; a.rel = 'noopener'; }
          });
        })
        .catch(function () { fail(state, 'this project'); });
    }
  }

  // Research library: every source cited across all projects
  var rowsEl = document.getElementById('kb-lib-rows');
  if (rowsEl) {
    loadAllSources().then(function (rows) {
      rows.sort(function (a, b) { return (b.year || 0) - (a.year || 0); });
      rowsEl.innerHTML = rows.map(function (s) {
        var tags = String(s.tags || '').split(/\s*;\s*/).filter(Boolean).join(' ');
        var links = (s.pmc ? '<a href="https://pmc.ncbi.nlm.nih.gov/articles/' + esc(s.pmc) + '/" target="_blank" rel="noopener">Full text</a>' : '') +
          (s.pmid ? '<a href="https://pubmed.ncbi.nlm.nih.gov/' + esc(s.pmid) + '/" target="_blank" rel="noopener">PMID ' + esc(s.pmid) + '</a>' : '') +
          (s.doi ? '<a href="https://doi.org/' + esc(s.doi) + '" target="_blank" rel="noopener">DOI</a>' : '');
        var access = s.pmc ? '<span class="pill live">' + esc(t('Open access', '开放获取')) + '</span>' : '<span class="pill">' + esc(t('Subscription', '需订阅')) + '</span>';
        var projects = s.projects.map(function (p) { return '<a href="' + PAGE + encodeURIComponent(p.dir) + '">' + esc(cn() ? p.title_zh : p.title) + '</a>'; }).join('<br>');
        return '<tr data-tags="' + esc(tags) + '"><td class="lib-study"><b>' + esc(s.title) + '</b><span>' + esc(s.authors) + ' · ' + esc(s.journal) + ', ' + esc(s.year) +
          '</span><span class="lib-links">' + links + '</span></td><td>' + esc(s.studied_in) + '</td><td>' + esc(s.topic) + '</td><td>' + access + '</td><td class="lib-proj">' + projects + '</td></tr>';
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
      fail(rowsEl.querySelector('td'), 'the sources');
    });
  }
})();
