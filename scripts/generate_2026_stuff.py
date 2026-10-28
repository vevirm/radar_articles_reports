#!/usr/bin/env python3
"""Build a cumulative 2026 publication catalogue from the R&I Radar's scanner archives.
Only writes 2026-stuff/ outputs, never alters source evidence. No pip dependencies.
"""
import argparse, collections, datetime, json, re, sys, zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'2026-stuff'
HEAD=['Publication date','Title','Source / venue','Authors','Strand','Record type','Summary / finding','Topics','Source URL','Collection','Admission status','First seen']

def load(path):
    with (ROOT/path).open(encoding='utf-8') as f:return json.load(f)
def clean(s):return re.sub(r'\s+',' ',str(s or '')).strip()
def date(s):
    m=re.match(r'^(\d{4}-\d{2}-\d{2})',clean(s))
    if not m:return ''
    try:datetime.date.fromisoformat(m[1]);return m[1]
    except ValueError:return ''
def correction_keys(r):
    url=clean(r.get('link') or r.get('url') or r.get('landing_page_url')).lower()
    title=clean(r.get('title') or r.get('headline')).lower()
    return [v for v in [('link:'+url) if url else '',('title:'+title) if title else ''] if v]
def apply_correction(r, corrections):
    r=dict(r)
    for k in correction_keys(r):
        patch=corrections.get(k)
        if isinstance(patch,dict):
            for f,v in (patch.get('fields') or {}).items():
                if f in ('date','title','headline','authors','source','link','url','summary','core_message') and v is not None:r[f]=v
            break
    return r

def source_rows():
    raw=load('radar.json'); hist=load('historical/historical.json')
    corr=load('record_corrections.json') if (ROOT/'record_corrections.json').exists() else {}
    patches=corr.get('records',{}) if isinstance(corr,dict) else {}
    for strand in ('strand_a','strand_b','strand_c','signal_archive'):
        for r in raw.get(strand,[]):
            if isinstance(r,dict):yield r,('Main Radar — '+strand),strand,patches
    for r in hist.get('items',[]):
        if isinstance(r,dict):yield r,'Earlier Findings',str(r.get('strand','A')).lower(),patches

def build():
    dedup={}; rejected=0
    for original,collection,strand,patches in source_rows():
        r=apply_correction(original,patches)
        d=date(r.get('date'))
        if not (d and '2026-01-01'<=d<='2026-12-31'):continue
        title=clean(r.get('title') or r.get('headline'))
        url=clean(r.get('link') or r.get('url') or r.get('landing_page_url'))
        if not title:rejected+=1;continue
        key=('url',url.lower().rstrip('/')) if url else ('title',title.casefold())
        summary=clean(r.get('reader_more') or r.get('reader_point') or r.get('core_message') or r.get('summary') or r.get('what') or r.get('signal_note') or r.get('why_it_matters'))
        st=clean(strand).replace('strand_','').upper()
        is_signal=st=='C' or strand=='signal_archive'
        row={'date':d,'title':title,'source':clean(r.get('source') or r.get('venue')),'authors':clean(r.get('authors')),'strand':st,'kind':'Signal / news' if is_signal else 'Research / report','summary':summary,'topics':', '.join(clean(t) for t in (r.get('topic_labels') or r.get('topics') or []) if t),'url':url,'collections':[collection],'admission':clean(r.get('admission_status') or r.get('admission_decision') or r.get('public_active')),'first_seen':clean(r.get('first_seen'))}
        prior=dedup.get(key)
        if prior:
            prior['collections']=sorted(set(prior['collections']+row['collections']))
            if len(row['summary'])>len(prior['summary']):prior['summary']=row['summary']
            if not prior['authors']:prior['authors']=row['authors']
            if prior['kind']=='Signal / news' and row['kind']=='Research / report':prior.update({k:row[k] for k in ('strand','kind')})
        else:dedup[key]=row
    rows=sorted(dedup.values(),key=lambda x:(x['date'],x['title'].casefold()),reverse=True)
    if not rows:raise RuntimeError('No 2026 records found; refusing to overwrite outputs.')
    OUT.mkdir(exist_ok=True)
    old=OUT/'publications.json'
    if old.exists():
        try:
            old_count=len(json.loads(old.read_text(encoding='utf-8')).get('records',[]))
            if old_count>0 and len(rows)<old_count*.90:raise RuntimeError(f'Safety stop: {old_count} previous records -> {len(rows)} current records (>10% decrease). Review source archives.')
        except (ValueError,TypeError,KeyError):pass
    payload={'year':2026,'date_from':'2026-01-01','snapshot_generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),'count':len(rows),'research_count':sum(r['kind']=='Research / report' for r in rows),'signal_count':sum(r['kind']=='Signal / news' for r in rows),'records':rows,'note':'Scanner catalogue: discovery is not verification. Publication date corrections applied where identifiable.'}
    new_json=OUT/'publications.json'
    new_excel=OUT/'2026_publications.xlsx'
    # Produce both before replacing either output.
    tmp_excel=OUT/'_2026_publications.xlsx'
    make_xlsx(tmp_excel,rows)
    tmp_json=OUT/'_publications.json'
    tmp_json.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp_excel.replace(new_excel);tmp_json.replace(new_json)
    print(f'2026 catalogue: {len(rows)} records, {payload["research_count"]} research/reports, {payload["signal_count"]} signals; {rejected} missing titles')

def vals(rows):
    for r in rows:
        yield [r['date'],r['title'],r['source'],r['authors'],r['strand'],r['kind'],r['summary'],r['topics'],r['url'],'; '.join(r['collections']),r['admission'],r['first_seen']]

def sheet_xml(headers, rows):
    def col(n):
        s='';n+=1
        while n:s=chr(65+(n-1)%26)+s;n=(n-1)//26
        return s
    chunks=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/><cols>']
    for i in range(len(headers)):chunks.append(f'<col min="{i+1}" max="{i+1}" width="{[17,62,30,35,12,22,90,40,55,37,18,22][i]}" customWidth="1"/>')
    chunks.append('</cols><sheetData>')
    for ri,line in enumerate([headers]+list(rows),1):
        chunks.append(f'<row r="{ri}">')
        for ci,value in enumerate(line):
            s=escape(clean(value),{'"':'&quot;'})
            # inline strings are robust in Excel and require no sharedStrings.xml.
            style=' s="1"' if ri==1 else ''
            chunks.append(f'<c r="{col(ci)}{ri}" t="inlineStr"{style}><is><t>{s}</t></is></c>')
        chunks.append('</row>')
    chunks.append(f'</sheetData><autoFilter ref="A1:{col(len(headers)-1)}{ri}"/></worksheet>')
    return ''.join(chunks).encode('utf-8')

def make_xlsx(path,records):
    groups=[('All 2026',records),('Research and reports',[r for r in records if r['kind']=='Research / report']),('Signals and news',[r for r in records if r['kind']=='Signal / news'])]
    x='http://schemas.openxmlformats.org/spreadsheetml/2006/main';rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,4))+'</Types>')
        z.writestr('_rels/.rels',f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{x}" xmlns:r="{rel}"><sheets>'+''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(groups,1))+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels',f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="{rel}/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,4))+f'<Relationship Id="rId4" Type="{rel}/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml',f'<styleSheet xmlns="{x}"><fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Aptos"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF183B62"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs></styleSheet>')
        for i,(_,rows) in enumerate(groups,1):z.writestr(f'xl/worksheets/sheet{i}.xml',sheet_xml(HEAD,vals(rows)))

if __name__=='__main__':
    try:build()
    except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
