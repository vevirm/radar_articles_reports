"""Construct a tiny SYNTHETIC five-sheet XLSX using OOXML (Python stdlib only).
The example is NOT empirical evidence about history.
"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.sax.saxutils import escape

SHEETS={
 'Historical findings':[
 ['Title','Published','Event date','Original source','Topic','Finding','Evidence type','Verification','Outcome','Event ID'],
 ['Fictional chip goal proposed','2019-01-01','','https://example.org/chip-proposal','chips','Government proposed a test goal for 2023.','proposed_action','Verified','',''],
 ['Fictional chip goal was discussed again','2022-01-01','','https://example.org/chip-discussion','chips','Officials still discussed the proposal, not implementation.','observation','provisional','',''],
 ['Fictional quantum prototype launched','2020-08-10','2020-07-01','https://example.org/quantum-a','quantum','Laboratory launched a research prototype.','implemented_action','verified','','event-q'],
 ['Prototype mentioned in a second report','2021-01-20','2020-07-01','https://example.edu/quantum-b','quantum','A later article describes the same research prototype.','observation','verified','','event-q'],
 ],
 'All publication data':[
 ['Title','Published','Event date','Original source','Topic','Summary','Evidence type','Verification','Outcome'],
 ['Fictional chip goal proposed','2019-01-01','','https://example.org/chip-proposal','chips','Proposed goal duplicated by data aggregation','proposed_action','verified',''],
 ['Later independent assessment','2024-04-08','2024-03-01','https://example.edu/chip-audit','chips','Audit finds no recorded implementation.','observation','verified','No evidence of implementation found'],
 ['Fictional quantum result improved','2024-12-02','2024-11-01','https://example.org/quantum-c','quantum','Scientific prototype was improved but remains a test.','observation','unverified',''],
 ['False sharp turn in coverage','2025-06-03','','https://example.org/different','rareword','One source mentions an abrupt change.','interpretation','provisional','']
 ],
 'Ranked sources':[['Title','Original source','Rank'],['Fictional chip goal proposed','https://example.org/chip-proposal','1']],
 'Shock audit':[['Title','Candidate shock','Confidence'],['A fictional claimed disruption','Inferred event','provisional']],
 'Method':[['Field','Value'],['Collection method','Synthetic research test for automated audit, NOT real historical data']]
}

def col(i):
 s=''; i+=1
 while i:s=chr(65+(i-1)%26)+s;i=(i-1)//26
 return s

def workbook(path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 N='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
 with ZipFile(path,'w',ZIP_DEFLATED) as z:
  contents=['<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>']
  for n in range(1,len(SHEETS)+1):contents.append(f'<Override PartName="/xl/worksheets/sheet{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
  contents.append('</Types>');z.writestr('[Content_Types].xml',''.join(contents))
  z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
  ws=['<?xml version="1.0"?><workbook xmlns="'+N+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
  rel=['<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
  for n,(name,data) in enumerate(SHEETS.items(),1):
   ws.append(f'<sheet name="{escape(name)}" sheetId="{n}" r:id="rId{n}"/>')
   rel.append(f'<Relationship Id="rId{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{n}.xml"/>')
   rows=[]
   for r, row in enumerate(data,1):
    cells=[]
    for c,v in enumerate(row):
     cells.append(f'<c r="{col(c)}{r}" t="inlineStr"><is><t>{escape(str(v))}</t></is></c>')
    rows.append(f'<row r="{r}">'+''.join(cells)+'</row>')
   z.writestr(f'xl/worksheets/sheet{n}.xml',f'<?xml version="1.0"?><worksheet xmlns="{N}"><sheetData>'+''.join(rows)+'</sheetData></worksheet>')
  ws.append('</sheets></workbook>');rel.append('</Relationships>')
  z.writestr('xl/workbook.xml',''.join(ws));z.writestr('xl/_rels/workbook.xml.rels',''.join(rel))
 return path
