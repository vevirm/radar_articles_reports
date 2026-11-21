"""Proof-carrying, defeasible foresight *hypothesis* generator.

Key epistemic boundary: a published study, adopted policy, or announced programme
is evidence of the event described, NOT proof that its predicted consequence happened.
No score here is a probability or a causal-effect estimate.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass,asdict,replace
from datetime import date
import re
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
from typing import Iterable
from .adapter import Evidence

UNREALIZED={'intention','proposed','in_negotiation','announced','call_open'}
MEASURED={'measures','detects'}
CAPACITY_ACTS={'builds','launches','funds','invests','allocates','adds_capacity','adopts',
    'associates','procures','supports','collaborates','coordinates','standardises',
    'harmonises','diversifies','sells','supplies','integrates','transfers'}
RESTRICT_ACTS={'restricts','excludes','screens','opposes','requires'}


def _hash(*parts: str) -> str:
    return sha256('|'.join(parts).encode()).hexdigest()[:18]


def _status(c: dict) -> str:
    return (c.get('status') or '').lower()


def _date(c: dict) -> str:
    return (c.get('status_date') or '')[:10]


def _parse_date(value: str) -> date | None:
    raw=(value or '').strip()[:10]
    if re.fullmatch(r'\d{4}-\d{2}',raw): raw+='-01'
    try: return date.fromisoformat(raw)
    except ValueError: return None


def _date_days(a: str,b: str) -> int | None:
    da,db=_parse_date(a),_parse_date(b)
    return abs((da-db).days) if da and db else None


def _same_scope(a: dict,b: dict) -> bool:
    """EU can be matched to EU; other levels require explicit identical countries.

    An unspecified 'external' scope is NOT evidence about every external region.
    """
    x,y=a.get('scope') or {}, b.get('scope') or {}
    lx,ly=x.get('level'),y.get('level')
    if not lx or not ly or lx!=ly:return False
    xa,ya=set(x.get('countries') or []),set(y.get('countries') or [])
    if xa or ya: return bool(xa) and xa==ya
    return lx=='eu'


def _scope_key(c: dict) -> str:
    scope=c.get('scope') or {}
    return (scope.get('level') or '')+':'+','.join(sorted(scope.get('countries') or []))


VERIFIED_CLASSES=frozenset({'deep_scan_authoritative_keep',
    'historical_authoritative_keep','independent_credible','credible_primary_claim_only'})


def verification_status(e: Evidence) -> str:
    """The workbook's vetting verdict, NOT external truth of every statement."""
    if e.admission=='keep' and e.quality_class in VERIFIED_CLASSES:
        return 'workbook_verified'
    if e.admission in {'provisional','awaiting','lead'}:
        return 'provisional'
    if e.admission in {'review','needs_review'}:
        return 'review'
    return 'not_admitted'


# For discovery only, not arithmetic evidence aggregation. A provisional finding's
# 0.02 never accumulates into a conclusion, no matter how many leads exist.
DISCOVERY_WEIGHTS={'workbook_verified':1.0,'review':0.10,'provisional':0.02,
                   'not_admitted':0.0}


def _verified(e: Evidence,c: dict) -> bool:
    return verification_status(e)=='workbook_verified' and not c.get('provisional',False)


def _family_independent(a: Evidence,b: Evidence) -> bool:
    # Publisher grouping is a MINIMUM safeguard, not independent verification of origin.
    return a.source_key!=b.source_key and a.source_family!=b.source_family and 'unknown' not in (a.source_family,b.source_family)


def _weight(e: Evidence,c: dict) -> float:
    """Verified-only, conservative evidential relevance index, NOT a probability.

    Verification is a hard gate. Within verified material, DIRECTNESS, claim
    uncertainty, and merit matter. Advocacy cannot become observed measurement.
    """
    if not _verified(e,c):return 0.0
    confidence={'high':1.0,'medium':.78,'low':.50}.get(
        (c.get('confidence') or e.confidence or '').lower(),.60)
    merit=c.get('merit')
    try: merit=float(merit)
    except (TypeError,ValueError):merit=50
    merit_factor=.55+.45*max(0,min(100,merit))/100
    kind,mechanism=c.get('kind'),c.get('mechanism')
    if kind=='advocacy':directness=.38
    elif kind=='diagnosis':
        directness={'measures':1.0,'detects':.95,'evaluates':.86,'assesses':.74}.get(mechanism,.65)
    elif kind=='action':directness=.92 if mechanism not in {'proposes','advocates'} else .52
    else: directness=.46
    return round(confidence*merit_factor*directness,4)


def _phase_weight(c: dict) -> float:
    # An 'operating' PROGRAMME might still lack measured downstream outcomes.
    return {'intention':.17,'proposed':.23,'in_negotiation':.30,'announced':.39,
            'call_open':.35,'adopted':.69,'in_force':.83,'operating':.95,
            'delivered':.70,'abandoned':.05}.get(_status(c),.31)


FUTURE_LANGUAGE=(r'\bpropos(?:es|ed|al|ing)\b',r'\bplans? to\b',
    r'\bplanned\b',r'\bexpects?\b',r'\btarget(?:s|ing|ed)?\b',
    r'\bambition\b',r'\baims? to\b',r'\bseeks? to\b',
    r'\bpotentially\b',r'\bwould\b',r'\bcould\b',
    r'\bup-to\b',r'\bby 20\d{2}\b',r'\bfunding opportunities\b',
    r'\bgrant preparation\b',r'\bcalled for\b')


def _projected_action(c:dict)->bool:
    """Conservative safeguard against mistaking confirmed PLANS for outcomes.

    Heuristic marking is a review prompt. It is not NLP verification and a
    documented present action can coexist with future-oriented claims.
    """
    if c.get('kind')!='action':return False
    text=(c.get('text') or '').lower()
    return any(re.search(pattern,text) for pattern in FUTURE_LANGUAGE)


def _effective_phase_weight(c:dict)->float:
    return min(_phase_weight(c),.42) if _projected_action(c) else _phase_weight(c)


@dataclass(frozen=True)
class Finding:
    id: str
    rule: str
    type: str
    status: str
    title: str
    inference: str
    logic: str
    assumptions: tuple[str,...]
    counter_case: str
    disconfirmation_test: str
    evidence_ids: tuple[str,...]
    claim_ids: tuple[str,...]
    proof: tuple[dict,...]
    support_index: int
    caveat: str
    model_version: str
    verified_anchor_count: int = 0
    publisher_family_count: int = 0
    unverified_score_contribution: float = 0.0

    def as_json(self) -> dict:
        d=asdict(self)
        for x in ('assumptions','evidence_ids','claim_ids','proof'):d[x]=list(d[x])
        return d


def _cit(e: Evidence, c: dict) -> dict:
    return {'record':e.id,'claim':c.get('claim_id',''), 'object':c.get('object',''),
            'kind':c.get('kind',''),'mechanism':c.get('mechanism',''),
            'direction':c.get('direction',''),'status':c.get('status',''),
            'date':_date(c),'text':c.get('text',''),
            'source':e.publisher,'source_url':e.url,
            'qualification':c.get('qualification') or e.qualification,
            'scope':c.get('scope'), 'source_family':e.source_family,
            'projected_action_language':_projected_action(c),
            'verification':verification_status(e),
            'evidential_weight':_weight(e,c)}


def _score(ea: Evidence,ca: dict,eb: Evidence,cb: dict, rule: str) -> int:
    # Conjunctive bottleneck: weakest verified premise governs. No averaging
    # with high-quality inputs, no volume bonus for reprints/unverified leads.
    if not (_verified(ea,ca) and _verified(eb,cb)):return 0
    bottleneck=min(_weight(ea,ca),_weight(eb,cb))
    maturity=_effective_phase_weight(ca) if ca.get('kind')=='action' else .78
    # 0.90 marks an analyst-hypothesized mechanism; not observed causality.
    return min(74,round(100*bottleneck*(.55+.45*maturity)*.90))


def _finding(rule:str, typ:str, title:str, text:str, bridge:dict,
             a: tuple[Evidence,dict],b:tuple[Evidence,dict], version:str) -> Finding:
    ea,ca=a;eb,cb=b
    proof=(_cit(ea,ca),_cit(eb,cb))
    ids=tuple(sorted((ea.id,eb.id)))
    claims=tuple(sorted((ca.get('claim_id') or 'none:'+ea.id,cb.get('claim_id') or 'none:'+eb.id)))
    inference_id='f:'+_hash(rule,bridge['id'],*claims)
    return Finding(id=inference_id,rule=rule,type=typ,status='conditional_hypothesis',
        title=title,inference=text,
        logic=f"{ca.get('object')} --[{bridge['relation']}; MODEL ASSUMPTION]--> {cb.get('object')}",
        assumptions=(bridge['condition'],'The two sources refer to comparable places, periods and affected activities.',
                     'Publisher separation does not by itself prove evidence independence.'),
        counter_case=bridge['risk_if_absent'],disconfirmation_test=bridge['indicator'],
        evidence_ids=ids,claim_ids=claims,proof=proof,
        support_index=_score(ea,ca,eb,cb,rule),
        caveat='No causal effect has been inferred as observed. A verified source can describe an unimplemented plan.',
        model_version=version,verified_anchor_count=2,publisher_family_count=2)


def generate_motifs(evidences:list[Evidence],bridges:list[dict],version:str,max_per_bridge=6) -> list[Finding]:
    indexed=defaultdict(list)
    for e in evidences:
        if e.admission!='keep':continue
        for c in e.claims:
            if not _verified(e,c) or not c.get('object'):continue
            indexed[c['object']].append((e,c))
    for items in indexed.values():
        items.sort(key=lambda x:(-_weight(*x),-_phase_weight(x[1]),x[0].id))
    findings=[]
    for bridge in bridges:
        left=indexed.get(bridge['from'],[])[:70]
        right=indexed.get(bridge['to'],[])[:70]
        out=[]
        for a,b in product(left,right):
            ea,ca=a;eb,cb=b
            if not _family_independent(ea,eb) or not _same_scope(ca,cb):continue
            separation=_date_days(_date(ca),_date(cb))
            if separation is None or separation>1095:continue
            rel=bridge['relation']
            # Identify *different roles*, never simply add topic co-occurrences.
            if rel in ('enables','substitutes'):
                if (ca.get('kind')!='action' or ca.get('mechanism') not in CAPACITY_ACTS
                    or ca.get('direction')!='expands'):continue
                if cb.get('kind')!='diagnosis' or cb.get('mechanism') not in {'assesses','measures','evaluates','detects'}:continue
                if cb.get('direction') not in {'becomes_conditional','becomes_contested','contracts','unchanged','expands'}:continue
                if _status(ca) in UNREALIZED or _projected_action(ca):rule='R_IMPLEMENTATION_GAP';typ='risk_and_opportunity'
                else:rule='R_CONDITIONAL_ENABLER';typ='opportunity'
                word='substitution' if rel=='substitutes' else 'capacity expansion'
                title=f"Conditional {word}: {bridge['from']} → {bridge['to']}"
                text=(f"The source reports {ca.get('mechanism')} of {bridge['from']} ({_status(ca)}); a separate study assesses {bridge['to']} "
                      f"({cb.get('direction')}). This combination creates a TESTABLE opportunity, not a proven outcome, "
                      f"if {bridge['condition']}.")
            elif rel=='constrains':
                if (ca.get('kind')!='action' or ca.get('mechanism') not in RESTRICT_ACTS
                     or ca.get('direction') not in {'contracts','becomes_conditional','becomes_contested'}):continue
                if cb.get('kind')!='diagnosis' or cb.get('direction') not in {'becomes_conditional','contracts','becomes_contested','unchanged','expands'}:continue
                rule='R_RESTRICTION_EXPOSURE';typ='risk'
                title=f"Conditional restriction exposure: {bridge['from']} → {bridge['to']}"
                text=(f"Documented {bridge['from']} action ({_status(ca)}) could constrain {bridge['to']} "
                      f"under the specified bridge. This is an exposure hypothesis, not evidence that projects have already been harmed.")
            else:continue
            out.append(_finding(rule,typ,title,text,bridge,a,b,version))
        # Aggregate a SET of findings into a coherent mechanism hypothesis.
        # Repeated pairs are not new trends, and the same original work is never
        # counted twice. Keep only a bounded, auditable sample of distinct works.
        groups=defaultdict(list)
        for item in out:
            scope=_scope_key({'scope':item.proof[0].get('scope')})
            groups[(item.rule,scope)].append(item)
        for (rule,scope),samples in sorted(groups.items()):
            samples.sort(key=lambda f:(-f.support_index,f.id))
            best=samples[0]
            used_records=set();proof=[];families=set()
            # Best pair always gives two distinct publisher families.
            for sample in samples:
                for row in sample.proof:
                    if row['record'] in used_records:continue
                    if len(proof)>=min(12,2*max_per_bridge):break
                    # Multiple records from one publisher do not strengthen corroboration.
                    if row['source_family'] in families:continue
                    proof.append(row)
                    used_records.add(row['record']);families.add(row['source_family'])
                if len(proof)>=min(12,2*max_per_bridge):break
            if len(proof)<2:continue
            # Publisher-deduped corroboration gives bounded uplift (+<=12).
            score=round(best.support_index+(74-best.support_index)*min(.50,.06*(len(families)-2)))
            findings.append(replace(best,id='f:'+_hash(rule,bridge['id'],scope),
                evidence_ids=tuple(sorted(x['record'] for x in proof)),
                claim_ids=tuple(sorted(x['claim'] or x['record'] for x in proof)),
                proof=tuple(proof),support_index=score,
                verified_anchor_count=len(proof),publisher_family_count=len(families),
                caveat=best.caveat+' Additional records are separate publisher reports, not proven independent datasets.'))
    return sorted(findings,key=lambda f:(-f.support_index,f.id))



def generate_countervailing(evidences:list[Evidence],bridges:list[dict],version:str,max_per_target:int=2) -> list[Finding]:
    """Three-premise interaction: enabling lever + constraining lever + observed target.

    Never outputs an observed net impact. A measured target state is a separate
    premise, not automatically the result of either intervention.
    """
    byobj=defaultdict(list)
    for e in evidences:
        for c in e.claims:
            if _verified(e,c) and c.get('object'):byobj[c['object']].append((e,c))
    bytarget=defaultdict(lambda:{'enables':[],'constrains':[]})
    for br in bridges:
        if br['relation'] in {'enables','constrains'}:
            bytarget[br['to']][br['relation']].append(br)
    findings=[]
    for target,relations in bytarget.items():
        local=[]
        for enable,limit in product(relations['enables'],relations['constrains']):
            e_pool=[(e,c) for e,c in byobj[enable['from']]
                    if c.get('kind')=='action' and c.get('direction')=='expands'
                    and c.get('mechanism') in CAPACITY_ACTS]
            r_pool=[(e,c) for e,c in byobj[limit['from']]
                    if c.get('kind')=='action'
                    and c.get('direction') in {'contracts','becomes_conditional','becomes_contested'}
                    and c.get('mechanism') in RESTRICT_ACTS]
            d_pool=[(e,c) for e,c in byobj[target]
                    if c.get('kind')=='diagnosis' and c.get('mechanism') in {'assesses','measures','detects','evaluates'}]
            for a,b,c in product(e_pool[:30],r_pool[:30],d_pool[:30]):
                ea,ca=a;eb,cb=b;ec,cc=c
                if len({ea.source_family,eb.source_family,ec.source_family})!=3:continue
                if 'unknown' in (ea.source_family,eb.source_family,ec.source_family):continue
                if len({ea.source_key,eb.source_key,ec.source_key})!=3:continue
                if not (_same_scope(ca,cb) and _same_scope(cb,cc)):continue
                ds=[_parse_date(_date(cl)) for cl in (ca,cb,cc)]
                if any(v is None for v in ds):continue
                if (max(ds)-min(ds)).days>1095:continue
                body=(f'Verified sources separately document an enabling intervention in {enable["from"]}, '
                    f'a potentially constraining intervention in {limit["from"]}, and '
                    f'an assessment of {target}. The combined direction is unresolved: '
                    f'implementation, sequencing, and the two conditional bridges determine the outcome.')
                proof=(_cit(ea,ca),_cit(eb,cb),_cit(ec,cc))
                idx=min(70,round(100*.82*min(_weight(ea,ca),_weight(eb,cb),_weight(ec,cc))
                        *(.55+.45*min(_phase_weight(ca),_phase_weight(cb)))))
                sc=_scope_key(ca)
                local.append(Finding(
                    id='f:'+_hash('COUNTERVAIL',enable['id'],limit['id'],sc),
                    rule='R_COUNTERVAILING_FORCES',type='risk_and_opportunity',
                    status='conditional_hypothesis',title=f'Competing forces on {target}',
                    inference=body,
                    logic=f'{enable["from"]} --enables?--> {target} <--constrains?-- {limit["from"]}',
                    assumptions=(enable['condition'],limit['condition'],'Interventions address the same population and timeframe.'),
                    counter_case='The interventions may be non-overlapping, unequally implemented, or offset one another.',
                    disconfirmation_test=enable['indicator']+'; '+limit['indicator'],
                    evidence_ids=tuple(sorted({ea.id,eb.id,ec.id})),
                    claim_ids=tuple(sorted(cl.get('claim_id','') for cl in (ca,cb,cc))),
                    proof=proof,support_index=idx,
                    caveat='Causal links are specified bridge hypotheses. Opposing actions do not establish an observed net effect.',
                    model_version=version,verified_anchor_count=3,publisher_family_count=3))
        dedup={}
        for f in sorted(local,key=lambda x:(-x.support_index,x.id)):
            dedup.setdefault(f.id,f)
        findings.extend(list(dedup.values())[:max_per_target])
    return sorted(findings,key=lambda f:(-f.support_index,f.id))

def generate_tensions(evidences:list[Evidence],version:str,max_per_object=2) -> list[Finding]:
    """Opposite measured directions = measurement tension, not logical contradiction."""
    indexed=defaultdict(lambda:{'expands':[],'contracts':[]})
    for e in evidences:
        for c in e.claims:
            if not _verified(e,c):continue
            if c.get('kind')!='diagnosis' or c.get('mechanism') not in MEASURED:continue
            d=c.get('direction')
            if d in ('expands','contracts'):indexed[c.get('object','')][d].append((e,c))
    out=[]
    for obj, groups in indexed.items():
        for a,b in product(groups['expands'][:20],groups['contracts'][:20]):
            ea,ca=a;eb,cb=b
            if not _family_independent(ea,eb) or not _same_scope(ca,cb):continue
            proof=(_cit(ea,ca),_cit(eb,cb))
            claims=tuple(sorted((ca.get('claim_id',''),cb.get('claim_id',''))))
            out.append(Finding(id='f:'+_hash('TENSION',*claims),rule='R_DIRECTIONAL_TENSION',type='uncertainty',
                status='requires_reconciliation',title=f'Conflicting directional measurements: {obj}',
                inference=f'Different published measurements point in different directions for {obj}; check metrics, reference dates and population before asserting an underlying reversal.',
                logic='measured(expands) ∧ measured(contracts) ∧ same_scope → measurement_tension',
                assumptions=('Measurement methods, baselines and samples are comparable.',),
                counter_case='The directions may differ because the measures or reference periods are incomparable.',
                disconfirmation_test='Reconcile datasets and repeat under a common, explicitly defined metric.',
                evidence_ids=tuple(sorted((ea.id,eb.id))),claim_ids=claims,proof=proof,
                support_index=min(74,round(75*min(_weight(ea,ca),_weight(eb,cb)))),
                caveat='Not an established contradiction or time-series reversal.',model_version=version,
                verified_anchor_count=2,publisher_family_count=2))
        # intentionally no implicit causal generalization
    by=defaultdict(list)
    for f in out:by[f.title].append(f)
    return [f for key,fs in by.items() for f in sorted(fs,key=lambda x:-x.support_index)[:max_per_object]]


def generate_convergence(evidences:list[Evidence],version:str) -> list[Finding]:
    """Repeated independent measurements over time support WATCH STATUS, not a numeric slope."""
    indexed=defaultdict(list)
    for e in evidences:
        for c in e.claims:
            if not _verified(e,c):continue
            if c.get('kind')=='diagnosis' and c.get('mechanism')=='measures' and c.get('direction') in ('expands','contracts'):
                indexed[(c.get('object'),c['direction'],str(c.get('scope') or ''))].append((e,c))
    out=[]
    for (obj,d,scope),items in indexed.items():
        family={}
        for e,c in sorted(items,key=lambda ec:(-_weight(*ec),ec[0].id)):
            if e.source_family not in family: family[e.source_family]=(e,c)
        chosen=list(family.values())
        if len(chosen)<3:continue
        dates=[dtv for e,c in chosen if (dtv:=_parse_date(_date(c))) is not None]
        if len(dates)<3 or (max(dates)-min(dates)).days<90:continue
        chosen=sorted(chosen,key=lambda ec:-_weight(*ec))[:6]
        proof=tuple(_cit(e,c) for e,c in chosen)
        ids=tuple(sorted(e.id for e,c in chosen))
        claims=tuple(sorted(c.get('claim_id','') for e,c in chosen))
        out.append(Finding(id='f:'+_hash('CONVERGENCE',obj,d,scope),rule='R_MEASURED_CONVERGENCE',
             type='trend_candidate',status='monitoring_candidate',title=f'Repeated measured {d} signals: {obj}',
             inference=f'At least three publisher-separated measured claims describe {d} for {obj}, across at least 90 days. This warrants a longitudinal test but does not establish a statistical trend.',
             logic='independent_measurements≥3 ∧ time_span≥90d ∧ same_object/scope/direction → trend_test_candidate',
             assumptions=('Metrics and baselines are comparable over time.','Source families do not repackage one dataset.'),
             counter_case='Different studies may measure different populations, dates or quantities.',
             disconfirmation_test='Build a harmonised measured time series; compare against a stable baseline and missing-data controls.',
             evidence_ids=ids,claim_ids=claims,proof=proof,
             support_index=min(74,round(60+2*len(chosen))),
             caveat='Number of publications is not trend acceleration.',model_version=version,
             verified_anchor_count=len(chosen),publisher_family_count=len(chosen)))
    return sorted(out,key=lambda f:(-f.support_index,f.id))


def _scenario_proxies(byobj: dict, rules: list[dict],limit:int=3) -> list[dict]:
    candidates=[]
    for spec in rules:
        for e,c in byobj[spec['object']]:
            if spec.get('kind') and spec['kind']!=c.get('kind'):continue
            for field in ('direction','status','mechanism'):
                allowed=spec.get(field)
                if allowed is None:continue
                if c.get(field) not in (allowed if isinstance(allowed,list) else [allowed]):break
            else:
                candidates.append((e,c))
    candidates.sort(key=lambda pair:(-_weight(*pair),pair[0].id))
    chosen=[];seen=set()
    for e,c in candidates:
        if e.source_family in seen:continue
        seen.add(e.source_family)
        chosen.append({'record_id':e.id,'claim_id':c.get('claim_id',''),
            'observed_claim':c.get('text',''), 'status':c.get('status',''),
            'publisher':e.publisher,'source_url':e.url,'verification':verification_status(e)})
        if len(chosen)>=limit:break
    return chosen


def generate_scenarios(evidences:list[Evidence], axes:list[dict],version:str) -> list[dict]:
    if len(axes)!=3 or len({a['id'] for a in axes})!=3:raise ValueError('Exactly three named scenario axes required')
    tags=[set(a['object_tags']) for a in axes]
    if any(tags[i]&tags[j] for i in range(3) for j in range(i+1,3)):
        raise ValueError('Scenario axes overlap in object tags; redesign axes before generating eight worlds')
    byobj=defaultdict(list)
    for e in evidences:
        for c in e.claims:
            if _verified(e,c):byobj[c.get('object')].append((e,c))
    from .deductions import SCENARIO_COMBINATIONS
    worlds=[]
    for signs in product((False,True),repeat=3):
        bits=''.join('1' if p else '0' for p in signs)
        diagnostic=[]; relevant=[]
        for a,s in zip(axes,signs):
            proxies=a.get('proxy_rules') or {}
            matching=_scenario_proxies(byobj,proxies.get('high' if s else 'low',[]))
            opposing=_scenario_proxies(byobj,proxies.get('low' if s else 'high',[]))
            relevant.extend(x['record_id'] for x in matching+opposing)
            diagnostic.append({'axis':a['id'],'state':'high' if s else 'low',
                'consistent_proxies':matching,'countervailing_proxies':opposing,
                'interpretation':'Proxies are evidence on indicators, not proof of the scenario state.'})
        narr='; '.join(f"{a['name']}: {a['high_implication'] if hi else a['low_implication']}" for a,hi in zip(axes,signs))
        world_title,interaction,emergence,choice=SCENARIO_COMBINATIONS[bits]
        aligned=sum(len(x['consistent_proxies']) for x in diagnostic)
        opposed=sum(len(x['countervailing_proxies']) for x in diagnostic)
        if any(not x['consistent_proxies'] and not x['countervailing_proxies'] for x in diagnostic):
            proxy_state='coverage_gap'
        elif aligned and opposed:
            proxy_state='mixed_indicators'
        elif aligned and not opposed:
            proxy_state='indicators_aligned'
        elif opposed and not aligned:
            proxy_state='indicators_opposed'
        else:
            proxy_state='no_indicator_evidence'
        worlds.append({
          'verified_proxy_diagnostic':{'aligned':aligned,'opposed':opposed,
             'state':proxy_state,
             'interpretation':'Qualitative indicator alignment only; NOT a scenario likelihood or an observed future.'},
          'id':'S'+bits,
          'emergent_world':world_title,
          'interaction_inference':interaction,
          'second_order_dynamics':emergence,
          'strategic_choice':choice,
          'axis_states':{a['id']:'high' if s else 'low' for a,s in zip(axes,signs)},
          'scenario_name':' / '.join(('OPEN' if s else 'CONSTRAINED')+' '+a['id'] for a,s in zip(axes,signs)),
          'conditional_narrative':'IF '+', AND '.join(a['high'] if s else a['low'] for a,s in zip(axes,signs))+'; THEN '+narr+'.',
          'tests':[{'axis':a['id'],'watch':a['high_test'] if s else a['low_test']} for a,s in zip(axes,signs)],
          'axis_evidence_diagnostics':diagnostic,
          'relevant_evidence_ids':sorted(set(relevant)),
          'status':'exploratory_not_forecast','relative_likelihood':None,
          'caution':'Axes are model-separated, NOT demonstrated statistically independent. Proxy signals may conflict. A scenario is a conditional stress test, not a prediction.',
          'verification_policy':'Workbook-verified claims only; a proxy is not an outcome.',
          'version':version})
    return worlds


def delta(previous:list[dict], current:list[dict]) -> dict:
    prev={x['id']:x for x in previous}
    new={x['id']:x for x in current}
    return {'added':sorted(new.keys()-prev.keys()),
            'withdrawn_from_current_run':sorted(prev.keys()-new.keys()),
            'revised':sorted(i for i in prev.keys()&new.keys() if prev[i]!=new[i]),
            'unchanged':len([i for i in prev.keys()&new.keys() if prev[i]==new[i]]),
            'warning':'A withdrawn inference is not a disproved prediction; it may reflect source changes, verification or rule edits.'}
