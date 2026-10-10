"""Conservative evidence import, graph discovery, chains and adversarial tests.

No LLM: outputs SOURCE DESCRIPTIONS and POSSIBLE connections, not alleged causes.
Every evidence claim points to an original workbook row and available link.
"""
from __future__ import annotations
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from .xlsx_reader import read_sheets,normalize_date
from .storage import connect,add,rows,j

STOP = set('the a an and of for in on to with by from as at into about that this using use study paper article research europe european eu new future policy project report analysis development towards toward through their its they are was were is have has within between among system systems approach approaches technology technologies innovation innovative based regarding potential evidence results findings implications perspective effects case review official information work how where why what 2026 2025 2024 2023'.split())
COLUMN_ALIASES = {
 'title':['title','publication title','source title','name','headline'],
 'url':['original source','source url','url','link','doi','original url','publication link','source link'],
 'pubdate':['publication date','published date','published','date published','publication year','year','date'],
 'eventdate':['event date','historical event date','date of event','occurred on','occurred','year of event'],
 'subject':['topic','themes','theme','subject','area','domain','field','category','keywords','tags','strand','focus'],
 'claim':['structured claim','historical finding','finding','claim','key finding','summary','description','abstract','radar note','evidence','conclusion','main finding','finding text'],
 'type':['evidence type','claim type','statement type','record type'],
 'verification':['verification status','verified','verification','source status','status'],
 'quality':['source quality','quality','evidence strength','authority'],
 'actors':['actors','stakeholders','organizations','organisations','who'],
 'mechanism':['mechanism','causal mechanism','reason','relationship'],
 'outcome':['observed outcome','measured outcome','outcome','impact measured'],
 'qualification':['limitations','qualification','uncertainty','caveat','method note'],
 'eventid':['historical event id','event id','development id','underlying event id'],
}
VERIFIED_WORDS=('verified','confirmed','audited','primary','official','validated')
PROVISIONAL_WORDS=('unverified','provisional','inferred','hypothetical','draft','needs verification','not verified')
ALLOWED_TYPES={'observation','condition','event','proposed_action','announced_decision','implemented_action','measurable_outcome','prediction','warning','scenario','interpretation','unclassified'}

def sid(s): return hashlib.sha256(str(s).encode('utf8')).hexdigest()[:16]
def utc():return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def norm(s):return re.sub(r'\s+',' ',re.sub(r'[^\w\s]',' ',str(s).lower())).strip()
def first(row,keys,default=''):
    # prefer exact semantic column before fuzzy name matches
    m={norm(k):k for k in row}
    for key in keys:
        if norm(key) in m and str(row[m[norm(key)]]).strip(): return str(row[m[norm(key)]]).strip()
    return default

def canonical_url(text):
    text=str(text or '').strip()
    if text.startswith('doi:'): text='https://doi.org/'+text[4:].strip()
    elif re.fullmatch(r'10\.\d{4,9}/[^\s]+',text,re.I): text='https://doi.org/'+text
    return text.split('#')[0] if text.startswith(('http://','https://')) else ''

def subject_text(row):
    return first(row,COLUMN_ALIASES['subject'])

def tokens(text):
    return set(w for w in re.findall(r'[a-z][a-z0-9-]{3,}',norm(text)) if w not in STOP and not w.isdigit())

def source_family(url,title):
    if url:
        net = urlparse(url).netloc.lower().removeprefix('www.')
        if net in ('doi.org','dx.doi.org'):
            return 'doi-'+urlparse(url).path.split('/')[1] if len(urlparse(url).path.split('/'))>1 else 'doi.org'
        return net
    return 'unlinked:'+sid(title)[:7]

def quality_assessment(raw,origin):
    ver=first(raw,COLUMN_ALIASES['verification'])
    quality=first(raw,COLUMN_ALIASES['quality'])
    combined=(ver+' '+quality).lower()
    if any(w in combined for w in PROVISIONAL_WORDS): q='provisional'
    elif any(w in combined for w in VERIFIED_WORDS): q='documented_in_database'
    else: q='not_verified_in_database'
    # Even a 'verified' label is not proof of the real-world proposition.
    if origin=='Shock audit' and q!='documented_in_database':q='audit_lead_only'
    return q,ver,quality

def classify(raw,claim):
    explicit=first(raw,COLUMN_ALIASES['type']).lower().replace(' ','_').replace('-','_')
    if explicit in ALLOWED_TYPES:return explicit,'explicit_sheet_metadata'
    if explicit:
        if 'proposal' in explicit:return 'proposed_action','interpreted_sheet_metadata'
        if 'prediction' in explicit:return 'prediction','interpreted_sheet_metadata'
        if 'warning' in explicit:return 'warning','interpreted_sheet_metadata'
    # Conservative lexical clues: never upgrade 'proposed' to delivered.
    text=(claim or '').lower()
    if re.search(r'\b(proposes?|proposal|calls for|recommends?|should|plans? to)\b',text):return 'proposed_action','lexical_hint_not_verified'
    if re.search(r'\b(warns?|risks?|could threaten)\b',text):return 'warning','lexical_hint_not_verified'
    if re.search(r'\b(predicts?|forecasts?|projects? that|by 20[2-9]\d will)\b',text):return 'prediction','lexical_hint_not_verified'
    if re.search(r'\b(announced|intends to|will launch|planned investment)\b',text):return 'announced_decision','lexical_hint_not_verified'
    if re.search(r'\b(inaugurated|opened|launched|enacted|implemented|began operation)\b',text):return 'implemented_action','lexical_hint_not_verified'
    if re.search(r'\b(measured|observed|decreased by|increased by|reached \d)\b',text):return 'observation','lexical_hint_not_verified'
    return 'unclassified','no_explicit_evidence_type'

def import_workbook(db,workbook,synthetic=False):
    blob=Path(workbook).read_bytes(); filehash=hashlib.sha256(blob).hexdigest()
    snapshot_id=sid(filehash); stamp=utc()
    sheets,warnings=read_sheets(workbook)
    if any('REQUIRED sheet' in x for x in warnings):
        raise ValueError('Required workbook sheet(s) missing: '+'; '.join(warnings))
    add(db,'snapshots',dict(snapshot_id=snapshot_id, generated_utc=stamp,workbook_sha256=filehash,workbook_name=Path(workbook).name,notes='SYNTHETIC FIXTURE' if synthetic else 'Original workbook imported without modification'))
    seen={}
    for sheet, data in sheets.items():
        for row in data:
            rownum=int(row['_sheet_row']); rid=sid(f'{snapshot_id}|{sheet}|{rownum}')
            add(db,'raw_records',dict(raw_id=rid,snapshot_id=snapshot_id,sheet=sheet,row_num=rownum,raw_json=j(row)))
            if row.get('_preamble'):
                continue
            if sheet not in ('Historical findings','All publication data'):
                continue  # Ranked sources is metadata, shock audit is a lead, Method is metadata.
            title=first(row,COLUMN_ALIASES['title'])
            claim=first(row,COLUMN_ALIASES['claim'])
            url=canonical_url(first(row,COLUMN_ALIASES['url']))
            date=normalize_date(first(row,COLUMN_ALIASES['pubdate']))
            event_date=normalize_date(first(row,COLUMN_ALIASES['eventdate']))
            if not (title or claim): continue
            if not claim: claim=title
            key = url.lower() if url else 'title:'+norm(title)+'|date:'+str(date)
            # Sources are de-duplicated; raw rows and sheet membership are never dropped.
            eid=seen.get(key) or sid('publication:'+key)
            if key in seen:
                add(db,'evidence_occurrences',{'evidence_id':eid,'raw_id':rid})
                continue
            seen[key]=eid
            etype,basis=classify(row,claim)
            q,ver,qual=quality_assessment(row,sheet)
            event_id=first(row,COLUMN_ALIASES['eventid'])
            add(db,'evidence',dict(
                evidence_id=eid,snapshot_id=snapshot_id,primary_raw_id=rid,
                publication_id=sid(key), event_group_id=sid('event:'+event_id) if event_id else None,
                origin_sheet=sheet,title=title,source_url=url,publication_date=date,event_date=event_date,
                ingested_utc=stamp,source_family=source_family(url,title),subject=subject_text(row),
                evidence_type=etype,classification_basis=basis,source_quality=q,
                verification=ver,claim_text=claim,actors=first(row,COLUMN_ALIASES['actors']),
                area=subject_text(row),mechanism=first(row,COLUMN_ALIASES['mechanism']),
                outcome=first(row,COLUMN_ALIASES['outcome']),qualifications=first(row,COLUMN_ALIASES['qualification']),
                metadata_json=j({'sheet':sheet,'raw_row':rownum,'quality_text':qual})
            ))
            add(db,'evidence_occurrences',{'evidence_id':eid,'raw_id':rid})
    db.commit()
    return snapshot_id, sheets, warnings


def infer_subject_groups(evidence):
    """Prefer supplied subject labels. Else choose shared data-derived keywords.

    They are navigation clusters, not claims that research fields are causally linked.
    """
    df=Counter()
    for e in evidence:
        df.update(tokens(e['title']+' '+e['subject']))
    count=len(evidence)
    groups=defaultdict(list)
    for e in evidence:
        if e['subject']:
            pieces=re.split(r'[|;,]',e['subject'])
            label=(pieces[0].strip() or 'Untitled subject')[:85]
            groups['explicit: '+label.lower()].append(e)
        else:
            words=tokens(e['title'])
            candidates=[x for x in words if 2 <= df[x] <= max(3,int(count*.60))]
            if candidates:
                # pick shared but not ubiquitous concept, stable tie-breaking
                label=sorted(candidates,key=lambda x:(-df[x],x))[0]
                groups['lexical: '+label].append(e)
            else:
                groups['unclustered'].append(e)
    return groups


def make_graph(db,snapshot_id,max_neighbors=5):
    all_e=[e for e in rows(db,'evidence') if e['snapshot_id']==snapshot_id]
    groups=infer_subject_groups(all_e)
    chain_map={}
    for name, items in groups.items():
        if len(items)<2 or name=='unclustered':continue
        ordered=sorted(items,key=lambda e:(e['publication_date'] or '9999',e['evidence_id']))
        ids=[e['evidence_id'] for e in ordered]
        cid=sid('chain:'+snapshot_id+name)
        dates=[e['publication_date'] for e in ordered if e['publication_date']]
        is_lexical=name.startswith('lexical:')
        notes=['Lexical grouping is provisional; shared terminology is not proof of shared historical development.'] if is_lexical else []
        if any(not x['event_date'] for x in ordered):notes.append('Event dates missing for some records: displayed dates are publication dates.')
        add(db,'chains',dict(chain_id=cid,snapshot_id=snapshot_id,subject=name,evidence_ids_json=j(ids),
            period_start=min(dates) if dates else None,period_end=max(dates) if dates else None,
            description=f'{len(items)} publications share '+('a selected subject label' if not is_lexical else 'a title term')+'; no causal chain established.',warnings_json=j(notes)))
        chain_map[cid]=ordered
        # Temporal / topical links are weak; documented same-event links stronger.
        for i, source in enumerate(ordered):
            for target in ordered[i+1:i+1+max_neighbors]:
                if source['event_group_id'] and source['event_group_id']==target['event_group_id']:
                    rt,st='same_explicit_event','documented'
                    reason='Both rows share an explicit underlying-event identifier.'
                else:
                    rt,st='chronological_and_topical','weak'
                    reason='Publications share a selected topic and are chronologically ordered; no causal connection inferred.'
                rid=sid(source['evidence_id']+'|'+target['evidence_id']+'|'+rt)
                add(db,'relations',dict(relation_id=rid,snapshot_id=snapshot_id,from_id=source['evidence_id'],to_id=target['evidence_id'],relation_type=rt,strength=st,justification=reason,evidence_json=j([source['evidence_id'],target['evidence_id']])))
    db.commit()
    return chain_map


def judge_support(items, filtered=None):
    filtered=filtered if filtered is not None else items
    fam={e['source_family'] for e in filtered}
    underlying={e['event_group_id'] or e['evidence_id'] for e in filtered}
    dates={e['publication_date'][:4] for e in filtered if e['publication_date']}
    type_counts=Counter(x['evidence_type'] for x in filtered)
    return {'publications':len(filtered),'underlying_developments':len(underlying),'independent_source_families':len(fam),'years':len(dates),
            'explicit_outcomes':sum(bool(x['outcome']) for x in filtered),
            'verified_metadata':sum(x['source_quality']=='documented_in_database' for x in filtered),
            'types':dict(type_counts)}


def evaluate_chains(db,snapshot_id,chain_map):
    for cid,items in chain_map.items():
        if len(items)<2:continue
        metrics=judge_support(items)
        # Only eligible if more than one independent family and more than one year.
        eligible=metrics['independent_source_families']>=2 and metrics['underlying_developments']>=2 and metrics['years']>=2
        candidates=[
            ('Repeated attention to the same subject across the years',
             'The records might reflect continued reporting rather than a change in the real world.'),
            ('Possible development from earlier claims toward later reported actions or outcomes',
             'Later records may reflect a distinct initiative or an independently occurring change.'),
            ('Possible coverage or terminology effect in the apparent timeline',
             'A genuine transition may exist but is obscured by differences in publication coverage.')]
        for index,(claim,alternative) in enumerate(candidates):
            hid=sid(cid+'|hypothesis|'+str(index))
            counter=[]
            if metrics['independent_source_families']<2:counter.append('Fewer than two independent source families.')
            if metrics['years']<2:counter.append('No independent evidence spanning two publication years.')
            if metrics['underlying_developments']<2:counter.append('Multiple publications appear to describe one underlying event.')
            if index==1 and not any(e['outcome'] for e in items):counter.append('No explicit outcome column documents a realised result.')
            if index==1 and not any(e['event_date'] for e in items):counter.append('Event dates missing; only publication chronology can be shown.')
            if index==2:counter.append('This dataset has no external publication-denominator coverage measure.')
            if index==1:expected=['Original proposal or problem','Later implementation document','Independent observed outcome evidence']
            elif index==0:expected=['Comparable source coverage','Consistent terminology','Independent observations across years']
            else:expected=['Stable independent sampling','External publication baseline by period','Same concept described under changed terminology']
            claim_is_strong = eligible and index==0
            status = 'plausible' if claim_is_strong else ('contested' if eligible and index==1 and metrics['explicit_outcomes'] else 'insufficient_evidence')
            # Robustness test: remove all from each source family; remove provisional; duplicates already collapsed.
            robust=[]
            pending_robustness=[]
            for family in sorted({e['source_family'] for e in items}):
                rest=[e for e in items if e['source_family']!=family]
                ok=judge_support(rest)
                survived=ok['independent_source_families']>=2 and ok['underlying_developments']>=2 and ok['years']>=2
                robust.append(survived)
                pending_robustness.append(dict(assessment_id=sid(hid+'|exclude_family|'+family),hypothesis_id=hid,
                        test_name='exclude_source_family:'+family,outcome='survives' if survived else 'fragile',details_json=j(ok)))
            trusted=[e for e in items if e['source_quality']=='documented_in_database']
            qm=judge_support(trusted)
            survives_qa=qm['independent_source_families']>=2 and qm['underlying_developments']>=2 and qm['years']>=2
            pending_robustness.append(dict(assessment_id=sid(hid+'|exclude_provisional_and_unverified'),hypothesis_id=hid,
                   test_name='verified_metadata_only',outcome='survives' if survives_qa else 'fragile',details_json=j(qm)))
            if not all(robust) and status=='plausible':status='contested'
            if not survives_qa and status=='plausible':status='contested'
            # At this stage no hypothesized causality is established.
            add(db,'hypotheses',dict(hypothesis_id=hid,snapshot_id=snapshot_id,chain_id=cid,
                claim=claim,alternative=alternative,support_json=j([e['evidence_id'] for e in items]),
                against_json=j([]),expected_json=j(expected),falsifier_json=j(['Independent counterexample','Documented incompatible timeline']),
                missing_json=j(counter),status=status,evaluation_json=j({'automated':True,'eligibility':eligible,'metrics':metrics,'survives_leave_family_out':all(robust) if robust else False,'verified_only_survives':survives_qa,'causation_demonstrated':False})))
            for item in pending_robustness: add(db,'robustness',item)
    db.commit()
