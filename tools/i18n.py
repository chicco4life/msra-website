#!/usr/bin/env python3
"""Collect the site's English text and check the translations.

Usage (from the repository folder, after `bundle exec jekyll build`):
    python3 tools/i18n.py

It reads every built page in _site/ plus assets/js/*.js, writes assets/i18n/en.json
(the English source text for every key), and lists, for each language file
(ja, nl, es, zh), the keys that are missing or no longer used.
A missing key is not an error on the live site: that text simply shows in English.
"""
import json, pathlib, re, sys
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE, OUT = ROOT / '_site', ROOT / 'assets' / 'i18n'
LANGS = ['ja', 'nl', 'es', 'zh']


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def collect():
    en, clash = {}, []
    for f in sorted(SITE.rglob('*.html')):
        soup = BeautifulSoup(f.read_text(encoding='utf-8'), 'html.parser')
        for el in soup.select('[data-i18n]'):
            k, v = el['data-i18n'], norm(el.decode_contents())
            if k in en and en[k] != v:
                clash.append((k, f.relative_to(SITE)))
            en.setdefault(k, v)
        for el in soup.select('[data-i18n-attr]'):
            for pair in el['data-i18n-attr'].split(';'):
                if ':' in pair:
                    attr, k = [x.strip() for x in pair.split(':', 1)]
                    en.setdefault(k, el.get(attr, ''))
    # strings used from JavaScript: T('key', 'English') / t('key', 'English')
    pat = re.compile(r"""\b[Tt]\(\s*'([\w.\-]+)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)""")
    for f in sorted((ROOT / 'assets' / 'js').glob('*.js')):
        for k, v in pat.findall(f.read_text(encoding='utf-8')):
            en.setdefault(k, v.replace("\\'", "'"))
    return dict(sorted(en.items())), clash


def main():
    if not SITE.exists():
        sys.exit('Build the site first: bundle exec jekyll build')
    en, clash = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'en.json').write_text(json.dumps(en, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'en.json: {len(en)} strings')
    for k, f in clash:
        print(f'  ! key "{k}" has different English text in {f}')
    for lang in LANGS:
        p = OUT / f'{lang}.json'
        tr = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        missing = [k for k in en if not tr.get(k)]
        unused = [k for k in tr if k not in en]
        print(f'{lang}.json: {len(tr)} strings, {len(missing)} missing, {len(unused)} unused')
        for k in missing[:40]:
            print(f'  missing  {k}')
        for k in unused[:20]:
            print(f'  unused   {k}')


if __name__ == '__main__':
    main()
