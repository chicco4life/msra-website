#!/usr/bin/env python3
"""Materialize full, crawlable marketing editions from rendered English + dictionaries.

Run the source preview (or a real English Jekyll build) first, then pass --built.
This is source generation, never a deployment. Generated HTML lives in the
localized collection and receives the normal production Jekyll build afterwards.
"""
import argparse
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit
from prepare_localizations import ROOT, LOCALES, read_documents, source_route, translation_key, marketing_source_fingerprint

VOID = set('area base br col embed hr img input link meta param source track wbr'.split())


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def all(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.all()

    def inner(self):
        return ''.join(child.html() if isinstance(child, Node) else child for child in self.children)

    def html(self):
        if not self.tag:
            return self.inner()
        attrs = ''.join(' '+key+('="'+escape(str(value), quote=True)+'"' if value is not None else '') for key, value in self.attrs.items())
        return '<'+self.tag+attrs+'>'+('' if self.tag in VOID else self.inner()+'</'+self.tag+'>')

    def text(self, value):
        self.children = [escape(value)]


class Tree(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.root = Node()
        self.current = self.root
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data): self.current.children.append(data)
    def handle_entityref(self, name): self.current.children.append('&'+name+';')
    def handle_charref(self, name): self.current.children.append('&#'+name+';')
    def handle_comment(self, text): pass


def first(root, predicate):
    return next((node for node in root.all() if predicate(node)), None)


def classed(node, value):
    return value in (node.attrs.get('class') or '').split()


def translate(root, dictionary, ui, support, extra, registry, locale):
    # Dictionaries contain reviewed-by-author HTML for the handful of existing
    # inline links/emphasis. They are repository inputs, never visitor input.
    for node in list(root.all()):
        key = node.attrs.get('data-i18n')
        if key:
            assert key in dictionary, f'{locale}: missing marketing key {key}'
            node.children = [dictionary[key]]
        for pair in (node.attrs.get('data-i18n-attr') or '').split(';'):
            if ':' in pair:
                attr, key = pair.split(':', 1)
                node.attrs[attr.strip()] = re.sub('<[^>]+>', '', dictionary[key.strip()])
        if node.tag == 'img' and node.attrs.get('alt'):
            src = node.attrs.get('src', '')
            if src.endswith('tortoise.webp'):
                node.attrs['alt'] = dictionary['home.emblem']
            else:
                image_product = {'reptile.webp':'reptile-probiotics', 'gutdaily.webp':'gutdaily', 'settle.webp':'settle', 'plumacalm.webp':'plumacalm', 'omegacat.webp':'omega-cat', 'calmcat.webp':'calmcat'}
                slug = image_product.get(src.rsplit('/', 1)[-1])
                if slug:
                    node.attrs['alt'] = 'MSRA · '+dictionary['p.'+slug+'.species']
        if node.attrs.get('lang') == 'en':
            node.attrs['lang'] = locale
        if classed(node, 'subscription-entry'):
            node.attrs['aria-label'] = ui['email_heading']
        if node.attrs.get('data-subscription-entry-email') is not None or 'data-subscription-entry-email' in node.attrs:
            node.attrs['aria-label'] = node.attrs['placeholder'] = extra['email']
        if node.tag == 'form' and 'data-subscription-entry' in node.attrs:
            for child in node.all():
                if child.tag == 'button': child.text(extra['receive'])
                if classed(child, 'visually-hidden'): child.text(extra['email'])
        replacements = {
            'research-updates-hero-note': extra['free'],
            'research-updates-cta__note': extra['preferences'],
        }
        for css, value in replacements.items():
            if classed(node, css): node.text(value)
        if classed(node, 'research-updates-cta__copy'):
            for child in node.all():
                if child.tag == 'h2': child.text(extra['follow'])
                elif child.tag == 'p': child.text(ui['email_heading'] if classed(child, 'label') else extra['choose'])
        if (node.attrs.get('aria-label') or '').startswith('A closed loop:'): node.attrs['aria-label'] = dictionary['loop.h2']
        if node.attrs.get('aria-label') == 'Breadcrumb': node.attrs['aria-label'] = ui['primary_navigation']
        if node.attrs.get('aria-label') == 'On this page': node.attrs['aria-label'] = dictionary['pd.more']
    # Reparse translated inline dictionary markup before localizing its links.
    root = Tree(root.html()).root
    for node in root.all():
        if node.tag != 'a' or not node.attrs.get('href'): continue
        target = urlsplit(node.attrs['href'])
        if target.netloc not in ('', 'msralab.com') or target.scheme not in ('', 'https'): continue
        identity = registry['by_route'].get(target.path)
        if not identity: continue
        resource = registry['resources'][identity['translation_key']]
        variant = resource['variants'].get(locale)
        route = variant['url'] if variant else '/'+locale.lower()+resource['source_route']
        node.attrs['href'] = urlunsplit(('', '', route, target.query, target.fragment))
        node.attrs['hreflang'] = locale
        # Existing static report cards contain source metadata outside i18n nodes.
        if resource['kind'] == 'report' and variant:
            for child in node.all():
                if child.tag == 'b': child.text(variant['display_title'] or variant['title'])
        if resource['kind'] == 'report' and variant and node.parent and node.parent.tag == 'b':
            node.text(variant['display_title'] or variant['title'])
    # The product related-report summary is a sibling of its translated link.
    for node in root.all():
        if not classed(node, 'pd-text'): continue
        report_link = first(node, lambda n: n.tag == 'a' and '/research/20' in (n.attrs.get('href') or ''))
        if report_link:
            target = urlsplit(report_link.attrs['href']).path
            identity = registry['by_route'].get(target)
            if identity:
                variant = registry['resources'][identity['translation_key']]['variants'][locale]
                paragraphs = [n for n in node.children if isinstance(n, Node) and n.tag == 'p']
                if len(paragraphs) > 1: paragraphs[1].text(variant['summary'])
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--built', type=Path, required=True)
    parser.add_argument('--locales', nargs='*')
    args = parser.parse_args()
    fingerprint = marketing_source_fingerprint(ROOT)
    manifest = args.built/'preview-manifest.json'
    if manifest.exists():
        built_meta = json.loads(manifest.read_text())
        assert built_meta.get('marketingSourceFingerprint') == fingerprint, 'English source snapshot is stale; render it again before generating marketing pages'
    registry = json.loads((ROOT/'_data/localization_registry.json').read_text())
    extra_all = json.loads((ROOT/'_data/marketing_extras.json').read_text())
    locales = args.locales or [locale for locale in LOCALES if locale != 'en']
    sources = [doc for doc in read_documents(ROOT) if doc['file'] in ('index.html', '404.html') or doc['file'].startswith('shop/')]
    created = []
    for locale in locales:
        dictionary_path = ROOT/'assets/i18n'/(locale+'.json')
        assert dictionary_path.is_file(), f'{locale}: dictionary not ready'
        dictionary = json.loads(dictionary_path.read_text())
        ui = json.loads((ROOT/'_data/localized_ui'/(locale+'.json')).read_text())
        support = json.loads((ROOT/'_data/localized_support'/(locale+'.json')).read_text())
        extra = extra_all[locale]
        data_dictionary = ROOT/'_data/marketing_ui'/(locale+'.json')
        data_dictionary.parent.mkdir(exist_ok=True)
        data_dictionary.write_text(dictionary_path.read_text())
        for doc in sources:
            route, key = source_route(doc), translation_key(doc)
            path = args.built/route.lstrip('/')/('index.html') if route.endswith('/') else args.built/route.lstrip('/')
            tree = Tree(path.read_text()).root
            main_node = first(tree, lambda node: node.tag == 'main')
            assert main_node, str(path)
            holder = Tree(main_node.inner()).root
            waitlist = first(tree, lambda node: node.attrs.get('id') == 'waitlist')
            if waitlist: holder.children.append(waitlist)
            translated = translate(holder, dictionary, ui, support, extra, registry, locale)
            h1 = first(translated, lambda node: node.tag == 'h1')
            title = re.sub('<[^>]+>', '', h1.inner()).replace('&amp;', '&')
            slug = doc['meta'].get('product')
            description = re.sub('<[^>]+>', '', dictionary['p.'+slug+'.blurb'] if slug else dictionary['home.lead'] if route == '/' else dictionary['shop.lead'] if route == '/shop/' else dictionary['nf.h1'])
            metadata = {
                'layout':'localized-marketing', 'locale':locale, 'translation_key':key,
                'locale_key':key+'::'+locale, 'permalink':'/'+locale.lower()+route,
                'source_fragment_ids': sorted({'top'} | set(re.findall(r'\bid=[\"\']([^\"\']+)', holder.html()))),
                'source_content_id':None, 'source_route':route, 'source_file':doc['file'],
                'source_sha256':sha256((ROOT/doc['file']).read_bytes()).hexdigest(),
                'source_prepared_date':None, 'source_refs':[],
                'title': title, 'display_title': title, 'seo_title': title,
                'description': description, 'summary':description,
                'image':doc['meta'].get('image'),
                'content_label': dictionary['brand.name'], 'translation_status':'ai-draft',
                'native_review_status':'pending', 'clinical_review_status':'not-applicable',
                'publication_state':'editorial-draft', 'release_approved':False,
                'robots':'noindex', 'sitemap':False, 'marketing_product':slug,
                'dictionary_sha256':sha256(dictionary_path.read_bytes()).hexdigest(),
                'generator_input_sha256':fingerprint,
            }
            filename = 'marketing-'+(slug or 'home' if route == '/' else slug or 'shop' if route == '/shop/' else slug or 'not-found')+'.html'
            destination = ROOT/'_localized'/locale/filename
            stale_markdown = destination.with_suffix('.md')
            if stale_markdown.is_file(): stale_markdown.unlink()
            destination.parent.mkdir(exist_ok=True)
            destination.write_text('---\n'+json.dumps(metadata, ensure_ascii=False, indent=2)+'\n---\n'+translated.html()+'\n')
            created.append(str(destination.relative_to(ROOT)))
    print(json.dumps({'generated':len(created), 'locales':locales, 'source_fingerprint':fingerprint}, ensure_ascii=False))


if __name__ == '__main__': main()
