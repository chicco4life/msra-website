#!/usr/bin/env python3
"""Prepare an explicit indexing/routing scope for the current complete editions.

This is a local release candidate, not publication or clinical/native approval.
New content identities stay out of discovery until deliberately added here and
checked in a fresh production build. Existing scientific review states are kept.
"""
import argparse
from datetime import date
import json
from pathlib import Path
from prepare_localizations import ROOT, build_registry

def build_manifest(root, prepared_on):
    registry = build_registry(root)
    locales = set(registry['locales'])
    private = {'page:not-found', 'page:learn-updates', 'page:research-project'}
    resources = {}
    for key, source in registry['resources'].items():
        assert set(source['variants']) == locales, f'{key}: complete all commissioned editions first'
        resources[key] = {
            'indexable':source['kind'] != 'feed' and key not in private,
            'locales':list(source['variants']),
            'variant_sha256':{locale:variant['document_sha256'] for locale,variant in source['variants'].items()},
            'source_route':source['source_route'],
            'source_sha256_at_preparation':source['source_sha256'],
        }
    return {
        'prepared_on':prepared_on, 'status':'prepared-local-release-candidate',
        'authorization':'Owner requested full-site localization, regional SEO/GEO and automatic language selection, ready to push. No push performed.',
        'review_scope':'Technical/content-preservation verification; native editorial and independent veterinary review are not asserted.',
        'new_identity_policy':'An unlisted content identity stays noindex and cannot trigger automatic routing.',
        'resources':resources,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true', help='check the frozen allowlist without writing or authorizing new content')
    args = parser.parse_args()
    root = args.root.resolve()
    destination = root/'_data/publication_manifest.json'
    if args.check:
        assert destination.is_file(), 'Publication manifest is missing; a reviewed allowlist is required'
        prepared_on = json.loads(destination.read_text()).get('prepared_on')
        assert isinstance(prepared_on, str) and date.fromisoformat(prepared_on).isoformat() == prepared_on, 'Publication preparation date must be an ISO date'
    else:
        prepared_on = date.today().isoformat()
    manifest = build_manifest(root, prepared_on)
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2)+'\n'
    if args.check:
        assert destination.is_file() and destination.read_text() == encoded, 'Publication manifest is stale; review the changed editions before deliberately preparing a new allowlist'
    else:
        destination.write_text(encoded)
    resources = manifest['resources']
    print(json.dumps({'check_only':args.check, 'resources':len(resources),'prepared_indexable_routes':sum(len(r['locales']) for r in resources.values() if r['indexable'])}))


if __name__ == '__main__':
    main()
