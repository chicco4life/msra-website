#!/usr/bin/env python3
"""Validate registered Google Keyword Planner exports; never mutate website data.

This is an audit import, not a keyword-volume or SEO-difficulty estimator. The
current UI/export pairing supplies grouped/rounded buckets, not exact counts.
Run --check to validate without writing, or explicitly name a new external JSON:

  python3 tools/import_google_keyword_evidence.py --packet /audit/packet \
    --register EXPORT_REGISTER.json --check
  python3 tools/import_google_keyword_evidence.py --packet /audit/packet \
    --register EXPORT_REGISTER.json --check --export-id KP-US-en-01 \
    --target-term 'cat urinary blockage'

The register must contain {"exports": [{export_id, country, locale,
language_setting, network, date_start, date_end, raw_path, sha256,
ui_metric_precision, ui_bucket_map, settings_evidence_refs, provided_seeds}]}.
Dates are ISO dates and must agree with the export's reporting-date line.
Country must be an ISO 3166-1 alpha-2 code. The locale property is required:
either a supported site edition, or null with a nonempty, unique input_locales
list of supported editions and language_setting exactly "All languages".
The latter declares one multilingual export, not one export per input locale.
Settings are explicit assertions backed by referenced artifacts: the CSV itself
does not prove geography, language, network or precision.

Historical exports require report_mode="historical_metrics" and an explicit
aggregate_segmentation_labels list (e.g. ["All", "United States"]). Blank-label
rows with those segment labels are retained separately as excluded aggregates,
never treated as keyword demand. Discover is the default report mode. The two
schemas are checked by exact headers; their different average-search column
positions are never inferred from offsets.

ui_metric_precision must be "grouped_rounded_bucketed" or the explicit alias
"grouped_rounded_bucketed_estimates". ui_bucket_map maps raw positive strings
to the actually observed display labels, e.g. {"50": "10–100", "500":
"100–1K"}. Values may instead be {"ui_label":"10–100", "lower_bound":10,
"upper_bound":100}; supplied bounds must agree with the label. Endpoint
inclusivity is deliberately unspecified. An empty map is allowed: a positive
representative without run-specific UI calibration stays positive_unresolved_range.
Local evidence paths resolve inside
--packet and must exist. HTTPS references may not include private Ads UI URLs,
credentials, query strings, fragments or account-ID patterns.

--output is exclusive, never overwrites a file, never writes within the site
checkout and never creates directories. Raw ideas belong in the external audit
packet. A later reviewed adapter can select current-target evidence for the site.
Only Python's standard library is required. --self-test exercises offline
fixtures in a temporary directory without invoking the evidence-output writer.
"""

import argparse
from collections import Counter
import csv
from datetime import date
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit


SITE_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_LOCALES = frozenset((
    'en', 'de', 'fr', 'it', 'es', 'nl', 'pl', 'sv', 'ja', 'pt-BR', 'ko',
    'zh-Hans', 'pt-PT', 'da', 'nb', 'fi', 'ru', 'hi',
))
# ISO 3166-1 alpha-2 assigned codes; no filename/currency-to-country inference.
ISO_COUNTRIES = frozenset('''AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ
BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG
CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES
ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY
HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN
KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM
MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM
PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG
SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO
TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'''.split())
PRECISIONS = frozenset(('grouped_rounded_bucketed', 'grouped_rounded_bucketed_estimates'))
BASE_HEADERS = (
    'Keyword', 'Currency', 'Avg. monthly searches', 'Three month change',
    'YoY change', 'Competition', 'Competition (indexed value)',
    'Top of page bid (low range)', 'Top of page bid (high range)',
    'Ad impression share', 'Organic impression share', 'Organic average position',
    'In account?', 'In plan?',
)
HISTORICAL_HEADERS = (
    'Keyword', 'Currency', 'Segmentation', 'Avg. monthly searches',
    'Three month change', 'YoY change', 'Competition',
    'Competition (indexed value)', 'Top of page bid (low range)',
    'Top of page bid (high range)', 'Ad impression share',
    'Organic average position', 'Organic impression share', 'In Account',
)
MONTH_NAMES = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December')
MONTHS = {name: number for number, name in enumerate(MONTH_NAMES, 1)}
MONTH_ABBRS = {name[:3]: number for name, number in MONTHS.items()}
ACCOUNT_ID = re.compile(r'(?<!\d)\d{3}-\d{3}-\d{4}(?!\d)')
LIMITS = (
    'Positive export representatives are grouped/rounded UI bucket estimates, '
    'not exact monthly counts or independently measured demand for each label.',
    'A zero or blank average-search export field is unknown/suppressed, not '
    'evidence of zero demand.',
    'UI range endpoints are retained without asserting inclusive/exclusive bounds.',
    'Advertising competition is not organic keyword difficulty; top-of-page bid '
    'ranges are not observed CPC. No rank, CPC or SEO-difficulty metric is derived.',
    'Blank monthly columns do not establish a monthly series or seasonality.',
    'Country, language, network, precision and seeds come from the explicit '
    'register and its evidence, not the filename, currency or keyword wording.',
)


class EvidenceError(ValueError):
    """An input has insufficient or inconsistent provenance."""


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def nonempty_string(value, field):
    require(isinstance(value, str) and bool(value.strip()), f'{field}: nonempty string required')
    require(not ACCOUNT_ID.search(value), f'{field}: private account-ID pattern is forbidden')
    return value


def packet_path(value, packet, field):
    value = nonempty_string(value, field)
    path = Path(value)
    path = (path if path.is_absolute() else packet / path).resolve()
    require(path.is_relative_to(packet), f'{field}: path must remain inside --packet')
    require(path.is_file(), f'{field}: referenced file does not exist')
    return path


def evidence_refs(values, packet):
    require(isinstance(values, list) and bool(values), 'settings_evidence_refs: nonempty list required')
    result = []
    for value in values:
        value = nonempty_string(value, 'settings_evidence_refs')
        url = urlsplit(value)
        if url.scheme or url.netloc:
            require(url.scheme == 'https' and bool(url.hostname), 'settings_evidence_refs: HTTPS required')
            require(not (url.username or url.password or url.query or url.fragment),
                    'settings_evidence_refs: private URL components are forbidden')
            require(not (url.hostname == 'ads.google.com' or url.hostname.endswith('.ads.google.com')),
                    'settings_evidence_refs: private Ads UI URLs are forbidden; use a local artifact')
            result.append(value)
        else:
            path = packet_path(value, packet, 'settings_evidence_refs')
            result.append(path.relative_to(packet).as_posix())
    require(len(set(result)) == len(result), 'settings_evidence_refs: duplicate references')
    return result


def iso_date(value, field):
    require(isinstance(value, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value)),
            f'{field}: ISO YYYY-MM-DD required')
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise EvidenceError(f'{field}: invalid date') from error


def report_date(value):
    match = re.fullmatch(r'([A-Za-z]+) (\d{1,2}), (\d{4})', value)
    require(match and match[1] in MONTHS, 'export: unsupported report-date format')
    try:
        return date(int(match[3]), MONTHS[match[1]], int(match[2]))
    except ValueError as error:
        raise EvidenceError('export: invalid reporting date') from error


def display_bound(value):
    match = re.fullmatch(r'(\d+)([KkMm]?)', value.replace(',', ''))
    require(match is not None, 'ui_bucket_map: unsupported UI range endpoint')
    return int(match[1]) * {'': 1, 'k': 1000, 'm': 1000000}[match[2].lower()]


def bucket_map(value):
    require(isinstance(value, dict), 'ui_bucket_map: explicit object required (may be empty)')
    result = {}
    for raw, entry in value.items():
        require(isinstance(raw, str) and bool(re.fullmatch(r'[1-9]\d*', raw)),
                'ui_bucket_map: raw keys must be positive integer strings')
        require(isinstance(entry, (str, dict)), 'ui_bucket_map: label string or range object required')
        label = entry if isinstance(entry, str) else entry.get('ui_label')
        label = nonempty_string(label, 'ui_bucket_map.ui_label')
        match = re.fullmatch(r'\s*([\d,]+[KkMm]?)\s*[–—-]\s*([\d,]+[KkMm]?)\s*', label)
        require(match is not None, 'ui_bucket_map: an explicitly displayed range label is required')
        lower, upper = display_bound(match[1]), display_bound(match[2])
        require(0 < lower < upper, 'ui_bucket_map: positive ascending UI endpoints required')
        if isinstance(entry, dict):
            for key, parsed in (('lower_bound', lower), ('upper_bound', upper)):
                if key in entry:
                    require(type(entry[key]) is int and entry[key] == parsed,
                            f'ui_bucket_map: {key} disagrees with displayed label')
        result[raw] = {'ui_display_label': label, 'lower_bound': lower, 'upper_bound': upper,
                       'endpoint_inclusivity': 'not_asserted'}
    return result


def classify_average(raw, buckets):
    """Retain the export representative; never return it as an exact count."""
    value = raw.strip()
    require(value == '' or bool(re.fullmatch(r'\d+(?:\.\d+)?', value)),
            'export: unsupported average-search representative')
    canonical = value
    if '.' in value and not value.split('.', 1)[1].strip('0'):
        canonical = value.split('.', 1)[0]
    if canonical == '' or not value.strip('0.'):
        return {
            'raw_export_value': raw, 'metric_kind': 'unknown_or_suppressed',
            'unknown_reason': 'blank_export_field' if value == '' else 'zero_export_representative',
            'ui_display_label': None, 'estimated_monthly_search_range': None,
            'exact_monthly_search_count': None,
        }
    if canonical not in buckets:
        return {
            'raw_export_value': raw, 'metric_kind': 'positive_unresolved_range',
            'unknown_reason': 'positive_export_representative_without_run_specific_UI_range_evidence',
            'ui_display_label': None, 'estimated_monthly_search_range': None,
            'exact_monthly_search_count': None,
        }
    bucket = buckets[canonical]
    return {
        'raw_export_value': raw,
        'metric_kind': 'google_keyword_planner_grouped_rounded_bucketed_estimate',
        'unknown_reason': None, 'ui_display_label': bucket['ui_display_label'],
        'estimated_monthly_search_range': {
            'lower_bound': bucket['lower_bound'], 'upper_bound': bucket['upper_bound'],
            'endpoint_inclusivity': bucket['endpoint_inclusivity'],
            'unit': 'searches_per_month_as_displayed_UI_bucket_not_exact_count',
        },
        'exact_monthly_search_count': None,
    }


def read_export(path, registered_start, registered_end, *, raw_bytes=None,
                report_mode='discover_keywords', aggregate_segmentation_labels=()):
    raw = path.read_bytes() if raw_bytes is None else raw_bytes
    require(raw.startswith((b'\xff\xfe', b'\xfe\xff')), 'export: UTF-16 BOM required')
    try:
        text = raw.decode('utf-16')
        table = list(csv.reader(io.StringIO(text, newline=''), delimiter='\t', strict=True))
    except (UnicodeError, csv.Error) as error:
        raise EvidenceError('export: invalid UTF-16 TSV') from error
    require(len(table) >= 4, 'export: report lines, header and data required')
    require(len(table[0]) == 1, 'export: invalid report title line')
    title = re.fullmatch(r'Keyword Stats (\d{4}-\d{2}-\d{2}) at (\d{2}_\d{2}_\d{2})', table[0][0])
    require(title is not None, 'export: unsupported report title; no account identifiers allowed')
    generated = iso_date(title[1], 'export generated date')
    require(len(table[1]) == 1 and ' - ' in table[1][0], 'export: reporting-date line required')
    parts = table[1][0].split(' - ')
    require(len(parts) == 2, 'export: invalid reporting-date range')
    start, end = (report_date(part) for part in parts)
    require(start == registered_start and end == registered_end,
            'export: reporting dates disagree with register')
    require(start <= end <= generated, 'export: inconsistent reporting/generation dates')
    headers = table[2]
    require(len(headers) == len(set(headers)), 'export: duplicate column headers')
    require(report_mode in ('discover_keywords', 'historical_metrics'), 'export: unsupported explicit report mode')
    expected_headers = HISTORICAL_HEADERS if report_mode == 'historical_metrics' else BASE_HEADERS
    require(tuple(headers[:len(expected_headers)]) == expected_headers,
            'export: unsupported header schema; account-ID/unknown columns are not imported')
    monthly = headers[len(expected_headers):]
    require(bool(monthly), 'export: monthly column headers required, even if their values are blank')
    actual_months = []
    for header in monthly:
        match = re.fullmatch(r'Searches: ([A-Za-z]{3}) (\d{4})', header)
        require(match and match[1] in MONTH_ABBRS, 'export: unsupported monthly column')
        actual_months.append((int(match[2]), MONTH_ABBRS[match[1]]))
    expected_months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        expected_months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    require(actual_months == expected_months, 'export: monthly headers disagree with reporting dates')
    rows, labels, aggregates = [], set(), []
    for line_number, cells in enumerate(table[3:], 4):
        if not cells or not any(cells):
            continue
        require(len(cells) == len(headers), f'export row {line_number}: wrong number of TSV fields')
        fields = dict(zip(headers, cells))
        label = cells[0]
        require(not any(ACCOUNT_ID.search(cell) for cell in cells),
                f'export row {line_number}: private account-ID pattern is forbidden')
        if report_mode == 'historical_metrics' and not label.strip():
            require(fields['Currency'] == '' and fields['Segmentation'] in aggregate_segmentation_labels,
                    f'export row {line_number}: undeclared aggregate segment')
            aggregates.append({'source_row': line_number, 'classification': 'excluded_segment_aggregate_not_keyword',
                               'raw_export_fields': fields})
            continue
        require(bool(label.strip()), f'export row {line_number}: missing keyword label')
        if report_mode == 'historical_metrics':
            require(fields['Segmentation'] == '', f'export row {line_number}: keyword rows must not be segment totals')
        require(label not in labels, f'export row {line_number}: duplicate exact keyword label')
        labels.add(label)
        rows.append((line_number, fields))
    require(bool(rows), 'export: no keyword idea rows')
    return {'generated_on': generated.isoformat(), 'generated_time_zone': 'not_supplied',
            'report_date_label': table[1][0], 'headers': headers, 'monthly_columns': monthly,
            'rows': rows, 'excluded_aggregate_rows': aggregates, 'sha256': sha256(raw).hexdigest()}


def parse_registered_export(entry, packet):
    require(isinstance(entry, dict), 'exports: each entry must be an object')
    export_id = nonempty_string(entry.get('export_id'), 'export_id')
    require(bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,95}', export_id)), 'export_id: unsafe identifier')
    require(isinstance(entry.get('country'), str) and entry['country'] in ISO_COUNTRIES,
            f'{export_id}: country must be ISO alpha-2 uppercase')
    require('locale' in entry, f'{export_id}: explicit locale property required')
    language = nonempty_string(entry.get('language_setting'), f'{export_id}.language_setting')
    input_locales = None
    if entry['locale'] is None:
        require(language == 'All languages',
                f'{export_id}: locale null requires language_setting exactly All languages')
        input_locales = entry.get('input_locales')
        require(isinstance(input_locales, list) and bool(input_locales),
                f'{export_id}.input_locales: nonempty list required for locale null')
        require(all(isinstance(locale, str) and locale in SUPPORTED_LOCALES for locale in input_locales),
                f'{export_id}.input_locales: unsupported locale')
        require(len(set(input_locales)) == len(input_locales),
                f'{export_id}.input_locales: duplicate locale')
        input_locales = list(input_locales)
    else:
        require(isinstance(entry['locale'], str) and entry['locale'] in SUPPORTED_LOCALES,
                f'{export_id}: unsupported locale')
    network = nonempty_string(entry.get('network'), f'{export_id}.network')
    require(isinstance(entry.get('ui_metric_precision'), str) and entry['ui_metric_precision'] in PRECISIONS,
            f'{export_id}: explicit grouped/rounded/bucketed UI precision required')
    buckets = bucket_map(entry.get('ui_bucket_map'))
    refs = evidence_refs(entry.get('settings_evidence_refs'), packet)
    seeds = entry.get('provided_seeds')
    require(isinstance(seeds, list), f'{export_id}.provided_seeds: explicit list required (may be empty)')
    seeds = [nonempty_string(seed, f'{export_id}.provided_seeds') for seed in seeds]
    require(len(set(seeds)) == len(seeds), f'{export_id}.provided_seeds: duplicate exact seed')
    start, end = iso_date(entry.get('date_start'), 'date_start'), iso_date(entry.get('date_end'), 'date_end')
    report_mode = entry.get('report_mode', 'discover_keywords')
    require(report_mode in ('discover_keywords', 'historical_metrics'), f'{export_id}: unsupported report_mode')
    aggregate_labels = entry.get('aggregate_segmentation_labels', [])
    require(isinstance(aggregate_labels, list), f'{export_id}: aggregate_segmentation_labels must be a list')
    if report_mode == 'historical_metrics':
        require(bool(aggregate_labels), f'{export_id}: explicit historical aggregate labels required')
    aggregate_labels = [nonempty_string(label, 'aggregate_segmentation_labels') for label in aggregate_labels]
    path = packet_path(entry.get('raw_path'), packet, f'{export_id}.raw_path')
    expected_hash = entry.get('sha256')
    require(isinstance(expected_hash, str) and bool(re.fullmatch(r'[0-9a-fA-F]{64}', expected_hash)),
            f'{export_id}.sha256: full SHA-256 required')
    # Hash and parse the same snapshot even if an exporter replaces the path
    # during the import. A later replay still has to match this registered hash.
    raw_bytes = path.read_bytes()
    require(sha256(raw_bytes).hexdigest() == expected_hash.lower(), f'{export_id}: raw export SHA-256 mismatch')
    parsed = read_export(path, start, end, raw_bytes=raw_bytes, report_mode=report_mode,
                         aggregate_segmentation_labels=aggregate_labels)
    ideas = []
    monthly_populated = 0
    for line, fields in parsed['rows']:
        monthly_populated += sum(bool(fields[key].strip()) for key in parsed['monthly_columns'])
        ideas.append({
            'source_row': line, 'returned_keyword_label': fields['Keyword'],
            'provided_seed_exact_match': fields['Keyword'] in seeds,
            'search_demand': classify_average(fields['Avg. monthly searches'], buckets),
            'raw_export_fields': fields,
        })
    kinds = Counter(idea['search_demand']['metric_kind'] for idea in ideas)
    displays = Counter(idea['search_demand']['ui_display_label'] for idea in ideas
                       if idea['search_demand']['ui_display_label'] is not None)
    result = {
        'export_id': export_id, 'country': entry['country'], 'locale': entry['locale'],
        'language_setting': language, 'network': network,
        'date_start': start.isoformat(), 'date_end': end.isoformat(),
        'raw_path': path.relative_to(packet).as_posix(), 'sha256': parsed['sha256'],
        'settings_evidence_refs': refs, 'provided_seeds': seeds,
        'settings_validation': 'explicit_register_with_referenced_artifacts_not_inferred_from_export',
        'ui_metric_precision': entry['ui_metric_precision'], 'ui_bucket_map': buckets,
        'report_mode': report_mode, 'aggregate_segmentation_labels': aggregate_labels,
        'report': {key: parsed[key] for key in ('generated_on', 'generated_time_zone', 'report_date_label', 'headers', 'monthly_columns')},
        'summary': {
            'unique_returned_labels': len(ideas), 'metric_kind_rows': dict(sorted(kinds.items())),
            'excluded_aggregate_rows': len(parsed['excluded_aggregate_rows']),
            'ui_display_bucket_rows': dict(sorted(displays.items())),
            'monthly_columns_status': 'all_blank' if monthly_populated == 0 else 'raw_values_present_not_interpreted',
            'populated_monthly_fields': monthly_populated,
        },
        'excluded_aggregate_rows': parsed['excluded_aggregate_rows'],
        'ideas': ideas,
    }
    if input_locales is not None:
        result['input_locales'] = input_locales
    return result


def import_register(register, packet):
    """Pure validation/import result; no evidence file or site data is written."""
    packet = Path(packet).resolve()
    require(packet.is_dir(), '--packet: existing directory required')
    require(isinstance(register, dict), 'register: JSON object required')
    entries = register.get('exports')
    require(isinstance(entries, list) and bool(entries), 'register.exports: nonempty list required')
    exports = [parse_registered_export(entry, packet) for entry in entries]
    require(len({entry['export_id'] for entry in exports}) == len(exports), 'register: duplicate export_id')
    return {'schema_version': 1, 'evidence_scope': 'external_audit_raw_keyword_ideas_not_website_data',
            'measurement_limits': list(LIMITS), 'exports': exports}


def exact_target_check(evidence, export_id, label):
    """Check the exact returned label; no stemming, translation or fuzzy match."""
    nonempty_string(label, '--target-term')
    matches = [item for item in evidence['exports'] if item['export_id'] == export_id]
    require(len(matches) == 1, '--export-id: exactly one registered export must match')
    ideas = [idea for idea in matches[0]['ideas'] if idea['returned_keyword_label'] == label]
    return {'export_id': export_id, 'requested_exact_label': label, 'exact_label_returned': bool(ideas),
            'match_policy': 'exact_Unicode_string_no_normalization_or_semantic_inference',
            'source_row': ideas[0]['source_row'] if ideas else None,
            'search_demand': ideas[0]['search_demand'] if ideas else None,
            'absence_interpretation': None if ideas else 'not_returned_under_this_exact_label_not_evidence_of_zero_demand'}


def output_path(value, input_paths):
    path = Path(value).expanduser().resolve()
    require(path.suffix.lower() == '.json', '--output: explicit .json file required')
    require(not path.is_relative_to(SITE_ROOT), '--output: writing inside the website checkout is forbidden')
    require(path not in input_paths, '--output: must not replace an input')
    require(path.parent.is_dir(), '--output: parent directory must already exist')
    require(not path.exists(), '--output: refusing to overwrite an existing file')
    return path


def self_test():
    """Focused offline fixtures, all in memory except disposable input artifacts."""
    import copy
    from unittest.mock import patch
    checks = 0

    def check(condition):
        nonlocal checks
        require(condition, f'self-test assertion {checks + 1} failed')
        checks += 1

    def rejects(call):
        try:
            call()
        except EvidenceError:
            check(True)
        else:
            check(False)

    with tempfile.TemporaryDirectory(prefix='msra-keyword-evidence-') as folder:
        packet = Path(folder)
        (packet / 'settings-proof.txt').write_text('Fixture only; not actual UI evidence.', encoding='utf-8')
        raw = packet / 'input.csv'
        labels = [('déshydratation 猫 ™', '50'), ('bucket large', '50000'), ('unknown zero', '0'), ('unknown blank', '')]
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['Keyword Stats 2026-10-29 at 20_07_56'])
        writer.writerow(['October 1, 2025 - September 30, 2026'])
        month_headers = [f'Searches: {name[:3]} {year}' for year, names in
                         ((2025, MONTH_NAMES[9:]), (2026, MONTH_NAMES[:9])) for name in names]
        writer.writerow([*BASE_HEADERS, *month_headers])
        for label, avg in labels:
            writer.writerow([label, 'USD', avg, ' --', '∞', 'Low', '0', '0.01', '0.25', '', '', '', '', '', *([''] * 12)])
        raw.write_bytes(stream.getvalue().encode('utf-16'))
        entry = {'export_id': 'fixture-US-en', 'country': 'US', 'locale': 'en',
                 'language_setting': 'English', 'network': 'Google', 'date_start': '2025-10-01',
                 'date_end': '2026-09-30', 'raw_path': 'input.csv', 'sha256': sha256(raw.read_bytes()).hexdigest(),
                 'ui_metric_precision': 'grouped_rounded_bucketed',
                 'ui_bucket_map': {'50': '10–100', '500': '100–1K', '5000': '1K–10K',
                                   '50000': {'ui_label': '10K–100K', 'lower_bound': 10000, 'upper_bound': 100000}},
                 'settings_evidence_refs': ['settings-proof.txt'], 'provided_seeds': [labels[0][0]]}
        result = import_register({'exports': [entry]}, packet)
        ideas = result['exports'][0]['ideas']
        check(len(ideas) == 4)
        check(ideas[0]['returned_keyword_label'] == labels[0][0])
        check(ideas[0]['search_demand']['raw_export_value'] == '50')
        check(ideas[0]['search_demand']['estimated_monthly_search_range']['upper_bound'] == 100)
        check(ideas[1]['search_demand']['estimated_monthly_search_range']['lower_bound'] == 10000)
        check(all(idea['search_demand']['exact_monthly_search_count'] is None for idea in ideas))
        check(all(idea['search_demand']['metric_kind'] == 'unknown_or_suppressed' for idea in ideas[2:]))
        check(ideas[2]['search_demand']['unknown_reason'] != ideas[3]['search_demand']['unknown_reason'])
        check(ideas[0]['raw_export_fields']['Competition (indexed value)'] == '0')
        check(ideas[0]['raw_export_fields']['Three month change'] == ' --')
        check(ideas[0]['raw_export_fields']['YoY change'] == '∞')
        check(result['exports'][0]['summary']['monthly_columns_status'] == 'all_blank')
        check(exact_target_check(result, 'fixture-US-en', labels[0][0])['exact_label_returned'])
        check(not exact_target_check(result, 'fixture-US-en', 'Déshydratation 猫 ™')['exact_label_returned'])
        check(json.loads(json.dumps(result, ensure_ascii=False)) == result)
        original_read_bytes = Path.read_bytes
        resolved_raw = raw.resolve()
        raw_reads = 0

        def counted_read_bytes(path):
            nonlocal raw_reads
            if path == resolved_raw:
                raw_reads += 1
            return original_read_bytes(path)

        with patch.object(Path, 'read_bytes', counted_read_bytes):
            parse_registered_export(entry, packet.resolve())
        check(raw_reads == 1)

        def changed(**updates):
            modified = copy.deepcopy(entry)
            modified.update(updates)
            return lambda: import_register({'exports': [modified]}, packet)

        # Multilingual scope stays one registered run and never assigns a locale
        # to individual labels from their wording, country, currency or filename.
        mixed_entry = dict(entry, export_id='fixture-US-multilingual', locale=None,
                           language_setting='All languages', input_locales=['en', 'pl', 'ja'])
        mixed = import_register({'exports': [mixed_entry]}, packet)
        check(len(mixed['exports']) == 1)
        mixed_export = mixed['exports'][0]
        check(mixed_export['locale'] is None)
        check(mixed_export['input_locales'] == ['en', 'pl', 'ja'])
        check(mixed_export['country'] == 'US')
        check(mixed_export['ideas'] == ideas)
        check(json.loads(json.dumps(mixed, ensure_ascii=False)) == mixed)
        check(result['exports'][0]['locale'] == 'en' and 'input_locales' not in result['exports'][0])
        missing_locale = dict(mixed_entry)
        del missing_locale['locale']
        rejects(lambda: import_register({'exports': [missing_locale]}, packet))
        missing_inputs = dict(mixed_entry)
        del missing_inputs['input_locales']
        rejects(lambda: import_register({'exports': [missing_inputs]}, packet))
        for invalid_inputs in (None, [], 'en', ['en', 'en'], ['en', 'zh-Hant'], ['en', {}], ['en', None]):
            rejects(lambda invalid_inputs=invalid_inputs: import_register(
                {'exports': [dict(mixed_entry, input_locales=invalid_inputs)]}, packet))
        for invalid_language in ('English', 'all languages', 'All languages ', 'All languages (disabled historical UI)'):
            rejects(lambda invalid_language=invalid_language: import_register(
                {'exports': [dict(mixed_entry, language_setting=invalid_language)]}, packet))
        rejects(lambda: import_register({'exports': [mixed_entry, mixed_entry]}, packet))
        check(import_register({'exports': [dict(entry, language_setting='All languages')]}, packet)
              ['exports'][0]['locale'] == 'en')

        rejects(changed(sha256='0' * 64))
        rejects(changed(date_start='2025-09-01'))
        rejects(changed(date_end='2026-09-29'))
        rejects(changed(ui_metric_precision='exact'))
        rejects(changed(ui_metric_precision=''))
        rejects(changed(settings_evidence_refs=[]))
        rejects(changed(settings_evidence_refs=['missing-proof.png']))
        rejects(changed(settings_evidence_refs=['https://ads.google.com/aw/overview']))
        rejects(changed(settings_evidence_refs=['https://example.com/proof?customer=123']))
        rejects(changed(settings_evidence_refs=['proof-123-456-7890.png']))
        rejects(changed(country='ZZ'))
        rejects(changed(country='us'))
        rejects(changed(country=[]))
        rejects(changed(locale='zh-Hant'))
        rejects(changed(ui_metric_precision={}))
        rejects(changed(language_setting=''))
        rejects(changed(network=''))
        rejects(changed(provided_seeds=None))
        rejects(changed(ui_bucket_map={'50': {'ui_label': '10–100', 'upper_bound': 500}, '50000': '10K–100K'}))
        rejects(changed(ui_bucket_map={'50': '50', '50000': '10K–100K'}))
        partial = import_register({'exports': [dict(entry, ui_bucket_map={'50': '10–100'})]}, packet)
        check(partial['exports'][0]['ideas'][1]['search_demand']['metric_kind'] == 'positive_unresolved_range')
        empty_map = import_register({'exports': [dict(entry, ui_bucket_map={})]}, packet)
        check(empty_map['exports'][0]['ideas'][0]['search_demand']['estimated_monthly_search_range'] is None)
        rejects(lambda: import_register({'exports': [entry, entry]}, packet))
        rejects(lambda: exact_target_check(result, 'unknown-export', 'term'))
        rejects(lambda: output_path(SITE_ROOT / '_data' / 'forbidden.json', set()))
        rejects(lambda: output_path(raw, {raw}))
        rejects(lambda: output_path(packet / 'missing' / 'out.json', set()))
        historical = packet / 'historical.csv'
        history = io.StringIO(newline='')
        hw = csv.writer(history, delimiter='\t', lineterminator='\n')
        hw.writerows([['Keyword Stats 2026-10-29 at 20_33_01'],
                      ['October 1, 2025 - September 30, 2026'],
                      [*HISTORICAL_HEADERS, *month_headers]])
        for segment in ('All', 'United States'):
            hw.writerow(['', '', segment, '16700.0', *([''] * 22)])
        hw.writerow(['actual positive', 'USD', '', '5000.0', *([''] * 22)])
        hw.writerow(['actual blank', 'USD', '', '', *([''] * 22)])
        historical.write_bytes(history.getvalue().encode('utf-16'))
        hist_entry = dict(entry, export_id='fixture-history', raw_path='historical.csv',
                          sha256=sha256(historical.read_bytes()).hexdigest(),
                          report_mode='historical_metrics', aggregate_segmentation_labels=['All', 'United States'])
        hist_result = import_register({'exports': [hist_entry]}, packet)['exports'][0]
        check(hist_result['summary']['unique_returned_labels'] == 2)
        check(hist_result['summary']['excluded_aggregate_rows'] == 2)
        check(hist_result['ideas'][0]['search_demand']['raw_export_value'] == '5000.0')
        check(hist_result['ideas'][0]['search_demand']['ui_display_label'] == '1K–10K')
        check(hist_result['ideas'][1]['search_demand']['metric_kind'] == 'unknown_or_suppressed')
        rejects(lambda: import_register({'exports': [dict(hist_entry, report_mode='discover_keywords')]}, packet))
        rejects(lambda: import_register({'exports': [dict(hist_entry, aggregate_segmentation_labels=['All'])]}, packet))
        rejects(lambda: import_register({'exports': [dict(hist_entry, aggregate_segmentation_labels=[])]}, packet))
        check(classify_average('0.0', {})['metric_kind'] == 'unknown_or_suppressed')
        check(classify_average('5000.0', {})['metric_kind'] == 'positive_unresolved_range')
        rejects(lambda: classify_average('-1', {}))
        # No evidence-output write function is invoked by the fixture suite.
        check(sorted(p.name for p in packet.iterdir()) == ['historical.csv', 'input.csv', 'settings-proof.txt'])
    print(json.dumps({'result': 'PASS', 'checks': checks, 'network_requests': 0,
                      'evidence_output_writes': 0, 'scope': 'offline parser/provenance/label fixtures'}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--packet', type=Path, help='External audit packet root, never inferred from filenames')
    parser.add_argument('--register', help='JSON register path inside --packet')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='Validate and print only an audit summary; no output file')
    action.add_argument('--output', help='New external evidence JSON path (no overwrite, never in site checkout)')
    parser.add_argument('--export-id', help='Export whose exact labels should be checked')
    parser.add_argument('--target-term', action='append', default=[], help='Exact returned label; repeat for multiple curated terms')
    parser.add_argument('--self-test', action='store_true', help='Run offline fixtures without writing evidence output')
    args = parser.parse_args(argv)
    if args.self_test:
        require(not (args.packet or args.register or args.check or args.output or args.export_id or args.target_term),
                '--self-test must run alone')
        self_test()
        return 0
    require(args.packet is not None and args.register, '--packet and --register are required')
    require(args.check or args.output, 'explicit --check or --output is required; no default writer')
    require(bool(args.export_id) == bool(args.target_term), '--export-id and --target-term must be used together')
    packet = args.packet.resolve()
    register_path = packet_path(args.register, packet, '--register')
    try:
        register = json.loads(register_path.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError('register: valid UTF-8 JSON required') from error
    evidence = import_register(register, packet)
    summary = {'result': 'PASS', 'exports': len(evidence['exports']),
               'unique_labels_per_export': {item['export_id']: item['summary']['unique_returned_labels'] for item in evidence['exports']},
               'evidence_output_written': False, 'network_requests': 0,
               'measurement_limits': evidence['measurement_limits']}
    if args.target_term:
        summary['target_checks'] = [exact_target_check(evidence, args.export_id, term) for term in args.target_term]
    if args.output:
        inputs = {register_path} | {(packet / item['raw_path']).resolve() for item in evidence['exports']}
        destination = output_path(args.output, inputs)
        # Exclusive create also prevents a race from overwriting an existing file.
        with destination.open('x', encoding='utf-8') as output:
            json.dump(evidence, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write('\n')
        summary['evidence_output_written'] = True
        summary['output'] = str(destination)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (EvidenceError, OSError) as error:
        print(f'Keyword evidence validation failed: {error}', file=sys.stderr)
        raise SystemExit(2)
