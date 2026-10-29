#!/usr/bin/env python3
"""Index actual English sources and complete local translation drafts.

This tool writes only _data/localization_registry.json. It never translates,
rewrites manuscripts, assigns a clinical review, or publishes a locale URL.
Run after source/UI translation files have been saved, before preview rendering.

    python3 tools/prepare_localizations.py
    python3 tools/prepare_localizations.py --check
    python3 tools/prepare_localizations.py --root /path/to/fixture
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
LOCALES = {
    'en': ('English', 'en_GB'), 'de': ('Deutsch', 'de_DE'),
    'fr': ('Français', 'fr_FR'), 'it': ('Italiano', 'it_IT'),
    'es': ('Español', 'es_ES'), 'nl': ('Nederlands', 'nl_NL'),
    'pl': ('Polski', 'pl_PL'), 'sv': ('Svenska', 'sv_SE'),
    'ja': ('日本語', 'ja_JP'), 'pt-BR': ('Português (Brasil)', 'pt_BR'),
    'ko': ('한국어', 'ko_KR'), 'zh-Hans': ('简体中文', 'zh_CN'),
    'pt-PT': ('Português (Portugal)', 'pt_PT'),
    'da': ('Dansk', 'da_DK'), 'nb': ('Norsk bokmål', 'nb_NO'),
    'fi': ('Suomi', 'fi_FI'), 'ru': ('Русский', 'ru_RU'),
    'hi': ('हिन्दी', 'hi_IN'),
}
# Ordinals name the source's urgent warning paragraph without inspecting English wording.
URGENT_PARAGRAPHS = {'G01': 1, 'G02': 1, 'G03': 1, 'G04': 3, 'G05': 2, 'H00': 2, 'T24': 1, 'O00': 3, 'E09': 1, 'V25': 2, 'R00': 3}
SOURCE_DATE_LABELS = {'nl': 'Datum van de bronversie', 'ja': '原文の日付', 'de': 'Datum der Ausgangsfassung', 'ru': 'Дата исходной версии', 'pl': 'Data wersji źródłowej', 'fi': 'Lähdeversion päivämäärä', 'en': 'Source date', 'pt-PT': 'Data da versão de origem', 'it': 'Data della versione originale', 'zh-Hans': '原文日期', 'fr': 'Date de la version source', 'pt-BR': 'Data da versão de origem', 'ko': '원문 날짜', 'da': 'Kildeudgavens dato', 'sv': 'Källversionens datum', 'es': 'Fecha de la versión original', 'nb': 'Kildeversjonens dato', 'hi': 'मूल संस्करण की तारीख'}
TEXT_FIELDS = ('title', 'seo_title', 'description', 'display_title', 'summary', 'content_label')
DRAFT_FIELDS = {
    'layout': 'localized', 'translation_status': 'ai-draft',
    'native_review_status': 'pending',
    'clinical_review_status': 'not-independently-reviewed',
    'publication_state': 'editorial-draft', 'release_approved': False,
    'robots': 'noindex', 'sitemap': False,
}


def marketing_source_fingerprint(root):
    root = Path(root)
    names = {'index.html', '404.html', '_config.yml', '_data/products.yml',
             '_data/shop.yml', '_data/research.json', '_data/library.json', '_data/subscriptions.yml'}
    for folder in ('shop', '_includes', '_layouts'):
        names.update(str(path.relative_to(root)) for path in (root/folder).rglob('*.html'))
    digest = sha256()
    for name in sorted(names):
        path = root/name
        if not path.is_file(): continue
        data = path.read_bytes()
        if name == '_config.yml':
            data = re.sub(rb'^(?:localization_public_release|language_routing_enabled):[^\n]*\n', b'', data, flags=re.M)
        digest.update(name.encode()+b'\0'+data+b'\0')
    return digest.hexdigest()


def read_documents(root):
    """Use the selected Ruby with safe date-aware YAML on Ruby 2.6 and 3.3."""
    ruby = r'''
require 'yaml'; require 'json'; require 'date'
def metadata_yaml(text)
  YAML.safe_load(text, permitted_classes: [Date, Time], permitted_symbols: [], aliases: true) || {}
end
root=ARGV[0]
config=metadata_yaml(File.read(root+'/_config.yml', encoding:'UTF-8')); defaults=config['defaults']||[]
files=Dir.glob(root+'/{index.html,404.html,shop/**/*.html,learn/**/*.{md,html,xml},research/**/*.html,privacy/**/*.{md,html},_articles/**/*.md,_research/**/*.md,_localized/**/*.{md,html,xml}}')
docs=[]
files.sort.each do |file|
  text=File.read(file, encoding:'UTF-8')
  next unless text.start_with?("---\n")
  parts=text.split(/^---\s*$\n/,3)
  relative=file.sub(root+'/', ''); meta=metadata_yaml(parts[1]); effective={}
  type=relative.start_with?('_') ? relative.split('/')[0].sub(/^_/, '') : nil
  defaults.each do |rule|
    scope=rule['scope']||{}; prefix=scope['path'].to_s.sub(%r{/$}, '')
    match_path=prefix.empty? || relative==prefix || relative.start_with?(prefix+'/')
    match_type=!scope['type'] || scope['type']==type
    effective.merge!(rule['values']||{}) if match_path && match_type
  end
  docs << {file:relative, meta:meta, effective_meta:effective.merge(meta), body:parts[2]||''}
end
puts JSON.generate(docs)
'''
    result = subprocess.run(['ruby', '-EUTF-8', '-e', ruby, str(root)],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def source_route(doc):
    meta, filename = doc['meta'], doc['file']
    if meta.get('permalink'):
        return meta['permalink']
    path = Path(filename)
    if filename.startswith('_research/'):
        return '/research/'+str(meta.get('dir') or path.stem)+'/'
    if filename.startswith('_articles/'):
        return '/learn/'+path.stem+'/'
    return '/'+re.sub(r'index\.html$', '', re.sub(r'\.md$', '.html', filename))


def translation_key(doc):
    meta, filename = doc['meta'], doc['file']
    if filename == 'index.html':
        return 'page:home'
    if filename == '404.html':
        return 'page:not-found'
    if filename.startswith('shop/'):
        return 'product:'+str(meta['product']) if meta.get('product') else 'page:shop'
    if meta.get('content_id'):
        return meta['content_id']
    if filename.startswith('_research/'):
        return 'research:'+str(meta.get('dir') or Path(filename).stem)
    return 'page:'+re.sub(r'\.xml$', '', source_route(doc).strip('/')).replace('/', '-')


def local_route(route, locale):
    return '/'+locale.lower()+route


def valid_route(route):
    if not isinstance(route, str):
        return False
    parsed = urlsplit(route)
    return (route.startswith('/') and not route.startswith('//')
            and not (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment)
            and '..' not in parsed.path.split('/') and (route.endswith('/') or route.endswith(('.xml', '.html'))))


def read_ui(root, locale):
    path = root/'_data'/'localized_ui'/(locale+'.json')
    assert path.is_file(), f'{locale}: missing complete static UI {path}'
    ui = json.loads(path.read_text())
    assert isinstance(ui, dict) and all(isinstance(v, str) and v.strip() for v in ui.values()), f'{path}: UI values must be nonempty strings'
    return ui


def read_handover(root):
    """Optional commissioning evidence, separate from actual saved variants."""
    snapshot = root/'_data/localization_plan.json'
    if snapshot.is_file():
        plan = json.loads(snapshot.read_text())
        return plan['aliases'], {(pair['inventory_id'], pair['locale']): pair for pair in plan['pairs']}
    folder = root.parent.parent/'growth-research'/'full-localization-handover-2026-10-29'
    matrix = folder/'FULL_LOCALE_PAGE_MATRIX.json'
    inventory = folder/'SITE_CONTENT_INVENTORY.json'
    if not matrix.is_file() or not inventory.is_file():
        return {}, {}
    matrix_data = json.loads(matrix.read_text())
    inventory_data = json.loads(inventory.read_text())
    aliases = {item['route']: item['inventory_id'] for item in inventory_data['inventory']}
    maps = {}
    for pair in matrix_data['content_pairs']+matrix_data['support_pairs']:
        fields = ('pair_id', 'inventory_id', 'locale', 'owner_task', 'primary_keyword_or_seed',
                  'primary_wording_status', 'target_evidence_records', 'additional_editorial_seed',
                  'additional_seed_status', 'monthly_search_volume', 'keyword_difficulty', 'CPC',
                  'scope', 'keyword_target')
        maps[(pair['inventory_id'], pair['locale'])] = {key: pair[key] for key in fields if key in pair}
    return aliases, maps


def clean_fragment_ids(values):
    """Keep actual ID strings, never unresolved Liquid or data-*-id values."""
    return {value for value in values if isinstance(value, str) and value
            and not re.search(r'[\s{}<>]', value)}


def document_fragment_ids(doc, key, projects, bibliographies):
    body = doc['body']
    ids = {'top'} | clean_fragment_ids(re.findall(r'(?<![\w:-])id\s*=\s*["\']([^"\']+)', body, re.I))
    # These support identities render data-driven includes whose IDs are
    # absent from their Markdown source. Match the include, not a locale prefix.
    if key in ('page:learn', 'page:learn-cats', 'page:research', 'page:research-project'):
        local_index = re.search(r'{%-?\s*include\s+localized-project-index\.html\b([^%]*)%}', body)
        english_index = 'include library-project-browser.html' in body
        english_cats = key == 'page:learn-cats' and 'include library-project.html' in body
        if local_index or english_index or english_cats:
            cats_only = english_cats or bool(local_index and re.search(r'\bcats_only\s*=\s*true\b', local_index.group(1)))
            for project in projects:
                if cats_only and project.get('id') != 'feline-urinary': continue
                identity = project.get('id')
                if identity in clean_fragment_ids([identity]):
                    ids.update(('project-'+identity, 'project-'+identity+'-title'))
            if local_index and not cats_only: ids.add('localized-project-select')
    if key in ('page:research', 'page:research-library'):
        local_publications = 'include localized-publications.html' in body
        english_publications = 'include research-publications.html' in body
        if local_publications or english_publications:
            ids.add('referenced-publications')
            if english_publications: ids.add('referenced-publications-title')
            for bibliography in bibliographies:
                identity = bibliography.get('id')
                if identity in clean_fragment_ids([identity]): ids.add('publications-'+identity)
    return sorted(ids)


def build_registry(root):
    root = Path(root).resolve()
    documents = read_documents(root)
    english = [doc for doc in documents if not doc['file'].startswith('_localized/')]
    translated = [doc for doc in documents if doc['file'].startswith('_localized/')]
    base_ui = read_ui(root, 'en')
    consumer_cards = json.loads((root/'_data/library.json').read_text()).get('cards', {})
    consumer_reports = json.loads((root/'_data/research.json').read_text()).get('projects', [])
    project_file = root/'_data/library_projects.json'
    projects = json.loads(project_file.read_text()).get('projects', []) if project_file.is_file() else []
    bibliography_file = root/'_data/research_publications.json'
    bibliographies = json.loads(bibliography_file.read_text()).get('projects', []) if bibliography_file.is_file() else []
    inventory_aliases, keyword_maps = read_handover(root)
    resources, paths, routes = {}, {}, {}
    for doc in english:
        meta, filename = doc['meta'], doc['file']
        key, route = translation_key(doc), source_route(doc)
        assert valid_route(route), f'{filename}: invalid English source route {route}'
        assert key not in resources and route not in routes, f'{filename}: duplicate English identity/route'
        is_feed = route.endswith('.xml')
        is_marketing = filename in ('index.html', '404.html') or filename.startswith('shop/')
        source_title = meta.get('title') or ('MSRA Lab' if filename == 'index.html' else 'MSRA Pet Health Library RSS' if is_feed else '')
        assert source_title and (doc['body'].strip() or meta.get('product')), f'{filename}: empty source page'
        digest = sha256((root/filename).read_bytes()).hexdigest()
        is_report = filename.startswith('_research/')
        is_resource = filename.startswith(('_articles/', '_research/')) or bool(meta.get('content_id'))
        kind = 'report' if is_report else 'article' if is_resource else 'page'
        if key == 'T24': kind = 'record'
        if key in ('H00', 'S00'): kind = 'collection'
        if is_feed: kind = 'feed'
        if is_marketing: kind = 'marketing'
        refs = [int(ref) for ref in meta.get('source_refs', [])]
        entry = {
            'translation_key': key, 'source_content_id': meta.get('content_id'),
            'inventory_id': inventory_aliases.get(route, key),
            'source_route': route, 'source_file': filename, 'source_sha256': digest,
            'source_prepared_date': str(meta.get('prepared_date') or meta.get('date') or '') or None,
            'source_clinical_review_status': meta.get('clinical_review_status') or 'source-state-not-recorded',
            'source_evidence_review_status': meta.get('evidence_review_status') or 'source-state-not-recorded',
            'kind': kind, 'scope': 'full-resource' if is_resource else 'supporting-page',
            'topic': 'feline-urinary' if '/cats/urinary-health/' in route or key == 'R00' else 'rabbit-gut' if is_report else None,
            'source_refs': refs, 'variants': {},
            'urgent': meta.get('urgent') is True or key in URGENT_PARAGRAPHS,
            'urgent_paragraph': URGENT_PARAGRAPHS.get(key),
            'product': meta.get('product'),
        }
        entry['variants']['en'] = {
            'locale': 'en', 'locale_key': key+'::en', 'url': route, 'document_sha256':digest,
            'title': source_title, 'display_title': consumer_cards.get(meta.get('content_id'), {}).get('title') or next((report.get('card_title') for report in consumer_reports if report.get('url') == route), None) or meta.get('display_title') or source_title,
            'summary': meta.get('summary') or meta.get('description') or '',
            'content_label': meta.get('content_label') or meta.get('label') or '',
            'source_file': filename, 'is_local_draft': False,
            'publication_state': meta.get('publication_state') or 'legacy-source',
            'native_review_status': meta.get('native_review_status') or 'source-state-not-recorded',
            'clinical_review_status': meta.get('clinical_review_status') or 'source-state-not-recorded',
            'release_approved': meta.get('release_approved') is True,
            'live_verified': False,
            'source_indexable': doc.get('effective_meta',meta).get('sitemap') is not False and 'noindex' not in str(doc.get('effective_meta',meta).get('robots','')) and key != 'page:not-found',
            'fragment_ids': document_fragment_ids(doc, key, projects, bibliographies),
        }
        resources[key] = entry
        paths[filename] = key
        routes[route] = {'translation_key': key, 'locale': 'en'}
    active_locales = {'en'}
    for doc in translated:
        meta, filename = doc['meta'], doc['file']
        locale, key = meta.get('locale'), meta.get('translation_key')
        assert locale in LOCALES and locale != 'en', f'{filename}: unsupported/English translation locale {locale}'
        assert key in resources, f'{filename}: unknown English translation_key {key}'
        source = resources[key]
        assert locale not in source['variants'], f'{filename}: duplicate ({key}, {locale})'
        assert meta.get('locale_key') == key+'::'+locale, f'{filename}: invalid locale_key'
        for field in ('source_content_id', 'source_route', 'source_file', 'source_sha256'):
            assert meta.get(field) == source[field], f'{filename}: stale or mismatched {field}; reconcile with English source'
        assert str(meta.get('source_prepared_date') or '') == str(source['source_prepared_date'] or ''), f'{filename}: source preparation date differs'
        expected_fields = dict(DRAFT_FIELDS)
        if source['kind'] == 'feed': expected_fields['layout'] = None
        if source['kind'] == 'marketing':
            expected_fields['layout'] = 'localized-marketing'
            assert meta.get('dictionary_sha256') == sha256((root/'assets/i18n'/(locale+'.json')).read_bytes()).hexdigest(), f'{filename}: marketing dictionary changed; regenerate'
            assert meta.get('generator_input_sha256') == marketing_source_fingerprint(root), f'{filename}: source templates changed; regenerate marketing editions'
        if source['scope'] == 'supporting-page' and meta.get('clinical_review_status') == 'not-applicable':
            expected_fields['clinical_review_status'] = 'not-applicable'
        for field, expected in expected_fields.items():
            assert meta.get(field) == expected, f'{filename}: {field} must remain {expected!r}'
        required_text = ('title', 'description') if source['kind'] == 'feed' else TEXT_FIELDS
        for field in required_text:
            assert isinstance(meta.get(field), str) and meta[field].strip(), f'{filename}: missing translated {field}'
        if source['kind'] != 'feed':
            reading_time = meta.get('reading_time')
            assert reading_time is None or (isinstance(reading_time, (int, float)) and reading_time > 0), f'{filename}: invalid reading_time'
        assert meta.get('source_refs') == source['source_refs'], f'{filename}: source reference identities differ'
        route = meta.get('permalink')
        assert valid_route(route) and route == local_route(source['source_route'], locale), f'{filename}: permalink must preserve the English route under /{locale.lower()}/'
        assert route not in routes, f'{filename}: duplicate localized route'
        assert doc['body'].strip() and not re.fullmatch(r'(todo|placeholder|coming soon)[\s.!]*', doc['body'].strip(), re.I), f'{filename}: empty translation body'
        assert not re.search(r'^#\s+\S', doc['body'], re.M), f'{filename}: layout owns H1; remove the body H1'
        ui = read_ui(root, locale)
        assert set(ui) == set(base_ui), f'{locale}: UI keys differ from en.json'
        for field in ('source_search_results',):
            assert set(re.findall(r'\{\w+\}', ui[field])) == set(re.findall(r'\{\w+\}', base_ui[field])), f'{locale}.{field}: UI placeholders changed'
        if source['kind'] == 'marketing':
            source['variants']['en']['fragment_ids'] = sorted({'top'} | clean_fragment_ids(meta.get('source_fragment_ids', [])))
        source['variants'][locale] = {
            'locale': locale, 'locale_key': meta['locale_key'], 'url': route, 'document_sha256':sha256((root/filename).read_bytes()).hexdigest(),
            **{field: meta.get(field) or '' for field in TEXT_FIELDS},
            'reading_time': meta.get('reading_time'), 'file': filename,
            'is_local_draft': True, 'translation_status': meta['translation_status'],
            'native_review_status': meta['native_review_status'],
            'clinical_review_status': meta['clinical_review_status'],
            'release_approved': meta['release_approved'],
            'publication_state': meta['publication_state'], 'live_verified': False,
            'fragment_ids': document_fragment_ids(doc, key, projects, bibliographies),
        }
        routes[route] = {'translation_key': key, 'locale': locale}
        active_locales.add(locale)
    for key, resource in resources.items():
        inventory_id = resource['inventory_id']
        resource['keyword_maps'] = {locale: keyword_maps[(inventory_id, locale)] for locale in LOCALES if (inventory_id, locale) in keyword_maps}
        resource['pair_states'] = {}
        for locale in LOCALES:
            variant = resource['variants'].get(locale)
            resource['pair_states'][locale] = {
                'body_status': ('existing-english-source' if locale == 'en' else 'ai-draft') if variant else 'missing',
                'native_review_status': variant['native_review_status'] if variant else 'not-performed',
                'clinical_review_status': variant['clinical_review_status'] if variant else 'not-performed',
                'release_approved': variant['release_approved'] if variant else False,
                'live_verified': False,
            }
    catalog = {locale: {'label': label, 'html_lang': locale,
                        'route_prefix': '' if locale == 'en' else '/'+locale.lower(),
                        'og_locale': og, 'has_actual_pages': locale in active_locales}
               for locale, (label, og) in LOCALES.items()}
    return {
        'schema_version': 1,
        'artifact_role': 'Actual source and local-draft routes; no record asserts a verified live translation.',
        'default_locale': 'en', 'live_hreflang_enabled': False,
        'locales': catalog, 'resources': resources, 'by_route': routes,
        'coverage': {locale: {
            'full_resources': [key for key, resource in resources.items() if resource['scope'] == 'full-resource' and locale in resource['variants']],
            'missing_full_resources': [key for key, resource in resources.items() if resource['scope'] == 'full-resource' and locale not in resource['variants']],
            'supporting_pages': [key for key, resource in resources.items() if resource['scope'] == 'supporting-page' and locale in resource['variants']],
            'missing_supporting_pages': [key for key, resource in resources.items() if resource['scope'] == 'supporting-page' and locale not in resource['variants']],
        } for locale in catalog},
        'counts': {'english_resources': sum(r['scope'] == 'full-resource' for r in resources.values()),
                   'english_supporting_pages': sum(r['scope'] == 'supporting-page' for r in resources.values()),
                   'translated_pages': len(translated),
                   'commissioned_content_pairs': len(LOCALES)*sum(r['scope'] == 'full-resource' for r in resources.values()),
                   'commissioned_support_pairs': len(LOCALES)*sum(r['scope'] == 'supporting-page' for r in resources.values())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true', help='verify registry freshness without writing')
    args = parser.parse_args()
    root = args.root.resolve()
    registry = build_registry(root)
    destination = root/'_data'/'localization_registry.json'
    encoded = json.dumps(registry, ensure_ascii=False, indent=2)+'\n'
    if args.check:
        assert destination.is_file() and destination.read_text() == encoded, 'Localization registry is stale; run tools/prepare_localizations.py'
    else:
        destination.write_text(encoded)
    print(json.dumps({'registry': str(destination), 'check_only': args.check, **registry['counts']}))


if __name__ == '__main__':
    main()
