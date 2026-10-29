#!/usr/bin/env python3
"""Verify library project tables and retained cards against actual sources.

    python3 tools/verify_library_presentation.py
    python3 tools/verify_library_presentation.py --built /absolute/path/to/preview

Reads the website checkout only. This tool does not read the research knowledge
base, generate pages, change publication state or assess scientific readiness.
"""
import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

from sync_research import front_matter
from verify_knowledge import Page, normalized, source_route

ROOT = Path(__file__).resolve().parent.parent
ORIGIN = 'https://msralab.com'
COPY_FIELDS = {'title', 'summary', 'label'}
SHELVES = ('guide_ids', 'featured_ids', 'related_ids', 'study_ids')
FELINE_GUIDES = {'G01', 'G02', 'G03', 'G04', 'G05'}
FELINE_ARTICLES = FELINE_GUIDES | {'E09', 'V25'}
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


def sources(root):
    records, routes = {}, {}
    paths = list((root/'_articles').glob('*.md'))
    paths += list((root/'_research').glob('*.md'))
    paths += [path for path in (root/'learn').rglob('*') if path.suffix in ('.html', '.md')]
    for path in paths:
        meta, body = front_matter(path.read_text())
        content_id = meta.get('content_id')
        if not content_id:
            assert path.parent != root/'_articles', f'{path}: article is missing its stable content_id'
            continue
        assert re.fullmatch(r'[A-Z]\d{2}', content_id), f'{path}: invalid content_id {content_id}'
        if meta.get('permalink') and meta.get('url'):
            assert meta['permalink'] == meta['url'], f'{path}: URL and permalink disagree'
        route = source_route(meta, path, root)
        parsed = urlsplit(route)
        prefix = '/research/' if path.parent == root/'_research' else '/learn/'
        assert route and route.startswith(prefix) and route.endswith('/') and '..' not in parsed.path.split('/') and not (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment), f'{path}: expected one local canonical {prefix} route'
        assert content_id not in records, f'Duplicate source content_id: {content_id}'
        assert route not in routes, f'Duplicate source canonical route: {route}'
        assert meta.get('title') and body.strip(), f'{path}: card cannot resolve to an empty placeholder'
        assert not re.fullmatch(r'(?:todo|placeholder|coming soon)[\s.!]*', body.strip(), re.I), f'{path}: placeholder is not an implemented destination'
        records[content_id] = dict(meta, route=route, path=str(path))
        routes[route] = content_id
    assert 'O00' in records and 'T24' in records, 'Overview O00 and public record T24 must resolve to actual site pages'
    return records


def project_config(root, records, topics):
    data = json.loads((root/'_data/library_projects.json').read_text())
    projects = data.get('projects')
    assert isinstance(projects, list) and len(projects) == 2, 'Project selector needs the two actual research projects'
    ids = [project.get('id') for project in projects]
    assert len(ids) == len(set(ids)) and set(ids) == {'feline-urinary', 'rabbit-gut'}, 'Project selector has missing, unknown or duplicate topic IDs'
    assert data.get('default_project') in ids, 'Default project is not an available project'
    catalog = json.loads((root/'_data/research.json').read_text())['projects']
    catalog = {project['dir']: project for project in catalog}
    cores = {}
    for path in (root/'_research').glob('*.md'):
        meta, body = front_matter(path.read_text())
        directory = meta.get('dir') or path.stem
        assert directory not in cores and meta.get('title') and body.strip(), f'{path}: duplicate or empty core review'
        route = source_route(meta, path, root)
        parsed = urlsplit(route)
        assert route.startswith('/research/') and route.endswith('/') and '..' not in parsed.path.split('/') and not (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment), f'{path}: core review lacks one local research canonical'
        cores[directory] = dict(meta, route=route, path=str(path))
    assert {project.get('core_dir') for project in projects} == set(catalog), 'Project choices do not cover the actual research catalog exactly once'
    article_ids = {content_id for content_id, record in records.items() if Path(record['path']).parent == root/'_articles'}
    for project in projects:
        project_id = project['id']
        assert project_id in topics and project.get('core_dir') == topics[project_id].get('source_project'), f'{project_id}: core review belongs to another topic'
        assert isinstance(project.get('label'), str) and project['label'].strip(), f'{project_id}: missing project label'
        core = cores.get(project['core_dir'])
        assert core and core['route'] == catalog[project['core_dir']]['url'], f'{project_id}: missing core source or changed canonical route'
        assert core['title'] == catalog[project['core_dir']]['title'], f'{project_id}: catalog/core source title differs'
        expected_core_id = core.get('content_id') or ''
        assert project.get('core_id') == expected_core_id, f'{project_id}: core content ID changes actual source identity'
        if expected_core_id:
            assert expected_core_id in records and records[expected_core_id]['path'] == core['path'], f'{project_id}: unresolved core content ID'
        rows = project.get('article_ids')
        assert isinstance(rows, list) and len(rows) == len(set(rows)), f'{project_id}: missing or duplicate article rows'
        expected = {content_id for content_id in article_ids if records[content_id].get('source_project') == project['core_dir']}
        assert set(rows) == expected, f'{project_id}: article list differs from actual project articles'
        assert set(rows) == (FELINE_ARTICLES if project_id == 'feline-urinary' else set()), f'{project_id}: expected seven feline articles and no invented rabbit articles'
        utilities = project.get('utility_ids')
        assert isinstance(utilities, list) and len(utilities) == len(set(utilities)), f'{project_id}: invalid/duplicate utility IDs'
        assert set(utilities) == ({'O00', 'S00', 'T24'} if project_id == 'feline-urinary' else set()), f'{project_id}: utility destinations differ from the actual supporting pages'
        for content_id in utilities:
            assert content_id in records and Path(records[content_id]['path']).is_relative_to(root/'learn'), f'{project_id}: utility is not an actual site Page'
        labels = project.get('utility_labels', {})
        assert isinstance(labels, dict) and set(labels) <= set(utilities) and all(isinstance(label, str) and label.strip() for label in labels.values()), f'{project_id}: invalid utility label override'
        if project.get('publications_url'):
            route = urlsplit(project['publications_url'])
            assert not route.scheme and not route.netloc and not route.query and route.path == '/research/' and route.fragment, f'{project_id}: publications link is not an internal research fragment'
    return data, cores, {'configured_projects': len(projects), 'feline_article_rows': 7,
                         'rabbit_article_rows': 0, 'core_reviews_resolve_to_actual_sources': True}


def check_config(root):
    library = json.loads((root/'_data/library.json').read_text())
    assert library.get('schema_version') == 1, 'Unsupported library presentation schema'
    assert set(library) <= {'schema_version', 'topics', 'cards', 'configuration_role', 'editorial_context'}, 'Unexpected library-level configuration fields'
    records = sources(root)
    registry = json.loads((root/'_data/knowledge.json').read_text())
    topics = {topic['id']: topic for topic in registry['topics']}
    assert isinstance(library.get('topics'), dict) and library['topics'], 'Library needs configured topics'
    assert isinstance(library.get('cards', {}), dict), 'cards must be an ID-to-copy mapping'
    referenced = set()
    for topic_id, shelves in library['topics'].items():
        assert topic_id in topics and topics[topic_id].get('url'), f'Unknown/unavailable topic: {topic_id}'
        assert isinstance(shelves, dict) and set(shelves) == {'overview_id', 'tool_id', *SHELVES}, f'{topic_id}: expected overview, public tool and four presentation shelves'
        overview = shelves['overview_id']
        assert isinstance(overview, str) and overview in records, f'{topic_id}: unresolved overview ID {overview}'
        assert records[overview].get('content_type') == 'evidence-overview', f'{topic_id}: overview ID is not an evidence overview'
        referenced.add(overview)
        tool = shelves['tool_id']
        assert isinstance(tool, str) and tool in records, f'{topic_id}: unresolved public tool ID {tool}'
        assert records[tool]['route'].startswith(topics[topic_id]['url']), f'{topic_id}: public tool belongs to another collection'
        referenced.add(tool)
        for field in SHELVES:
            values = shelves[field]
            assert isinstance(values, list) and all(isinstance(value, str) for value in values), f'{topic_id}.{field}: expected a list of stable IDs'
            assert len(values) == len(set(values)), f'{topic_id}.{field}: duplicate card IDs'
            for content_id in values:
                assert content_id in records, f'{topic_id}.{field}: unresolved/placeholder content ID {content_id}'
                assert records[content_id]['route'].startswith(topics[topic_id]['url']), f'{topic_id}.{field}: destination belongs to another collection'
                referenced.add(content_id)
        if topic_id == 'feline-urinary':
            assert set(shelves['guide_ids']) == FELINE_GUIDES, 'Feline guide shelf must use the five actual G01–G05 destinations exactly once'
        assert set(shelves['featured_ids']) <= set(shelves['guide_ids']), f'{topic_id}: featured cards must come from the actual guide shelf'
        assert all(records[content_id].get('content_type') == 'study-analysis' for content_id in shelves['study_ids']), f'{topic_id}: Studies explained needs actual study-analysis destinations'
    for content_id, copy in library.get('cards', {}).items():
        assert content_id in records, f'Card copy exists for an unimplemented content ID: {content_id}'
        assert isinstance(copy, dict) and set(copy) <= COPY_FIELDS, f'{content_id}: card overrides may contain only title, summary and label; URL/identity stays in source metadata'
        assert all(isinstance(value, str) and (not value or value.strip()) for value in copy.values()), f'{content_id}: copy overrides must be text or an empty fallback'
    packet_path = root/'_data/feline_packet.json'
    packet = json.loads(packet_path.read_text()) if packet_path.exists() else {}
    navigation = packet.get('navigation', {})
    for content_id, record in records.items():
        if record.get('packet_version') == '2.0':
            assert content_id in navigation, f'{content_id}: v2 destination lacks packet navigation mapping'
    for content_id, placement in navigation.items():
        assert content_id in records, f'Packet navigation has an unimplemented source ID: {content_id}'
        for field in ('sidebar', 'related_cards'):
            links = placement.get(field)
            assert isinstance(links, list), f'{content_id}.{field}: expected navigation records'
            ids = []
            for link in links:
                target_id = link.get('content_id')
                assert target_id in records, f'{content_id}.{field}: unresolved destination {target_id}'
                assert link.get('target') == records[target_id]['route'], f'{content_id}.{field}: {target_id} target changes canonical identity'
                assert isinstance(link.get('label'), str) and link['label'].strip(), f'{content_id}.{field}: missing descriptive link label'
                ids.append(target_id)
                referenced.add(target_id)
            assert len(ids) == len(set(ids)), f'{content_id}.{field}: duplicate configured destinations'
    _, _, projects_result = project_config(root, records, topics)
    return library, records, topics, {'source_destinations': len(records), 'configured_topics': len(library['topics']),
        'configured_destination_ids': len(referenced), 'copy_overrides': len(library.get('cards', {})),
        'duplicate_ids_or_routes': 0, 'unresolved_or_placeholder_cards': 0, 'mutable_card_urls': 0,
        'project_index': projects_result}


class Structure(HTMLParser):
    """Keep enough ancestry to scope selector, core and table checks."""
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.root = {'tag': 'document', 'attrs': {}, 'children': []}
        self.stack = [self.root]
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'children': []}
        self.stack[-1]['children'].append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, 0, -1):
            if self.stack[index]['tag'] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1]['children'].append(data)


def nodes(node, tag=None, attr=None):
    found = []
    if (tag is None or node['tag'] == tag) and (attr is None or attr in node['attrs']):
        found.append(node)
    for child in node['children']:
        if isinstance(child, dict):
            found.extend(nodes(child, tag, attr))
    return found


def text(node):
    if node['tag'] in ('script', 'style'):
        return ''
    return normalized(' '.join(text(child) if isinstance(child, dict) else child for child in node['children']))


def hrefs(node, route):
    return [urljoin(ORIGIN+route, link['attrs']['href']) for link in nodes(node, 'a') if link['attrs'].get('href')]


class Cards(HTMLParser):
    """Read cards by their stable ID, including nested h2/h3 titles and links."""
    def __init__(self, markup):
        super().__init__()
        self.stack, self.cards, self.current, self.heading_depth = [], [], None, None
        self.public_body, self.public_links = None, {}
        self.feed(markup)
        assert self.current is None, 'Unclosed data-content-id card'

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('data-public-copy-id'):
            assert self.public_body is None, 'Nested public-copy wrappers'
            self.public_body = {'id': attrs['data-public-copy-id'], 'tag': tag, 'depth': len(self.stack)+1}
            self.public_links.setdefault(attrs['data-public-copy-id'], [])
        if self.public_body and tag == 'a' and attrs.get('href'):
            self.public_links[self.public_body['id']].append(attrs['href'])
        if attrs.get('data-content-id'):
            assert self.current is None, 'Nested data-content-id cards'
            self.current = {'id': attrs['data-content-id'], 'title': '', 'hrefs': [], 'tag': tag, 'depth': len(self.stack)+1}
        if self.current:
            if tag in ('h2', 'h3') and self.heading_depth is None and not self.current['title']:
                self.heading_depth = len(self.stack)+1
            if tag == 'br' and self.heading_depth is not None:
                self.current['title'] += ' '
            if tag == 'a' and attrs.get('href'):
                self.current['hrefs'].append(attrs['href'])
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.current and self.heading_depth is not None:
            self.current['title'] += data

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if self.heading_depth == len(self.stack) and tag in ('h2', 'h3'):
            self.heading_depth = None
        if self.current and self.current['depth'] == len(self.stack) and self.current['tag'] == tag:
            self.cards.append(self.current)
            self.current = None
        if self.public_body and self.public_body['depth'] == len(self.stack) and self.public_body['tag'] == tag:
            self.public_body = None
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()


def built_path(output, route):
    return output/route.lstrip('/')/'index.html'


def check_project_page(output, route, project_data, cores, library, records, picker):
    markup = built_path(output, route).read_text()
    tree = Structure(markup).root
    mains = nodes(tree, 'main')
    assert len(mains) == 1, f'{route}: expected one main region'
    main = mains[0]
    configured = project_data['projects'] if picker else [project for project in project_data['projects'] if project['id'] == 'feline-urinary']
    panels = nodes(main, attr='data-library-project')
    assert [panel['attrs']['data-library-project'] for panel in panels] == [project['id'] for project in configured], f'{route}: missing/duplicate project panels or wrong order'
    assert all('hidden' not in panel['attrs'] for panel in panels), f'{route}: server rendering hides a project from no-JavaScript readers'
    forbidden_cards = {'knowledge-card', 'knowledge-overview-card', 'knowledge-species-card'}
    assert not any(forbidden_cards & set(node['attrs'].get('class', '').split()) for node in nodes(main)), f'{route}: project index still has duplicate card decks'
    pickers = nodes(main, 'select', 'data-library-project-picker')
    fallbacks = nodes(main, attr='data-library-project-fallback')
    if picker:
        assert len(pickers) == 1, f'{route}: expected one native project selector'
        options = nodes(pickers[0], 'option')
        assert [option['attrs'].get('value') for option in options] == [project['id'] for project in configured], f'{route}: selector options differ from the two actual projects'
        assert [text(option) for option in options] == [project['label'] for project in configured], f'{route}: selector labels differ from configuration'
        assert [option['attrs'].get('value') for option in options if 'selected' in option['attrs']] == [project_data['default_project']], f'{route}: selector default differs from configuration'
        enhanced = nodes(main, attr='data-library-project-enhanced')
        assert len(enhanced) == 1 and 'hidden' in enhanced[0]['attrs'] and len(nodes(enhanced[0], 'select', 'data-library-project-picker')) == 1, f'{route}: JS-only selector must start hidden with fallback available'
        assert len(fallbacks) == 1 and 'hidden' not in fallbacks[0]['attrs'], f'{route}: missing visible no-JavaScript project links'
        assert hrefs(fallbacks[0], route) == [ORIGIN+route+'#'+panel['attrs']['id'] for panel in panels], f'{route}: project fallback links do not target the actual panels'
    else:
        assert not pickers and not fallbacks, f'{route}: Cats index must remain pinned to its feline project'
        assert ORIGIN+'/learn/' in hrefs(main, route), f'{route}: missing link back to all ongoing projects'
    rows_checked = 0
    for panel, project in zip(panels, configured):
        project_id = project['id']
        core_source = cores[project['core_dir']]
        core_url = ORIGIN+core_source['route']
        core_nodes = nodes(panel, attr='data-library-core')
        assert len(core_nodes) == 1 and core_nodes[0]['attrs']['data-library-core'] == project['core_dir'], f'{route}: {project_id} core identity changed'
        core = core_nodes[0]
        headings = nodes(core, 'h2')
        assert len(headings) == 1 and hrefs(headings[0], route) == [core_url], f'{route}: {project_id} core heading must link to the actual review'
        core_copy = library.get('cards', {}).get(project.get('core_id'), {})
        assert text(headings[0]) == normalized(core_copy.get('title') or project.get('core_title') or core_source['title']), f'{route}: {project_id} core title differs from selected source copy'
        expected_links = Counter({core_url: 2})
        for content_id in project['utility_ids']:
            destination = records[content_id]['route']
            assert built_path(output, destination).is_file(), f'{route}: {content_id} utility destination is absent'
            expected_links[ORIGIN+destination] += 1
        if project.get('publications_url'):
            destination = project['publications_url']
            expected_links[ORIGIN+destination] += 1
            target = urlsplit(destination)
            assert target.fragment in Page(built_path(output, target.path).read_text()).ids, f'{route}: {project_id} publications fragment is missing'
        assert Counter(hrefs(core, route)) == expected_links, f'{route}: {project_id} core/resources hrefs differ from canonical destinations'
        articles = nodes(panel, attr='data-library-articles')
        assert len(articles) == 1, f'{route}: {project_id} missing/duplicated article-table region'
        rows = nodes(articles[0], attr='data-library-article-id')
        assert [row['attrs']['data-library-article-id'] for row in rows] == project['article_ids'], f'{route}: {project_id} article IDs/order differ or occur more than once'
        tables = nodes(articles[0], 'table')
        if project['article_ids']:
            assert len(tables) == 1 and len(nodes(tables[0], 'tbody')) == 1, f'{route}: {project_id} needs one flat article table'
            assert len(nodes(nodes(tables[0], 'tbody')[0], 'tr')) == len(rows), f'{route}: {project_id} table has an unmarked or extra row'
        else:
            assert not tables and re.search(r'\bno (?:separate )?articles (?:yet|available)\b', text(articles[0]), re.I), f'{route}: {project_id} must honestly show that no separate articles exist'
        for row in rows:
            content_id = row['attrs']['data-library-article-id']
            assert row['tag'] == 'tr', f'{route}: {content_id} is not a flat table row'
            source = records[content_id]
            copy = library.get('cards', {}).get(content_id, {})
            links = nodes(row, 'a')
            assert len(links) == 1 and hrefs(row, route) == [ORIGIN+source['route']], f'{route}: {content_id} article href changes source canonical identity'
            assert text(links[0]) == normalized(copy.get('title') or source['title']), f'{route}: {content_id} row title differs from selected source copy'
            assert built_path(output, source['route']).is_file(), f'{route}: {content_id} table destination is absent'
            rows_checked += 1
    parsed = Page(markup)
    assert parsed.canonicals == [ORIGIN+route] and parsed.h1s == 1, f'{route}: navigation index lost its self-canonical or single H1'
    return {'route': route, 'project_panels': len(panels), 'selector_options': len(configured) if picker else 0,
            'article_rows': rows_checked, 'no_card_decks': True, 'canonical_links_match_sources': True,
            'no_javascript_projects_available': True}


def check_built(output, library, records, topics, root=ROOT):
    pages, public_links = {}, {}
    packet_path = root/'_data/feline_packet.json'
    packet = json.loads(packet_path.read_text()) if packet_path.exists() else {}
    navigation = packet.get('navigation', {})
    checked_cards = 0
    paths = list((output/'learn').rglob('*.html')) + list((output/'research').rglob('*.html'))
    for path in paths:
        route = '/'+path.relative_to(output).as_posix()
        route = route[:-10] if route.endswith('index.html') else route
        rendered = Cards(path.read_text())
        cards = rendered.cards
        ids = [card['id'] for card in cards]
        for card in cards:
            content_id = card['id']
            assert content_id in records, f'{route}: rendered card has unknown ID {content_id}'
            source = records[content_id]
            copy = library.get('cards', {}).get(content_id, {})
            assert normalized(card['title']) == normalized(copy.get('title') or source['title']), f'{route}: {content_id} card title does not match its override/fallback'
            assert card['hrefs'], f'{route}: {content_id} card has no destination link'
            assert all(urljoin(ORIGIN+route, href) == ORIGIN+source['route'] for href in card['hrefs']), f'{route}: {content_id} card href changed canonical identity'
            assert built_path(output, source['route']).is_file(), f'{route}: {content_id} card destination is missing from preview'
            checked_cards += 1
        pages[route] = ids
        public_links[route] = rendered.public_links
    assert pages, 'No rendered library HTML found'
    for topic_id, shelves in library['topics'].items():
        topic_route = topics[topic_id]['url']
        packet_hub = next((record for record in records.values() if record['route'] == topic_route and record.get('packet_version') == '2.0'), None)
        if packet_hub:
            hub_id = packet_hub['content_id']
            assert pages.get(topic_route) == [], f'{topic_route}: H00 still has removed overview/study/related card stacks'
            expected_guides = [ORIGIN+records[content_id]['route'] for content_id in shelves['guide_ids']]
            body_links = [urljoin(ORIGIN+topic_route, href) for href in public_links.get(topic_route, {}).get(hub_id, [])]
            body_guides = [href for href in body_links if href in expected_guides]
            assert body_guides == expected_guides, f'{topic_route}: five prepared-body guide destinations/order differ from configuration'
        else:
            assert pages.get(topic_route) == [shelves['overview_id'], *shelves['guide_ids'], *shelves['study_ids']], f'{topic_route}: overview/guide/study card order differs from configuration'
            assert pages.get(topic_route+'studies/') == [shelves['overview_id'], *shelves['study_ids']], f'{topic_route}studies/: card order differs from configuration'
        for content_id, record in records.items():
            if record.get('packet_version') == '2.0':
                related = [link['content_id'] for link in navigation[content_id]['related_cards']]
                if content_id == 'H00':
                    continue  # H00's preserved body guide links and removed card stacks were checked above.
                expected = [*shelves['study_ids'], *related] if content_id == 'S00' else related
                assert pages.get(record['route']) == expected, f'{record["route"]}: packet-related card order differs from mapping: {pages.get(record["route"])} != {expected}'
            elif record.get('layout') == 'knowledge-article' and record['route'].startswith(topic_route):
                expected = [related_id for related_id in shelves['related_ids'] if related_id != content_id][:3]
                assert pages.get(record['route']) == expected, f'{record["route"]}: related-card order differs from configuration/cap 3'
    project_data, cores, _ = project_config(root, records, topics)
    project_pages = [check_project_page(output, '/learn/', project_data, cores, library, records, True),
                     check_project_page(output, '/learn/cats/', project_data, cores, library, records, False)]
    assert pages.get('/learn/') == [] and pages.get('/learn/cats/') == [], 'Project index routes must not duplicate article card shelves'
    for content_id, record in records.items():
        path = built_path(output, record['route'])
        assert path.is_file(), f'{content_id}: actual source is absent from preview'
        parsed = Page(path.read_text())
        assert parsed.canonicals == [ORIGIN+record['route']], f'{content_id}: source self-canonical changed'
        assert parsed.h1s == 1 and normalized(parsed.h1_text) == normalized(library.get('cards', {}).get(content_id, {}).get('title') or record['title']), f'{content_id}: destination H1 differs from its consumer title'
    for directory, core in cores.items():
        parsed = Page(built_path(output, core['route']).read_text())
        assert parsed.canonicals == [ORIGIN+core['route']], f'{directory}: core source self-canonical changed'
        assert parsed.h1s == 1 and normalized(parsed.h1_text) == normalized(library.get('cards', {}).get(core.get('content_id'), {}).get('title') or next(project for project in project_data['projects'] if project['core_dir'] == directory).get('core_title') or core['title']), f'{directory}: core-review H1 differs from its consumer title'
    return {'rendered_cards': checked_cards, 'checked_source_canonicals': len(records),
            'retained_card_order_matches': True, 'card_titles_and_real_hrefs_match': True,
            'consumer_h1s_match_overlays': True, 'core_review_canonicals_checked': len(cores),
            'project_indexes': project_pages, 'h00_prepared_guide_links_preserved': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(ROOT), help='website checkout, never the research knowledge base')
    parser.add_argument('--built', help='matching rendered preview directory')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    library, records, topics, result = check_config(root)
    report = {'library_configuration': result}
    if args.built:
        report['rendered_presentation'] = check_built(Path(args.built).resolve(), library, records, topics, root)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
