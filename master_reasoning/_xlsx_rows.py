"""Read-only XLSX streaming reader for the two upstream workbook schemas.

Handles inline strings, shared strings, numeric/cached-formula cells and worksheet
relationship mappings. It never opens an Excel file in write mode, never
recalculates formulas and never writes input bytes.
"""
from __future__ import annotations
from pathlib import PurePosixPath
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import re

NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKGREL='{http://schemas.openxmlformats.org/package/2006/relationships}'
ADDR=re.compile(r'^[A-Z]+')


def _sheet_path(z, sheet_index):
    """Resolve logical 1-based sheet index even when OOXML sheetN IDs change."""
    entries=set(z.namelist())
    if 'xl/workbook.xml' not in entries or 'xl/_rels/workbook.xml.rels' not in entries:
        fallback=f'xl/worksheets/sheet{sheet_index}.xml'
        if fallback in entries:return fallback
        raise ValueError('Workbook has no worksheet mapping or expected sheet: '+fallback)
    root=ET.fromstring(z.read('xl/workbook.xml'))
    sheets=root.find(NS+'sheets')
    if sheets is None or len(sheets)<sheet_index:
        raise ValueError(f'Workbook is missing logical worksheet {sheet_index}')
    relation=sheets[sheet_index-1].get(REL+'id')
    rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    for item in rels.findall(PKGREL+'Relationship'):
        if item.get('Id')==relation:
            target=item.get('Target','').replace('\\','/')
            if target.startswith('/'):resolved=target.lstrip('/')
            else:resolved=str(PurePosixPath('xl')/target)
            if resolved not in entries:raise ValueError('Missing mapped worksheet: '+resolved)
            return resolved
    raise ValueError('Cannot resolve worksheet relationship '+str(relation))


def _shared_strings(z):
    if 'xl/sharedStrings.xml' not in z.namelist():return []
    data=[]
    with z.open('xl/sharedStrings.xml') as stream:
        for _,el in ET.iterparse(stream,events=('end',)):
            if el.tag != NS+'si':continue
            data.append(''.join(node.text or '' for node in el.iter(NS+'t')))
            el.clear()
    return data


def read_rows(path, sheet_index, with_meta=False):
    with ZipFile(path,'r') as z:
        strings=_shared_strings(z)
        sheet=_sheet_path(z,sheet_index)
        with z.open(sheet) as stream:
            for _,el in ET.iterparse(stream,events=('end',)):
                if el.tag != NS+'row':continue
                row={}
                for c in el.findall(NS+'c'):
                    ref=c.get('r',''); match=ADDR.match(ref)
                    if not match:continue
                    key=match.group()
                    v=c.find(NS+'v')
                    inline=c.find(NS+'is')
                    typ=c.get('t','')
                    if typ=='inlineStr' and inline is not None:
                        value=''.join(t.text or '' for t in inline.iter(NS+'t'))
                    elif typ=='s' and v is not None and v.text is not None:
                        index=int(v.text)
                        if index<0 or index>=len(strings):raise ValueError('Invalid shared-string index '+str(index))
                        value=strings[index]
                    elif v is not None:
                        value=v.text or ''
                    elif inline is not None:
                        value=''.join(t.text or '' for t in inline.iter(NS+'t'))
                    else:
                        value=''
                    row[key]=value
                yield (int(el.attrib['r']),row) if with_meta else row
                el.clear()


def as_dicts(path, sheet_index):
    rows=read_rows(path,sheet_index)
    try:headers=next(rows)
    except StopIteration:return
    if not headers:
        raise ValueError(f'Workbook sheet {sheet_index} contains no header row')
    for row in rows:
        yield {header:row.get(col,'') for col,header in headers.items() if header}
