"""Generate a reading-first foresight report; keep the formal inference rules outside it.

All gates, candidate selection and traceability remain in the underlying inference
engine. This module deliberately presents the *reasoned outcomes*, not the
repeated methodology / review checklist for every individual result.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from . import graphics

NAVY=RGBColor(26,43,59)
SEA=RGBColor(38,100,107)
MUTED=RGBColor(94,106,117)


def _p(doc, text='', style=None, before=0, after=9):
    p=doc.add_paragraph(style=style)
    p.add_run(str(text))
    p.paragraph_format.space_before=Pt(before)
    p.paragraph_format.space_after=Pt(after)
    p.paragraph_format.line_spacing=1.14
    return p


def _link(p, text, url):
    if not isinstance(url,str) or not url.startswith(('https://','http://')):
        p.add_run(text); return
    rid=p.part.relate_to(url,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True)
    elt=OxmlElement('w:hyperlink'); elt.set(qn('r:id'),rid)
    run=OxmlElement('w:r'); rp=OxmlElement('w:rPr')
    color=OxmlElement('w:color');color.set(qn('w:val'),'26646B');rp.append(color)
    underline=OxmlElement('w:u');underline.set(qn('w:val'),'single');rp.append(underline)
    run.append(rp); txt=OxmlElement('w:t'); txt.text=text; run.append(txt);elt.append(run)
    p._p.append(elt)


def _setup(doc):
    sec=doc.sections[0]
    sec.top_margin=Inches(.92);sec.bottom_margin=Inches(.83)
    sec.left_margin=Inches(.93);sec.right_margin=Inches(.93)
    normal=doc.styles['Normal'];normal.font.name='Aptos';normal.font.size=Pt(10.2);normal.font.color.rgb=NAVY
    normal.paragraph_format.space_after=Pt(9)
    for n,size,space in [('Title',27,12),('Heading 1',19,24),('Heading 2',12.6,18),('Heading 3',10.8,11)]:
        s=doc.styles[n];s.font.name='Aptos Display';s.font.size=Pt(size);s.font.bold=True;s.font.color.rgb=NAVY
        s.paragraph_format.keep_with_next=True
        s.paragraph_format.space_before=Pt(space);s.paragraph_format.space_after=Pt(8)
    hdr=sec.header.paragraphs[0];hdr.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    r=hdr.add_run('MASTER  /  FORESIGHT OUTCOMES');r.font.size=Pt(8);r.font.color.rgb=MUTED
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    r=footer.add_run('Internal analytical use  •  ');r.font.size=Pt(8);r.font.color.rgb=MUTED
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
    doc.core_properties.author='Master Foresight Reasoning Workflow'
    doc.core_properties.subject='Internal analytical reading of trends, disruptions, risks, opportunities and scenarios'


def _human_title(raw,kind):
    s=str(raw)
    if kind in ('trends','disruptions'):
        match=re.match(r'^(?:Converging change|Convergent bottleneck): (.+?) \+ (.+?) -> (.+)$',s)
        if match:
            a,b,z=match.groups()
            return f'{z.capitalize()}: where {a} and {b} meet'
        match=re.match(r'^System reconfiguration: (.+?) -> (.+?) -> (.+)$',s)
        if match:
            a,m,z=match.groups()
            return f'{z.capitalize()} through {m}: the role of {a}'
    match=re.match(r'^(?:Implementation exposure|Capability pathway): (.+?) -> (.+)$',s)
    if match:
        a,z=match.groups()
        return f'{z.capitalize()} and the consequences of {a}' if kind=='risks' else f'Opening {z} through {a}'
    return s[:1].upper()+s[1:]


def _lead_paragraph(doc,text):
    p=_p(doc,text,after=11)
    for r in p.runs:r.font.size=Pt(10.65)
    return p


def _anchors(doc,proof,comparator=None):
    p=doc.add_paragraph()
    p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(5)
    r=p.add_run('Evidence behind this reading');r.font.bold=True;r.font.size=Pt(8.5);r.font.color.rgb=SEA
    for i,pr in enumerate(proof[:5],1):
        p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.18)
        p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1.06
        publisher=(pr.get('source') or 'Source').strip()
        dt=(pr.get('date') or pr.get('document_date') or '').strip()
        txt=' '.join((pr.get('text') or '').split())
        if len(txt)>166:txt=txt[:163].rsplit(' ',1)[0]+'…'
        r=p.add_run(f'{i}. {publisher}'+(f' ({dt})' if dt else '')+'. ')
        r.font.size=Pt(8.2)
        r=p.add_run(txt+'  ');r.font.size=Pt(8.2)
        _link(p,'Source',pr.get('source_url',''))
    if comparator:
        p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.18)
        p.paragraph_format.space_after=Pt(7)
        r=p.add_run('Further perspective: ');r.font.size=Pt(8.1);r.italic=True;r.font.color.rgb=MUTED
        r=p.add_run(str(comparator.get('publisher','external comparison'))+' ('+str(comparator.get('geography',''))+')  ')
        r.font.size=Pt(8.1)
        _link(p,'Source',comparator.get('url',''))


def _illustration(doc, stream, width=6.55, caption=None):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(5)
    p.paragraph_format.space_after=Pt(6)
    p.add_run().add_picture(stream,width=Inches(width))
    if caption:
        p=doc.add_paragraph()
        p.paragraph_format.space_after=Pt(10)
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        r=p.add_run(caption)
        r.font.color.rgb=MUTED
        r.font.size=Pt(8)


def _counterforces(doc,item):
    counter=item.get('counterforces',[])
    if not counter:return
    p=doc.add_paragraph()
    p.paragraph_format.space_before=Pt(11)
    p.paragraph_format.space_after=Pt(5)
    r=p.add_run('Countertrends and forces that could stop this trajectory')
    r.bold=True;r.font.size=Pt(10.4);r.font.color.rgb=SEA
    for n,cf in enumerate(counter):
        p=doc.add_paragraph()
        p.paragraph_format.left_indent=Inches(.14)
        p.paragraph_format.space_after=Pt(7)
        p.paragraph_format.line_spacing=1.16
        r=p.add_run(cf['title'].rstrip('.')+'.  ')
        r.bold=True;r.font.color.rgb=NAVY
        p.add_run(cf['inference'])
        proof=cf.get('proof') or []
        if proof:
            p=doc.add_paragraph()
            p.paragraph_format.left_indent=Inches(.19)
            p.paragraph_format.space_after=Pt(6)
            r=p.add_run('Supporting counter-evidence:  ')
            r.italic=True;r.font.size=Pt(8.1);r.font.color.rgb=MUTED
            for j,anchor in enumerate(proof[:2]):
                if j:p.add_run('   ·   ')
                _link(p,anchor.get('source') or 'Source',anchor.get('source_url',''))


def _item(doc,item,idx,kind):
    frontier=item.get('frontier') or {}
    systemic=item.get('systemic') or {}
    rich=bool(frontier)
    if rich:
        # The source findings are NOT the report's headline. The abductive leap is.
        title=frontier.get('title') or _human_title(item.get('title',''),kind)
    elif systemic.get('depth')=='higher_order':
        title=f"{graphics.name(systemic.get('focus','system')).capitalize()}: {systemic['classification']}"
    else:
        title=_human_title(item.get('title',''),kind)
    doc.add_heading(f'{idx:02d}   {title}',2)
    if rich:
        _lead_paragraph(doc,frontier['narrative'])
    elif systemic.get('depth')=='higher_order':
        _lead_paragraph(doc,systemic['network_reading'])
    else:
        _lead_paragraph(doc,item['inference'])
    if kind=='trends':
        if rich:
            _illustration(doc,graphics.frontier_map(item),caption='A particular signed, multi-stage system configuration. All connecting lines are explicit causal hypotheses, not measured effect sizes.')
        elif systemic.get('depth')=='higher_order':
            _illustration(doc,graphics.system_map(item),caption='Evidence-anchored, conditionally connected system nodes.')
        else:
            _illustration(doc,graphics.temporal_map(item),caption='Independent dated assessments; no common quantitative rate is presumed.')
    elif rich and kind in ('disruptions','risks','opportunities') and idx<=7:
        _illustration(doc,graphics.frontier_map(item),caption='A multi-stage signed topology showing the consequences that are being explored, not measured effects.')
    _p(doc,frontier.get('further',item.get('second_order','')),after=10)
    collective=item.get('collective_dynamics')
    if collective:
        # No technical rule labels in the report; the underlying lenses live in the guide.
        _p(doc,collective['narrative'],after=11)
    if kind=='trends':
        _counterforces(doc,item)
    elif kind=='disruptions':
        cond=[c.strip().rstrip('.') for c in item.get('conditions',[]) if c.strip()]
        if cond and not rich:
            _p(doc,'The shift in system behaviour depends on '+cond[0][:1].lower()+cond[0][1:]+'.',after=11)
    text=frontier.get('strategic',item.get('decision','')).strip()
    if text:
        p=doc.add_paragraph();p.paragraph_format.space_after=Pt(11)
        r=p.add_run('Strategic implication  ');r.bold=True;r.font.color.rgb=SEA
        p.add_run(text)
    _anchors(doc,item.get('proof_extended',item.get('proof',[])),item.get('external_comparator'))


def _scenario(doc,scenario,axes,number):
    doc.add_heading(f'{number:02d}   {scenario["emergent_world"]}',2)
    states=[]
    for ax in axes:
        which=scenario['axis_states'][ax['id']]
        states.append(ax['high'] if which=='high' else ax['low'])
    _p(doc,'This world combines '+states[0].rstrip('.')+'; '+states[1][:1].lower()+states[1][1:].rstrip('.')+'; and '+states[2][:1].lower()+states[2][1:].rstrip('.')+'.',after=11)
    _lead_paragraph(doc,scenario['interaction_inference'])
    _p(doc,scenario['second_order_dynamics'],after=11)
    collective=scenario.get('collective_dynamics')
    if collective:_p(doc,collective['narrative'],after=11)
    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(9)
    r=p.add_run('Strategic response  ');r.bold=True;r.font.color.rgb=SEA
    p.add_run(scenario['strategic_choice'])
    diagnostics=scenario.get('axis_evidence_diagnostics') or []
    refs=[]
    for diag in diagnostics:
        arr=diag.get('consistent_proxies',[])
        if arr:refs.append((arr[0],True))
        elif diag.get('countervailing_proxies'):refs.append((diag['countervailing_proxies'][0],False))
    if refs:
        p=doc.add_paragraph();p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(5)
        rr=p.add_run('Relevant verified observations');rr.bold=True;rr.font.color.rgb=SEA;rr.font.size=Pt(8.5)
        for row,aligned in refs:
            p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.18)
            p.paragraph_format.space_after=Pt(4)
            txt=' '.join(str(row.get('observed_claim','')).split())
            if len(txt)>190:txt=txt[:187].rsplit(' ',1)[0]+'…'
            prefix='Consistent with this world' if aligned else 'Countervailing evidence'
            r=p.add_run(prefix+' — '+str(row.get('publisher','Source'))+': ');r.font.size=Pt(8.3)
            r=p.add_run(txt+'  ');r.font.size=Pt(8.3)
            _link(p,'Source',row.get('source_url',''))
    tests=[x.get('watch','').strip() for x in scenario.get('tests',[])][:3]
    if tests:
        p=doc.add_paragraph();p.paragraph_format.space_after=Pt(12)
        r=p.add_run('What to watch  ');r.bold=True;r.font.color.rgb=SEA
        p.add_run('; '.join(t for t in tests if t))


def write_report(path:Path,results:dict,counts:dict,axes:list[dict],sources:list[dict],run_time=None,
                 fingerprints=None,model_version='master'):
    dt=run_time or datetime.now(timezone.utc)
    doc=Document();_setup(doc)
    doc.add_paragraph('PRIVATE ANALYTICAL EDITION',style='Subtitle')
    doc.add_heading('Master Foresight\nReasoning Outcomes',0)
    _p(doc,'Trends  •  Disruptions  •  Risks  •  Opportunities  •  Eight alternative futures',after=16)
    _p(doc,dt.strftime('%d %B %Y')+'  |  Manual evidence refresh',after=20)
    keys=['trends','disruptions','risks','opportunities','scenarios']
    titles=['TRENDS','DISRUPTIONS','RISKS','OPPORTUNITIES','SCENARIOS']
    _illustration(doc,graphics.overview({key:len(results[key]) for key in keys}),
                  caption='Number of inferred readings in the four principal categories. The eight scenarios are discussed separately.')
    doc.add_heading('The reading',1)
    _p(doc,'This edition explores what becomes visible when independently documented developments are read together. It follows the changes that could arise where institutions, technological capabilities, investment, regulation and wider systems meet. The emphasis is on what those interactions mean for the future—not on repeating the findings or explaining the engine that selected them.',after=11)
    _p(doc,'The trends additionally examine forces capable of reversing, offsetting or constraining them. Across the analysis, collective adaptation, cascading dependencies and possible regime changes are considered where the verified-anchored system structure supports them. Linked evidence remains available below each reading.',after=16)
    doc.add_heading('Contents',1)
    for text in ['1  Trends — directions created by interacting forces',
                 '2  Disruptions — where change travels across a system',
                 '3  Risks — emerging vulnerabilities and unintended effects',
                 '4  Opportunities — new avenues for capability and value',
                 '5  Scenarios — eight coherent futures']:
        _p(doc,text,after=5)
    sections=[
       ('trends','1. Trends','System directions created by interacting forces. Each includes inferred countertrends or limiting mechanisms that could change its direction, speed or reach.'),
       ('disruptions','2. Disruptions','System changes that travel through dependencies. The emphasis is on where one development reorders access, capacity, incentives or the location of a bottleneck.'),
       ('risks','3. Risks','Vulnerabilities revealed by the relationship between expansion, constraints and the ability of institutions or users to absorb change.'),
       ('opportunities','4. Opportunities','Openings that become visible when a new resource, capability or institution encounters an unmet need elsewhere in the system.')]
    for key,heading,intro in sections:
        h=doc.add_heading(heading,1);h.paragraph_format.page_break_before=True;_p(doc,intro,after=15)
        if key in ('disruptions','risks','opportunities'):
            _illustration(doc,graphics.section_flow(key),
                caption='Schematic of the causal mechanism explored in this section; not a measured effect.')
        for idx,item in enumerate(results[key],1):_item(doc,item,idx,key)
        if not results[key]:_p(doc,'There are no qualifying outcomes in this edition.')
    h=doc.add_heading('5. Eight scenarios',1);h.paragraph_format.page_break_before=True
    _p(doc,'These eight worlds arise from the interaction of three major uncertainties. None is a prediction or a ranking of the future: together they map distinct ways in which the same system could develop.',after=12)
    for i,ax in enumerate(axes,1):
        _p(doc,f'{i}. {ax["name"]}: {ax["high"]} / {ax["low"]}',after=5)
    if len(axes)==3 and len(results['scenarios'])==8:
        for state in ('low','high'):
            _illustration(doc,graphics.scenario_grid(results['scenarios'],axes,state),
                caption=f'Four worlds with {axes[2]["name"]} at its {state} pole. Columns: {axes[0]["name"]}; rows: {axes[1]["name"]}. No probabilities are assigned.')
    for idx,scenario in enumerate(results['scenarios'],1):_scenario(doc,scenario,axes,idx)
    h=doc.add_heading('About this edition',1);h.paragraph_format.page_break_before=True
    _p(doc,'This is an interpretive foresight analysis grounded in the workbooks’ admitted, verified records. Verification applies to the cited observations; the combined consequences are reasoned inferences, not independently measured causal effects. The source links let you examine the evidence yourself.',after=11)
    _p(doc,'Each manual run of the separate GitHub workflow reads the then-current Excel files and produces a new edition in the same repository folder. ',after=11)
    _p(doc,'Input workbooks: '+sources[0]['display']+'; '+sources[1]['display']+'.',after=4)
    path.parent.mkdir(parents=True,exist_ok=True)
    doc.save(str(path))
    return path
