#!/usr/bin/env python3
"""Import manifest-listed Growth drafts without overwriting newer site work.

Normalizes the implementation locale_key and marks the new translation itself
as not independently reviewed. The packet's separate source-clinical field and
scientific body remain unchanged. This never publishes or sends anything.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from prepare_localizations import ROOT, LOCALES, read_documents, translation_key, source_route, SOURCE_DATE_LABELS
from sync_research import front_matter

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('packet',type=Path)
    p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args(); packet=a.packet.resolve(); manifest=json.loads((packet/'manifest.json').read_text())
    locale=manifest['locale']; assert locale in LOCALES and locale != 'en'
    destination=ROOT/'_localized'/locale
    allowed_sources={doc['file']:doc for doc in read_documents(ROOT) if not doc['file'].startswith('_localized/')}
    planned=[]; receipt=[]; obsolete=[]
    yaml_code="require 'yaml';require 'json';require 'date';puts JSON.generate(YAML.load(STDIN.read))"
    def metadata(text):
        header=text.split('---',2)[1]
        return json.loads(subprocess.run(['/usr/bin/ruby','-EUTF-8','-e',yaml_code],input=header,text=True,capture_output=True,check=True).stdout)
    entries=manifest.get('bodies',[])+manifest.get('support_pages',[])
    for entry in entries:
        src=Path(entry['path']).resolve()
        assert src.is_relative_to(packet), 'Manifest path leaves packet'
        raw=src.read_bytes(); assert sha256(raw).hexdigest()==entry['sha256'], f'Changed packet file: {src}'
        text=raw.decode(); meta=metadata(text); body=front_matter(text)[1]
        assert meta['locale']==locale and meta['translation_status']=='ai-draft'
        assert meta['source_file'] in allowed_sources, f'Unknown source: {src}'
        assert meta['translation_key'] == translation_key(allowed_sources[meta['source_file']]), f'Mismatched source identity: {src}'
        assert meta['source_route'] == source_route(allowed_sources[meta['source_file']]), f'Mismatched source route: {src}'
        source=ROOT/meta['source_file']; assert sha256(source.read_bytes()).hexdigest()==meta['source_sha256'],f'Stale source: {src}'
        assert meta.get('release_approved') is False and meta.get('sitemap') is False and 'noindex' in meta.get('robots','')
        assert meta.get('native_review_status')=='pending'
        assert meta.get('clinical_review_status') not in ('independently-reviewed','approved','cleared')
        key=meta['translation_key']; normalized=key+'::'+locale
        converted=re.sub(r'^locale_key:.*$', 'locale_key: '+json.dumps(normalized), text, count=1, flags=re.M)
        converted=re.sub(r'^permalink:.*$', 'permalink: '+json.dumps('/'+locale.lower()+meta['source_route']), converted,count=1,flags=re.M)
        original_meta=allowed_sources[meta['source_file']]['meta']
        recorded_date=original_meta.get('prepared_date') or original_meta.get('date')
        converted=re.sub(r'^source_prepared_date:.*$', 'source_prepared_date: '+json.dumps(recorded_date), converted,count=1,flags=re.M)
        # Translation review is pending even when the legacy source did not supply a status.
        if meta.get('clinical_review_status') not in ('not-independently-reviewed','not-applicable'):
            converted=re.sub(r'^clinical_review_status:.*$', 'clinical_review_status: "not-independently-reviewed"', converted,count=1,flags=re.M)
        target=destination/src.name
        if meta['source_route'].endswith('.xml'): target=target.with_suffix('.xml')
        if target.exists(): assert target.read_text()==converted, f'Refusing overwrite: {target}'
        planned.append((target,converted))
        previous=destination/src.name
        if previous != target and previous.exists():
            assert previous.read_text()==converted, f'Refusing to replace modified original filename: {previous}'
            archive=a.receipt.parent/'import-original-filenames'/locale/previous.name
            obsolete.append((previous,archive,converted))
        receipt.append({'source':str(src),'packet_sha256':entry['sha256'],'destination':str(target),'imported_sha256':sha256(converted.encode()).hexdigest(),'body_preserved':front_matter(converted)[1]==body,'normalizations':['recorded source date (preparation or source date)','lowercase locale route prefix','implementation locale_key','translation review pending; source status retained']})
    for source_name, folder in [('ui.json','localized_ui'),('support-ui.json','localized_support')]:
        src=packet/source_name
        if not src.exists(): continue
        data=json.loads(src.read_text())
        if folder == 'localized_ui': data['prepared']=SOURCE_DATE_LABELS[locale]
        base=json.loads((ROOT/'_data'/folder/'en.json').read_text())
        assert set(data)==set(base), f'{src}: UI key mismatch'
        for k in base: assert set(re.findall(r'\{\w+\}',data[k]))==set(re.findall(r'\{\w+\}',base[k]))
        target=ROOT/'_data'/folder/(locale+'.json'); converted=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if target.exists(): assert json.loads(target.read_text())==data,f'Refusing UI overwrite: {target}'
        planned.append((target,converted))
    for target,text in planned:
        target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text)
    for previous,archive,converted in obsolete:
        assert previous.read_text()==converted, f'File changed during import: {previous}'
        archive.parent.mkdir(parents=True,exist_ok=True); archive.write_text(converted); previous.unlink()
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps({'locale':locale,'files':receipt,'imported_resource_bodies':len(entries),'publishes':False},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'locale':locale,'imported':len(entries),'receipt':str(a.receipt)}))
if __name__=='__main__':main()
