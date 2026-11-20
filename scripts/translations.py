#!/usr/bin/env python3
"""Translation helper that needs nothing but the Python standard library.

The project keeps Russian as the source language: every msgid in the code and
templates is the original Russian text, and locale/<lang>/LC_MESSAGES/django.po
holds the translations. GNU gettext is not required (handy on Windows).

    python scripts/translations.py extract   # add new strings to the .po files
    python scripts/translations.py compile   # build django.mo from django.po
    python scripts/translations.py check     # fail if a string is missing or
                                             # a .mo file is out of date

The compiled .mo files are committed, so the Docker image and CI need no
gettext tools either.
"""
import ast
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALE_DIR = ROOT / 'locale'
LANGUAGES = {
    'en': 'nplurals=2; plural=(n != 1);',
    'ja': 'nplurals=1; plural=0;',
}
SOURCE_DIRS = [ROOT / 'main', ROOT / 'strikezoneweb']
GETTEXT_NAMES = {'_', 'gettext', 'gettext_lazy'}

CYRILLIC = re.compile('[А-Яа-яЁё]')
PLACEHOLDER = re.compile(r'%\(\w+\)s')

# ---------------------------------------------------------------- extraction

TRANSLATE_TAG = re.compile(
    r"""\{%\s*translate\s+(?P<q>["'])(?P<text>.*?)(?P=q)(?:\s+as\s+\w+)?\s*%\}""", re.S)
BLOCK_TAG = re.compile(
    r"""\{%\s*blocktranslate(?P<opts>[^%]*)%\}(?P<body>.*?)\{%\s*endblocktranslate\s*%\}""", re.S)
VARIABLE = re.compile(r'\{\{\s*(\w+)\s*\}\}')


def extract_python(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) != 1:
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, 'attr', None)
        arg = node.args[0]
        if name in GETTEXT_NAMES and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            yield arg.value


def extract_template(path):
    text = path.read_text(encoding='utf-8')
    for match in TRANSLATE_TAG.finditer(text):
        yield match.group('text')
    for match in BLOCK_TAG.finditer(text):
        body = match.group('body')
        if 'trimmed' in match.group('opts'):
            body = ' '.join(line.strip() for line in body.splitlines() if line.strip())
        yield VARIABLE.sub(lambda m: '%%(%s)s' % m.group(1), body)


def extract_all():
    found = []
    for base in SOURCE_DIRS:
        for path in sorted(base.rglob('*')):
            if 'migrations' in path.parts or 'tests' in path.parts:
                continue
            if path.suffix == '.py':
                found.extend(extract_python(path))
            elif path.suffix == '.html':
                found.extend(extract_template(path))
    unique = []
    for msgid in found:
        if msgid not in unique:
            unique.append(msgid)
    return unique


# ----------------------------------------------------------------- .po files

def po_escape(text):
    return (text.replace('\\', '\\\\').replace('"', '\\"')
            .replace('\n', '\\n').replace('\t', '\\t'))


def po_unescape(text):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), text)


def parse_po(path):
    """Return {msgid: msgstr}; fuzzy entries are skipped like msgfmt does."""
    entries = {}
    msgid = msgstr = None
    fuzzy = False
    target = None

    def flush():
        if msgid is not None and msgstr is not None and not fuzzy:
            entries[msgid] = msgstr

    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line.startswith('#,') and 'fuzzy' in line:
            flush()
            msgid = msgstr = None
            fuzzy = True
            continue
        if not line or line.startswith('#'):
            continue
        if line.startswith('msgid '):
            flush()
            if msgstr is not None or msgid is not None:
                fuzzy = False if msgstr is not None else fuzzy
            msgid, msgstr, target = po_unescape(line[7:-1]), None, 'id'
        elif line.startswith('msgstr '):
            msgstr, target = po_unescape(line[8:-1]), 'str'
        elif line.startswith('"'):
            piece = po_unescape(line[1:-1])
            if target == 'id':
                msgid += piece
            else:
                msgstr += piece
    flush()
    return entries


def header(lang):
    return (
        'Project-Id-Version: Strike Zone\n'
        'Language: %s\n'
        'MIME-Version: 1.0\n'
        'Content-Type: text/plain; charset=UTF-8\n'
        'Content-Transfer-Encoding: 8bit\n'
        'Plural-Forms: %s\n' % (lang, LANGUAGES[lang]))


def write_po(lang, msgids, translations):
    def block(msgid, msgstr):
        return 'msgid "%s"\nmsgstr "%s"\n' % (po_escape(msgid), po_escape(msgstr))

    parts = [block('', header(lang))]
    for msgid in msgids:
        parts.append(block(msgid, translations.get(msgid, '')))
    po_path(lang).write_text('\n'.join(parts), encoding='utf-8')


def po_path(lang):
    return LOCALE_DIR / lang / 'LC_MESSAGES' / 'django.po'


def mo_path(lang):
    return LOCALE_DIR / lang / 'LC_MESSAGES' / 'django.mo'


# ----------------------------------------------------------------- .mo files

def build_mo(entries, lang):
    """Binary .mo content (little endian, same layout as GNU msgfmt)."""
    catalog = {'': header(lang)}
    catalog.update({k: v for k, v in entries.items() if k and v})
    keys = sorted(catalog)
    ids = b''
    strs = b''
    offsets = []
    for key in keys:
        kb, vb = key.encode('utf-8'), catalog[key].encode('utf-8')
        offsets.append((len(ids), len(kb), len(strs), len(vb)))
        ids += kb + b'\0'
        strs += vb + b'\0'
    count = len(keys)
    keystart = 7 * 4 + 16 * count
    valuestart = keystart + len(ids)
    table = []
    for o1, l1, _o2, _l2 in offsets:
        table += [l1, o1 + keystart]
    for _o1, _l1, o2, l2 in offsets:
        table += [l2, o2 + valuestart]
    output = struct.pack('<Iiiiiii', 0x950412de, 0, count, 7 * 4, 7 * 4 + count * 8, 0, 0)
    output += struct.pack('<%di' % len(table), *table)
    return output + ids + strs


# ------------------------------------------------------------------ commands

def cmd_extract():
    msgids = extract_all()
    for lang in LANGUAGES:
        old = parse_po(po_path(lang)) if po_path(lang).exists() else {}
        po_path(lang).parent.mkdir(parents=True, exist_ok=True)
        write_po(lang, msgids, old)
        missing = [m for m in msgids if not old.get(m)]
        print('%s: %d strings, %d untranslated' % (lang, len(msgids), len(missing)))


def cmd_compile():
    for lang in LANGUAGES:
        entries = parse_po(po_path(lang))
        mo_path(lang).write_bytes(build_mo(entries, lang))
        print('compiled', mo_path(lang).relative_to(ROOT))


def cmd_check():
    errors = []
    msgids = extract_all()
    for lang in LANGUAGES:
        if not po_path(lang).exists():
            errors.append('%s: %s is missing' % (lang, po_path(lang).relative_to(ROOT)))
            continue
        entries = parse_po(po_path(lang))
        for msgid in msgids:
            msgstr = entries.get(msgid)
            if not msgstr:
                errors.append('%s: no translation for %r (run "extract" and fill it in)' % (lang, msgid))
            elif sorted(PLACEHOLDER.findall(msgid)) != sorted(PLACEHOLDER.findall(msgstr)):
                errors.append('%s: placeholders differ in %r' % (lang, msgid))
        for msgid in entries:
            if msgid and msgid not in msgids and CYRILLIC.search(msgid):
                errors.append('%s: obsolete string %r (run "extract")' % (lang, msgid))
        expected = build_mo(entries, lang)
        if not mo_path(lang).exists() or mo_path(lang).read_bytes() != expected:
            errors.append('%s: django.mo is out of date (run "compile")' % lang)
    for error in errors:
        print('ERROR', error)
    if errors:
        return 1
    print('translations OK: %d strings, languages: %s' % (len(msgids), ', '.join(LANGUAGES)))
    return 0


def main(argv):
    commands = {'extract': cmd_extract, 'compile': cmd_compile, 'check': cmd_check}
    if len(argv) != 2 or argv[1] not in commands:
        print(__doc__)
        return 2
    return commands[argv[1]]() or 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
