#!/usr/bin/env python3
"""Check the gated Kit integration locally, without network or provider actions.

    python3 tools/verify_subscriptions.py
    python3 tools/verify_subscriptions.py --built /absolute/disabled-preview \
        --active-built /absolute/isolated-active-preview
    python3 tools/verify_subscriptions.py --hosted-built /absolute/hosted-preview \
        --blocked-built missing-privacy=/absolute/blocked-preview

The optional previews are supplied by the caller. This verifier never enables
collection, renders pages, submits forms, or establishes provider/account checks.
Only Python's standard library is used. The YAML reader intentionally accepts
the simple mappings, lists and scalars used by subscriptions.yml and fails on
unsupported syntax rather than silently guessing its meaning.
"""
import argparse
from dataclasses import dataclass, field
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = 'docs/kit-form-public-2026-10-29.html'
INCLUDE = '_includes/kit-research-form.html'
FORM_ID = '10113119'
UID = '924e9b0702'
ACTION = 'https://app.kit.com/forms/10113119/subscriptions'
SCRIPT = 'https://f.convertkit.com/ckjs/ck.5.js'
HOSTED = 'https://msra.kit.com/924e9b0702'
DIALOG_ID = 'research-subscription-dialog'
TOPICS = {
    'feline-urinary': ('25146776', 'Feline urinary health'),
    'rabbit-gut': ('25146778', 'Rabbit digestive health'),
    'new-research': ('25146779', 'New research launches'),
}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'link', 'meta', 'param', 'source', 'track', 'wbr'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uncomment(line):
    quote = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == '\\' and quote == '"':
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char == '#' and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    require(quote is None, 'Unclosed YAML quote')
    return line.rstrip()


def scalar(value):
    if value.startswith('"'):
        result = json.loads(value)
        require(isinstance(result, str), 'Expected a quoted YAML string')
        return result
    if value.startswith("'"):
        require(value.endswith("'"), 'Unclosed single-quoted YAML scalar')
        return value[1:-1].replace("''", "'")
    if value in ('true', 'false'):
        return value == 'true'
    if value in ('null', '~'):
        return None
    if re.fullmatch(r'-?(?:0|[1-9][0-9]*)', value):
        return int(value)
    require(value and not value.startswith(('[', '{', '|', '>', '&', '*', '!')),
            f'Unsupported YAML scalar: {value!r}')
    return value


def read_config(path):
    lines = []
    for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        require('\t' not in raw, f'{path}:{number}: tabs are unsupported in YAML')
        line = uncomment(raw)
        if line.strip():
            lines.append((len(line) - len(line.lstrip()), line.lstrip(), number))

    def block(index, indent):
        is_list = lines[index][1].startswith('- ')
        result = [] if is_list else {}
        while index < len(lines) and lines[index][0] == indent:
            _, text, number = lines[index]
            if is_list:
                require(text.startswith('- '), f'{path}:{number}: mixed YAML list/mapping')
                result.append(scalar(text[2:].strip()))
                index += 1
                continue
            match = re.fullmatch(r'([A-Za-z0-9_-]+):(?:\s+(.*))?', text)
            require(match is not None, f'{path}:{number}: unsupported YAML mapping')
            key, value = match.groups()
            require(key not in result, f'{path}:{number}: duplicate YAML key {key}')
            index += 1
            if value is not None and value.strip():
                result[key] = scalar(value.strip())
            else:
                require(index < len(lines) and lines[index][0] > indent,
                        f'{path}:{number}: empty YAML block {key}')
                result[key], index = block(index, lines[index][0])
            if index < len(lines):
                require(lines[index][0] <= indent,
                        f'{path}:{lines[index][2]}: unexpected YAML indentation')
        return result, index

    require(lines and lines[0][0] == 0, f'{path}: expected a root YAML mapping')
    result, consumed = block(0, 0)
    require(consumed == len(lines) and isinstance(result, dict), f'{path}: invalid root YAML mapping')
    return result


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def all(self, tag=None, attr=None):
        found = []
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag == tag) and (attr is None or attr in child.attrs):
                    found.append(child)
                found.extend(child.all(tag, attr))
        return found

    def text(self):
        return ' '.join(''.join(child.text() if isinstance(child, Node) else child
                                for child in self.children).split())


class Document(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.root = Node('document')
        self.stack = [self.root]
        self.feed(markup)
        self.close()

    def handle_starttag(self, tag, attributes):
        require(len(attributes) == len(dict(attributes)), f'Duplicate {tag} attributes')
        node = Node(tag, dict(attributes))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        # HTML permits a few optional end tags; retain ancestry without treating
        # unrelated page HTML as an XML document. Vendor integrity is checked
        # independently by exact artifact preservation and form structure.
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def vendor_forms(document):
    return [node for node in document.all('form')
            if 'formkit-form' in node.attrs.get('class', '').split()]


def check_vendor_markup(markup):
    document = Document(markup).root
    forms = vendor_forms(document)
    require(len(forms) == 1, 'Expected exactly one genuine Kit form')
    form = forms[0]
    for key, expected in {'action': ACTION, 'method': 'post', 'data-sv-form': FORM_ID,
                          'data-uid': UID, 'data-format': 'inline', 'data-version': '5'}.items():
        require(form.attrs.get(key) == expected, f'Kit form {key} differs from saved artifact')
    require(not form.all('form'), 'Kit form contains a nested form')
    inputs = form.all('input')
    emails = [node for node in inputs if node.attrs.get('type') == 'email']
    require(len(emails) == 1 and emails[0].attrs.get('name') == 'email_address'
            and 'required' in emails[0].attrs, 'Expected the genuine required Kit email field')
    boxes = [node for node in inputs if node.attrs.get('type') == 'checkbox']
    require(len(boxes) == 3, 'Expected exactly three Kit topic checkboxes')
    labels = {node.attrs.get('for'): node.text() for node in form.all('label')}
    observed = {}
    for box in boxes:
        require(box.attrs.get('name') == 'tags[]', 'Kit topic checkbox field name changed')
        require('checked' not in box.attrs, 'Saved Kit markup must not preselect topic consent')
        tag = box.attrs.get('value')
        require(tag not in observed, 'Duplicate Kit topic tag')
        observed[tag] = labels.get(box.attrs.get('id'))
    require(observed == {tag: label for tag, label in TOPICS.values()},
            'Kit checkbox labels/tags differ from the observed public artifact')
    require(len(inputs) == 4, 'Unexpected additional Kit input, including hidden consent fields')
    require(len([node for node in form.all('button')
                 if node.attrs.get('data-element') == 'submit']) == 1,
            'Expected one genuine Kit submit control')
    scripts = [node for node in document.all('script') if node.attrs.get('src') == SCRIPT]
    require(len(scripts) == 1, 'Expected one genuine Kit behavior script')
    branding = [node for node in form.all('a') if node.attrs.get('data-element') == 'powered-by']
    require(len(branding) == 1 and branding[0].text() == 'Built with Kit'
            and branding[0].attrs.get('href', '').startswith('https://kit.com/features/forms?'),
            'Genuine Kit branding must remain present')
    options = json.loads(form.attrs.get('data-options', '{}')).get('settings', {})
    require(options.get('powered_by', {}).get('show') is True, 'Kit branding disabled in options')
    require(options.get('after_subscribe', {}).get('action') == 'message'
            and 'confirmation link' in options.get('after_subscribe', {}).get('success_message', ''),
            'Kit response must direct the visitor to confirm their email')
    require(not any(options.get('analytics', {}).values()), 'Unexpected analytics in vendor form')
    return {'form_id': FORM_ID, 'uid': UID, 'email_fields': 1, 'topic_checkboxes': 3,
            'vendor_scripts': 1, 'kit_branding_preserved': True}


def check_source(root):
    artifact = (root / ARTIFACT).read_bytes()
    require((root / INCLUDE).read_bytes() == artifact,
            f'{INCLUDE} must preserve the saved public Form HTML byte-for-byte')
    vendor = check_vendor_markup(artifact.decode('utf-8'))
    config = read_config(root / '_data/subscriptions.yml')
    for key in ('enabled', 'account_checks_verified'):
        require(config.get(key) is False, f'Saved source must keep {key}: false')
    signup = config.get('signup', {})
    require(signup.get('topic_choices_verified') is False,
            'Saved source must keep topic_choices_verified: false')
    require(config.get('provider_name') == 'Kit' and signup.get('mode') == 'inline',
            'Expected the gated inline Kit configuration')
    require(signup.get('hosted_form_url') == HOSTED, 'Hosted fallback must use the genuine Kit Share URL')
    inline = signup.get('inline', {})
    expected = {'form_id': FORM_ID, 'uid': UID, 'action': ACTION, 'script_url': SCRIPT,
                'email_field': 'email_address', 'topic_field': 'tags[]',
                'topic_tags': {topic: tag for topic, (tag, _) in TOPICS.items()}}
    require(inline == expected, 'Inline configuration must match the genuine form and exact topic catalog')
    topics = config.get('topics', {})
    require({item.get('id') for item in topics.values()} == set(TOPICS),
            'Subscription catalog has an unknown or missing topic ID')
    require(len(topics) == len(TOPICS), 'Duplicate subscription topic ID')
    for item in topics.values():
        require(item.get('enabled') is True and item.get('label') == TOPICS[item['id']][1],
                'Subscription catalog label or enabled state differs from form mapping')
    require(set(config.get('project_topics', {}).values()) <= set(TOPICS),
            'A research project maps to an unknown subscription topic')
    require(config.get('product_updates', {}).get('enabled') is False,
            'Product subscription collection must remain disabled')
    modal = (root / '_includes/subscription-modal.html').read_text(encoding='utf-8')
    require(modal.count('include kit-research-form.html') == 1,
            'Shared dialog must include the genuine Kit form once')
    require('data-subscription-inline' in modal and 'data-topic-tags=' in modal,
            'Inline topic mapping is missing from the shared dialog')
    layout = (root / '_layouts/default.html').read_text(encoding='utf-8')
    require(layout.count('include subscription-modal.html') == 1,
            'Default layout must include one shared subscription dialog')
    page = (root / 'learn/updates/index.html').read_text(encoding='utf-8')
    require('include subscription-bar.html' in page
            and 'include kit-research-form.html' not in page,
            'Fallback page must reuse the entry bar and shared dialog, without a second provider form')
    return config, artifact.decode('utf-8'), {'saved_collection_flags': 'off',
        'vendor_include_matches_artifact': True,
        'artifact_sha256': hashlib.sha256(artifact).hexdigest(),
        'topic_mapping': expected['topic_tags'], 'vendor_form': vendor}


def page_at(output):
    page = output / 'learn/updates/index.html'
    require(page.is_file(), f'Missing rendered updates page: {page}')
    return page.read_text(encoding='utf-8')


def shared_dialog(document):
    dialogs = document.all('dialog', 'data-subscription-modal')
    require(len(dialogs) == 1, 'Expected exactly one shared research subscription dialog')
    dialog = dialogs[0]
    require(dialog.attrs.get('id') == DIALOG_ID and 'open' not in dialog.attrs,
            'Shared subscription dialog must have the expected ID and start closed')
    for attribute in ('aria-labelledby', 'aria-describedby'):
        target = dialog.attrs.get(attribute)
        require(target and len([node for node in dialog.all()
                                if node.attrs.get('id') == target]) == 1,
                f'Shared dialog has a missing or duplicated {attribute} target')
    close = dialog.all('button', 'data-subscription-close')
    require(len(close) == 1 and close[0].attrs.get('type') == 'button'
            and close[0].attrs.get('aria-label'), 'Shared dialog needs one labeled close button')
    return dialog


def check_entries(document):
    entries = document.all('form', 'data-subscription-entry')
    require(entries, 'Expected at least one local research email entry bar')
    for entry in entries:
        require(entry.attrs.get('method', '').lower() == 'get'
                and re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)*learn/updates/',
                                 entry.attrs.get('action', '')),
                'Entry bar fallback must be an internal updates-page GET without query data')
        require(not entry.all('form'), 'Entry bar contains a nested form')
        emails = entry.all('input', 'data-subscription-entry-email')
        require(len(emails) == 1 and emails[0].attrs.get('type') == 'email'
                and 'required' in emails[0].attrs,
                'Entry bar needs one local required email input')
        controls = entry.all('input') + entry.all('button') + entry.all('textarea') + entry.all('select')
        require(all(not {'name', 'form', 'formaction', 'formmethod'} & control.attrs.keys()
                    for control in controls),
                'Entry-bar controls must not serialize an email or attach to another form')
        require(all('value' not in email.attrs for email in emails),
                'Saved entry bars must not prefill an email address')
        buttons = entry.all('button')
        require(len(buttons) == 1 and buttons[0].attrs.get('type') == 'submit'
                and buttons[0].attrs.get('aria-haspopup') == 'dialog'
                and buttons[0].attrs.get('aria-controls') == DIALOG_ID,
                'Entry bar must open the shared research dialog')
        require(entry.attrs.get('data-topic', '') in {'', *TOPICS},
                'Entry bar has an unknown suggested topic')
    return len(entries)


def local_preview_form(dialog, require_three_topics=True):
    forms = dialog.all('form', 'data-subscription-preview-form')
    require(len(forms) == 1 and len(dialog.all('form')) == 1,
            'Local preview must contain one dialog-only form')
    form = forms[0]
    require(form.attrs.get('method') == 'dialog' and 'action' not in form.attrs,
            'Local preview must not submit to a network destination')
    controls = form.all('input') + form.all('button') + form.all('textarea') + form.all('select')
    require(all(not {'name', 'form', 'formaction', 'formmethod'} & control.attrs.keys()
                for control in controls),
            'Local preview controls must not serialize email or topic data')
    emails = form.all('input', 'data-subscription-email')
    require(len(emails) == 1 and emails[0].attrs.get('type') == 'email'
            and 'value' not in emails[0].attrs, 'Expected one empty local preview email input')
    topics = form.all('input', 'data-subscription-topic')
    if require_three_topics:
        require(len(topics) == 3 and {node.attrs.get('value') for node in topics} == set(TOPICS),
                'Local topic preview differs from the public catalog')
    require(all(node.attrs.get('type') == 'checkbox' and 'checked' not in node.attrs for node in topics),
            'Local topic suggestions must start as unchecked checkbox controls')
    return form, topics


def check_disabled(output, require_three_topics=True):
    markup = page_at(output)
    document = Document(markup).root
    dialog = shared_dialog(document)
    entry_count = check_entries(document)
    require(dialog.attrs.get('data-signup-mode') == 'preview'
            and dialog.attrs.get('data-signup-ready') == 'false',
            'Disabled dialog must explicitly remain in preview mode')
    require(not vendor_forms(document), 'Disabled page exposes a provider form')
    require(not [node for node in document.all('input') if node.attrs.get('name') == 'email_address'],
            'Disabled page exposes a provider email field')
    require(ACTION not in markup and SCRIPT not in markup,
            'Disabled page exposes the vendor action or behavior script')
    require(not document.all(attr='data-subscription-inline'), 'Disabled page exposes inline readiness')
    require(not document.all(attr='data-subscription-link'), 'Disabled page exposes a provider handoff')
    form, local = local_preview_form(dialog, require_three_topics)
    final = form.all('button')
    require(len(final) == 1 and final[0].attrs.get('type') == 'button'
            and 'disabled' in final[0].attrs, 'Preview final action must remain disabled')
    require('preview only' in form.text().lower() and 'not saved or sent' in form.text().lower(),
            'Local preview must explain that email and choices are not saved or sent')
    return {'output': str(output), 'shared_dialogs': 1, 'entry_bars': entry_count,
            'provider_forms': 0, 'provider_email_fields': 0, 'vendor_scripts': 0,
            'local_preview_email_fields': 1 + entry_count,
            'local_topic_previews': len(local), 'provider_handoffs': 0}


def check_active(output, artifact):
    markup = page_at(output)
    require(markup.count(artifact) == 1, 'Active fixture must render the exact saved vendor markup once')
    document = Document(markup).root
    dialog = shared_dialog(document)
    entry_count = check_entries(document)
    require(dialog.attrs.get('data-signup-mode') == 'inline'
            and dialog.attrs.get('data-signup-ready') == 'true',
            'Active fixture must expose a ready inline shared dialog')
    require(len(dialog.all('form')) == 1 and len(vendor_forms(document)) == 1,
            'Active fixture must contain exactly one provider form, inside the shared dialog')
    vendor = check_vendor_markup(markup)
    require(not document.all(attr='data-subscription-chooser')
            and not document.all(attr='data-subscription-topic'),
            'Active inline fixture contains a duplicate local topic chooser')
    containers = dialog.all(attr='data-subscription-inline')
    require(len(containers) == 1, 'Expected one inline Kit mapping container')
    mapping = json.loads(containers[0].attrs.get('data-topic-tags', '{}'))
    require(mapping == {topic: tag for topic, (tag, _) in TOPICS.items()},
            'Active fixture contains an unknown/missing/mismatched topic-to-tag mapping')
    require(len(vendor_forms(containers[0])) == 1, 'Genuine form is outside its topic-mapping container')
    require(not document.all(attr='data-subscription-link'), 'Active inline fixture exposes hosted fallback')
    require(not dialog.all(attr='data-subscription-preview-form'),
            'Active dialog contains a duplicate preview form')
    nojs = document.all('noscript')
    require(any(link.attrs.get('href') == HOSTED for node in nojs for link in node.all('a')),
            'Active dialog needs a reachable genuine hosted fallback without JavaScript')
    return {'output': str(output), 'shared_dialogs': 1, 'entry_bars': entry_count,
            'local_duplicate_choosers': 0, 'topic_mapping_exact': True,
            'vendor_markup_preserved': True, 'vendor_form': vendor,
            'scope': 'local rendered fixture only; no provider submission or confirmation tested'}


def check_hosted(output, hosted_url):
    markup = page_at(output)
    document = Document(markup).root
    dialog = shared_dialog(document)
    entry_count = check_entries(document)
    require(dialog.attrs.get('data-signup-mode') == 'hosted-reconfirm',
            'Hosted fallback must explicitly use hosted-reconfirm mode')
    require(not vendor_forms(document) and ACTION not in markup and SCRIPT not in markup,
            'Hosted fallback exposes an inline vendor form/action/script')
    require(not document.all(attr='data-subscription-inline'), 'Hosted fallback exposes inline readiness')
    chooser, local = local_preview_form(dialog)
    links = dialog.all('a', 'data-subscription-link')
    require(len(links) == 1 and links[0].attrs.get('href') == hosted_url,
            'Hosted fallback must use the genuine Share URL without local query forwarding')
    require('choose your topics again' in chooser.text().lower(),
            'Hosted fallback must explain that the visitor chooses topics again on Kit')
    return {'output': str(output), 'shared_dialogs': 1, 'entry_bars': entry_count,
            'provider_forms': 0, 'local_preview_email_fields': 1 + entry_count,
            'local_topic_previews': 3, 'genuine_hosted_handoffs': 1,
            'topic_reconfirmation_explained': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--built', type=Path, help='rendered disabled site directory')
    parser.add_argument('--active-built', type=Path, help='isolated active-inline rendered fixture directory')
    parser.add_argument('--hosted-built', type=Path, help='isolated active hosted-fallback fixture directory')
    parser.add_argument('--blocked-built', action='append', default=[], metavar='LABEL=DIRECTORY',
                        help='isolated invalid-config fixture expected to block capture (repeatable)')
    args = parser.parse_args()
    try:
        config, artifact, result = check_source(args.source_root.resolve())
        if args.built:
            result['disabled_render'] = check_disabled(args.built.resolve())
        if args.active_built:
            result['active_fixture'] = check_active(args.active_built.resolve(), artifact)
        if args.hosted_built:
            result['hosted_fixture'] = check_hosted(args.hosted_built.resolve(),
                                                   config['signup']['hosted_form_url'])
        if args.blocked_built:
            result['blocked_fixtures'] = {}
            for fixture in args.blocked_built:
                label, separator, directory = fixture.partition('=')
                require(separator and label and directory,
                        '--blocked-built must be LABEL=DIRECTORY')
                require(label not in result['blocked_fixtures'], 'Duplicate blocked fixture label')
                result['blocked_fixtures'][label] = check_disabled(Path(directory).resolve(), False)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f'Subscription verification failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
