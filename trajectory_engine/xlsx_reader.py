"""Read xlsx OOXML with Python stdlib. Read-only: preserves original workbook untouched.

Does not evaluate formulas. Formula cells use cached calculated values where available.
Intended for GitHub runners where third-party spreadsheet dependencies may not exist.
"""
from __future__ import annotations
import datetime as dt
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

SS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RR = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'
MANDATORY = ('Historical findings', 'All publication data', 'Ranked sources', 'Shock audit', 'Method')


def _read_xml(archive, filename):
    return ET.fromstring(archive.read(filename))


def _excel_col(address):
    letters = re.match(r'([A-Z]+)', address or '')
    if not letters:
        return 0
    col = 0
    for c in letters.group(1):
        col = col * 26 + ord(c) - 64
    return col - 1


def _shared_strings(z):
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    root = _read_xml(z, 'xl/sharedStrings.xml')
    return [''.join(e.text or '' for e in item.iter(SS + 't')) for item in root.findall(SS+'si')]


def _cell_value(c, shared):
    typ = c.attrib.get('t', '')
    if typ == 'inlineStr':
        return ''.join(n.text or '' for n in c.iter(SS+'t'))
    value = c.find(SS+'v')
    if value is None or value.text is None:
        return ''
    val = value.text
    if typ == 's':
        try: return shared[int(val)]
        except (ValueError, IndexError): return val
    if typ == 'b':
        return val == '1'
    # Keep serial dates in raw data, convert known date columns at extraction stage.
    return val


def read_sheets(path):
    """Return all original sheet rows as dictionaries, plus mapping/warnings.

    Only the first non-empty row is used as the header; duplicate headers retained
    with suffixes. All original columns of all 5 sheets are preserved.
    """
    result, warnings = {}, []
    with zipfile.ZipFile(path) as z:
        book = _read_xml(z, 'xl/workbook.xml')
        relationships = _read_xml(z, 'xl/_rels/workbook.xml.rels')
        rels = {el.attrib.get('Id'):el.attrib.get('Target','') for el in relationships.findall(REL+'Relationship')}
        strings = _shared_strings(z)
        for sh in book.findall('.//'+SS+'sheet'):
            name, rid = sh.attrib['name'], sh.attrib[RR+'id']
            target = rels.get(rid, '')
            if target.startswith('/'):
                path_in_zip = target.lstrip('/')
            else:
                path_in_zip = 'xl/' + target.lstrip('/')
            # Some writers use ./ relative targets.
            path_in_zip = path_in_zip.replace('xl/./','xl/')
            if path_in_zip not in z.namelist():
                warnings.append('Missing worksheet content: '+name)
                continue
            root = _read_xml(z, path_in_zip)
            raw_rows = []
            for row in root.findall('.//'+SS+'sheetData/'+SS+'row'):
                vals = {}
                for c in row.findall(SS+'c'):
                    value = _cell_value(c, strings)
                    vals[_excel_col(c.attrib.get('r',''))] = value
                if vals:
                    raw_rows.append((int(row.attrib.get('r','0')), vals))
            if not raw_rows:
                result[name] = []
                continue
            # Search first 15 rows for a real field header rather than guessing
            # that the first decorated title row is the table header.
            hints = { 'title','publication title','source title','url','doi',
                      'source','original source','published','publication date',
                      'finding','historical finding','summary','topic','abstract',
                      'date','year','rank','value','method','verification','status'}
            def score(candidate):
                values=[str(x).strip().lower() for x in candidate.values()]
                return sum(v in hints for v in values)
            first_i, heads = max(raw_rows[:15], key=lambda pair:(score(pair[1]),-pair[0]))
            if score(heads)<2:
                first_i,heads=raw_rows[0]
            if first_i!=raw_rows[0][0]:
                warnings.append(f'{name}: table header detected at row {first_i}; earlier rows retained as preamble metadata')
            columns, existing = [], set()
            for i in range(max(heads)+1):
                hdr = str(heads.get(i,'')).strip() or f'Unlabelled column {i+1}'
                orig = hdr
                index = 2
                while hdr in existing:
                    hdr = f'{orig} ({index})'; index += 1
                existing.add(hdr); columns.append(hdr)
            records=[]
            for rnum, vals in raw_rows:
                if rnum == first_i:continue
                if rnum < first_i:
                    records.append({'_sheet_row':rnum, '_preamble':True,
                        '_preamble_cells':{str(k):str(v) for k,v in vals.items()}})
                    continue
                if not any(str(v).strip() for v in vals.values()):
                    continue
                item = {columns[i] if i<len(columns) else f'Column {i+1}':v for i,v in vals.items()}
                item['_sheet_row'] = rnum
                records.append(item)
            result[name] = records
    for required in MANDATORY:
        if required not in result:
            warnings.append('REQUIRED sheet not found: '+required)
    return result, warnings


def normalize_date(value):
    if value is None or value == '': return None
    if isinstance(value, (dt.date,dt.datetime)): return value.isoformat()[:10]
    s = str(value).strip()
    if re.fullmatch(r'\d+(\.\d+)?', s):
        try:
            n=float(s)
            if 20000 <= n <= 80000:
                return (dt.datetime(1899,12,30)+dt.timedelta(days=n)).date().isoformat()
            if 1850 <= n <= 2150 and int(n)==n:
                return str(int(n))
        except (ValueError,OverflowError): pass
    m = re.search(r'(19\d{2}|20\d{2}|21\d{2})[-/.](\d{1,2})[-/.](\d{1,2})', s)
    if m:
        try: return dt.date(int(m[1]),int(m[2]),int(m[3])).isoformat()
        except ValueError: pass
    m = re.fullmatch(r'(19\d{2}|20\d{2}|21\d{2})',s)
    if m: return s  # Year precision must not masquerade as 1 January
    return None
