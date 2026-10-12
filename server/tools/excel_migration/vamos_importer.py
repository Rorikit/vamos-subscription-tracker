"""Lossless XLSX -> versioned migration staging. Python 3.11+, stdlib only."""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sqlite3, sys, zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET

VERSION = '1.0.0'
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'s': S}
MAX_XML = 128 * 1024 * 1024

def canonical_json(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(x):
    return hashlib.sha256(canonical_json(x).encode('utf-8')).hexdigest()

def tidy(x):
    return re.sub(r'\s+', ' ', str(x or '').replace('\u00a0', ' ')).strip()

def key(x):
    # Deliberately do not collapse е/ё or male/female surnames.
    return tidy(x).casefold()

def colnum(address):
    n = 0
    for c in re.match(r'[A-Z]+', address)[0]:
        n = n * 26 + ord(c) - 64
    return n

def rownum(address):
    return int(re.search(r'\d+$', address)[0])

def number(cell, money=False):
    if not cell or cell.get('value') is None or not str(cell.get('value')).strip():
        return None
    if cell.get('formula') is not None or cell['type'] in ['e', 'b', 'd']:
        raise ValueError('formula/error/date/boolean is not a trusted numeric input')
    # No ambiguous thousands separators, currency symbols or date serial styles.
    if cell.get('is_date'):
        raise ValueError('date/time formatted cell in numeric field')
    raw = str(cell['value']).strip().replace('\u00a0', '').replace(' ', '')
    if not re.fullmatch(r'[+-]?\d+(?:[.,]\d+)?', raw):
        raise ValueError('invalid numeric input')
    try:
        d = Decimal(raw.replace(',', '.'))
    except InvalidOperation as exc:
        raise ValueError('invalid decimal') from exc
    if not d.is_finite():
        raise ValueError('non-finite number')
    if money:
        try:
            if d != d.quantize(Decimal('.01')):
                raise ValueError('more than two decimal places; no silent rounding')
        except InvalidOperation as exc:
            raise ValueError('decimal exceeds supported precision') from exc
    return format(d, 'f')

class XLSX:
    def __init__(self, path):
        self.path = Path(path)
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.z = zipfile.ZipFile(self.path)
        if len(self.z.namelist()) != len(set(self.z.namelist())):
            raise ValueError('duplicate ZIP members')
        self.shared = []
        if 'xl/sharedStrings.xml' in self.z.namelist():
            self.shared = [self.text(si) for si in self.xml('xl/sharedStrings.xml')]
        wb = self.xml('xl/workbook.xml')
        props = wb.find('s:workbookPr', NS)
        self.date1904 = props is not None and props.get('date1904') in ['1', 'true']
        rels = self.xml('xl/_rels/workbook.xml.rels')
        targets = {}
        for r in rels:
            if r.get('TargetMode') == 'External':
                continue
            target = r.get('Target', '')
            p = posixpath.normpath('xl/' + target) if not target.startswith('/') else target.lstrip('/')
            if not p.startswith('xl/') or '..' in p.split('/'):
                raise ValueError('unsafe relationship target')
            targets[r.get('Id')] = p
        self.sheets = []
        for i, s in enumerate(wb.find('s:sheets', NS), 1):
            p = targets.get(s.get('{' + R + '}id'))
            if p is None or not p.startswith('xl/worksheets/'):
                raise ValueError('unsupported worksheet relationship')
            self.sheets.append({'index': i, 'name': s.get('name', ''), 'sheet_id': s.get('sheetId'), 'path': p, 'state': s.get('state', 'visible')})
        self.date_styles = set()
        if 'xl/styles.xml' in self.z.namelist():
            styles = self.xml('xl/styles.xml')
            formats = {int(x.get('numFmtId')): x.get('formatCode', '') for x in styles.findall('s:numFmts/s:numFmt', NS)}
            for i, x in enumerate(styles.findall('s:cellXfs/s:xf', NS)):
                fmt_id = int(x.get('numFmtId', '0'))
                fmt = re.sub(r'"[^"]*"|\\.|\[(?![hms]\])[^\]]*\]', '', formats.get(fmt_id, ''), flags=re.I).lower()
                if fmt_id in set(range(14, 23)) | set(range(45, 48)) or re.search(r'[ymdhis]', fmt):
                    self.date_styles.add(i)

    @staticmethod
    def text(element):
        # Exclude phonetic runs from shared/rich strings.
        return ''.join(t.text or '' for t in element.findall('s:t', NS)) + ''.join(t.text or '' for t in element.findall('s:r/s:t', NS))

    def xml(self, name):
        info = self.z.getinfo(name)
        if info.file_size > MAX_XML:
            raise ValueError('XML part exceeds size limit')
        data = self.z.read(name)
        if b'<!DOCTYPE' in data or b'<!ENTITY' in data:
            raise ValueError('DTD/entities are forbidden')
        return ET.fromstring(data)

    def cells(self, spec):
        root = self.xml(spec['path'])
        cells = {}
        for c in root.findall('s:sheetData/s:row/s:c', NS):
            address = c.get('r')
            if not address or not re.fullmatch('[A-Z]+[1-9][0-9]*', address) or address in cells:
                raise ValueError('invalid or duplicate cell address')
            typ = c.get('t', 'n')
            v = c.findtext('s:v', namespaces=NS)
            if typ == 's':
                v = self.shared[int(v)]
            elif typ == 'inlineStr':
                inline = c.find('s:is', NS)
                v = self.text(inline) if inline is not None else ''
            f = c.find('s:f', NS)
            cells[address] = {'address': address, 'type': typ, 'value': v, 'style': c.get('s'), 'is_date': int(c.get('s', '0')) in self.date_styles,
                              'formula': (f.text or '') if f is not None else None, 'formula_attributes': dict(f.attrib) if f is not None else {},
                              'raw_xml': ET.tostring(c, encoding='unicode')}
        return cells, [m.get('ref') for m in root.findall('s:mergeCells/s:mergeCell', NS)]

    def close(self):
        self.z.close()

STUDENT = {'фио студента', 'фио ученика'}
CHANNELS = {'нал': 'cash', 'наличные': 'cash', 'безнал': 'bank', 'безналичные': 'bank', 'qr': 'qr', 'юкасса': 'yookassa', 'юkassa': 'yookassa'}
FIELDS = {**CHANNELS, 'аб.': 'subscription_value', 'тип аб.': 'subscription_value', 'абонемент': 'subscription_value',
          'цена': 'subscription_price', 'цена аб': 'subscription_price', 'цена аб.': 'subscription_price',
          'выручка': 'allocated_revenue', 'педагог': 'teacher_allocation', 'преподаватель': 'teacher_allocation',
          'часы': 'hours', 'кол_во часов': 'hours', 'кол-во часов': 'hours'}
SERVICE = re.compile(r'^(?:итого|всего|отмена|отменено|нет занятия|выручка|педагог|нал|безнал|остаток|№)\b', re.I)

def build(manifest, aliases=None):
    """Pure parsing result; no destination connection or database writes."""
    if manifest.get('currency') != 'RUB':
        raise ValueError('set currency=RUB explicitly for these workbooks')
    books = manifest['books']
    ids = [b['source_key'] for b in books]
    if len(set(ids)) != len(ids) or not all(re.fullmatch('[a-zA-Z0-9_-]+', x) for x in ids):
        raise ValueError('source_key must be unique stable identifiers')
    aliases = aliases or {'teacher': {}, 'student': {}}
    sources, events, issues, raw, sheet_meta = [], [], [], [], []
    covered = set()
    bindings = manifest.get('person_bindings', {})

    def issue(code, source, sheet, address=None, detail=None, severity='review', event=None):
        item = {'code': code, 'severity': severity, 'source_key': source, 'sheet_index': sheet['index'], 'sheet_name': sheet['name'], 'cell': address, 'detail': detail}
        if event:
            item['record_key'] = event['record_key']
            event['issues'].append(code)
        issues.append(item)

    def identity(role, label, event):
        if not label:
            event['issues'].append('MISSING_' + role.upper())
            return {'raw': label, 'normalized': None, 'product_id': None, 'resolution': 'missing'}
        candidate = aliases.get(role, {}).get(key(label))
        normalized = candidate if isinstance(candidate, str) else tidy(label)
        # Previous surname-based unions are label suggestions, never an identity proof.
        binding = bindings.get(role, {}).get(key(label))
        if not isinstance(binding, str) or not binding.strip():
            binding = None
            event['issues'].append('UNRESOLVED_' + role.upper())
        return {'raw': label, 'normalized': normalized, 'product_id': binding, 'resolution': 'explicit_binding' if binding else 'suggestion_only'}

    for book in books:
        kind, source = book['kind'], book['source_key']
        if kind not in ['groups', 'income', 'expenses']:
            raise ValueError('unsupported book kind')
        wb = XLSX(book['path'])
        original = XLSX(book['original_path']) if book.get('original_path') else None
        try:
            if original and [(s['index'],s['name']) for s in original.sheets] != [(s['index'],s['name']) for s in wb.sheets]:
                raise ValueError('original and standardized worksheet inventories differ')
            sources.append({'source_key': source, 'kind': kind, 'sha256': wb.sha, 'original_sha256': original.sha if original else None, 'filename': wb.path.name, 'sheet_count': len(wb.sheets), 'date1904': wb.date1904})
            titles = Counter(s['name'] for s in wb.sheets)
            for sheet in wb.sheets:
                cells, merges = wb.cells(sheet)
                if original:
                    before,_=original.cells(original.sheets[sheet['index']-1])
                    if before.keys()!=cells.keys():raise ValueError('original cell inventory differs')
                    for address,c in cells.items():
                        old=before[address]
                        if c['formula']!=old['formula'] or c['formula_attributes']!=old['formula_attributes']:
                            raise ValueError('formula differs from original workbook')
                        if c['value']!=old['value']:
                            if c['type'] not in ['s','str','inlineStr'] or old['type'] not in ['s','str','inlineStr']:
                                raise ValueError('numeric/date input differs from original workbook')
                            c['original_value']=old['value']
                by_row = defaultdict(dict)
                for address, c in cells.items():
                    by_row[rownum(address)][colnum(address)] = c
                    raw.append({'source_key': source, 'sheet_index': sheet['index'], **c})
                    if c['type'] == 'e':
                        issue('EXCEL_ERROR', source, sheet, address, c['value'])
                    if c['formula'] is not None and c['value'] is None:
                        issue('FORMULA_WITHOUT_CACHE', source, sheet, address)
                if not sheet['name'] or titles[sheet['name']] > 1:
                    issue('INVALID_OR_DUPLICATE_SHEET_NAME', source, sheet, severity='review')
                if not sheet['sheet_id']:
                    issue('MISSING_EXCEL_SHEET_ID', source, sheet)
                # A sheet index, not its ambiguous display name, is the authoritative key.
                date_value = manifest.get('sheet_dates', {}).get(source, {}).get(str(sheet['index']))
                if date_value is not None:
                    date_value = date.fromisoformat(date_value).isoformat()
                    match = re.match(r'^\s*(\d{1,2})[.,](\d{1,2})(?:[.,](\d{4}))?(?:\s|$)', sheet['name'])
                    if match:
                        d = date.fromisoformat(date_value)
                        if (d.day, d.month) != (int(match[1]), int(match[2])) or (match[3] and d.year != int(match[3])):
                            raise ValueError(f'date mapping disagrees with sheet label: {source}/{sheet["index"]}')
                else:
                    issue('DATE_REQUIRES_CONFIRMATION', source, sheet, detail='Year/site not inferred from sheet order or current date')
                site = manifest.get('sheet_sites', {}).get(source, {}).get(str(sheet['index']))
                sheet_meta.append({'source_key': source, **sheet, 'date': date_value, 'site_id': site, 'merges': merges})

                def new_event(event_kind, row, block, selected, section=None):
                    loc = {'source_key': source, 'sheet_index': sheet['index'], 'row': row, 'block': block, 'kind': event_kind}
                    e = {'record_key': digest(loc), 'location': loc, 'date': date_value, 'site_id': site, 'currency': 'RUB', 'section': section,
                         'cells': {a: cells[a] for a in selected}, 'issues': [], 'payments': {}, 'fields': {}}
                    if not date_value: e['issues'].append('DATE_REQUIRES_CONFIRMATION')
                    if not site: e['issues'].append('SITE_REQUIRES_CONFIRMATION')
                    return e

                def fields_into(e, row, mapping):
                    for column, name in mapping.items():
                        c = by_row[row].get(column)
                        if not c: continue
                        a = c['address']; covered.add((source, sheet['index'], a))
                        if name in CHANNELS.values():
                            try:
                                n = number(c, money=True)
                                if n is not None:
                                    if name in e['payments']:
                                        e['issues'].append('DUPLICATE_PAYMENT_CHANNEL')
                                    e['payments'].setdefault(name, []).append({'amount': n, 'cell': a})
                                    if Decimal(n) < 0: e['issues'].append('NEGATIVE_AMOUNT_REQUIRES_REVIEW')
                            except ValueError as exc:
                                issue('INVALID_PAYMENT_VALUE', source, sheet, a, str(exc), event=e)
                        else:
                            e['fields'][name] = {'cell': a, 'value': c['value'], 'formula': c['formula'], 'trusted': c['formula'] is None and c['type'] != 'e'}
                            if c['formula'] is not None:
                                e['issues'].append('FORMULA_RESULT_NOT_TRUSTED')
                            if name in ['hours', 'subscription_price', 'teacher_allocation'] and c['value'] not in [None, ''] and c['formula'] is None:
                                try: number(c, money=name != 'hours')
                                except ValueError as exc: issue('INVALID_NUMERIC_FIELD', source, sheet, a, str(exc), event=e)

                if kind == 'groups':
                    headers = [(r, column) for r, cs in by_row.items() for column, c in cs.items() if key(c['value']) in STUDENT]
                    for header_row, name_col in headers:
                        mapping = {}
                        next_name = min([col for r, col in headers if r == header_row and col > name_col] or [10**6])
                        for col, c in by_row[header_row].items():
                            if name_col < col < min(next_name - 1, name_col + 8) and key(c['value']) in FIELDS:
                                mapping[col] = FIELDS[key(c['value'])]
                        if not mapping:
                            issue('UNRECOGNIZED_GROUP_HEADER', source, sheet, by_row[header_row][name_col]['address'])
                            continue
                        following = min([r for r, col in headers if col == name_col and r > header_row] or [max(by_row) + 4])
                        # Context rows immediately preceding next block are not attendees.
                        end = following - 3
                        teacher_cell = by_row.get(header_row - 2, {}).get(name_col)
                        time_cell = by_row.get(header_row - 1, {}).get(name_col)
                        teacher_label = teacher_cell.get('original_value',teacher_cell['value']) if teacher_cell else None
                        for row in sorted(r for r in by_row if header_row < r < end):
                            name = by_row[row].get(name_col)
                            label = tidy(name['value']) if name else ''
                            nonempty_payment = any(by_row[row].get(col, {}).get('value') not in [None, '', '0', '0.0'] for col, field in mapping.items() if field in CHANNELS.values())
                            if not label and not nonempty_payment: continue
                            selected = [c['address'] for col, c in by_row[row].items() if name_col <= col <= max(mapping)]
                            e = new_event('group_row', row, f'{header_row}:{name_col}', selected)
                            if name: covered.add((source, sheet['index'], name['address']))
                            e['student'] = identity('student', name.get('original_value',label) if name else label, e)
                            e['teacher'] = identity('teacher', teacher_label, e)
                            e['session_time_raw'] = time_cell
                            e['issues'].extend(['SUBSCRIPTION_SEMANTICS_UNCONFIRMED', 'ATTENDANCE_STATUS_UNCONFIRMED'])
                            if not label or SERVICE.search(label) or re.search(r'\bи\b|\+', label):
                                e['issues'].append('SERVICE_OR_COMBINED_PERSON_ROW')
                            fields_into(e, row, mapping)
                            events.append(e)
                else:
                    headers = []
                    for r, cs in by_row.items():
                        mapping = {col: CHANNELS[key(c['value'])] for col, c in cs.items() if key(c['value']) in CHANNELS}
                        if len(mapping) >= 2 or (mapping and key(cs.get(1, {}).get('value')) in ['милонга','бар','аренда зала','абонементы','практика','прочее','педагоги','преподаватели']):
                            for col, c in cs.items():
                                if key(c['value']) in ['часы', 'кол_во часов', 'кол-во часов']: mapping[col] = 'hours'
                            headers.append((r, mapping))
                    for idx, (header_row, mapping) in enumerate(headers):
                        end = headers[idx + 1][0] if idx + 1 < len(headers) else max(by_row) + 1
                        section = tidy(by_row[header_row].get(1, {}).get('value'))
                        if key(section) in ['педагог', 'преподаватель', 'препод']:
                            section = 'Аренда зала'
                        role = 'student' if key(section) == 'абонементы' else 'teacher' if key(section) in ['аренда зала', 'практика', 'педагоги', 'преподаватели'] else None
                        if role == 'student':
                            # These templates reuse a "hours" heading for subscription type/capacity.
                            mapping = {col: ('subscription_value' if field == 'hours' else field) for col, field in mapping.items()}
                        for row in sorted(r for r in by_row if header_row < r < end):
                            # Only explicit money entries produce financial candidates.
                            active = any(by_row[row].get(col, {}).get('value') not in [None, '', '0', '0.0'] for col, field in mapping.items() if field in CHANNELS.values())
                            if not active: continue
                            labelcell = by_row[row].get(1)
                            label = tidy(labelcell['value']) if labelcell else ''
                            selected = [c['address'] for c in by_row[row].values()]
                            e = new_event('income_row' if kind == 'income' else 'expense_row', row, str(header_row), selected, section)
                            e['label_raw'] = label
                            if labelcell: covered.add((source, sheet['index'], labelcell['address']))
                            if role: e['person'] = identity(role, labelcell.get('original_value',label) if labelcell else label, e)
                            else: e['issues'].append('FINANCIAL_CATEGORY_UNCONFIRMED')
                            if role == 'student':e['issues'].append('SUBSCRIPTION_SEMANTICS_UNCONFIRMED')
                            if not label or SERVICE.search(label):e['issues'].append('MISSING_OR_TOTAL_LABEL')
                            fields_into(e, row, mapping)
                            e['issues'].append('PAYMENT_ACCOUNTING_POLICY_UNCONFIRMED')
                            events.append(e)

                if kind == 'groups' and not headers:
                    issue('NO_SUPPORTED_HEADERS', source, sheet)
                if kind != 'groups' and not headers:
                    issue('NO_SUPPORTED_HEADERS', source, sheet)
                # Retain every populated cell, including footer totals, unknown blocks and annotations.
                for r, cs in by_row.items():
                    uncovered_numeric = [c['address'] for c in cs.values() if c['value'] not in [None, '', '0', '0.0'] and c['type'] == 'n' and c['formula'] is None and not c['is_date'] and (source, sheet['index'], c['address']) not in covered]
                    if uncovered_numeric:
                        issue('UNMAPPED_NUMERIC_CELLS', source, sheet, detail=uncovered_numeric, severity='info')
        finally:
            wb.close()
            if original:original.close()

    # Potential overlap is flagged, never deduplicated on name/amount/day alone.
    candidates = defaultdict(list)
    for e in events:
        person = e.get('student') or e.get('person')
        if not e['date'] or not person or not person.get('product_id'):continue
        for channel, ps in e['payments'].items():
            for p in ps:
                if Decimal(p['amount']) != 0:
                    candidates[(e['date'], e['site_id'], person['product_id'], channel, p['amount'])].append(e)
    for bucket in candidates.values():
        if len(bucket) > 1:
            for e in bucket:e['issues'].append('POSSIBLE_OVERLAPPING_PAYMENT')
    for e in events:
        e['issues'] = sorted(set(e['issues']))
        e['status'] = 'review' if e['issues'] else 'ready'
    config = {k: v for k, v in manifest.items() if k != 'books'}
    fingerprint = digest({'version': VERSION, 'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'sources': sources, 'config': config, 'aliases': aliases})
    stats = {'sources': len(sources), 'sheets': len(sheet_meta), 'raw_cells': len(raw), 'events': len(events), 'ready': sum(e['status'] == 'ready' for e in events),
             'issues_by_code': dict(Counter(i['code'] for i in issues)), 'event_issues_by_code': dict(Counter(c for e in events for c in e['issues'])),
             'formula_cells': sum(c['formula'] is not None for c in raw), 'excel_error_cells': sum(c['type'] == 'e' for c in raw)}
    totals = defaultdict(Decimal)
    for e in events:
        for channel, ps in e['payments'].items():
            for p in ps:totals[(e['location']['source_key'], channel)] += Decimal(p['amount'])
    stats['recognized_detail_amounts'] = {source: {channel: format(amount, 'f') for (src, channel), amount in totals.items() if src == source} for source in ids}
    return {'version': VERSION, 'fingerprint': fingerprint, 'sources': sources, 'sheets': sheet_meta, 'events': events, 'issues': issues, 'raw_cells': raw, 'stats': stats}

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS migration_batches (fingerprint TEXT PRIMARY KEY, parser_version TEXT NOT NULL, manifest_hash TEXT NOT NULL, stats_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS migration_sources (source_key TEXT PRIMARY KEY, source_sha TEXT NOT NULL, fingerprint TEXT NOT NULL REFERENCES migration_batches(fingerprint), metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS migration_raw_cells (source_key TEXT NOT NULL REFERENCES migration_sources(source_key), sheet_index INTEGER NOT NULL, address TEXT NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(source_key,sheet_index,address));
CREATE TABLE IF NOT EXISTS migration_events (record_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL REFERENCES migration_batches(fingerprint), status TEXT NOT NULL CHECK(status IN ('review','ready')), payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS migration_issues (fingerprint TEXT NOT NULL REFERENCES migration_batches(fingerprint), ordinal INTEGER NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(fingerprint,ordinal));
CREATE TABLE IF NOT EXISTS migration_sheets (source_key TEXT NOT NULL REFERENCES migration_sources(source_key), sheet_index INTEGER NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(source_key,sheet_index));
'''

def stage(result, db_path):
    """Atomic staging only. Changed files/config require a fresh staging database."""
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        connection.execute('BEGIN IMMEDIATE')
        exists = connection.execute('SELECT 1 FROM migration_batches WHERE fingerprint=?', (result['fingerprint'],)).fetchone()
        if exists:
            connection.rollback()
            return {'inserted': False, 'fingerprint': result['fingerprint']}
        for s in result['sources']:
            if connection.execute('SELECT 1 FROM migration_sources WHERE source_key=?', (s['source_key'],)).fetchone():
                raise ValueError('source/config already staged with a different fingerprint; use a new staging database')
        connection.execute('INSERT INTO migration_batches VALUES (?,?,?,?)', (result['fingerprint'], VERSION, result['fingerprint'], canonical_json(result['stats'])))
        connection.executemany('INSERT INTO migration_sources VALUES (?,?,?,?)', [(s['source_key'], s['sha256'], result['fingerprint'], canonical_json(s)) for s in result['sources']])
        connection.executemany('INSERT INTO migration_raw_cells VALUES (?,?,?,?)', [(c['source_key'], c['sheet_index'], c['address'], canonical_json(c)) for c in result['raw_cells']])
        connection.executemany('INSERT INTO migration_events VALUES (?,?,?,?)', [(e['record_key'], result['fingerprint'], e['status'], canonical_json(e)) for e in result['events']])
        connection.executemany('INSERT INTO migration_issues VALUES (?,?,?)', [(result['fingerprint'], i, canonical_json(x)) for i, x in enumerate(result['issues'])])
        connection.executemany('INSERT INTO migration_sheets VALUES (?,?,?)', [(s['source_key'], s['index'], canonical_json(s)) for s in result['sheets']])
        assert connection.execute('SELECT COUNT(*) FROM migration_events WHERE fingerprint=?', (result['fingerprint'],)).fetchone()[0] == len(result['events'])
        connection.commit()
        return {'inserted': True, 'fingerprint': result['fingerprint']}
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()

def write_preview(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'summary.json').write_text(json.dumps({k: result[k] for k in ['version','fingerprint','sources','stats']}, ensure_ascii=False, indent=2), encoding='utf-8')
    for keyname in ['events', 'issues', 'sheets']:
        with (directory/(keyname+'.jsonl')).open('w', encoding='utf-8') as f:
            for item in result[keyname]:f.write(canonical_json(item)+'\n')
    with (directory/'sheet_dates_template.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['source_key','sheet_index','sheet_name','confirmed_date','site_id'])
        for s in result['sheets']:writer.writerow([s['source_key'],s['index'],s['name'],s['date'] or '',s['site_id'] or ''])

def load_manifest(path):
    m = json.loads(path.read_text(encoding='utf-8-sig'))
    for book in m['books']:
        for field in ['path','original_path']:
            if not book.get(field):continue
            p = Path(book[field])
            book[field] = str((path.parent/p).resolve()) if not p.is_absolute() else str(p)
    csv_name = m.pop('sheet_dates_csv', None)
    if csv_name:
        with (path.parent/csv_name).open(encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f, delimiter=';'):
                source, index = row['source_key'], row['sheet_index']
                if row['confirmed_date'].strip():
                    date.fromisoformat(row['confirmed_date'])
                    target = m.setdefault('sheet_dates', {}).setdefault(source, {})
                    if index in target and target[index] != row['confirmed_date']:raise ValueError('conflicting date mapping')
                    target[index] = row['confirmed_date']
                if row.get('site_id', '').strip():m.setdefault('sheet_sites', {}).setdefault(source, {})[index] = row['site_id'].strip()
    return m

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--aliases', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--stage-db', type=Path, help='local migration staging SQLite; never the product database')
    args = parser.parse_args(argv)
    try:
        result = build(load_manifest(args.manifest), json.loads(args.aliases.read_text(encoding='utf-8')) if args.aliases else None)
        write_preview(result, args.out)
        if args.stage_db:
            args.stage_db.parent.mkdir(parents=True, exist_ok=True)
            print(canonical_json(stage(result, args.stage_db)))
        print(canonical_json(result['stats']))
        return 0
    except (ValueError, OSError, zipfile.BadZipFile, ET.ParseError, sqlite3.Error, KeyError, IndexError) as exc:
        print(f'IMPORT FAILED: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
