#!/usr/bin/env python3
"""Snapshot sourced local wording and apply per-page SEO targets, without metrics fiction.

The three input schemas intentionally distinguish publisher wording, observed
search features and actual query/volume data. Normalization retains the original
records in a repository snapshot. Utility pages get metadata, not invented demand.
An optional google_keyword_evidence.json snapshot can replace selected targets
with positive historical Planner aggregates. Its raw rows, actual scope and
optional content pins are checked; unresolved UI ranges remain null.
"""
import argparse
from copy import deepcopy
from datetime import date
from decimal import Decimal
from hashlib import sha256
from html import unescape
import json
import math
from pathlib import Path
import re
from prepare_localizations import ROOT, read_documents

FILES = ('PRIORITY_MARKET_KEYWORDS.json', 'EUROPE_NORTH_EAST_KEYWORDS.json', 'ASIA_PORTUGUESE_KEYWORDS.json')
NAVIGATION_HUBS = {
    'page:learn': ('pet_health_library_navigation', 'general_library_navigation'),
    'page:learn-cats': ('cat_health_collection_navigation', 'species_collection_navigation'),
    'page:research': ('open_research_index_navigation', 'open_research_navigation'),
}
QUERY_EVIDENCE_CLASSES = {
    'google_keyword_planner_aggregate',
    'google_search_console_aggregate_query',
    'google_trends_aggregate_related_query',
}
PLANNER_CLASS = 'google_keyword_planner_aggregate'
PLANNER_METRIC_STATE = 'account_coarsened_UI_range_not_exact_monthly_volume'
PLANNER_UNRESOLVED_STATE = 'positive_coarsened_export_UI_range_unresolved'
PLANNER_UI_ONLY_STATE = 'positive_historical_UI_range_no_csv_export'
PLANNER_STATUS = 'positive_google_planner_aggregate_in_recorded_market'
PLANNER_MODES = {'Discover new keywords', 'Get search volume and forecasts'}
LOCALE_LANGUAGES = {
    'en': {'english'}, 'de': {'german'}, 'fr': {'french'}, 'it': {'italian'},
    'es': {'spanish'}, 'nl': {'dutch'}, 'pl': {'polish'}, 'sv': {'swedish'},
    'da': {'danish'}, 'nb': {'norwegian', 'norwegian bokmål'}, 'fi': {'finnish'},
    'ja': {'japanese'}, 'pt-BR': {'portuguese'}, 'pt-PT': {'portuguese'},
    'ko': {'korean'}, 'zh-Hans': {'chinese (simplified)', 'simplified chinese'},
    'ru': {'russian'}, 'hi': {'hindi'},
}
# Country is an explicit source setting, not something inferred from its locale.
ISO_COUNTRY_CODES = set(('AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE '
    'BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL '
    'CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ '
    'FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM '
    'HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP '
    'KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM '
    'MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ '
    'OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD '
    'SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL '
    'TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE '
    'YT ZA ZM ZW').split())


def clean(value):
    return ' '.join(unescape(re.sub('<[^>]+>', '', value or '')).split())


def normal(record, filename):
    phrases = record.get('target_phrases', [])
    primary = record.get('primary_keyword') or record.get('primary_candidate') or (phrases[0]['phrase'] if phrases else '')
    secondary = record.get('secondary_keywords') or record.get('secondary_candidates') or [item['phrase'] for item in phrases[1:]]
    return {
        'record_id':record.get('record_id') or record['target_id'],
        'locale':record['locale'], 'family':record.get('family') or record.get('content_family') or record['family_id'],
        'source_route':record.get('existing_English_route') or record['retained_english_route'],
        'primary':primary, 'secondary':secondary,
        'title':record.get('draft_localized_title') or record.get('proposed_title') or record.get('proposed_title_pending_native_review'),
        'description':record.get('draft_meta_description') or record.get('proposed_meta_description') or record.get('proposed_meta_description_pending_native_review'),
        'evidence_class':record.get('phrase_evidence_class') or record.get('evidence_class') or 'editorial_candidate_not_observed_search_query',
        'source_file':filename, 'original_record':record,
        'monthly_search_volume':None, 'keyword_difficulty':None, 'CPC':None,
    }


def apply_navigation_hub_policy(key, entry, page_target):
    """Do not turn three different navigation hubs into one acquisition target.

    A family brief is not evidence for a page-specific hub query. A future matrix
    may supply an explicit ``page_specific_target`` with a primary_keyword,
    target_record_id, keyword_evidence_class and source_evidence_refs. Its evidence
    must be classified aggregate query data, not publisher wording or a seed.
    Titles, descriptions and the existing page-specific intent stay unchanged.
    """
    if key not in NAVIGATION_HUBS:
        return entry
    intent, role = NAVIGATION_HUBS[key]
    entry.update({
        'primary_keyword': None, 'secondary_keywords': [],
        'intent_family': intent,
        'keyword_role': role + '_no_evidence_backed_page_specific_target',
        'keyword_evidence_class': 'navigation_no_evidence_backed_page_specific_target',
        'target_record_id': None,
    })
    override = page_target.get('page_specific_target') or {}
    refs = override.get('source_evidence_refs')
    if (clean(override.get('primary_keyword')) and override.get('target_record_id')
            and override.get('keyword_evidence_class') in QUERY_EVIDENCE_CLASSES
            and isinstance(refs, list) and refs
            and all(isinstance(ref, str) and ref.strip() for ref in refs)):
        entry.update({
            'primary_keyword': clean(override['primary_keyword']),
            'secondary_keywords': override.get('secondary_keywords') or [],
            'keyword_role': role + '_with_evidence_backed_page_specific_target',
            'keyword_evidence_class': override['keyword_evidence_class'],
            'target_record_id': override['target_record_id'],
            'source_evidence_refs': refs,
        })
    return entry


def require(condition, where, message):
    if not condition:
        raise ValueError(f'{where}: {message}')


def nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def countries(value, where):
    require(isinstance(value, list) and bool(value), where, 'country_codes must be a nonempty ISO2 list')
    require(all(isinstance(item, str) and item in ISO_COUNTRY_CODES for item in value),
            where, 'country_codes contains an invalid ISO2 country')
    require(len(value) == len(set(value)), where, 'country_codes contains duplicates')
    return sorted(value)


def historical_context(record, where, registry_run_id):
    """Validate declared, frozen run scope without inferring language from IP.

    The raw CSV and controls are verified upstream. This deterministic importer
    compares each row to that frozen source registry; it makes no new network
    request and cannot turn a declared hash into an independent source audit.
    language_setting records the actual ideas control. Historical averages cover
    the term and close variants regardless of user language; a single-language
    ideas filter is not a measured native-speaker or audience restriction.
    """
    require(isinstance(record, dict), where, 'context must be an object')
    locale = record.get('locale')
    require(isinstance(locale, str) and locale in LOCALE_LANGUAGES, where, 'unsupported locale')
    setting = record.get('language_setting')
    require(nonempty_text(setting), where, 'actual language_setting is required')
    language = setting.strip().casefold()
    all_languages = language == 'all languages'
    require(all_languages or language in LOCALE_LANGUAGES[locale], where,
            'language_setting does not match the declared locale or All languages')
    scope = 'all_languages' if all_languages else 'single_language'
    if 'language_filter_scope' in record:
        require(record['language_filter_scope'] == scope, where, 'language_filter_scope contradicts the actual filter')
    if 'locale_is_language_filter' in record:
        require(type(record['locale_is_language_filter']) is bool
                and record['locale_is_language_filter'] == (not all_languages),
                where, 'locale_is_language_filter contradicts the actual filter')
    require(record.get('network') == 'Google', where, 'network must be the recorded Google-only scope')
    require(isinstance(record.get('mode'), str) and record['mode'] in PLANNER_MODES,
            where, 'unsupported Planner mode')
    require(record.get('data_kind') == 'historical', where, 'forecast or unknown data_kind is not historical evidence')
    parsed_dates = {}
    for field in ('date_start', 'date_end', 'retrieved_on'):
        value = record.get(field)
        require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), where, f'{field} must be an ISO date')
        try:
            parsed_dates[field] = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f'{where}: {field} is not a valid date') from error
    require(parsed_dates['date_start'] <= parsed_dates['date_end'] < parsed_dates['retrieved_on'],
            where, 'historical dates must end before retrieval and start no later than they end')
    artifact_kind = record.get('source_artifact_kind', 'planner_csv')
    require(artifact_kind in ('planner_csv', 'planner_ui_transcript'), where,
            'source_artifact_kind must identify a Planner CSV or captured UI transcript')
    if artifact_kind == 'planner_ui_transcript':
        require(record.get('raw_export_available') is False, where,
                'a UI transcript must explicitly state that no CSV export is available')
    elif 'raw_export_available' in record:
        require(record['raw_export_available'] is True, where,
                'CSV evidence cannot claim that its raw export is unavailable')
    raw_hash = record.get('raw_file_sha256')
    require(isinstance(raw_hash, str) and re.fullmatch(r'[0-9a-f]{64}', raw_hash),
            where, 'raw_file_sha256 must hash the declared CSV or UI-transcript artifact')
    if 'source_capture_sha' in record:
        require(record['source_capture_sha'] == raw_hash, where,
                'source_capture_sha differs from the declared artifact hash')
    if 'source_artifact_path' in record:
        require(nonempty_text(record['source_artifact_path']), where,
                'source_artifact_path must identify the actual captured artifact')
    source_run_id = record.get('source_run_id', registry_run_id)
    require(nonempty_text(source_run_id), where, 'underlying source run ID must be text')
    return {
        'locale': locale, 'country_codes': countries(record.get('country_codes'), where),
        'language_setting': setting, 'network': record['network'],
        'date_start': record['date_start'], 'date_end': record['date_end'],
        'retrieved_on': record['retrieved_on'], 'raw_file_sha256': raw_hash,
        'mode': record['mode'], 'data_kind': record['data_kind'],
        'language_filter_scope': scope, 'locale_is_language_filter': not all_languages,
        'source_artifact_kind': artifact_kind,
        'source_run_id': source_run_id,
    }


def validate_planner_row(record, sources, selected_phrases, target_locale, where):
    require(isinstance(record, dict), where, 'evidence row must be an object')
    require(record.get('evidence_class') == PLANNER_CLASS, where, 'row is not Google Keyword Planner aggregate evidence')
    run_id = record.get('run_id')
    require(isinstance(run_id, str) and run_id in sources, where, 'run_id is absent from the source registry')
    context = historical_context(record, where, run_id)
    require(context['locale'] == target_locale, where, 'evidence locale differs from target locale')
    require(context == sources[run_id], where, 'row scope, dates or raw hash differs from its source run')
    row_id = record.get('row_id')
    require(isinstance(row_id, str) and re.fullmatch(re.escape(run_id) + r':row:\d{5,}', row_id),
            where, 'row_id must identify a source data row in its run')
    row_number = int(row_id.rsplit(':', 1)[1])
    require(row_number > 0, where, 'row_id must identify a positive data row')
    if 'raw_data_record_1based' in record:
        require(type(record['raw_data_record_1based']) is int and record['raw_data_record_1based'] == row_number,
                where, 'raw_data_record_1based differs from row_id')
    phrase = record.get('keyword_label_verbatim')
    require(nonempty_text(phrase) and phrase in selected_phrases, where,
            'keyword_label_verbatim is not an exact selected phrase')
    require(record.get('reported_positive_aggregate_support') is True, where, 'positive aggregate support is required')
    state = record.get('metric_state')
    require(state in (PLANNER_METRIC_STATE, PLANNER_UNRESOLVED_STATE, PLANNER_UI_ONLY_STATE), where,
            'metric is unknown, exact or forecast rather than positive historical aggregate support')
    raw_average = record.get('avg_monthly_searches_export_verbatim')
    if state == PLANNER_UI_ONLY_STATE:
        require(context['source_artifact_kind'] == 'planner_ui_transcript', where,
                'UI-only support must identify the captured transcript, not a CSV')
        require('avg_monthly_searches_export_verbatim' in record and raw_average is None, where,
                'UI-only evidence cannot fabricate a numerical CSV export field')
        observation_id = record.get('source_ui_observation_id')
        source_run = context['source_run_id']
        require(nonempty_text(source_run) and isinstance(observation_id, str)
                and re.fullmatch(re.escape(source_run) + r':ui-observation:\d{2,}', observation_id), where,
                'UI-only evidence must retain its underlying captured observation ID')
        require(int(observation_id.rsplit(':', 1)[1]) == row_number, where,
                'internal UI row order differs from the captured observation order')
    else:
        require(context['source_artifact_kind'] == 'planner_csv', where,
                'CSV metric states require a Planner CSV artifact')
        require(isinstance(raw_average, str) and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', raw_average),
                where, 'zero or unknown average cannot support a selected phrase')
        # CSV codes can be 500 or 500.0. Preserve the string and test positivity,
        # without treating the code as a monthly search count or a UI-only value.
        raw_positive_value = Decimal(raw_average)
        require(raw_positive_value.is_finite() and raw_positive_value > 0,
                where, 'zero or unknown average cannot support a selected phrase')
    band = record.get('monthly_searches_UI_range')
    if state == PLANNER_UNRESOLVED_STATE:
        require('monthly_searches_UI_range' in record and band is None, where,
                'an unresolved UI range must remain explicitly null')
    else:
        require(isinstance(band, dict) and nonempty_text(band.get('display')), where, 'a directly witnessed UI range is required')
        require(band.get('basis_type') == 'direct_keyword_label_UI_observation'
                and nonempty_text(band.get('basis')), where,
                'UI range requires direct exact-label observation provenance, not code inference')
        lower, upper = band.get('lower'), band.get('upper')
        require(all(type(value) is int or type(value) is float and math.isfinite(value) for value in (lower, upper))
                and 0 < lower < upper, where, 'UI range must have finite positive ordered bounds')
        # Export representatives are account-coarsened codes. Their magnitude
        # must not be used to infer, or contradict, a separately witnessed band.
        if 'account_coarsening' in band:
            require(band['account_coarsening'] is True, where, 'range must retain its account-coarsening status')
        if state == PLANNER_UI_ONLY_STATE:
            # The displayed band is the only positive metric in this state.
            # Reject zero-inclusive or contradictory labels as well as invented
            # numeric fields; do not infer a midpoint or a CSV representative.
            displayed_number = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?[KkMm]?'
            match = re.fullmatch(r'\s*(' + displayed_number + r')\s*[–—-]\s*(' + displayed_number + r')\s*', band['display'])
            require(match is not None, where, 'UI-only range display is not a captured numeric band')
            displayed = []
            for text in match.groups():
                scale = Decimal(1000 if text[-1:].casefold() == 'k' else 1000000 if text[-1:].casefold() == 'm' else 1)
                displayed.append(Decimal(text.rstrip('KkMm').replace(',', '')) * scale)
            require(displayed == [Decimal(str(lower)), Decimal(str(upper))] and 0 < displayed[0] < displayed[1],
                    where, 'UI-only displayed range must itself have positive matching bounds')
    for metric in ('exact_monthly_search_volume', 'monthly_search_volume',
            'keyword_difficulty', 'CPC', 'actual_CPC', 'organic_keyword_difficulty'):
        require(record.get(metric) is None, where, f'a coarse Planner row cannot establish {metric}')
    require(record.get('is_individual_query_log', False) is False, where, 'aggregate data is not an individual query log')
    return context


def safe_pin_file(filename, root, where):
    require(nonempty_text(filename) and '\\' not in filename and '\x00' not in filename,
            where, 'a pin must identify a contained relative file')
    path = Path(filename)
    require(not path.is_absolute() and all(part not in ('.', '..') for part in filename.split('/')),
            where, 'a pin must not use an absolute or traversing path')
    require(path.as_posix() not in {'_data/google_keyword_evidence.json', '_data/localized_seo.json'},
            where, 'keyword snapshot and generated metadata cannot pin themselves')
    try:
        resolved = (root/path).resolve(strict=True)
        resolved.relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise ValueError(f'{where}: pinned file is missing or outside the source root') from error
    require(resolved.is_file(), where, 'a pin must identify a file')
    return resolved


def validate_content_pins(target, registry, root, where):
    """Optional content-fit pins are checked, never silently ignored.

    Source pins refer to the canonical source document. Translated-edition pins
    can be added under a separate future contract; a source pin does not pretend
    to be native review of a translated edition.
    """
    file_key, hash_key = 'source_file_at_curation', 'source_document_sha256_at_curation'
    if file_key in target or hash_key in target:
        require(file_key in target and hash_key in target, where, 'source file and document hash pins must be supplied together')
        require(registry is not None, where, 'source document pins require the actual route registry')
        resource = registry.get('resources', {}).get(target['translation_key'], {})
        filename, digest = target[file_key], target[hash_key]
        require(filename == resource.get('source_file'), where, 'source file pin differs from the registered identity')
        require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest), where, 'source document pin must be a SHA-256')
        require(digest == resource.get('source_sha256'), where, 'source document pin differs from the registered source hash')
        english_hash = resource.get('variants', {}).get('en', {}).get('document_sha256')
        if english_hash:
            require(digest == english_hash, where, 'source document pin differs from the English document identity')
        require(sha256(safe_pin_file(filename, root, where).read_bytes()).hexdigest() == digest,
                where, 'curation source document has changed')
    if 'dependency_sha256' in target:
        dependencies = target['dependency_sha256']
        require(isinstance(dependencies, dict) and bool(dependencies), where, 'dependency_sha256 must be a nonempty file/hash map')
        for filename, digest in dependencies.items():
            require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest), where, 'dependency pin must be a SHA-256')
            require(sha256(safe_pin_file(filename, root, where).read_bytes()).hexdigest() == digest,
                    where, f'curation dependency has changed: {filename}')


def validate_verified_targets(snapshot, registry=None, root=ROOT):
    """Return a validated optional target map; never grant a new hub target.

    Required snapshot schema: ``schema_version: 1``, ``sources`` keyed by run_id,
    and ``targets``. Sources carry historical_context fields. Targets carry
    translation_key, locale, primary_keyword, secondary_keywords,
    source_evidence_refs (selected row IDs) and evidence_records. Each row repeats
    its source context and supplies its exact label, row ID and positive coarse
    support. A directly observed exact-label range needs explicit provenance;
    an unresolved CSV UI range stays null. UI-only historical support explicitly
    identifies a hashed transcript and has no numerical CSV field. Optional title and description must be
    supplied together. Supplied source/dependency file pins are verified.
    """
    require(isinstance(snapshot, dict) and type(snapshot.get('schema_version')) is int
            and snapshot['schema_version'] == 1, 'verified targets', 'unsupported schema_version')
    source_input = snapshot.get('sources')
    require(isinstance(source_input, dict), 'verified targets', 'a sources registry is required')
    sources = {}
    for run_id, source in source_input.items():
        require(nonempty_text(run_id), 'verified targets', 'source run ID must be text')
        sources[run_id] = historical_context(source, f'source {run_id}', run_id)
    targets = snapshot.get('targets')
    require(isinstance(targets, list), 'verified targets', 'targets must be a list')
    result = {}
    for index, target in enumerate(targets):
        where = f'verified target {index + 1}'
        require(isinstance(target, dict), where, 'target must be an object')
        key, locale = target.get('translation_key'), target.get('locale')
        require(nonempty_text(key) and isinstance(locale, str) and locale in LOCALE_LANGUAGES,
                where, 'translation_key and supported locale are required')
        if registry is not None:
            resource = registry.get('resources', {}).get(key)
            require(isinstance(resource, dict) and locale in resource.get('variants', {})
                    and resource.get('kind') != 'feed', where, 'target must identify an actual HTML edition')
        validate_content_pins(target, registry, root, where)
        pair = (key, locale)
        require(pair not in result, where, 'duplicate target identity and locale')
        primary, secondary = target.get('primary_keyword'), target.get('secondary_keywords')
        require(nonempty_text(primary), where, 'a nonempty primary_keyword is required')
        require(isinstance(secondary, list) and len(secondary) <= 3
                and all(nonempty_text(phrase) for phrase in secondary), where, 'secondary_keywords must contain at most three phrases')
        phrases = [primary] + secondary
        require(len(phrases) == len(set(phrases)), where, 'selected phrases must be unique')
        refs, evidence = target.get('source_evidence_refs'), target.get('evidence_records')
        require(isinstance(refs, list) and bool(refs) and all(nonempty_text(ref) for ref in refs)
                and len(refs) == len(set(refs)), where, 'unique selected source row references are required')
        require(isinstance(evidence, list) and bool(evidence), where, 'evidence_records must be nonempty')
        supported, row_ids, contexts = set(), [], []
        for row_index, record in enumerate(evidence):
            contexts.append(validate_planner_row(record, sources, phrases, locale, f'{where}, row {row_index + 1}'))
            supported.add(record['keyword_label_verbatim'])
            row_ids.append(record['row_id'])
        require(supported == set(phrases), where, 'every selected phrase needs an exact positive source row')
        require(len(row_ids) == len(set(row_ids)) and set(refs) == set(row_ids),
                where, 'source_evidence_refs must exactly identify the unique selected evidence rows')
        geographic_scope = sorted({country for context in contexts for country in context['country_codes']})
        if 'geographic_scope' in target:
            require(countries(target['geographic_scope'], where) == geographic_scope,
                    where, 'geographic_scope differs from the selected evidence')
        if 'status' in target:
            require(target['status'] == PLANNER_STATUS, where, 'target status is not positive aggregate support')
        overrides = {}
        if 'title' in target or 'description' in target:
            require(isinstance(target.get('title'), str) and isinstance(target.get('description'), str),
                    where, 'title and description overrides must both be supplied')
            overrides = {field: clean(target[field]) for field in ('title', 'description')}
            require(all(overrides.values()), where, 'title and description overrides must both clean to nonempty text')
        verified = deepcopy(target)
        verified.update(overrides)
        verified['evidence_scope'] = {
            'locale': locale, 'country_codes': geographic_scope,
            'language_settings': sorted({context['language_setting'] for context in contexts}),
            'language_filters': [dict(language_setting=setting,
                language_filter_scope='all_languages' if setting.strip().casefold() == 'all languages' else 'single_language',
                locale_is_language_filter=setting.strip().casefold() != 'all languages')
                for setting in sorted({context['language_setting'] for context in contexts})],
            'network': 'Google', 'data_kind': 'historical',
            # Google Ads help 3022575: historical averages include close variants
            # regardless of language. Keep actual language controls separately.
            'historical_metric_scope': 'term_and_close_variants_in_recorded_country_network_period_regardless_user_language',
            'metric_states': sorted({record['metric_state'] for record in evidence}),
            'historical_periods': sorted({(context['date_start'], context['date_end']) for context in contexts}),
            'run_ids': sorted({record['run_id'] for record in evidence}),
        }
        result[pair] = verified
    return result


def load_verified_targets(path, registry=None, root=ROOT):
    return validate_verified_targets(json.loads(path.read_text()), registry, root) if path.is_file() else {}


def apply_verified_target(key, locale, entry, verified_targets):
    """Apply curated observed terms after hub policy, without inventing metrics."""
    if key in NAVIGATION_HUBS:
        return entry
    target = verified_targets.get((key, locale))
    if target is None:
        return entry
    entry.update({
        'primary_keyword': target['primary_keyword'],
        'secondary_keywords': target['secondary_keywords'],
        'keyword_role': 'curated_google_planner_terms_for_existing_page_intent',
        'keyword_evidence_class': PLANNER_CLASS,
        'keyword_evidence_status': PLANNER_STATUS,
        'target_record_id': f'google-planner:{key}::{locale}',
        'source_evidence_refs': target['source_evidence_refs'],
        'keyword_evidence_records': target['evidence_records'],
        'keyword_evidence_scope': target['evidence_scope'],
        'monthly_search_volume': None, 'keyword_difficulty': None, 'CPC': None,
    })
    if 'title' in target:
        entry.update({field: target[field] for field in ('title', 'description')})
    pins = {field: target[field] for field in ('source_file_at_curation',
        'source_document_sha256_at_curation', 'dependency_sha256') if field in target}
    if pins:
        entry['keyword_evidence_content_pins'] = pins
    return entry


def build_metadata(snapshot, registry, documents, verified_targets):
    records = {(record['locale'],record['source_route']):record for record in snapshot['records']}
    page_targets = {(pair['translation_key'],pair['locale']):pair for pair in snapshot.get('FULL_SITE_LOCALE_PAGE_MATRIX.json', {}).get('pairs', [])}
    metadata, count = {}, 0
    for key, resource in registry['resources'].items():
        metadata[key] = {}
        for locale, variant in resource['variants'].items():
            if resource['kind'] == 'feed': continue
            file = resource['source_file'] if locale == 'en' else variant['file']
            doc = documents[file]
            meta = doc['meta']
            record = records.get((locale,resource['source_route']))
            # The per-family brief owns only its primary page. Other resources
            # retain distinct, already localized titles and their actual intent.
            title = clean((record or {}).get('title') or meta.get('seo_title') or variant['display_title'] or variant['title'])
            description = clean((record or {}).get('description') or meta.get('description') or variant.get('summary'))
            prior = resource.get('keyword_maps', {}).get(locale, {})
            page_target = page_targets.get((key,locale), {})
            primary = page_target.get('primary_keyword_brief') if page_target else (record or {}).get('primary') or prior.get('primary_keyword_or_seed')
            if not primary and not page_target and resource['scope'] == 'full-resource': primary = variant['display_title'] or variant['title']
            metadata[key][locale] = {
                'title':title, 'description':description, 'primary_keyword':primary,
                'secondary_keywords':(record or {}).get('secondary', []),
                'intent_family':page_target.get('family_id') or (record or {}).get('family'),
                'page_specific_intent':page_target.get('page_specific_intent'),
                'keyword_role':page_target.get('keyword_role'),
                'target_record_id':(record or {}).get('record_id') or prior.get('pair_id'),
                'keyword_evidence_class':(record or {}).get('evidence_class') or prior.get('primary_wording_status') or 'utility-not-keyword-targeted',
                'source_route':resource['source_route'], 'locale_route':variant['url'],
                'monthly_search_volume':None, 'keyword_difficulty':None, 'CPC':None,
            }
            apply_navigation_hub_policy(key, metadata[key][locale], page_target)
            apply_verified_target(key, locale, metadata[key][locale], verified_targets)
            count += 1
    return metadata, count, len(records)


def save_or_check_metadata(path, metadata, check=False):
    encoded = json.dumps(metadata, ensure_ascii=False, indent=2) + '\n'
    if check:
        return path.is_file() and path.read_text() == encoded
    path.write_text(encoded)
    return True


def run_self_test():
    """Offline policy fixtures; temporary files only, no repository mutation."""
    import io
    import tempfile
    import unittest

    counters = {'valid_cases': 0, 'invalid_cases': 0}

    def fixture(locale='en', country='US', language='English'):
        run_id = 'fixture-run'
        source = {'locale': locale, 'country_codes': [country], 'language_setting': language,
            'network': 'Google', 'date_start': '2025-10-01', 'date_end': '2026-09-30',
            'retrieved_on': '2026-10-29', 'raw_file_sha256': sha256(b'fixture raw export').hexdigest(),
            'mode': 'Discover new keywords', 'data_kind': 'historical'}
        row = dict(deepcopy(source), evidence_class=PLANNER_CLASS, run_id=run_id,
            row_id=run_id + ':row:00001', raw_data_record_1based=1,
            keyword_label_verbatim='cat not peeing', reported_positive_aggregate_support=True,
            metric_state=PLANNER_METRIC_STATE, avg_monthly_searches_export_verbatim='500',
            monthly_searches_UI_range={'display': '100–1K', 'lower': 100, 'upper': 1000,
                'account_coarsening': True, 'basis_type': 'direct_keyword_label_UI_observation',
                'basis': 'Fixture exact-label UI witness; no value-code inference.'}, exact_monthly_search_volume=None,
            is_individual_query_log=False)
        return {'schema_version': 1, 'sources': {run_id: source}, 'targets': [{
            'translation_key': 'G01', 'locale': locale, 'primary_keyword': 'cat not peeing',
            'secondary_keywords': [], 'source_evidence_refs': [row['row_id']],
            'evidence_records': [row]}]}

    def set_path(snapshot, path, value):
        parent = snapshot
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = value

    def ui_only_fixture():
        snapshot = fixture('da', 'DK', 'Danish')
        source = snapshot['sources']['fixture-run']
        source.update(source_artifact_kind='planner_ui_transcript', raw_export_available=False,
            raw_file_sha256=sha256(b'{"kind":"fixture captured UI transcript"}').hexdigest(),
            source_artifact_path='fixtures/planner-ui-transcript.json')
        source['source_capture_sha'] = source['raw_file_sha256']
        row = snapshot['targets'][0]['evidence_records'][0]
        row.update(deepcopy(source), metric_state=PLANNER_UI_ONLY_STATE,
            avg_monthly_searches_export_verbatim=None,
            source_ui_observation_id='fixture-run:ui-observation:01')
        del row['raw_data_record_1based']
        return snapshot

    class PolicyTests(unittest.TestCase):
        def valid(self, snapshot):
            result = validate_verified_targets(snapshot)
            counters['valid_cases'] += 1
            return result

        def invalid(self, snapshot):
            with self.assertRaises(ValueError):
                validate_verified_targets(snapshot)
            counters['invalid_cases'] += 1

        def test_positive_terms_preserve_copy_and_null_exact_metrics(self):
            targets = self.valid(fixture())
            entry = {'title': 'Existing title', 'description': 'Existing description',
                'monthly_search_volume': 123, 'keyword_difficulty': 4, 'CPC': 5}
            apply_verified_target('G01', 'en', entry, targets)
            self.assertEqual(entry['primary_keyword'], 'cat not peeing')
            self.assertEqual(entry['title'], 'Existing title')
            self.assertEqual(entry['description'], 'Existing description')
            self.assertEqual(entry['keyword_evidence_class'], PLANNER_CLASS)
            self.assertEqual(entry['keyword_evidence_status'], PLANNER_STATUS)
            self.assertEqual(entry['keyword_evidence_scope']['country_codes'], ['US'])
            self.assertEqual(entry['keyword_evidence_scope']['historical_metric_scope'],
                'term_and_close_variants_in_recorded_country_network_period_regardless_user_language')
            for metric in ('monthly_search_volume', 'keyword_difficulty', 'CPC'):
                self.assertIsNone(entry[metric])

        def test_explicit_country_is_not_inferred_from_locale(self):
            for locale, country, language in [('en', 'GB', 'English'), ('fr', 'BE', 'French'),
                    ('pt-BR', 'US', 'Portuguese'), ('pt-PT', 'CA', 'Portuguese')]:
                with self.subTest(locale=locale, country=country):
                    self.assertIn(('G01', locale), self.valid(fixture(locale, country, language)))

        def test_all_languages_retains_honest_scope(self):
            entry = {}
            apply_verified_target('G01', 'fr', entry, self.valid(fixture('fr', 'FR', 'All languages')))
            self.assertEqual(entry['keyword_evidence_scope']['language_settings'], ['All languages'])
            self.assertEqual(entry['keyword_evidence_scope']['language_filters'], [{
                'language_setting': 'All languages', 'language_filter_scope': 'all_languages',
                'locale_is_language_filter': False}])

        def test_optional_snippets_are_a_sanitized_pair(self):
            snapshot = fixture()
            snapshot['targets'][0].update(title=' <b>Cat &amp; care</b> ', description=' A <em>useful</em>\n explanation. ')
            entry = {}
            apply_verified_target('G01', 'en', entry, self.valid(snapshot))
            self.assertEqual(entry['title'], 'Cat & care')
            self.assertEqual(entry['description'], 'A useful explanation.')
            for title, description in [('Only title', None), (None, 'Only description'), ('<b></b>', 'Description')]:
                item = fixture()
                if title is not None: item['targets'][0]['title'] = title
                if description is not None: item['targets'][0]['description'] = description
                self.invalid(item)

        def test_hub_policy_cannot_be_overridden_by_snapshot(self):
            for key in NAVIGATION_HUBS:
                snapshot = fixture()
                snapshot['targets'][0]['translation_key'] = key
                snapshot['targets'][0].update(title='Do not apply', description='Do not apply')
                entry = {'title': 'Existing hub', 'description': 'Navigation copy'}
                apply_navigation_hub_policy(key, entry, {})
                expected = deepcopy(entry)
                apply_verified_target(key, 'en', entry, self.valid(snapshot))
                self.assertEqual(entry, expected)

        def test_absent_snapshot_and_absent_target_preserve_fallback(self):
            with tempfile.TemporaryDirectory() as temporary:
                self.assertEqual(load_verified_targets(Path(temporary)/'missing.json'), {})
                counters['valid_cases'] += 1
            entry = {'primary_keyword': 'editorial target', 'title': 'Original'}
            original = deepcopy(entry)
            self.assertEqual(apply_verified_target('G02', 'en', entry, self.valid(fixture())), original)

        def test_multiple_exact_terms_and_source_rows(self):
            snapshot = fixture()
            target = snapshot['targets'][0]
            extra = deepcopy(target['evidence_records'][0])
            extra.update(keyword_label_verbatim='cat only peeing drops', row_id='fixture-run:row:00002', raw_data_record_1based=2)
            target['secondary_keywords'] = ['cat only peeing drops']
            target['evidence_records'].append(extra)
            target['source_evidence_refs'].append(extra['row_id'])
            self.assertEqual(len(self.valid(snapshot)[('G01', 'en')]['evidence_records']), 2)
            target['secondary_keywords'].append('unsupported secondary')
            self.invalid(snapshot)

        def test_historical_csv_decimal_range_representatives(self):
            for raw, lower, upper, display in [('5000.0', 1000, 10000, '1K–10K'),
                    ('500.0', 100, 1000, '100–1K'), ('50.0', 10, 100, '10–100')]:
                with self.subTest(raw=raw):
                    snapshot = fixture()
                    snapshot['sources']['fixture-run']['mode'] = 'Get search volume and forecasts'
                    row = snapshot['targets'][0]['evidence_records'][0]
                    row.update(mode='Get search volume and forecasts',
                        avg_monthly_searches_export_verbatim=raw,
                        monthly_searches_UI_range={'display': display, 'lower': lower,
                            'upper': upper, 'account_coarsening': True,
                            'basis_type': 'direct_keyword_label_UI_observation',
                            'basis': 'Fixture direct observation for the selected exact label.'})
                    entry = {}
                    apply_verified_target('G01', 'en', entry, self.valid(snapshot))
                    self.assertEqual(entry['keyword_evidence_records'][0]['avg_monthly_searches_export_verbatim'], raw)
                    self.assertIsNone(entry['monthly_search_volume'])

        def test_positive_export_with_unresolved_range_stays_unresolved(self):
            snapshot = fixture()
            row = snapshot['targets'][0]['evidence_records'][0]
            row.update(metric_state=PLANNER_UNRESOLVED_STATE, monthly_searches_UI_range=None)
            entry = {}
            apply_verified_target('G01', 'en', entry, self.valid(snapshot))
            self.assertIsNone(entry['keyword_evidence_records'][0]['monthly_searches_UI_range'])
            self.assertIsNone(entry['monthly_search_volume'])
            for field, value in [('monthly_searches_UI_range', {'display': 'invented range'}),
                    ('avg_monthly_searches_export_verbatim', '0.0'),
                    ('avg_monthly_searches_export_verbatim', ''), ('metric_state', 'unknown')]:
                invalid = deepcopy(snapshot)
                invalid['targets'][0]['evidence_records'][0][field] = value
                self.invalid(invalid)

        def test_direct_ui_band_does_not_infer_export_code_magnitude(self):
            snapshot = fixture()
            snapshot['targets'][0]['evidence_records'][0]['avg_monthly_searches_export_verbatim'] = '5000.0'
            self.assertEqual(self.valid(snapshot)[('G01', 'en')]['evidence_records'][0]['monthly_searches_UI_range']['display'], '100–1K')

        def test_ui_only_historical_transcript_preserves_its_actual_artifact(self):
            snapshot = ui_only_fixture()
            entry = {}
            apply_verified_target('G01', 'da', entry, self.valid(snapshot))
            row = entry['keyword_evidence_records'][0]
            self.assertEqual(row['metric_state'], PLANNER_UI_ONLY_STATE)
            self.assertEqual(row['source_artifact_kind'], 'planner_ui_transcript')
            self.assertEqual(row['source_ui_observation_id'], 'fixture-run:ui-observation:01')
            self.assertFalse(row['raw_export_available'])
            self.assertIsNone(row['avg_monthly_searches_export_verbatim'])
            self.assertEqual(row['source_capture_sha'], row['raw_file_sha256'])
            self.assertEqual(entry['keyword_evidence_scope']['metric_states'], [PLANNER_UI_ONLY_STATE])
            for metric in ('monthly_search_volume', 'keyword_difficulty', 'CPC'):
                self.assertIsNone(entry[metric])
            csv_snapshot = fixture()
            csv_snapshot['sources']['fixture-run'].update(source_artifact_kind='planner_csv', raw_export_available=True)
            csv_snapshot['targets'][0]['evidence_records'][0].update(source_artifact_kind='planner_csv', raw_export_available=True)
            self.valid(csv_snapshot)

        def test_ui_only_transcript_cannot_masquerade_as_csv_or_infer_metrics(self):
            row = ('targets', 0, 'evidence_records', 0)
            source = ('sources', 'fixture-run')
            cases = [
                (row + ('source_artifact_kind',), 'planner_csv'),
                (source + ('source_artifact_kind',), 'planner_csv'),
                (row + ('source_artifact_kind',), 'unknown'),
                (row + ('avg_monthly_searches_export_verbatim',), '500'),
                (row + ('avg_monthly_searches_export_verbatim',), '0'),
                (row + ('raw_export_available',), True),
                (source + ('raw_export_available',), True),
                (row + ('data_kind',), 'forecast'),
                (source + ('data_kind',), 'forecast'),
                (row + ('metric_state',), PLANNER_METRIC_STATE),
                (row + ('metric_state',), PLANNER_UNRESOLVED_STATE),
                (row + ('monthly_searches_UI_range',), None),
                (row + ('monthly_searches_UI_range', 'basis_type'), 'inferred_from_another_label'),
                (row + ('monthly_searches_UI_range', 'basis'), ''),
                (row + ('monthly_searches_UI_range', 'display'), '0–10'),
                (row + ('monthly_searches_UI_range', 'display'), '10,,100–1000'),
                (row + ('monthly_searches_UI_range', 'display'), 'Unknown'),
                (row + ('monthly_searches_UI_range', 'lower'), 0),
                (row + ('monthly_searches_UI_range', 'upper'), 100),
                (row + ('country_codes',), ['SE']),
                (row + ('language_setting',), 'Swedish'),
                (row + ('raw_file_sha256',), 'a' * 64),
                (row + ('source_capture_sha',), 'a' * 64),
                (row + ('source_artifact_path',), ''),
                (row + ('source_ui_observation_id',), 'other-run:ui-observation:01'),
                (row + ('source_ui_observation_id',), 'fixture-run:ui-observation:02'),
                (row + ('source_ui_observation_id',), 'fixture-run:row:00001'),
                (row + ('exact_monthly_search_volume',), 550),
            ]
            for path, value in cases:
                with self.subTest(path=path, value=value):
                    snapshot = ui_only_fixture()
                    set_path(snapshot, path, value)
                    self.invalid(snapshot)
            for path in (row + ('source_artifact_kind',), source + ('source_artifact_kind',),
                    row + ('raw_export_available',), source + ('raw_export_available',),
                    row + ('avg_monthly_searches_export_verbatim',), row + ('source_ui_observation_id',)):
                snapshot = ui_only_fixture()
                parent = snapshot
                for part in path[:-1]:
                    parent = parent[part]
                del parent[path[-1]]
                self.invalid(snapshot)
            paired_spoof = ui_only_fixture()
            paired_spoof['targets'][0]['evidence_records'][0].update(
                source_run_id='other-run', source_ui_observation_id='other-run:ui-observation:01')
            self.invalid(paired_spoof)

        def test_invalid_context_metrics_and_phrases_fail_closed(self):
            row = ('targets', 0, 'evidence_records', 0)
            source = ('sources', 'fixture-run')
            cases = [
                (('schema_version',), 2), (('sources',), None),
                (('targets', 0, 'primary_keyword'), ''),
                (('targets', 0, 'primary_keyword'), 'unsupported primary'),
                (('targets', 0, 'secondary_keywords'), ['one', 'two', 'three', 'four']),
                (('targets', 0, 'locale'), 'fr'),
                (row + ('keyword_label_verbatim',), 'Cat Not Peeing'),
                (row + ('locale',), 'fr'),
                (row + ('country_codes',), ['CA']),
                (row + ('country_codes',), ['UK']),
                (row + ('raw_file_sha256',), 'a' * 64),
                (row + ('raw_file_sha256',), 'not-a-hash'),
                (row + ('run_id',), 'unknown-run'),
                (row + ('row_id',), 'different-run:row:00001'),
                (row + ('raw_data_record_1based',), 2),
                (row + ('network',), 'Google and search partners'),
                (row + ('date_start',), '2026-10-01'),
                (row + ('date_end',), '2026-10-29'),
                (row + ('retrieved_on',), '2026-02-30'),
                (row + ('mode',), 'Forecasts'),
                (row + ('data_kind',), 'forecast'),
                (row + ('reported_positive_aggregate_support',), False),
                (row + ('metric_state',), 'unknown'),
                (row + ('avg_monthly_searches_export_verbatim',), '0'),
                (row + ('avg_monthly_searches_export_verbatim',), '0.0'),
                (row + ('avg_monthly_searches_export_verbatim',), ''),
                (row + ('avg_monthly_searches_export_verbatim',), 'NaN'),
                (row + ('avg_monthly_searches_export_verbatim',), 'inf'),
                (row + ('avg_monthly_searches_export_verbatim',), '5e2'),
                (row + ('avg_monthly_searches_export_verbatim',), '500.0junk'),
                (row + ('monthly_searches_UI_range',), None),
                (row + ('monthly_searches_UI_range', 'basis_type'), 'inferred_from_same_numeric_export_code'),
                (row + ('monthly_searches_UI_range', 'basis'), ''),
                (row + ('monthly_searches_UI_range', 'lower'), 0),
                (row + ('monthly_searches_UI_range', 'upper'), 100),
                (row + ('monthly_searches_UI_range', 'account_coarsening'), False),
                (row + ('exact_monthly_search_volume',), 500),
                (row + ('monthly_search_volume',), 500),
                (row + ('keyword_difficulty',), 25),
                (row + ('CPC',), 0.5),
                (row + ('actual_CPC',), 0.5),
                (row + ('organic_keyword_difficulty',), 25),
                (row + ('is_individual_query_log',), True),
                (('targets', 0, 'source_evidence_refs'), ['missing:row:00001']),
                (('targets', 0, 'geographic_scope'), ['CA']),
                (('targets', 0, 'status'), 'forecast-supported'),
                (source + ('language_setting',), 'French'),
                (source + ('locale_is_language_filter',), False),
                (source + ('data_kind',), 'forecast'),
            ]
            for path, value in cases:
                with self.subTest(path=path, value=value):
                    snapshot = fixture()
                    set_path(snapshot, path, value)
                    self.invalid(snapshot)
            snapshot = fixture()
            snapshot['targets'].append(deepcopy(snapshot['targets'][0]))
            self.invalid(snapshot)

        def test_unknown_actual_page_or_feed_is_rejected(self):
            registry = {'resources': {'G01': {'kind': 'article', 'variants': {'en': {}}}}}
            self.assertIn(('G01', 'en'), validate_verified_targets(fixture(), registry))
            counters['valid_cases'] += 1
            for resources in ({}, {'G01': {'kind': 'feed', 'variants': {'en': {}}}},
                    {'G01': {'kind': 'article', 'variants': {'de': {}}}}):
                with self.assertRaises(ValueError):
                    validate_verified_targets(fixture(), {'resources': resources})
                counters['invalid_cases'] += 1

        def test_supplied_source_and_dependency_pins_fail_when_stale_or_unsafe(self):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root/'source.md'
                source.write_text('Current reviewed source body.\n')
                digest = sha256(source.read_bytes()).hexdigest()
                dependency = root/'products.json'
                dependency.write_text('{"formula": "current"}\n')
                dependency_hash = sha256(dependency.read_bytes()).hexdigest()
                registry = {'resources': {'G01': {'kind': 'article', 'source_file': 'source.md',
                    'source_sha256': digest, 'variants': {'en': {'document_sha256': digest}}}}}
                snapshot = fixture()
                snapshot['targets'][0].update(source_file_at_curation='source.md',
                    source_document_sha256_at_curation=digest)

                def pinned_valid(item):
                    value = validate_verified_targets(item, registry, root)
                    counters['valid_cases'] += 1
                    return value

                def pinned_invalid(item):
                    with self.assertRaises(ValueError):
                        validate_verified_targets(item, registry, root)
                    counters['invalid_cases'] += 1

                self.assertIn(('G01', 'en'), pinned_valid(snapshot))
                with_dependencies = deepcopy(snapshot)
                with_dependencies['targets'][0]['dependency_sha256'] = {'products.json': dependency_hash}
                self.assertIn(('G01', 'en'), pinned_valid(with_dependencies))
                for missing in ('source_file_at_curation', 'source_document_sha256_at_curation'):
                    invalid = deepcopy(snapshot)
                    del invalid['targets'][0][missing]
                    pinned_invalid(invalid)
                for field, value in [('source_file_at_curation', 'different.md'),
                        ('source_document_sha256_at_curation', '0' * 64),
                        ('dependency_sha256', {}),
                        ('dependency_sha256', {'products.json': '0' * 64}),
                        ('dependency_sha256', {'products.json': 'invalid-hash'}),
                        ('dependency_sha256', {'missing.json': dependency_hash}),
                        ('dependency_sha256', {'../products.json': dependency_hash}),
                        ('dependency_sha256', {str(dependency): dependency_hash}),
                        ('dependency_sha256', {'_data/google_keyword_evidence.json': digest}),
                        ('dependency_sha256', {'_data/localized_seo.json': digest})]:
                    invalid = deepcopy(snapshot)
                    invalid['targets'][0][field] = value
                    pinned_invalid(invalid)
                source.write_text('Changed since keyword curation.\n')
                pinned_invalid(snapshot)
                source.write_text('Current reviewed source body.\n')
                dependency.write_text('{"formula": "changed"}\n')
                pinned_invalid(with_dependencies)
                with tempfile.TemporaryDirectory() as outside:
                    external = Path(outside)/'outside.json'
                    external.write_text('Outside source root.\n')
                    (root/'linked.json').symlink_to(external)
                    invalid = deepcopy(snapshot)
                    invalid['targets'][0]['dependency_sha256'] = {'linked.json': sha256(external.read_bytes()).hexdigest()}
                    pinned_invalid(invalid)

        def test_check_is_exact_and_never_writes(self):
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary)/'metadata.json'
                self.assertFalse(save_or_check_metadata(path, {'test': 1}, check=True))
                self.assertFalse(path.exists())
                path.write_text('stale bytes\n')
                self.assertFalse(save_or_check_metadata(path, {'test': 1}, check=True))
                self.assertEqual(path.read_text(), 'stale bytes\n')
                save_or_check_metadata(path, {'test': 1})
                original = path.read_bytes()
                self.assertTrue(save_or_check_metadata(path, {'test': 1}, check=True))
                self.assertEqual(path.read_bytes(), original)
                counters['valid_cases'] += 1

    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests))
    print(json.dumps({'passed': result.wasSuccessful(), 'test_methods': result.testsRun,
        **counters, 'scope': 'Offline in-memory policy and temporary-file fixtures; no site snapshot or metadata writes, no network.'}))
    if not result.wasSuccessful():
        print(stream.getvalue())
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--packet', type=Path)
    mode.add_argument('--check', action='store_true', help='Compare current metadata exactly without writing or importing a packet.')
    mode.add_argument('--self-test', action='store_true', help='Run offline evidence-policy fixtures without site mutations.')
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        return
    destination = ROOT/'_data/full_site_keywords.json'
    registry = json.loads((ROOT/'_data/localization_registry.json').read_text())
    try:
        verified_targets = load_verified_targets(ROOT/'_data/google_keyword_evidence.json', registry)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Invalid verified keyword snapshot: {error}\n')
    if args.packet:
        normalized, sources = [], {}
        for filename in FILES:
            path = args.packet/filename
            data = json.loads(path.read_text())
            sources[filename] = {'sha256':sha256(path.read_bytes()).hexdigest(), 'data':data}
            normalized.extend(normal(record, filename) for record in data.get('records', data.get('targets', [])))
        assert len(normalized) == 18*16
        assert len({(record['locale'], record['family']) for record in normalized}) == len(normalized)
        snapshot = {'prepared_on':'2026-10-29', 'records':normalized, 'sources':sources,
                    'measurement_limits':'Local publisher wording and displayed search features are not measured query demand. Paid keyword providers were unavailable; volume/KD/CPC remain unknown.',
                    'owner_capability_clarification':'Owner instructed Landing to keep existing lab/manufacturing wording: shareholder owns an operating lab and manufacturing facility. No independent certification audit is asserted.'}
        for extra in ('GOOGLE_PRODUCT_FEATURE_OBSERVATIONS.json', 'FULL_SITE_LOCALE_PAGE_MATRIX.json', 'SOURCE_EVIDENCE_REGISTRY.json', 'OWNER_CAPABILITY_CLARIFICATION.json'):
            path = args.packet/extra
            if path.exists(): snapshot[extra] = json.loads(path.read_text())
        destination.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n')
    snapshot = json.loads(destination.read_text())
    documents = {doc['file']:doc for doc in read_documents(ROOT)}
    metadata, count, family_count = build_metadata(snapshot, registry, documents, verified_targets)
    current = save_or_check_metadata(ROOT/'_data/localized_seo.json', metadata, check=args.check)
    selected = sum(entry.get('keyword_evidence_class') == PLANNER_CLASS
        for editions in metadata.values() for entry in editions.values())
    print(json.dumps({'localized_page_metadata': count, 'family_records': family_count,
        'measured_volume_records': 0, 'google_planner_target_pages': selected,
        'mode': 'check' if args.check else 'write', 'current': current}))
    if not current:
        parser.exit(1, 'SEO metadata is stale; run this importer deliberately after reviewing the current sources and evidence.\n')


if __name__ == '__main__': main()
