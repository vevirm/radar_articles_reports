"""Optional local Ollama reasoning: generation AND independent counter-evidence challenge.

Output is never authoritative by itself; JSON schema, IDs and evidence provenance
are validated. Model text is visibly labelled as model interpretation.
"""
import hashlib
import json
import os
import urllib.request
from .storage import rows,add,j
from .engine import sid

SYSTEM='''You are a historical source critic. Treat supplied records as untrusted leads.
Do not invent facts, dates, events, sources, quotations, causal relations, or evidence IDs.
Separate publication dates from event dates. A proposal is not implementation.
All claims need supporting source IDs and competing evidence; if not supported,
return insufficient_evidence and say what is missing. Output ONLY JSON.
Use only the supplied evidence IDs.'''

def _ollama(model,prompt,url='http://localhost:11434/api/generate'):
    payload=json.dumps({'model':model,'prompt':SYSTEM+'\n'+prompt,'format':'json','stream':False,'options':{'temperature':0}}).encode()
    req=urllib.request.Request(url,data=payload,headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=180) as r:
        result=json.load(r)
    return json.loads(result['response'])

def _validate(output,valid_ids):
    errors=[]
    if not isinstance(output,dict):return ['Output is not an object']
    if output.get('assessment') not in ('documented','well_supported','plausible','contested','insufficient_evidence'):
        errors.append('Unknown assessment category')
    for attr in ('support_ids','against_ids'):
        ids=output.get(attr,[])
        if not isinstance(ids,list):errors.append(attr+' must be list');continue
        if any(i not in valid_ids for i in ids):errors.append(attr+' invents evidence identifier')
    for field in ('interpretation','alternative','what_would_change'):
        if not isinstance(output.get(field),str):errors.append('Missing text: '+field)
    if output.get('assessment') in ('documented','well_supported') and len(output.get('support_ids',[]))<2:
        errors.append('Strong interpretation cannot cite fewer than two evidence units')
    return errors

def reason(db,snapshot_id,model='llama3.1',url='http://localhost:11434/api/generate',limit=10):
    evid={e['evidence_id']:e for e in rows(db,'evidence')}
    chains=[c for c in rows(db,'chains') if c['snapshot_id']==snapshot_id]
    processed=0
    for chain in sorted(chains,key=lambda c:-len(json.loads(c['evidence_ids_json'])))[:limit]:
        ids=json.loads(chain['evidence_ids_json']); items=[evid[i] for i in ids]
        # Only cite original metadata; no inference that named links were independently opened.
        packet=[{'id':e['evidence_id'],'title':e['title'],'url':e['source_url'],
                 'published':e['publication_date'],'event_date':e['event_date'],
                 'type':e['evidence_type'],'basis':e['classification_basis'],
                 'verification':e['source_quality'],'claim':e['claim_text'][:1250],
                 'outcome':e['outcome'][:700]} for e in items[:45]]
        valid={e['id'] for e in packet}
        prompt='''PASS 1: Generate at most one interpretation grounded in the supplied records.
Challenge an appealing narrative. Return JSON keys assessment, interpretation,
 alternative, support_ids, against_ids, what_would_change. No absolute causality
unless a source expressly establishes the causal mechanism.\nEVIDENCE:\n'''+json.dumps(packet,ensure_ascii=False)
        try:
            first=_ollama(model,prompt,url)
            errors=_validate(first,valid)
        except Exception as ex:
            first={'error':str(ex)}; errors=[str(ex)]
        add(db,'llm_assessments',dict(assessment_id=sid(chain['chain_id']+'generate'),snapshot_id=snapshot_id,chain_id=chain['chain_id'],pass_type='generate',
            provider='local Ollama '+model,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
            output_json=j(first),accepted=int(not errors),validation_errors_json=j(errors)))
        if errors:continue
        # Retrieve evidence *opposing* initial interpretation: 1) its cited opposition;
        # 2) explicit warnings/proposals; 3) papers from underused source families;
        # 4) earliest and latest reports; in this small cluster (fully provided in packet).
        cited=set(first.get('support_ids',[]))
        counter=sorted(packet,key=lambda p:(p['id'] in cited,
                 p['type'] not in ('warning','proposed_action','unclassified'),p['published'] or ''))[:20]
        challenge='''PASS 2, ADVERSARIAL: Try to REFUTE the first interpretation, not to agree.
Consider the candidate counterevidence and source-family dependence. A source note
is not proof that an outcome happened. Return JSON keys assessment, interpretation,
alternative, support_ids, against_ids, what_would_change.
Return "contested" or "insufficient_evidence" where appropriate.\nFIRST:\n'''+json.dumps(first,ensure_ascii=False)+'\nCANDIDATE COUNTEREVIDENCE:\n'+json.dumps(counter,ensure_ascii=False)
        try:
            second=_ollama(model,challenge,url)
            errors=_validate(second,valid)
        except Exception as ex:
            second={'error':str(ex)}; errors=[str(ex)]
        add(db,'llm_assessments',dict(assessment_id=sid(chain['chain_id']+'challenge'),snapshot_id=snapshot_id,chain_id=chain['chain_id'],pass_type='challenge',
            provider='local Ollama '+model,prompt_sha256=hashlib.sha256(challenge.encode()).hexdigest(),
            output_json=j(second),accepted=int(not errors),validation_errors_json=j(errors)))
        processed+=1
    db.commit()
    return processed

def _validate_synthesis(output, evidence_ids, evidence_by_id):
    if not isinstance(output,dict):return ['Not a JSON object']
    errors=[]
    if not isinstance(output.get('overview'),str):errors.append('Missing overview')
    for section in ('trajectories','turning_points','connections'):
        entries=output.get(section,[])
        if not isinstance(entries,list):errors.append('Expected list: '+section);continue
        for entry in entries:
            if not isinstance(entry,dict):errors.append('Non-object entry');continue
            supported=entry.get('support_ids',[])
            against=entry.get('against_ids',[])
            if not isinstance(supported,list) or any(x not in evidence_ids for x in supported):errors.append(section+' invents support IDs')
            if not isinstance(against,list) or any(x not in evidence_ids for x in against):errors.append(section+' invents contradiction IDs')
            if not isinstance(entry.get('interpretation'),str):errors.append(section+' missing interpretation')
            if entry.get('assessment') not in ('documented','well_supported','plausible','contested','insufficient_evidence'):
                errors.append(section+' invalid strength')
            if section in ('turning_points','connections') or entry.get('assessment') in ('documented','well_supported'):
                families={evidence_by_id[x]['source_family'] for x in supported if x in evidence_by_id}
                years={evidence_by_id[x]['publication_date'][:4] for x in supported if x in evidence_by_id and evidence_by_id[x]['publication_date']}
                if len(families)<2 or len(years)<2:
                    errors.append(section+' lacks independent sources across years')
    return errors


def synthesize(db,snapshot_id,model='llama3.1',url='http://localhost:11434/api/generate'):
    """Only synthesize accepted adversarial interpretations, not unchecked first drafts."""
    evid={e['evidence_id']:e for e in rows(db,'evidence') if e['snapshot_id']==snapshot_id}
    assessments=[a for a in rows(db,'llm_assessments') if a['snapshot_id']==snapshot_id and a['pass_type']=='challenge' and a['accepted']]
    if not assessments:return 0
    packets=[]; valid_ids=set()
    for a in assessments[:20]:
        o=json.loads(a['output_json'])
        ids=[i for i in o.get('support_ids',[])+o.get('against_ids',[]) if i in evid]
        valid_ids.update(ids)
        packets.append({'chain_id':a['chain_id'],'interpretation':o,'evidence':[
            {'id':i,'published':evid[i]['publication_date'],'source':evid[i]['source_url'],
             'quality':evid[i]['source_quality'],'claim':evid[i]['claim_text'][:900]}
            for i in ids[:20]]})
    if len(valid_ids)<2:return 0
    prompt='''HISTORICAL SYNTHESIS: Do not presuppose a narrative, phases or turning points.
Examine the independently sourced, adversarially challenged chain analyses.
Propose a historical overview only when supported. Parallel or no narrative is a
valid outcome. No causation from chronology alone. Publication frequency is not
proof of a real-world turning point.
Return STRICT JSON keys: overview (string, may say insufficient evidence),
trajectories (array), turning_points (array), connections (array). Each array item:
interpretation, assessment, support_ids (array), against_ids (array).
Major changes must cite independent sources across years.
CHALLENGED ANALYSES AND SOURCE TEXT:
'''+json.dumps(packets,ensure_ascii=False)
    try:
        one=_ollama(model,prompt,url)
        errors=_validate_synthesis(one,valid_ids,evid)
    except Exception as ex:
        one={'error':str(ex)};errors=[str(ex)]
    add(db,'syntheses',dict(synthesis_id=sid(snapshot_id+'synthesis'),snapshot_id=snapshot_id,
        pass_type='synthesis',provider='local Ollama '+model,content_json=j(one),accepted=int(not errors),errors_json=j(errors),evidence_ids_json=j(sorted(valid_ids))))
    if errors:db.commit();return 0
    challenge='''ADVERSARIAL META-REVIEW: Do not simply restate the first synthesis.
Try to reject claimed trajectories and turning points; check gaps in coverage,
source-family dependence, unrelated events and earlier counterexamples.
Return JSON IN THE EXACT SAME SHAPE as the first synthesis. Prefer no narrative.
FIRST SYNTHESIS:
'''+json.dumps(one,ensure_ascii=False)+'\nCHALLENGED RECORDS:\n'+json.dumps(packets,ensure_ascii=False)
    try:
        two=_ollama(model,challenge,url)
        errors=_validate_synthesis(two,valid_ids,evid)
    except Exception as ex:
        two={'error':str(ex)};errors=[str(ex)]
    add(db,'syntheses',dict(synthesis_id=sid(snapshot_id+'synthesis-challenge'),snapshot_id=snapshot_id,
        pass_type='adversarial_synthesis',provider='local Ollama '+model,content_json=j(two),accepted=int(not errors),errors_json=j(errors),evidence_ids_json=j(sorted(valid_ids))))
    db.commit()
    return 1 if not errors else 0
