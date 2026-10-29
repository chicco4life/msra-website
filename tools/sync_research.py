#!/usr/bin/env python3
"""Copy the research projects from MSRA-Open-Research into this site, so every report is a real HTML page.

Initial HTML keeps content accessible without JavaScript and predictable for crawlers and retrieval tools.
This script writes, for each project folder in the knowledge base:
    _research/<folder>.md     the report, rendered by Jekyll at /research/<folder>/
and one data file for the research hub, the library and the home page:
    _data/research.json       project list, every source, totals

Usage (from the repository folder):
    python3 tools/sync_research.py                      # downloads the knowledge base from GitHub
    python3 tools/sync_research.py --kb ../MSRA-Open-Research   # uses a local checkout
Then commit _research/ and _data/research.json. No extra packages needed.
"""
import argparse, csv, io, json, pathlib, re, sys, tarfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = 'chicco4life/MSRA-Open-Research'
BRANCH = 'main'
OUT_DOCS = ROOT / '_research'
OUT_DATA = ROOT / '_data' / 'research.json'
FOLDER = re.compile(r'^\d{4}-\d{2}-[a-z0-9-]+$')
FIELDS = ['ref', 'title', 'authors', 'journal', 'year', 'pmid', 'doi', 'pmc', 'studied_in', 'tags', 'topic']


def read_kb(path):
    """Return {folder: {'report': text, 'csv': text}} from a local checkout or the GitHub tarball."""
    files = {}
    if path:
        base = pathlib.Path(path)
        for d in sorted(p for p in base.iterdir() if p.is_dir() and FOLDER.match(p.name)):
            rep = d / 'report.md' if (d / 'report.md').exists() else d / 'README.md'
            src = d / 'sources' / 'sources.csv'
            files[d.name] = {'report': rep.read_text(encoding='utf-8'),
                             'csv': src.read_text(encoding='utf-8') if src.exists() else ''}
        return files
    url = f'https://codeload.github.com/{REPO}/tar.gz/refs/heads/{BRANCH}'
    with urllib.request.urlopen(url, timeout=60) as r:
        tar = tarfile.open(fileobj=io.BytesIO(r.read()), mode='r:gz')
    for m in tar.getmembers():
        parts = m.name.split('/')[1:]  # drop the "<repo>-<branch>/" prefix
        if not m.isfile() or not parts or not FOLDER.match(parts[0]):
            continue
        rel = '/'.join(parts[1:])
        if rel in ('report.md', 'README.md', 'sources/sources.csv'):
            text = tar.extractfile(m).read().decode('utf-8')
            files.setdefault(parts[0], {})[rel] = text
    out = {}
    for d, f in sorted(files.items()):
        if 'report.md' in f or 'README.md' in f:
            out[d] = {'report': f.get('report.md') or f['README.md'], 'csv': f.get('sources/sources.csv', '')}
    return out


def front_matter(text):
    """Split '---' front matter from the body. Handles the simple keys our reports use."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        km = re.match(r'^([A-Za-z_]+):\s*(.*)$', line)
        if not km:
            continue
        k, v = km.group(1), km.group(2).strip()
        if not v.startswith(('"', "'")):
            v = re.sub(r'\s+#.*$', '', v)  # trailing comment on an unquoted value
        if v.startswith('[') and v.endswith(']'):
            meta[k] = [x.strip().strip('"\'') for x in v[1:-1].split(',') if x.strip()]
        elif len(v) > 1 and v[0] == v[-1] and v[0] in '"\'':
            meta[k] = v[1:-1].replace('\\"', '"')
        else:
            meta[k] = v
    return meta, m.group(2)


def clean_body(body, folder):
    # The report repeats its title and summary at the top for GitHub readers; the page shows them in its header.
    body = re.sub(r'^\s*# [^\n]*\n+', '', body)
    body = re.sub(r'^\*[^\n]*\*\s*\n+', '', body)
    body = re.sub(r'^\[[^\n]*\]\([^)\n]*\)[^\n]*\n+', '', body)
    # Relative links point at files in the project folder on GitHub.
    def fix(m):
        href = m.group(2)
        if re.match(r'^(https?:|mailto:|#)', href):
            return m.group(0)
        kind = 'tree' if href.endswith('/') else 'blob'
        return f'{m.group(1)}(https://github.com/{REPO}/{kind}/{BRANCH}/{folder}/{href})'
    body = re.sub(r'(\[[^\]]*\])\(([^)\s]+)\)', fix, body)
    return body.strip() + '\n'


def q(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kb', help='path to a local MSRA-Open-Research checkout (default: download from GitHub)')
    args = ap.parse_args()
    # Locally audited corrections must be reconciled into their source before sync.
    protected = [p for p in OUT_DOCS.glob('*.md') if front_matter(p.read_text())[0].get('frontend_edited') in (True, 'true')]
    if protected:
        sys.exit('Local editorial report corrections need source reconciliation before sync: ' + ', '.join(p.name for p in protected))
    kb = read_kb(args.kb)
    if not kb:
        sys.exit('No research projects found; nothing written.')

    OUT_DOCS.mkdir(exist_ok=True)
    projects, library, by_key = [], [], {}
    for folder, f in kb.items():
        meta, body = front_matter(f['report'])
        rows = [r for r in csv.DictReader(io.StringIO(f['csv'])) if r.get('title')] if f['csv'] else []
        title = meta.get('title') or folder
        date = str(meta.get('date') or folder[:7])[:10]
        updated = str(meta.get('updated') or date)[:10]
        species = meta.get('species') or []
        if isinstance(species, str):
            species = [species]
        free = sum(1 for r in rows if r.get('pmc'))
        p = {'dir': folder, 'title': title, 'label': meta.get('label') or title, 'date': date, 'updated': updated,
             'summary': meta.get('summary', ''), 'authors': meta.get('authors', ''), 'species': species,
             'url': f'/research/{folder}/', 'studies': len(rows), 'free': free}
        projects.append(p)
        for r in rows:
            key = (r.get('pmid') or r.get('doi') or r['title']).lower()
            if key not in by_key:
                s = {k: (r.get(k) or '').strip() for k in FIELDS if k != 'ref'}
                s['tags'] = [t.strip() for t in s['tags'].split(';') if t.strip()]
                s['projects'] = []
                by_key[key] = s
                library.append(s)
            by_key[key]['projects'].append({'dir': folder, 'title': title, 'url': p['url']})

        body = clean_body(body, folder).replace('{% endraw %}', '{% endraw %}{{ "{% endraw %}" }}{% raw %}')
        doc = ['---', f'dir: {q(folder)}', f'title: {q(title)}', f'label: {q(p["label"])}', f'date: {date}',
               f'last_modified_at: {updated}', f'summary: {q(p["summary"])}', f'description: {q(p["summary"])}',
               f'authors: {q(p["authors"])}', f'species: {q(species)}', 'excerpt_separator: ""', '---',
               '<!-- Generated by tools/sync_research.py from the MSRA-Open-Research knowledge base. Edit the report there, not here. -->',
               '{% raw %}', body.rstrip(), '{% endraw %}', '']
        (OUT_DOCS / f'{folder}.md').write_text('\n'.join(doc), encoding='utf-8')

    for old in OUT_DOCS.glob('*.md'):  # projects removed from the knowledge base
        if old.stem not in kb:
            old.unlink()
            print(f'removed {old.relative_to(ROOT)}')

    projects.sort(key=lambda p: p['date'], reverse=True)
    library.sort(key=lambda s: int(s['year']) if s['year'].isdigit() else 0, reverse=True)
    data = {'source': f'https://github.com/{REPO}', 'projects': projects, 'library': library,
            'totals': {'projects': len(projects), 'studies': len(library), 'free': sum(1 for s in library if s['pmc'])}}
    OUT_DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    t = data['totals']
    print(f"{t['projects']} projects, {t['studies']} unique studies ({t['free']} free full text) -> _research/, _data/research.json")


if __name__ == '__main__':
    main()
