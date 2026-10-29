#!/usr/bin/env python3
"""Check publication safety in temporary fixtures and optionally a rendered site."""
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import sys
import tempfile
from urllib.parse import urljoin, urlsplit, unquote
import xml.etree.ElementTree as ET

import sync_articles
from sync_research import front_matter, q

ROOT = Path(__file__).resolve().parent.parent
ORIGIN = 'https://msralab.com'


def document(meta, body):
    return '\n'.join(['---'] + [f'{key}: {q(value)}' for key, value in meta.items()] + ['---', body, ''])


def snapshot(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


def check_gate(kb):
    registry = json.loads((kb/'content/topics.json').read_text())
    topic = next(topic for topic in registry['topics'] if topic['status'] == 'active')
    meta = dict(title='Temporary publication-gate fixture', slug='gate-fixture', topic=topic['id'],
                species=[topic['species']], summary='Temporary fixture, never published.', date='2026-10-29',
                content_type='explainer', authors='MSRA Research', publication_state='ready',
                evidence_review_status='source-checked', clinical_review_status='not-independently-reviewed')
    body = 'A temporary [source-link fixture](https://pubmed.ncbi.nlm.nih.gov/39935081/).'
    with tempfile.TemporaryDirectory(prefix='msra-publication-gate-') as tmp:
        base = Path(tmp)
        fixture, site = base/'kb', base/'site'
        source_dir = fixture/'content/articles'
        source_dir.mkdir(parents=True)
        (fixture/'content/topics.json').write_text(json.dumps(registry))
        source = source_dir/'ready.md'
        source.write_text(document(meta, body))
        (source_dir/'draft.md').write_text(document(dict(meta, slug='withheld-draft', publication_state='draft'), body))
        (site/'_data').mkdir(parents=True)
        previous_root = sync_articles.ROOT
        sync_articles.ROOT = site

        def run():
            with redirect_stdout(io.StringIO()):
                sync_articles.main(['--kb', str(fixture)])

        def rejected_without_changes(candidate):
            before = snapshot(site)
            source.write_text(document(candidate, body))
            try:
                run()
            except ValueError:
                pass
            else:
                raise AssertionError('Unsafe fixture was not rejected')
            assert snapshot(site) == before, 'Rejected batch changed website output'

        try:
            run()
            files = list((site/'_articles').glob('*.md'))
            assert len(files) == 1, 'Ineligible source draft escaped the gate'
            generated, _ = front_matter(files[0].read_text())
            assert generated['publication_state'] == 'editorial-draft'
            assert generated['robots'] == 'noindex' and generated['sitemap'] == 'false'
            assert not sync_articles.enabled(generated['release_approved'])
            rejected_without_changes(dict(meta, evidence_review_status='pending'))
            rejected_without_changes(dict(meta, release_approved=True))
            rejected_without_changes(dict(meta, release_approved=True, release_scope='clinical-guidance'))
            rejected_without_changes(dict(meta, clinical_review_status='independently-reviewed'))
            approved = dict(meta, release_approved=True, release_scope='literature-interpretation')
            source.write_text(document(approved, body))
            run()
            generated, _ = front_matter(files[0].read_text())
            assert generated['publication_state'] == 'published'
            assert generated['robots'] == 'index,follow' and generated['sitemap'] == 'true'
            assert generated['clinical_review_status'] == 'not-independently-reviewed', 'Clinical review was invented'
            # Protect both an overwrite and removal after a source slug changes.
            edited = files[0].read_text().replace('---\n', '---\nfrontend_edited: true\n', 1)
            files[0].write_text(edited + '\nLocal adaptation must survive.\n')
            rejected_without_changes(approved)
            rejected_without_changes(dict(approved, slug='replacement-slug'))
            return {'eligible_defaults_to_noindex_preview': True, 'ineligible_draft_withheld': True,
                    'unchecked_or_unscoped_release_rejected': True, 'clinical_review_not_invented': True,
                    'explicit_literature_release_supported': True, 'frontend_edits_protected_from_overwrite_and_removal': True,
                    'rejected_batches_leave_output_unchanged': True}
        finally:
            sync_articles.ROOT = previous_root


def normalized(text):
    return ' '.join(str(text).split())


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links, self.canonicals, self.jsonld, self.ids, self.meta = [], [], [], set(), {}
        self.times = []
        self.h1s, self.h1_text, self.text, self.breadcrumbs = 0, '', '', []
        self.active_json, self.buf, self.in_h1, self.hidden_tag = False, '', False, None
        self.in_breadcrumb, self.anchor = False, None
        self.in_main, self.main_links = False, []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'main':
            self.in_main = True
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('name'):
            self.ids.add(attrs['name'])
        if tag == 'h1':
            self.h1s += 1
            self.in_h1 = True
        if tag == 'time' and attrs.get('datetime'):
            self.times.append(attrs['datetime'][:10])
        if tag == 'nav' and 'breadcrumb' in attrs.get('aria-label', '').lower():
            self.in_breadcrumb = True
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
            if self.in_main:
                self.main_links.append(attrs['href'])
            if self.in_breadcrumb:
                self.anchor = [attrs['href'], '']
        if tag == 'link' and 'canonical' in attrs.get('rel', '').split():
            self.canonicals.append(attrs.get('href'))
        if tag == 'meta':
            key = attrs.get('name') or attrs.get('property')
            if key:
                self.meta[key] = attrs.get('content', '')
        if tag in ('script', 'style'):
            self.hidden_tag = tag
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.active_json, self.buf = True, ''

    def handle_data(self, data):
        if self.active_json:
            self.buf += data
        if not self.hidden_tag:
            self.text += data+' '
            if self.in_h1:
                self.h1_text += data
            if self.anchor is not None:
                self.anchor[1] += data

    def handle_endtag(self, tag):
        if tag == 'main':
            self.in_main = False
        if tag == 'h1':
            self.in_h1 = False
        if tag == 'a' and self.anchor is not None:
            self.breadcrumbs.append(self.anchor)
            self.anchor = None
        if tag == 'nav':
            self.in_breadcrumb = False
        if tag == 'script' and self.active_json:
            self.jsonld.append(json.loads(self.buf))
            self.active_json = False
        if tag == self.hidden_tag:
            self.hidden_tag = None


def graph_nodes(value):
    if isinstance(value, list):
        return [node for item in value for node in graph_nodes(item)]
    if isinstance(value, dict):
        return graph_nodes(value['@graph']) if '@graph' in value else [value]
    return []


def node_url(value):
    return (value.get('@id') or value.get('url')) if isinstance(value, dict) else value


def author_names(value):
    if isinstance(value, list):
        return [name for item in value for name in author_names(item)]
    if isinstance(value, dict):
        return [normalized(value.get('name', ''))]
    return [normalized(value)] if value else []


def source_route(meta, path, source_root):
    """Resolve the actual Jekyll destination without inventing a new identity."""
    route = meta.get('permalink') or meta.get('url')
    if route:
        return route
    if path.parent == source_root/'_research':
        return '/research/'+(meta.get('dir') or path.stem)+'/'
    if path.is_relative_to(source_root/'learn'):
        relative = path.relative_to(source_root)
        if path.name in ('index.html', 'index.md'):
            return '/'+relative.parent.as_posix()+'/'
        if path.suffix == '.md':
            return '/'+relative.with_suffix('').as_posix()+'/'
        return '/'+relative.as_posix()
    return None


def source_articles(source_root):
    articles = {}
    candidates = list((source_root/'_articles').glob('*.md'))
    candidates += [path for path in (source_root/'learn').rglob('*') if path.suffix in ('.html', '.md')]
    for path in candidates:
        meta, _ = front_matter(path.read_text())
        article_source = (path.parent == source_root/'_articles' or
                          meta.get('layout') == 'knowledge-article' or
                          meta.get('schema_type') == 'Article' or
                          (meta.get('layout') == 'knowledge-packet' and
                           meta.get('content_type') in ('guide', 'evidence-overview')))
        if not article_source:
            continue
        route = source_route(meta, path, source_root)
        assert route and route.startswith('/learn/'), f'{path}: missing owner article route'
        assert route not in articles, f'Duplicate source article route: {route}'
        articles[route] = meta
    return articles


def check_build(output, source_root=ROOT, public_index=False):
    paths = list((output/'learn').glob('**/*.html'))
    assert paths, 'No built owner pages'
    expected = source_articles(source_root)
    index_manifest = json.loads((source_root/'_data/publication_manifest.json').read_text())['resources'] if public_index else {}
    consumer_titles = json.loads((source_root/'_data/library.json').read_text()).get('cards', {})
    parsed_pages, routes = {}, {}
    for path in paths:
        route = '/'+path.relative_to(output).as_posix()
        if route.endswith('index.html'):
            route = route[:-10]
        routes[route] = path
        markup = path.read_text()
        assert not re.search(r'\{%\s*(include|assign|for|if|unless)\b|\{\{\s*\w', markup), f'Unrendered Liquid in {route}'
        parsed_pages[path] = Page(markup)
    cache = dict(parsed_pages)
    broken, noindex_urls, published, article_count, graphs, fragments = [], set(), set(), 0, 0, 0
    validated_articles = set()
    for route, path in routes.items():
        markup, parsed = path.read_text(), parsed_pages[path]
        canonical = ORIGIN+route
        assert parsed.h1s == 1, f'{route}: expected one h1'
        assert parsed.canonicals == [canonical], f'{route}: canonical mismatch {parsed.canonicals}'
        # Shop is allowed in the single global navigation, while owner content
        # remains free of local product checkout prompts.
        assert not any(urlsplit(urljoin(canonical, href)).netloc == urlsplit(ORIGIN).netloc and urlsplit(urljoin(canonical, href)).path.startswith('/shop/') for href in parsed.main_links), f'{route}: editorial content includes a shop link'
        if 'noindex' in parsed.meta.get('robots', '').lower():
            noindex_urls.add(canonical)
        nodes = [node for graph in parsed.jsonld for node in graph_nodes(graph)]
        articles = [node for node in nodes if node.get('@type') == 'Article']
        if articles:
            article_count += 1
            assert route in expected, f'{route}: built article lacks source metadata'
            meta = expected[route]
            validated_articles.add(route)
            released = meta.get('publication_state') == 'published' and sync_articles.enabled(meta.get('release_approved'))
            if released:
                assert meta.get('evidence_review_status') == 'source-checked', f'{route}: released source has not cleared evidence checking'
                assert meta.get('release_scope') in ('literature-interpretation', 'clinical-guidance'), f'{route}: released source lacks a declared scope'
                if meta.get('release_scope') == 'clinical-guidance':
                    assert meta.get('clinical_review_status') == 'independently-reviewed', f'{route}: clinical release lacks independent review'
                published.add(canonical)
                assert canonical not in noindex_urls, f'{route}: approved publication still noindex'
            else:
                prepared_index = public_index and index_manifest.get(meta.get('content_id'),{}).get('indexable')
                assert (canonical not in noindex_urls) if prepared_index else (canonical in noindex_urls), f'{route}: indexing state differs from the explicit release candidate'
                # Discoverability never changes the scientific review/publication status.
                assert not sync_articles.enabled(meta.get('sitemap')), f'{route}: unapproved source enables sitemap'
            assert normalized(parsed.h1_text) == normalized(consumer_titles.get(meta.get('content_id'), {}).get('title') or meta['title']), f'{route}: visible title differs from selected consumer title'
            breadcrumbs = [node for node in nodes if node.get('@type') == 'BreadcrumbList']
            assert len(articles) == 1 and len(breadcrumbs) == 1, f'{route}: expected Article and BreadcrumbList'
            article, breadcrumb = articles[0], breadcrumbs[0]
            assert article.get('@id') == canonical+'#article', f'{route}: Article ID differs from canonical'
            assert node_url(article.get('mainEntityOfPage')) == canonical, f'{route}: Article page URL differs from canonical'
            if article.get('url'):
                assert article['url'] == canonical, f'{route}: Article URL differs from canonical'
            assert normalized(article.get('headline')) == normalized(parsed.h1_text), f'{route}: schema headline differs from visible title'
            pending_dates = sync_articles.enabled(meta.get('publication_dates_pending'))
            if pending_dates:
                assert not released, f'{route}: released article still has pending publication dates'
                created = meta.get('prepared_date', '')[:10]
                assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', created), f'{route}: pending publication dates require a prepared_date'
                assert article.get('creativeWorkStatus') == 'Draft', f'{route}: prepared copy must remain a schema draft'
                assert article.get('dateCreated') == created, f'{route}: draft preparation date differs from source'
                assert not {'datePublished', 'dateModified'} & article.keys(), f'{route}: prepared draft invents publication/modification dates'
                assert not {'article:published_time', 'article:modified_time'} & parsed.meta.keys(), f'{route}: prepared draft invents social publication/modification dates'
                assert created in parsed.times, f'{route}: prepared_date lacks a visible dated time element'
            else:
                created = meta['date'][:10]
                modified = meta.get('last_modified_at', meta['date'])[:10]
                if released:
                    assert article.get('datePublished') == created == parsed.meta.get('article:published_time'), f'{route}: publication date differs across source/schema/social metadata'
                else:
                    assert article.get('creativeWorkStatus') == 'Draft', f'{route}: schema must identify an editorial draft'
                    assert article.get('dateCreated') == created, f'{route}: draft creation date differs from source'
                    assert 'datePublished' not in article and 'article:published_time' not in parsed.meta, f'{route}: unpublished draft claims a publication date'
                assert article.get('dateModified') == modified == parsed.meta.get('article:modified_time'), f'{route}: modification date differs across source/schema/social metadata'
                assert all(value in parsed.times for value in (created, modified)), f'{route}: source creation/publication or modification date lacks a visible dated time element'
            wanted_authors = author_names(meta['authors'])
            actual_authors = author_names(article.get('author'))
            assert actual_authors == wanted_authors and all(wanted_authors), f'{route}: schema author differs from source'
            assert all(name in normalized(parsed.text) for name in wanted_authors), f'{route}: schema authorship is not visible'
            if meta.get('clinical_review_status') == 'not-independently-reviewed':
                assert re.search(r'(independent veterinary review has not been (?:recorded|performed|completed)|not independently veterinary reviewed|qualified veterinary review (?:pending|has not (?:yet )?been completed)|has not been independently reviewed by a veterinarian)', parsed.text, re.I), f'{route}: missing honest clinical-review status'
                assert 'reviewedBy' not in article and not meta.get('clinical_reviewer'), f'{route}: unreviewed content invents a clinical reviewer'
            elif meta.get('clinical_review_status') == 'independently-reviewed':
                assert all(meta.get(key) for key in ('clinical_reviewer', 'clinical_review_scope', 'clinical_review_date')), f'{route}: independent review details are missing'
                assert normalized(meta['clinical_reviewer']) in normalized(parsed.text), f'{route}: recorded reviewer is not visible'
            else:
                raise AssertionError(f'{route}: unsupported clinical-review status')
            items = breadcrumb.get('itemListElement', [])
            assert [item.get('position') for item in items] == list(range(1, len(items)+1)), f'{route}: breadcrumb positions are not consecutive'
            assert items and node_url(items[-1].get('item')) == canonical, f'{route}: breadcrumb does not end at canonical'
            assert normalized(items[-1].get('name')) == normalized(parsed.h1_text), f'{route}: breadcrumb title differs from article'
            visible_parents = [(urljoin(canonical, href), normalized(name)) for href, name in parsed.breadcrumbs]
            schema_parents = [(node_url(item.get('item')), normalized(item.get('name'))) for item in items[:-1]]
            assert schema_parents == visible_parents, f'{route}: structured and visible breadcrumb parents differ'
            graphs += len(parsed.jsonld)
        for href in parsed.links:
            target_url = urlsplit(urljoin(canonical, href))
            if target_url.scheme not in ('http', 'https') or target_url.netloc != urlsplit(ORIGIN).netloc:
                continue
            target = output/unquote(target_url.path).lstrip('/')
            if target_url.path.endswith('/'):
                target = target/'index.html'
            if not target.exists():
                broken.append((route, href))
            elif target_url.fragment and target.suffix == '.html':
                if target not in cache:
                    cache[target] = Page(target.read_text())
                fragments += 1
                if unquote(target_url.fragment) not in cache[target].ids:
                    broken.append((route, href, 'missing fragment'))
    assert not broken, f'Broken internal links/fragments: {broken}'
    assert set(expected) <= set(routes), f'Article sources missing from output: {set(expected)-set(routes)}'
    assert set(expected) == validated_articles, f'Expected article sources lack Article JSON-LD: {set(expected)-validated_articles}'
    rss = ET.parse(output/'learn/feed.xml')
    urls = [item.findtext('link') for item in rss.findall('.//item')]
    assert len(urls) == len(set(urls)), 'Duplicate canonical RSS entries'
    assert set(urls) == published, f'RSS must contain exactly explicitly released articles: {set(urls)^published}'
    sitemap = ET.parse(output/'sitemap.xml')
    sitemap_urls = {node.text for node in sitemap.getroot().iter() if node.tag.split('}')[-1] == 'loc'}
    assert not noindex_urls & sitemap_urls, f'Noindex drafts escaped into sitemap: {noindex_urls & sitemap_urls}'
    assert not noindex_urls & set(urls), 'Noindex drafts escaped into RSS'
    assert published <= sitemap_urls, f'Released articles missing from sitemap: {published-sitemap_urls}'
    return {'owner_pages': len(paths), 'articles': article_count, 'published_articles': len(published),
            'noindex_pages': len(noindex_urls), 'jsonld_graphs': graphs, 'rss_entries': len(urls),
            'checked_internal_fragments': fragments, 'broken_internal_links': 0, 'noindex_drafts_in_rss_or_sitemap': 0, 'explicit_indexing_candidate': public_index}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kb', required=True)
    parser.add_argument('--release', action='store_true', help='check the explicit prepared-indexing manifest; preserve scientific review gates')
    parser.add_argument('--built', help='rendered site directory; report renderer provenance separately')
    parser.add_argument('--source-root', default=str(ROOT), help='matching website sources for rendered metadata checks')
    args = parser.parse_args()
    result = {'publication_gate': check_gate(Path(args.kb).resolve())}
    if args.built:
        result['rendered_output'] = check_build(Path(args.built).resolve(), Path(args.source_root).resolve(), args.release)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
