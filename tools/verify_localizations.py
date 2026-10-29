#!/usr/bin/env python3
"""Check saved translation drafts and, optionally, their isolated static preview.

    python3 tools/verify_localizations.py
    python3 tools/verify_localizations.py --built /private/tmp/msra-library-preview-locales
    python3 tools/verify_localizations.py --complete

Draft, missing, review and release states are counted separately. This tool does
not assess translation quality or clinical correctness, and does not publish.
"""
import argparse
from collections import Counter
from html.parser import HTMLParser
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit, parse_qs
import xml.etree.ElementTree as ET

from prepare_localizations import ROOT, build_registry, read_documents

ORIGIN = 'https://msralab.com'


def normalized(text):
    return ' '.join(text.split())


def external_urls(body):
    """Original bibliography/third-party targets, including multiplicity."""
    links = re.findall(r'\]\(\s*(https?://[^\s)]+)', body)
    links += re.findall(r'\bhref\s*=\s*[\"\'](https?://[^\"\']+)', body)
    return Counter(link for link in links if urlsplit(link).netloc != urlsplit(ORIGIN).netloc)


def explicit_ids(body):
    return set(re.findall(r'(?<![\w:-])(?:id|name)\s*=\s*[\"\']([^\"\']+)', body))


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.canonicals, self.alternates, self.links = [], [], []
        self.metadata, self.ids, self.h1s, self.schema = {}, [], [], []
        self.requests, self.forms = [], []
        self.body_links, self.body_ids = [], []
        self.equivalents = []
        self._stack, self._h1, self._script, self._body_depth = [], None, None, None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)
        if tag == 'html': self.lang = attrs.get('lang')
        if 'id' in attrs: self.ids.append(attrs['id'])
        if 'data-localized-body' in attrs: self._body_depth = len(self._stack)
        in_body = self._body_depth is not None
        if in_body and 'id' in attrs: self.body_ids.append(attrs['id'])
        if tag == 'h1': self._h1 = []
        if tag == 'meta': self.metadata[attrs.get('name') or attrs.get('property')] = attrs.get('content', '')
        if tag == 'link':
            if 'canonical' in attrs.get('rel', '').split(): self.canonicals.append(attrs.get('href'))
            if attrs.get('hreflang'): self.alternates.append(attrs)
            if 'stylesheet' in attrs.get('rel', '').split(): self.requests.append(attrs.get('href', ''))
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs)
            if in_body: self.body_links.append(attrs)
            if 'data-equivalent-key' in attrs: self.equivalents.append(attrs)
        if tag == 'form': self.forms.append(attrs)
        if tag in ('script', 'iframe', 'img', 'embed') and attrs.get('src'): self.requests.append(attrs['src'])
        if tag == 'script':
            self._script = {'type': attrs.get('type'), 'src': attrs.get('src'), 'parts': []}
        if tag in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self._stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'h1' and self._h1 is not None:
            self.h1s.append(normalized(''.join(self._h1)))
            self._h1 = None
        if tag == 'script' and self._script is not None:
            script = self._script
            text = ''.join(script['parts'])
            if script['type'] == 'application/ld+json': self.schema.append(json.loads(text))
            elif not script['src'] and script['type'] != 'application/json':
                expected_ga = "window.dataLayer=window.dataLayer||[];functiongtag(){dataLayer.push(arguments);}gtag('js',newDate());gtag('config',\"G-R7JTFRCH80\");"
                assert not text.strip() or re.sub(r'\s+', '', text) == expected_ga, 'Unexpected executable inline script on localized draft'
            self._script = None
        if tag in self._stack:
            index = len(self._stack)-1-self._stack[::-1].index(tag)
            self._stack = self._stack[:index]
            if self._body_depth is not None and len(self._stack) < self._body_depth:
                self._body_depth = None

    def handle_data(self, data):
        if self._h1 is not None: self._h1.append(data)
        if self._script is not None: self._script['parts'].append(data)


def output_path(built, route):
    return built/route.lstrip('/')/('index.html') if route.endswith('/') else built/route.lstrip('/')


def source_checks(root, registry, documents):
    by_file = {doc['file']: doc for doc in documents}
    draft_count = 0
    for source in registry['resources'].values():
        original = by_file[source['source_file']]['body']
        original_ids = explicit_ids(original)
        for locale, variant in source['variants'].items():
            if locale == 'en': continue
            draft_count += 1
            doc = by_file[variant['file']]
            body, meta = doc['body'], doc['meta']
            if source['scope'] == 'full-resource':
                assert external_urls(body) == external_urls(original), f'{variant["file"]}: original external source URLs/counts changed'
                assert original_ids <= explicit_ids(body), f'{variant["file"]}: missing stable source anchors {sorted(original_ids-explicit_ids(body))}'
                assert normalized(body) != normalized(original), f'{variant["file"]}: English source copied without translation'
                headings = lambda text: Counter(re.findall(r'^(#{2,6})\s+\S', text, re.M))
                assert headings(body) == headings(original), f'{variant["file"]}: source heading structure changed or truncated'
                table_rows = lambda text: sum(bool(re.match(r'^\s*\|.*\|\s*$', line)) for line in text.splitlines())
                assert table_rows(body) == table_rows(original), f'{variant["file"]}: source table rows changed or truncated'
                citations = lambda text: Counter(re.findall(r'\[(\d+(?:\s*[,–-]\s*\d+)*)\]', text))
                assert citations(body) == citations(original), f'{variant["file"]}: numbered source citations changed'
                if source['translation_key'] == 'S00':
                    titles = lambda text: re.findall(r'^###\s+(\d+\.\s+.+?)\s*$', text, re.M)
                    assert titles(body) == titles(original), f'{variant["file"]}: original publication titles/numbering changed'
            assert source['kind'] == 'marketing' or not re.search(r'<h1(?:\s|>)', body, re.I), f'{variant["file"]}: layout owns the sole H1'
            assert not re.search(r'<(?:script|iframe)(?:\s|>)', body, re.I) and (source['kind'] == 'marketing' or not re.search(r'<form(?:\s|>)', body, re.I)), f'{variant["file"]}: executable/embed/provider form in local body'
            assert not meta.get('datePublished') and not meta.get('dateModified'), f'{variant["file"]}: draft publication/revision date asserted'
    return draft_count


def built_checks(root, built, registry, documents):
    documents = {doc['file']: doc for doc in documents}
    cache, checked, fragment_count = {}, 0, 0
    def parsed(route):
        if route not in cache:
            path = output_path(built, route)
            assert path.is_file(), f'Missing rendered actual route: {route}'
            cache[route] = Page(path.read_text())
        return cache[route]
    for key, source in registry['resources'].items():
        for locale, variant in source['variants'].items():
            if locale == 'en': continue
            route = variant['url']
            if source['kind'] == 'feed':
                path = output_path(built, route)
                assert path.is_file(), f'{route}: localized RSS missing'
                tree = ET.fromstring(path.read_text())
                assert tree.findtext('./channel/language') == locale, f'{route}: RSS language differs'
                assert not tree.findall('./channel/item'), f'{route}: local draft records leaked to RSS'
                checked += 1
                continue
            page = parsed(route)
            canonical = ORIGIN+route
            assert page.lang == locale, f'{route}: document language differs'
            assert page.canonicals == [canonical], f'{route}: expected its own single canonical'
            assert page.h1s == [normalized(variant['display_title'] or variant['title'])], f'{route}: missing, duplicate or incorrect H1'
            assert 'noindex' in page.metadata.get('robots', ''), f'{route}: local draft is indexable'
            assert not page.alternates, f'{route}: draft hreflang discovery asserted'
            assert not page.metadata.get('article:published_time'), f'{route}: published date on draft'
            assert len(page.ids) == len(set(page.ids)), f'{route}: duplicate element IDs'
            assert all(form.get('method', 'get').lower() in ('get', 'dialog') and not urlsplit(form.get('action','')).netloc for form in page.forms), f'{route}: unexpected live provider form'
            assert all((urlsplit(url).netloc == '' and url.startswith('/assets/')) or url.startswith('https://www.googletagmanager.com/gtag/js?id=G-R7JTFRCH80') for url in page.requests), f'{route}: unexpected external or provider request'
            if key in ('page:learn', 'page:learn-cats'):
                # Content includes render before their outer layout; ensure units
                # survive that context instead of emitting unexplained numbers.
                ui = json.loads((root/'_data/localized_ui'/(locale+'.json')).read_text())
                visible = normalized(unescape(re.sub(r'<[^>]*>', ' ', output_path(built, route).read_text())))
                expected_times = Counter(str(registry['resources'][item]['variants'][locale]['reading_time'])+' '+ui['reading_minutes']
                    for item in ('G01','G02','G03','G04','G05','E09','V25'))
                for value, count in expected_times.items():
                    assert visible.count(value) >= count, f'{route}: article reading-time unit missing: {value}'
            assert len(page.schema) == 1, f'{route}: expected one draft schema record'
            schema = page.schema[0]
            assert schema.get('inLanguage') == locale and schema.get('creativeWorkStatus') == 'Draft', f'{route}: schema language/state differs'
            assert schema.get('url') == canonical and schema.get('mainEntityOfPage') == canonical, f'{route}: schema/canonical identity differs'
            assert 'datePublished' not in schema and 'dateModified' not in schema, f'{route}: unperformed publication/revision asserted'
            expected_equivalents = {ORIGIN+item['url'] for item in source['variants'].values()}
            assert {urljoin(canonical, item['href']) for item in page.equivalents} == expected_equivalents, f'{route}: language choices are not actual same-content variants'
            for link in page.equivalents:
                assert link.get('data-equivalent-key') == key, f'{route}: equivalent changes content identity'
            for link in page.body_links:
                target = urlsplit(urljoin(canonical, link['href']))
                if target.netloc != urlsplit(ORIGIN).netloc: continue
                record = registry['by_route'].get(target.path)
                if record:
                    destination = registry['resources'][record['translation_key']]
                    local = destination['variants'].get(locale)
                    # A bridge may explicitly link the original English remote viewer,
                    # after offering the real localized report. It is provenance, not an alternate.
                    original_project = None
                    if (key == 'page:research-project' and record['translation_key'] == 'page:research-project'
                            and 'data-source-edition' in link and link.get('hreflang') == 'en'):
                        project = parse_qs(target.query).get('p', [])
                        if len(project) == 1:
                            original_project = next((item for item in registry['resources'].values()
                                if item['kind'] == 'report' and item['source_route'] == '/research/'+project[0]+'/'), None)
                        assert original_project, f'{route}: unrecognized original project viewer'
                        real_variant = original_project['variants'].get(locale)
                        assert real_variant and any(urlsplit(urljoin(canonical, item['href'])).path == real_variant['url']
                            for item in page.body_links), f'{route}: original viewer lacks an actual translated report choice'
                    else:
                        assert target.path == (local['url'] if local else destination['source_route']), f'{route}: body link missed actual {locale} variant'
                        if not local:
                            assert link.get('data-language-fallback') == 'en' and link.get('data-fallback-label'), f'{route}: English fallback not labelled'
                if target.fragment:
                    fragment_count += 1
                    assert unquote(target.fragment) in parsed(target.path).ids, f'{route}: missing fragment {target.path}#{target.fragment}'
            checked += 1
    sitemap = built/'sitemap.xml'
    if sitemap.is_file():
        tree = ET.fromstring(sitemap.read_text())
        urls = {node.text for node in tree.iter() if node.tag.endswith('}loc') or node.tag == 'loc'}
        draft_urls = {ORIGIN+variant['url'] for source in registry['resources'].values() for locale, variant in source['variants'].items() if locale != 'en'}
        assert not urls & draft_urls, 'Localized drafts leaked to sitemap'
    return {'rendered_drafts_checked': checked, 'internal_fragments_checked': fragment_count,
            'provider_requests_or_forms': 0, 'draft_hreflang_claims': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--built', type=Path)
    parser.add_argument('--complete', action='store_true', help='require every commissioned locale/content/utility pair to exist')
    args = parser.parse_args()
    root = args.root.resolve()
    expected = build_registry(root)
    actual = json.loads((root/'_data/localization_registry.json').read_text())
    assert actual == expected, 'Localization registry is stale; run tools/prepare_localizations.py'
    assert expected['live_hreflang_enabled'] is False, 'Local drafts cannot assert live alternates'
    documents = read_documents(root)
    drafts = source_checks(root, expected, documents)
    missing_content = sum(len(row['missing_full_resources']) for row in expected['coverage'].values())
    missing_support = sum(len(row['missing_supporting_pages']) for row in expected['coverage'].values())
    if args.complete:
        assert not missing_content and not missing_support, f'Incomplete local editions: {missing_content} content and {missing_support} utility pairs missing'
    states = [state for resource in expected['resources'].values() for locale, state in resource['pair_states'].items() if locale != 'en']
    result = {
        'locales_including_english': len(expected['locales']),
        'actual_draft_bodies': drafts, 'missing_content_pairs': missing_content,
        'missing_support_pairs': missing_support,
        'native_review_pending': sum(state['body_status'] != 'missing' and state['native_review_status'] == 'pending' for state in states),
        'clinical_review_not_performed': sum(state['body_status'] != 'missing' and state['clinical_review_status'] == 'not-independently-reviewed' for state in states),
        'release_approved': sum(state['release_approved'] for state in states),
        'live_verified': sum(state['live_verified'] for state in states),
        'source_hashes_and_registry': 'current',
    }
    if args.built: result.update(built_checks(root, args.built.resolve(), expected, documents))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
