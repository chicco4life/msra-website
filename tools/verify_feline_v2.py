#!/usr/bin/env python3
"""Verify the ten feline v2 bodies in an actual rendered local site.

This verifier does not build Jekyll, install dependencies, or approve publication.
It records renderer provenance and compares rendered bodies with the prepared copy.
"""
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT.parents[1] / 'growth-research/feline-urinary/publication-prep-v2'
DEFAULT_BASELINE = Path('/private/tmp/msra-v2-before-buex4l7m/site')
DEFAULT_BASELINE_BUILT = Path('/private/tmp/msra-v2-baseline-rendered')
DEFAULT_LEGACY_PROOF = ROOT.parent / 'library-preview-2026-10-29/feline-v2-legacy-anchors.json'
NODE = '/Users/work/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
MODULES = '/Users/work/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
# Kramdown smart quotes and marked's straight quotes represent the same prose.
# Do not fold primes, minus signs, dashes, digits, citations or link targets.
TYPOGRAPHIC_QUOTES = str.maketrans({'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"'})


def normalize(value):
    return ' '.join(str(value).translate(TYPOGRAPHIC_QUOTES).split())


def enabled(value):
    return value is True or str(value).lower() == 'true'


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def elements(self):
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.elements()

    def text(self, omit_h1=False):
        if self.tag in ('script', 'style') or (omit_h1 and self.tag == 'h1'):
            return ''
        return ' '.join(child.text(omit_h1) if isinstance(child, Element) else child for child in self.children)

    def find(self, predicate):
        return [node for node in self.elements() if predicate(node)]

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()


class Page(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.root = Element('document')
        self.stack = [self.root]
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    @property
    def elements(self):
        return list(self.root.elements())

    @property
    def ids(self):
        return Counter(node.attrs['id'] for node in self.elements if node.attrs.get('id'))

    def tags(self, tag):
        return [node for node in self.elements if node.tag == tag]

    def main(self):
        found = self.tags('main')
        assert len(found) == 1, 'Expected one main element'
        return found[0]

    def metadata(self):
        return {node.attrs.get('name') or node.attrs.get('property'): node.attrs.get('content', '')
                for node in self.tags('meta')}

    def graphs(self):
        return [json.loads(''.join(child for child in node.children if isinstance(child, str)))
                for node in self.tags('script') if node.attrs.get('type') == 'application/ld+json']


def load_sources(root):
    """Read YAML with the already-installed Apple Ruby; no Python package needed."""
    code = '''root=ARGV[0]; docs=[]
Dir.glob(root+'/{index.html,404.html,learn/**/*.{html,md,xml},research/**/*.html,shop/**/*.html,_articles/**/*.md,_research/**/*.md}').each do |f|
  s=File.read(f); next unless s.start_with?("---\\n"); _,front,body=s.split(/^---\\s*$\\n/,3)
  docs<<{file:f.sub(root+'/', ''),meta:YAML.load(front)||{},body:body||''}
end
puts JSON.generate({config:YAML.load_file(root+'/_config.yml'),docs:docs})'''
    run = subprocess.run(['/usr/bin/ruby', '-EUTF-8', '-ryaml', '-rjson', '-rdate', '-e', code, str(root)],
                         text=True, capture_output=True, check=True)
    return json.loads(run.stdout)


def render_expected(copies, node, modules):
    code = '''import fs from 'node:fs';
const {marked}=await import(process.argv[1]+'/marked/lib/marked.esm.js');
const data=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(Object.fromEntries(Object.entries(data).map(([id,md])=>[id,marked.parse(md)]))));'''
    run = subprocess.run([node, '--input-type=module', '-e', code, modules], input=json.dumps(copies),
                         text=True, capture_output=True, check=True)
    return {key: Page(value) for key, value in json.loads(run.stdout).items()}


def graph_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from graph_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from graph_dicts(child)


def path_for(output, route):
    relative = unquote(urlsplit(route).path).lstrip('/')
    return output / relative / 'index.html' if route.endswith('/') else output / relative


def links(node):
    return [element.attrs['href'] for element in node.elements()
            if element.tag == 'a' and element.attrs.get('href')]


def external_links(node, origin):
    host = urlsplit(origin).netloc
    return Counter(href for href in links(node)
                   if urlsplit(href).scheme in ('http', 'https') and urlsplit(href).netloc != host)


def text_mismatch(expected, actual):
    match = next((n for n, (a, b) in enumerate(zip(expected, actual)) if a != b), min(len(expected), len(actual)))
    return {'offset': match, 'expected': expected[max(0, match-80):match+160],
            'actual': actual[max(0, match-80):match+160], 'expected_chars': len(expected), 'actual_chars': len(actual)}


def explicit_source_anchors(text):
    return re.findall(r'<(?:a|span|div|section|h[1-6])\b[^>]*\bid=["\x27]([^"\x27]+)', text)


def verify(args):
    packet, output, source_root = args.packet.resolve(), args.built.resolve(), args.source_root.resolve()
    publication = json.loads((packet/'PUBLICATION_METADATA.json').read_text())
    routing = json.loads((packet/'LINK_AND_ROUTE_MAP.json').read_text())
    prepared_qa = json.loads((packet/'PREPARATION_QA.json').read_text())
    assets = {asset['id']: asset for asset in publication['assets']}
    assert len(assets) == 10, 'Expected ten v2 assets'
    manifest = output/'preview-manifest.json'
    provenance = json.loads(manifest.read_text()) if manifest.exists() else {'renderer': 'unspecified; independently identify build provenance'}
    sources = load_sources(source_root)
    source_ids = {}
    for doc in sources['docs']:
        if doc['meta'].get('content_id') in assets:
            source_ids.setdefault(doc['meta']['content_id'], []).append(doc)
    consumer_titles = json.loads((source_root/'_data/library.json').read_text()).get('cards', {})
    seo_editions = json.loads((source_root/'_data/localized_seo.json').read_text()) if (source_root/'_data/localized_seo.json').exists() else {}
    copies = {key: (packet/asset['prepared_public_body']).read_text() for key, asset in assets.items()}
    expected = render_expected(copies, args.node, args.modules)
    map_manuscripts = {item['content_id']: item for item in routing['manuscripts']}
    map_navigation = {item['content_id']: item for item in routing['navigation_placements']}
    pages, checks, draft_urls = {}, [], set()
    total_external = 0
    for key, asset in assets.items():
        route, canonical = asset['retained_route'], asset['canonical_url']
        target = path_for(output, route)
        assert target.exists(), f'{key}: retained route missing: {route}'
        markup = target.read_text()
        page = pages.setdefault(target, Page(markup))
        h1s = page.tags('h1')
        assert len(h1s) == 1 and normalize(h1s[0].text()) == normalize(consumer_titles.get(key, {}).get('title') or asset['h1']), f'{key}: wrong/duplicate consumer H1'
        titles = page.tags('title')
        selected_seo = seo_editions.get(key, {}).get('en', {})
        wanted_title = selected_seo.get('title') or consumer_titles.get(key, {}).get('title') or asset['seo_title']
        if 'MSRA' not in wanted_title: wanted_title += ' | '+sources['config']['brand']
        assert len(titles) == 1 and normalize(titles[0].text()) == normalize(wanted_title), f'{key}: title/brand mismatch'
        assert titles[0].text().count(sources['config']['brand']) == 1, f'{key}: duplicate brand suffix'
        meta = page.metadata()
        assert meta.get('description') == (selected_seo.get('description') or asset['meta_description']), f'{key}: description differs from selected metadata'
        canonicals = [node.attrs.get('href') for node in page.tags('link') if 'canonical' in node.attrs.get('rel', '').split()]
        assert canonicals == [canonical], f'{key}: canonical mismatch: {canonicals}'
        duplicates = {anchor: count for anchor, count in page.ids.items() if count > 1}
        assert not duplicates, f'{key}: duplicate IDs: {duplicates}'
        wrappers = page.root.find(lambda node: node.attrs.get('data-public-copy-id') == key)
        assert len(wrappers) == 1, f'{key}: expected one marked public-copy body'
        body = wrappers[0]
        assert not body.find(lambda node: node.tag == 'h1'), f'{key}: body duplicates layout H1'
        wanted_text = normalize(expected[key].root.text(omit_h1=True))
        actual_text = normalize(body.text(omit_h1=True))
        assert actual_text == wanted_text, f'{key}: prepared body changed: {text_mismatch(wanted_text, actual_text)}'
        wanted_links, actual_links = external_links(expected[key].root, publication['canonical_origin']), external_links(body, publication['canonical_origin'])
        assert actual_links == wanted_links, f'{key}: external href multiplicities changed: missing={wanted_links-actual_links}, extra={actual_links-wanted_links}'
        total_external += sum(actual_links.values())
        footer = normalize(re.sub(r'^\*|\*$', '', map_manuscripts[key]['public_review_note_exact']))
        assert actual_text.count(footer) == 1 and normalize(page.main().text()).count(footer) == 1, f'{key}: public credits/review footer missing or duplicated'
        assert len(source_ids.get(key, [])) == 1, f'{key}: source identity missing/duplicated'
        doc = source_ids[key][0]
        front = doc['meta']
        wanted_refs = asset['numbered_source_refs']
        assert wanted_refs == map_manuscripts[key]['numbered_source_refs_from_public_direct_citations'], f'{key}: packet citation maps disagree'
        assert [int(value) for value in front.get('source_refs', [])] == wanted_refs, f'{key}: front-matter refs do not match actual public citations'
        assert enabled(front.get('publication_dates_pending')), f'{key}: missing publication date hold'
        assert front.get('publication_state') != 'published' and not enabled(front.get('release_approved')), f'{key}: unapproved v2 release'
        assert not enabled(front.get('sitemap')), f'{key}: source enables sitemap'
        assert ('noindex' not in meta.get('robots', '').lower()) if args.release else ('noindex' in meta.get('robots', '').lower()), f'{key}: indexing state differs from selected build profile'
        draft_urls.add(canonical)
        assert 'article:published_time' not in meta and 'article:modified_time' not in meta, f'{key}: pending dates presented as publication/modification'
        for graph in page.graphs():
            for node in graph_dicts(graph):
                assert 'reviewedBy' not in node, f'{key}: unperformed clinical review credited'
                assert 'datePublished' not in node and 'dateModified' not in node, f'{key}: pending publication dates escaped into schema'
                if node.get('@type') in ('Article', 'MedicalWebPage', 'WebPage', 'CollectionPage'):
                    status = node.get('creativeWorkStatus')
                    assert status is None or any(word in str(status).lower() for word in ('draft', 'preview')), f'{key}: unexpected schema release status'
        assert 'qualified veterinary review pending' in normalize(page.root.text()).lower(), f'{key}: preview-review boundary not visible'
        main = page.main()
        # The owner requested local email bars during the website hold. They may
        # demonstrate the shared dialog, but cannot serialize or send an address.
        assert not page.root.find(lambda node: node.tag == 'input' and node.attrs.get('type') == 'file'), f'{key}: new upload field'
        for control in page.root.find(lambda node: node.tag == 'input' and node.attrs.get('type') == 'email'):
            assert ('data-subscription-entry-email' in control.attrs or 'data-subscription-email' in control.attrs) and 'name' not in control.attrs and 'form' not in control.attrs and 'value' not in control.attrs, f'{key}: email hold violated by collecting/prefilled email field'
        for form in page.tags('form'):
            if 'data-subscription-entry' in form.attrs:
                assert form.attrs.get('method', '').lower() == 'get' and re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)*learn/updates/', form.attrs.get('action', '')), f'{key}: entry bar has an external/action query destination'
            else:
                assert 'data-subscription-preview-form' in form.attrs and form.attrs.get('method') == 'dialog' and 'action' not in form.attrs, f'{key}: email hold violated by a network form'
                final = form.find(lambda node: node.tag == 'button')
                assert len(final) == 1 and 'disabled' in final[0].attrs and final[0].attrs.get('type') == 'button', f'{key}: local preview final action is enabled'
            assert all(not {'name', 'form', 'formaction', 'formmethod'} & node.attrs.keys() for node in form.find(lambda node: node.tag in ('input', 'button', 'select', 'textarea'))), f'{key}: local form serializes email/topic data or overrides its local action'
        provider_hosts = ('kit.com', 'convertkit.com')
        def provider_url(href):
            host = urlsplit(href).hostname or ''
            return any(host == domain or host.endswith('.' + domain) for domain in provider_hosts)
        assert not any(provider_url(node.attrs.get('src', '')) for node in page.tags('script')), f'{key}: email hold violated by provider behavior script'
        assert not any(provider_url(href) for href in links(page.root)), f'{key}: email hold violated by provider handoff'
        assert not re.search(r'PUBLIC(?: ARTICLE)? BODY (?:START|END)|LANDING_PAGE_HANDOVER|PUBLICATION_METADATA\.json|CLAIM_APPENDIX|SOURCE_APPENDIX|MANIFEST\.json', main.text(), re.I), f'{key}: internal delivery material leaked'
        mapped_navigation = page.root.find(lambda node: node.has_class('knowledge-packet__navigation'))
        assert len(mapped_navigation) == 1, f'{key}: mapped collection navigation missing/duplicated'
        wanted_sidebar = [entry['target'] for entry in map_navigation[key]['sidebar']]
        assert links(mapped_navigation[0]) == wanted_sidebar, f'{key}: sidebar differs from the route map'
        related = page.root.find(lambda node: node.attrs.get('aria-labelledby') == 'packet-related-reading')
        if key == 'H00':
            assert not related and not page.root.find(lambda node: node.has_class('knowledge-card') or node.has_class('knowledge-overview-card')), 'H00: removed card stacks returned'
        else:
            assert len(related) == 1, f'{key}: mapped related cards missing/duplicated'
            related_cards = related[0].find(lambda node: node.has_class('knowledge-card'))
            assert [node.attrs.get('data-content-id') for node in related_cards] == [entry['content_id'] for entry in map_navigation[key]['related_cards']], f'{key}: related cards differ from map'
        checks.append({'id': key, 'route': route, 'body_chars': len(actual_text), 'external_hrefs': sum(actual_links.values()),
                       'source_refs': wanted_refs, 'unique_ids': len(page.ids), 'prepared_body_preserved': True})
    assert total_external == prepared_qa['total_external_links_preserved'] == 185, 'External source occurrence total changed'

    # Exact source identity plus clinical-body rendering, excluding shared navigation/cards.
    preserved = []
    for identity in routing['identity_preservation']:
        relative = Path(identity['local_existing_file'].split('msralab-site/', 1)[-1])
        old, new = args.baseline/relative, source_root/relative
        assert old.exists() and new.exists() and old.read_bytes() == new.read_bytes(), f'{identity["content_id"]}: body or status changed from baseline'
        target = path_for(output, identity['route'])
        assert target.exists(), f'{identity["content_id"]}: retained page missing'
        current = pages.setdefault(target, Page(target.read_text()))
        previous_target = path_for(args.baseline_built, identity['route'])
        rendered_body_checked = False
        if previous_target.exists():
            previous = Page(previous_target.read_text())
            old_body = previous.root.find(lambda node: node.has_class('knowledge-prose'))
            new_body = current.root.find(lambda node: node.has_class('knowledge-prose'))
            assert len(old_body) == len(new_body) == 1 and normalize(old_body[0].text()) == normalize(new_body[0].text()), f'{identity["content_id"]}: rendered clinical body changed'
            rendered_body_checked = True
        preserved.append({'id': identity['content_id'], 'source_bytes_identical': True, 'rendered_body_identical': rendered_body_checked})

    index_page = pages[path_for(output, assets['S00']['retained_route'])]
    source_records = json.loads((source_root/'_data/feline_sources.json').read_text())['records']
    source_identities = {int(record['ref']): record['id'] for record in source_records}
    flattened = index_page.elements
    for record in routing['source_index_anchors']['numbered_records']:
        assert source_identities[record['ref']] == record['stable_source_id'], f'S00: stable source identity changed at {record["ref"]}'
        anchor = record['anchor']
        assert index_page.ids[anchor] == 1, f'S00: {anchor} missing/duplicated'
        position = next(i for i, node in enumerate(flattened) if node.attrs.get('id') == anchor)
        heading = next((node for node in flattened[position:] if node.tag in ('h2', 'h3', 'h4')), None)
        wanted = normalize(re.sub(r'^#+\s*', '', record['insert_before_exact']))
        assert heading and normalize(heading.text()) == wanted, f'S00: {anchor} points to the wrong source'
    aliases = []
    for key, entries in routing['compatibility_anchors'].items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            target_url = entry.get('public_target')
            if not target_url:
                continue  # R00 candidate IDs need independently verified legacy-render evidence.
            parsed = urlsplit(target_url)
            target = path_for(output, parsed.path)
            parsed_page = pages.setdefault(target, Page(target.read_text()))
            assert parsed_page.ids[parsed.fragment] == 1, f'Compatibility anchor missing/duplicated: {target_url}'
            aliases.append(target_url)
    r00 = path_for(output, assets['R00']['retained_route'])
    old_r00 = path_for(args.baseline_built, assets['R00']['retained_route'])
    verified_r00_ids = []
    if old_r00.exists():
        old_page = Page(old_r00.read_text())
        old_main_ids = Counter(node.attrs['id'] for node in old_page.main().elements() if node.attrs.get('id'))
        for anchor in old_main_ids:
            assert pages[r00].ids[anchor] == 1, f'R00: old rendered explicit anchor lost: {anchor}'
            verified_r00_ids.append(anchor)
        old_body = old_page.root.find(lambda node: node.has_class('prose'))
        if old_body:
            signature = normalize(old_body[0].text())[:240]
            assert signature not in normalize(pages[r00].main().text()), 'R00: old body appended to replacement'
    live_alias_proof = None
    if args.legacy_anchors.exists():
        proof = json.loads(args.legacy_anchors.read_text())
        assert proof['source_url'] == assets['R00']['canonical_url'] and proof['method']['read_only'], 'Legacy proof has unexpected scope'
        observed = proof['observed_heading_ids']
        assert len(observed) == len(set(observed)) == 8, 'Expected eight independently observed live heading IDs'
        for anchor in observed + proof['compatibility_decision']['preserve_existing_layout_ids']:
            assert pages[r00].ids[anchor] == 1, f'R00: observed historical live alias missing/nonunique: {anchor}'
        live_alias_proof = {'artifact': str(args.legacy_anchors), 'source_url': proof['source_url'],
                            'observed_on': proof['observed_on'], 'observed_at': proof['observed_at'],
                            'evidence_basis': proof['evidence_basis'], 'observed_heading_ids_preserved': observed,
                            'new_live_fetch_performed_by_verifier': False}

    # Check all rendered HTML, including every sidebar, related card and legacy page.
    broken, fragments = [], 0
    origin = publication['canonical_origin']
    for target in output.rglob('*.html'):
        route = '/'+target.relative_to(output).as_posix().removesuffix('index.html')
        page = pages.setdefault(target, Page(target.read_text()))
        for href in links(page.root):
            decoded = unquote(href)
            assert not re.search(r'^(?:file:|/Users/|/private/|[A-Za-z]:\\)', decoded), f'{route}: filesystem href leaked: {href}'
            url = urlsplit(urljoin(origin+route, href))
            if url.scheme not in ('http', 'https') or url.netloc != urlsplit(origin).netloc:
                continue
            assert not unquote(url.path).endswith('.md'), f'{route}: local Markdown href leaked: {href}'
            destination = path_for(output, url.path)
            if not destination.exists():
                broken.append((route, href))
            elif url.fragment and destination.suffix == '.html':
                destination_page = pages.setdefault(destination, Page(destination.read_text()))
                fragments += 1
                if destination_page.ids[unquote(url.fragment)] != 1:
                    broken.append((route, href, 'fragment missing/nonunique'))
    assert not broken, f'Broken internal routes/fragments: {broken}'
    for filename in ('sitemap.xml', 'learn/feed.xml'):
        tree = ET.parse(output/filename)
        discovered = {node.text for node in tree.getroot().iter() if node.tag.split('}')[-1] in ('loc', 'link', 'guid')}
        if args.release and filename == 'sitemap.xml':
            assert draft_urls <= discovered, f'Prepared public research missing from {filename}: {draft_urls-discovered}'
        else:
            assert not draft_urls & discovered, f'v2 drafts escaped into {filename}: {draft_urls & discovered}'
    return {'renderer': provenance.get('renderer'), 'isJekyllBuild': provenance.get('isJekyllBuild'),
            'text_comparison_normalization': 'Whitespace and typographically equivalent straight/curly quotation marks only; numbers, citation text and external href multiplicities remain exact.',
            'assets': checks, 'assets_checked': len(checks), 'external_href_occurrences_preserved': total_external,
            'source_anchors_unique_and_matched': 41, 'compatibility_aliases_checked': len(aliases),
            'r00_previous_render_ids_preserved': verified_r00_ids, 'r00_old_body_not_appended': True,
            'r00_historical_live_alias_proof': live_alias_proof,
            'legacy_heading_id_scope': 'Baseline rendering plus the supplied historical read-only live DOM artifact; the verifier checks the new local aliases and does not fetch or deploy the live site.',
            'identity_preservation': preserved, 'checked_internal_fragments': fragments,
            'broken_internal_links': 0, 'indexable_research_release': args.release, 'drafts_in_discovery_files': len(draft_urls) if args.release else 0, 'publication_dates_pending': True,
            'clinical_review_claimed': False, 'email_capture_activated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--built', type=Path, required=True)
    parser.add_argument('--release', action='store_true', help='validate the explicit public indexing profile; clinical review status remains unchanged')
    parser.add_argument('--packet', type=Path, default=DEFAULT_PACKET)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--baseline', type=Path, default=DEFAULT_BASELINE)
    parser.add_argument('--baseline-built', type=Path, default=DEFAULT_BASELINE_BUILT)
    parser.add_argument('--legacy-anchors', type=Path, default=DEFAULT_LEGACY_PROOF,
                        help='read-only historical live heading-ID observation artifact')
    parser.add_argument('--node', default=NODE)
    parser.add_argument('--modules', default=MODULES)
    parser.add_argument('--output', type=Path, help='optional QA JSON path outside the checkout')
    args = parser.parse_args()
    result = verify(args)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    if args.output:
        destination = args.output.resolve()
        assert not destination.is_relative_to(args.source_root.resolve()), 'Keep generated QA outside the checkout'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serialized)
    print(serialized, end='')


if __name__ == '__main__':
    main()
