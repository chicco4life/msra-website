#!/usr/bin/env python3
"""Audit actual Jekyll HTML/RSS, independently of the source preview renderer.

    python3 tools/verify_full_site.py --built /path/to/staging --complete
    python3 tools/verify_full_site.py --built /path/to/production --complete --release

Default: staging (no analytics, no localized indexing/hreflang or IP routing).
--release: production analytics, public indexability and reciprocal discovery.
--production also checks production analytics without enabling release discovery.
No network requests, source mutations, publishing or scientific-content approval.
"""
import argparse
from collections import Counter
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
LOCALES = {'en', 'de', 'fr', 'it', 'es', 'nl', 'pl', 'sv', 'da', 'nb', 'fi',
           'ja', 'pt-BR', 'pt-PT', 'ko', 'zh-Hans', 'ru', 'hi'}
PRIVATE_KEYS = {'page:not-found', 'page:learn-updates', 'page:research-project'}
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
PROVIDER_HOSTS = ('kit.com', 'convertkit.com', 'ck.page', 'kit.co')


def normal(value):
    return ' '.join(unescape(value or '').split())


def scalar(text, key, default=''):
    match = re.search(r'^' + re.escape(key) + r':\s*([^\n]*)$', text, re.M)
    return match[1].strip().strip('"\'') if match else default


def provider_url(value):
    host = (urlsplit(value or '').hostname or '').lower()
    return any(host == name or host.endswith('.' + name) for name in PROVIDER_HOSTS)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.lang, self.title = None, ''
        self.ids, self.h1s, self.canonicals, self.alternates = [], [], [], []
        self.links, self.assets, self.forms, self.scripts, self.modals = [], [], [], [], []
        self.metadata, self.equivalents, self.ready_nodes = {}, [], []
        self._stack, self._title, self._h1, self._script = [], None, None, None
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        self._stack.append(tag)
        if tag == 'html': self.lang = attrs.get('lang')
        if 'id' in attrs: self.ids.append(attrs['id'])
        if tag == 'title': self._title = []
        if tag == 'h1': self._h1 = []
        if tag == 'meta':
            name = attrs.get('name') or attrs.get('property')
            if name: self.metadata.setdefault(name.lower(), []).append(attrs.get('content', ''))
        if tag == 'link':
            rel = attrs.get('rel', '').split()
            if 'canonical' in rel: self.canonicals.append(attrs.get('href', ''))
            if 'alternate' in rel and attrs.get('hreflang'): self.alternates.append(attrs)
            if 'stylesheet' in rel: self.assets.append(attrs.get('href', ''))
        if tag in ('a', 'area') and attrs.get('href'):
            self.links.append(attrs)
            if 'data-language-choice' in attrs: self.equivalents.append(attrs)
        if tag in ('img', 'script', 'iframe', 'embed', 'source') and attrs.get('src'):
            self.assets.append(attrs['src'])
        if tag == 'form': self.forms.append(attrs)
        if 'data-subscription-modal' in attrs: self.modals.append(attrs)
        if attrs.get('data-signup-ready') == 'true' or 'data-subscription-link' in attrs:
            self.ready_nodes.append(attrs)
        if tag == 'script': self._script = {'attrs': attrs, 'parts': []}
        if tag in VOID: self._stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID: self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'title' and self._title is not None:
            self.title = normal(''.join(self._title)); self._title = None
        if tag == 'h1' and self._h1 is not None:
            self.h1s.append(normal(''.join(self._h1))); self._h1 = None
        if tag == 'script' and self._script is not None:
            script = self._script
            script['text'] = ''.join(script.pop('parts'))
            self.scripts.append(script); self._script = None
        if tag in self._stack:
            self._stack = self._stack[:len(self._stack)-1-self._stack[::-1].index(tag)]

    def handle_data(self, data):
        if self._title is not None: self._title.append(data)
        if self._h1 is not None: self._h1.append(data)
        if self._script is not None: self._script['parts'].append(data)

    def meta(self, name):
        return self.metadata.get(name, [])

    @property
    def noindex(self):
        return any('noindex' in re.split(r'[\s,]+', text.lower())
                   or 'none' in re.split(r'[\s,]+', text.lower())
                   for text in self.meta('robots') + self.meta('googlebot'))


class Audit:
    def __init__(self, root, built, release=False, complete=False, production=False):
        self.root, self.built = root.resolve(), built.resolve()
        self.release, self.complete, self.production = release, complete, production or release
        self.failures, self.counts, self.pages = [], Counter(), {}
        self.registry = json.loads((root/'_data/localization_registry.json').read_text())
        self.seo = json.loads((root/'_data/localized_seo.json').read_text())
        config = (root/'_config.yml').read_text()
        self.origin = scalar(config, 'url', 'https://msralab.com').rstrip('/')
        self.base = scalar(config, 'baseurl').rstrip('/')
        self.brand = scalar(config, 'brand', 'MSRA Lab')
        self.ga = scalar(config, 'google_analytics', 'G-R7JTFRCH80')
        self.records = {}
        for key, resource in self.registry['resources'].items():
            for locale, variant in resource['variants'].items():
                route = variant['url']
                self.check(route not in self.records, 'duplicate_route', route, key)
                self.records[route] = (key, resource, locale, variant)

    def check(self, condition, code, route='', detail=''):
        if not condition:
            self.failures.append({'code': code, 'route': route, 'detail': detail})
        return bool(condition)

    def absolute(self, route):
        return self.origin + self.base + route

    def path(self, route):
        path = self.built/route.lstrip('/')
        return path/'index.html' if route.endswith('/') else path

    def page(self, route):
        if route not in self.pages:
            path = self.path(route)
            if not path.is_file(): return None
            try: self.pages[route] = Page(path.read_text(encoding='utf-8'))
            except (OSError, UnicodeError, ValueError) as error:
                self.check(False, 'html_parse', route, str(error)); return None
        return self.pages[route]

    def internal(self, href, route):
        try: target = urlsplit(urljoin(self.absolute(route), href))
        except ValueError: return None
        host = urlsplit(self.origin).hostname
        if target.hostname not in (host, 'www.' + host): return None
        path = unquote(target.path)
        if self.base:
            if path != self.base and not path.startswith(self.base + '/'): return ('', target)
            path = path[len(self.base):] or '/'
        if '..' in path.split('/') or '\\' in path: return ('', target)
        return (path, target)

    def discovery_eligible(self, key, resource):
        return key not in PRIVATE_KEYS and resource['kind'] != 'feed'

    def expected_alternates(self, resource):
        mapping = {lc: self.absolute(v['url']) for lc, v in resource['variants'].items()}
        mapping['x-default'] = self.absolute(resource['variants']['en']['url'])
        return mapping

    def alternate_map(self, nodes, route, code):
        pairs = [(n.get('hreflang'), n.get('href')) for n in nodes]
        self.check(len(pairs) == len(set(lc for lc, _ in pairs)), code + '_duplicate', route, pairs)
        return dict(pairs)

    def check_analytics(self, route, page):
        loaders = [s for s in page.scripts if urlsplit(s['attrs'].get('src', '')).hostname == 'www.googletagmanager.com'
                   and urlsplit(s['attrs'].get('src', '')).path == '/gtag/js']
        calls = [m for s in page.scripts if s['attrs'].get('type') not in ('application/json', 'application/ld+json')
                 for m in re.findall(r'\bgtag\s*\(\s*[\"\']config[\"\']\s*,\s*[\"\']([^\"\']+)[\"\']', s['text'])]
        expected = 1 if self.production else 0
        self.check(len(loaders) == expected and calls == ([self.ga] if expected else []),
                   'analytics_count', route, {'loaders': len(loaders), 'config_ids': calls, 'expected': expected})
        if loaders:
            self.check(loaders[0]['attrs'].get('src') == 'https://www.googletagmanager.com/gtag/js?id=' + self.ga,
                       'analytics_loader_id', route, loaders[0]['attrs'])
        self.counts['analytics_loaders'] += len(loaders)

    def check_links(self, route, page):
        for node in page.links:
            href = node.get('href', '')
            result = self.internal(href, route)
            if result is None: continue
            path, target = result
            self.counts['internal_links_checked'] += 1
            if not self.check(bool(path), 'internal_path', route, href): continue
            source_record, destination_record = self.records.get(route), self.records.get(path)
            if source_record and destination_record and source_record[2] != 'en':
                locale = source_record[2]
                local_destination = destination_record[1]['variants'].get(locale)
                intentional_choice = 'data-language-choice' in node or 'data-source-edition' in node
                if local_destination and not intentional_choice:
                    self.check(path == local_destination['url'], 'internal_link_language', route,
                               {'href': href, 'expected_route': local_destination['url']})
            dest = self.path(path)
            if not self.check(dest.is_file(), 'broken_internal_link', route, href): continue
            if target.fragment and dest.suffix.lower() == '.html':
                target_page = self.page(path)
                if target_page:
                    self.counts['fragments_checked'] += 1
                    self.check(unquote(target.fragment) in target_page.ids, 'broken_fragment', route, href)
        for href in page.assets:
            result = self.internal(href, route)
            if result is None: continue
            path, _ = result
            self.counts['internal_assets_checked'] += 1
            self.check(bool(path) and self.path(path).is_file(), 'broken_internal_asset', route, href)

    def check_routing(self, route, page, key, resource, locale):
        blocks = [s for s in page.scripts if s['attrs'].get('id') == 'msra-language-routing']
        if not self.check(len(blocks) == 1, 'routing_json_count', route, len(blocks)): return
        try: data = json.loads(blocks[0]['text'])
        except ValueError as error:
            self.check(False, 'routing_json_invalid', route, str(error)); return
        if not self.check(isinstance(data, dict), 'routing_json_structure', route): return
        self.check(data.get('resourceKey') == key and data.get('currentLocale') == locale
                   and data.get('sourceRoute') == self.base + resource['source_route'],
                   'routing_identity', route, {k: data.get(k) for k in ('resourceKey','currentLocale','sourceRoute')})
        self.check(data.get('enabled') is self.release, 'routing_environment', route,
                   {'enabled': data.get('enabled'), 'release_expected': self.release})
        self.check(data.get('siteUrl', '').rstrip('/') == self.origin
                   and data.get('countryEndpoint') == 'https://api.country.is/', 'routing_origin', route)
        variants = data.get('variants', {})
        expected = {lc: self.base + v['url'] for lc, v in resource['variants'].items()}
        if not self.check(isinstance(variants, dict) and all(isinstance(v, dict) for v in variants.values()),
                          'routing_variant_structure', route): return
        self.check({lc: v.get('url') for lc,v in variants.items()} == expected,
                   'routing_variants', route, expected)
        for lc, record in variants.items():
            variant = resource['variants'].get(lc)
            if not variant: continue
            target_page = self.page(variant['url'])
            if target_page:
                declared = record.get('fragmentIds')
                self.check(isinstance(declared, list) and set(declared) <= set(target_page.ids),
                           'routing_fragment_inventory', route, {'locale': lc, 'declared': declared})
        equivalents = page.equivalents
        expected_switches = {lc: self.absolute(v['url']) for lc,v in resource['variants'].items()} if len(resource['variants']) > 1 else {}
        actual = {}
        for link in equivalents:
            lc = link.get('data-language-choice')
            self.check(lc not in actual, 'switcher_duplicate', route, lc)
            actual[lc] = urljoin(self.absolute(route), link['href'])
            self.check(link.get('data-equivalent-key') == key, 'switcher_identity', route, link)
        self.check(actual == expected_switches, 'switcher_destinations', route,
                   {'actual': actual, 'expected': expected_switches})
        self.counts['routing_pages_checked'] += 1

    def check_html(self, route, record=None):
        page = self.page(route)
        if not page: return
        self.counts['html_pages_checked'] += 1
        duplicates = {key: count for key,count in Counter(page.ids).items() if count > 1}
        self.check(not duplicates, 'duplicate_ids', route, duplicates)
        dynamic_english = record and record[0] == 'page:research-project' and record[2] == 'en'
        valid_h1 = len(page.h1s) == 1 and bool(page.h1s[0])
        self.check(valid_h1 or dynamic_english and not page.h1s, 'single_h1', route, page.h1s)
        self.check(bool(page.title), 'empty_title', route)
        self.check(len(page.meta('description')) == 1 and bool(normal(page.meta('description')[0])),
                   'meta_description', route, page.meta('description'))
        self.check_analytics(route, page)
        self.check_links(route, page)
        self.check(not any(provider_url(a.get('action')) for a in page.forms)
                   and not any(provider_url(a) for a in page.assets) and not page.ready_nodes,
                   'active_email_collection', route,
                   {'provider_forms': [f for f in page.forms if provider_url(f.get('action'))],
                    'provider_requests': [s for s in page.assets if provider_url(s)], 'ready_nodes': page.ready_nodes})
        if not record: return
        key, resource, locale, variant = record
        self.check(page.lang == locale, 'html_language', route, {'actual': page.lang, 'expected': locale})
        if key == 'page:not-found' and locale == 'en':
            self.check(not page.canonicals, 'english_404_canonical', route, page.canonicals)
        else:
            self.check(page.canonicals == [self.absolute(route)], 'self_canonical', route, page.canonicals)
        eligible = self.discovery_eligible(key, resource)
        if self.release:
            self.check(page.noindex is (not eligible), 'release_indexability', route,
                       {'noindex': page.noindex, 'eligible': eligible})
        elif locale != 'en': self.check(page.noindex, 'staging_localized_indexability', route)
        expected_alts = self.expected_alternates(resource) if self.release and eligible else {}
        actual_alts = self.alternate_map(page.alternates, route, 'hreflang')
        self.check(actual_alts == expected_alts, 'hreflang_set', route,
                   {'actual': actual_alts, 'expected': expected_alts})
        for target in actual_alts.values():
            target_route = self.internal(target, route)
            if target_route:
                target_page = self.page(target_route[0])
                self.check(target_page is not None and not target_page.noindex, 'hreflang_target_indexable', route, target)
                if target_page:
                    self.check(dict((a.get('hreflang'),a.get('href')) for a in target_page.alternates) == actual_alts,
                               'hreflang_reciprocal', route, target)
        override = self.seo.get(key, {}).get(locale)
        if self.complete: self.check(isinstance(override, dict), 'seo_pair_missing', route, {'key': key, 'locale': locale})
        if override:
            if override.get('title'):
                expected_title = override['title']
                if 'MSRA' not in expected_title: expected_title += ' | ' + self.brand
                self.check(page.title == normal(expected_title), 'seo_title', route,
                           {'actual': page.title, 'expected': expected_title})
            if override.get('description'):
                self.check(page.meta('description') == [override['description']], 'seo_description', route,
                           {'actual': page.meta('description'), 'expected': override['description']})
            if locale != 'en':
                # Verify the rendered subject against the reviewed page map,
                # including the deliberate absence of a hub acquisition term.
                subjects = []
                for script in page.scripts:
                    if script['attrs'].get('type') != 'application/ld+json': continue
                    try: node = json.loads(script['text'])
                    except ValueError as error:
                        self.check(False, 'localized_schema_json', route, str(error)); continue
                    if isinstance(node, dict) and node.get('@id') == self.absolute(route) + '#page':
                        subjects.append(node)
                if self.check(len(subjects) == 1, 'localized_schema_page_identity', route, len(subjects)):
                    primary = override.get('primary_keyword')
                    expected_about = {'@type': 'Thing', 'name': primary} if primary else None
                    self.check(subjects[0].get('about') == expected_about, 'localized_schema_subject', route,
                               {'actual': subjects[0].get('about'), 'expected': expected_about})
                    self.counts['localized_subjects_checked'] += 1
            self.counts['seo_pairs_checked'] += 1
        if key.startswith('product:'):
            original = self.root/resource['source_file']
            image = scalar(original.read_text(), 'image')
            self.check(bool(image), 'source_product_image_missing', route, str(original))
            self.check(page.meta('og:image') == [urljoin(self.origin + self.base + '/', image.lstrip('/'))],
                       'product_og_image', route, {'actual': page.meta('og:image'), 'source_image': image})
        self.check_routing(route, page, key, resource, locale)
        self.check(len(page.modals) == 1 and page.modals[0].get('data-signup-ready') == 'false'
                   and page.modals[0].get('data-signup-mode') == 'preview', 'email_preview_modal', route, page.modals)

    def check_feed(self, route, record):
        key, resource, locale, _ = record
        try: document = ET.parse(self.path(route)).getroot()
        except (OSError, ET.ParseError) as error:
            self.check(False, 'rss_xml', route, str(error)); return
        channel = document.find('channel')
        if not self.check(document.tag == 'rss' and document.get('version') == '2.0'
                          and channel is not None, 'rss_structure', route): return
        self.check(bool(channel.findtext('title')) and bool(channel.findtext('description')),
                   'rss_required_text', route)
        self.check(channel.findtext('language') == locale, 'rss_language', route, channel.findtext('language'))
        library = self.registry['resources'].get('page:learn', {}).get('variants', {}).get(locale)
        if library: self.check(channel.findtext('link') == self.absolute(library['url']), 'rss_channel_url', route, channel.findtext('link'))
        self_links = [node.get('href') for node in channel.findall('{http://www.w3.org/2005/Atom}link') if node.get('rel') == 'self']
        self.check(self_links == [self.absolute(route)], 'rss_self_url', route, self_links)
        for item in channel.findall('item'):
            self.counts['rss_items_checked'] += 1
            target = self.internal(item.findtext('link') or '', route)
            self.check(bool(item.findtext('title')) and target is not None, 'rss_item_required', route)
            if target:
                pair = self.records.get(target[0])
                self.check(pair is not None and pair[2] == locale and pair[3].get('publication_state') == 'published'
                           and pair[3].get('release_approved') is True, 'rss_draft_or_wrong_locale', route, item.findtext('link'))
                self.check(self.path(target[0]).is_file(), 'rss_item_target', route, item.findtext('link'))
            try: self.check(parsedate_to_datetime(item.findtext('pubDate') or '') is not None, 'rss_pubdate', route)
            except (ValueError, TypeError): self.check(False, 'rss_pubdate', route, item.findtext('pubDate'))
        self.counts['rss_feeds_checked'] += 1

    def check_sitemap(self):
        try: document = ET.parse(self.built/'sitemap.xml').getroot()
        except (OSError, ET.ParseError) as error:
            self.check(False, 'sitemap_xml', '/sitemap.xml', str(error)); return
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        self.check(document.tag == ns+'urlset', 'sitemap_namespace', '/sitemap.xml', document.tag)
        entries = document.findall(ns+'url')
        urls = [node.findtext(ns+'loc') or '' for node in entries]
        self.check(len(urls) == len(set(urls)), 'sitemap_duplicate_urls', '/sitemap.xml')
        expected = set()
        for route, record in self.records.items():
            key, resource, _, _ = record
            if self.discovery_eligible(key, resource):
                page = self.page(route)
                if page and not page.noindex: expected.add(self.absolute(route))
        self.check(set(urls) == expected, 'sitemap_coverage', '/sitemap.xml',
                   {'missing': sorted(expected-set(urls)), 'unexpected': sorted(set(urls)-expected)})
        for entry, url in zip(entries, urls):
            target = self.internal(url or '', '/')
            pair = self.records.get(target[0]) if target else None
            self.check(pair is not None, 'sitemap_unknown_route', '/sitemap.xml', url)
            if not pair: continue
            key, resource, _, _ = pair
            page = self.page(target[0])
            self.check(self.discovery_eligible(key, resource) and page is not None and not page.noindex,
                       'sitemap_nonindexable', '/sitemap.xml', url)
            nodes = [n.attrib for n in entry.findall('{http://www.w3.org/1999/xhtml}link') if n.get('rel') == 'alternate']
            alts = self.alternate_map(nodes, url, 'sitemap_hreflang')
            expected_alts = self.expected_alternates(resource) if self.release else {}
            self.check(alts == expected_alts, 'sitemap_hreflang_set', url,
                       {'actual': alts, 'expected': expected_alts})
            if page:
                self.check(alts == dict((a.get('hreflang'),a.get('href')) for a in page.alternates),
                           'sitemap_html_alternates', url)
        self.counts['sitemap_urls_checked'] = len(urls)

    def run(self):
        self.check(self.built.is_dir(), 'built_directory', str(self.built))
        if self.complete:
            self.check(set(self.registry['locales']) == LOCALES, 'complete_locale_catalog', detail=sorted(self.registry['locales']))
            for key, resource in self.registry['resources'].items():
                self.check(set(resource['variants']) == LOCALES, 'complete_variants', resource['source_route'],
                           {'key': key, 'missing': sorted(LOCALES-set(resource['variants']))})
        for route, record in self.records.items():
            self.counts['registered_routes'] += 1
            if not self.check(self.path(route).is_file(), 'missing_route', route): continue
            if record[1]['kind'] == 'feed': self.check_feed(route, record)
            else: self.check_html(route, record)
        # Check additional output HTML as well, rather than hiding unregistered
        # documents from duplicate-ID, broken-link, analytics and collection QA.
        for path in self.built.rglob('*.html'):
            rel = path.relative_to(self.built).as_posix()
            route = '/' + (rel[:-10] if rel.endswith('index.html') else rel)
            if route in self.records: continue
            self.counts['unregistered_html_pages'] += 1
            self.check_html(route)
        self.check_sitemap()
        for count in ('registered_routes', 'html_pages_checked', 'rss_feeds_checked', 'rss_items_checked',
                      'internal_links_checked', 'fragments_checked', 'internal_assets_checked',
                      'analytics_loaders', 'seo_pairs_checked', 'routing_pages_checked',
                      'sitemap_urls_checked', 'unregistered_html_pages'):
            self.counts.setdefault(count, 0)
        return {'passed': not self.failures, 'mode': 'release' if self.release else 'production-staging' if self.production else 'staging',
                'complete_required': self.complete, 'built': str(self.built), 'counts': dict(self.counts),
                'failure_count': len(self.failures), 'failure_codes': dict(Counter(f['code'] for f in self.failures)),
                'failures': self.failures,
                'scope': 'Actual HTML/RSS technical checks; scientific citations and clinical/native review are assessed elsewhere.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--built', type=Path, required=True)
    parser.add_argument('--release', action='store_true')
    parser.add_argument('--complete', action='store_true')
    parser.add_argument('--production', action='store_true', help='production analytics without public-release indexing/routing')
    parser.add_argument('--report', type=Path, help='also save the JSON report at this path')
    args = parser.parse_args()
    try:
        result = Audit(args.root, args.built, args.release, args.complete, args.production).run()
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {'passed': False, 'mode': 'release' if args.release else 'staging', 'failure_count': 1,
                  'failures': [{'code': 'audit_input_error', 'route': '', 'detail': str(error)}]}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.report: args.report.write_text(encoded)
    print(encoded, end='')
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
