"""Strict evidence-gated, structured-rule, defeasible foresight hypothesis synthesis.

Everything here reads the upstream Excel data; nothing alters upstream state.
The report's numeric priority is an ordinal ANALYST REVIEW index, never probability.
No LLM or unreviewed semantic invention is used; typed bridges are explicit assumptions.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from hashlib import sha256
from itertools import product
import re
from .adapter import Evidence
from . import deductions
from .core import (_cit, _weight, _verified, _same_scope, _parse_date, _date,
                   _phase_weight, _projected_action, _family_independent,
                   CAPACITY_ACTS, RESTRICT_ACTS, UNREALIZED, generate_scenarios)

DIAGNOSES={'assesses','measures','detects','evaluates'}
ADVERSE={'becomes_conditional','becomes_contested','contracts'}
HUMAN_DIRECTION={'expands':'expansion','contracts':'contraction','becomes_contested':'contestation',
                 'becomes_conditional':'conditionality','unchanged':'persistence'}
CATEGORY={'ai':'AI','digital':'Digital','compute':'Computing','chips':'Semiconductors','research':'Research',
          'horizon':'EU research programmes','funding':'Funding','innovation':'Innovation','finance':'Investment',
          'industrial':'Industry','materials':'Materials','green':'Green transition','talent':'Research talent',
          'datacentre':'Data centres','cybersecurity':'Cybersecurity','health':'Health data',
          'quantum':'Quantum','research_security':'Research security','export_control':'Export controls',
          'defence':'Defence innovation','critical_infrastructure':'Infrastructure resilience',
          'methods':'Foresight methods','goal':'Strategic autonomy'}


def pretty(x):
    return deductions.name(x)


def _sid(*keys):
    return sha256('|'.join(str(k) for k in keys).encode('utf8')).hexdigest()[:16]


def _p(e,c):
    p=_cit(e,c)
    p['title']=e.title
    p['document_date']=e.date
    p['record_key']=e.source_key
    return p


def _scope(c):
    sc=c.get('scope') or {}
    return sc.get('level','')+':'+','.join(sorted(sc.get('countries') or []))


def _compatible(pairs,max_span=1095):
    """No unsupported time or place matches; no same-document/source-family joins."""
    if any(not _verified(e,c) or not c.get('text') or not c.get('object') for e,c in pairs):return False
    if len({e.source_key for e,c in pairs})!=len(pairs):return False
    if len({e.source_family for e,c in pairs})!=len(pairs):return False
    if 'unknown' in {e.source_family for e,c in pairs}:return False
    if any(not _same_scope(pairs[0][1],c) for _,c in pairs[1:]):return False
    dates=[_parse_date(_date(c)) for _,c in pairs]
    return all(dates) and (max(dates)-min(dates)).days<=max_span


def _score(pairs,penalty=1):
    if not _compatible(pairs):return 0
    bottleneck=min(_weight(e,c) for e,c in pairs)
    phases=[_phase_weight(c) if not _projected_action(c) else min(.42,_phase_weight(c))
            for e,c in pairs if c.get('kind')=='action']
    maturity=min(phases) if phases else .83
    # Deliberate ceiling. Never interpret as probability or causal confidence.
    return min(74,round(100*bottleneck*(.52+.48*maturity)*penalty))


def _mk(category,key,title,inference,mechanism,pairs,conditions,alternative,test,priority,rule):
    proof=[_p(e,c) for e,c in pairs]
    return {'id':category[:2].upper()+'-'+_sid(category,*key),'category':category,'rule':rule,'rule_key':list(key),
      'title':title,'inference':inference,'mechanism':mechanism,'conditions':conditions,
      'counter_explanation':alternative,'disconfirmation_test':test,
      'proof':proof,'priority':priority,'scope':_scope(pairs[0][1]),
      'source_families':len({e.source_family for e,c in pairs}),
      'epistemic_status':'verified_anchored_structural_inference',
      'caveat':'Verified describes the underlying source assessment, not independent proof of the inferred causal connection.',
      'subject':pairs[-1][1]['object'] if category!='trends' else pairs[0][1]['object']}


def _select(records,limit=28,max_per_topic=6):
    """Topic diversification reduces dominance by one big document family."""
    items=sorted(records,key=lambda v:(-v['priority'],-v['source_families'],v['id']))
    out=[];seen=set();by_topic=defaultdict(int)
    for v in items:
        topic=v['subject'].split('.')[0]
        if v['id'] in seen or by_topic[topic]>=max_per_topic:continue
        out.append(v);seen.add(v['id']);by_topic[topic]+=1
        if len(out)>=limit:break
    return out


def _index(evidences):
    index=defaultdict(list)
    for e in evidences:
        for c in e.claims:
            if _verified(e,c) and c.get('object') and c.get('text') and _parse_date(_date(c)):
                index[c['object']].append((e,c))
    for arr in index.values():
        arr.sort(key=lambda pair:(-_weight(*pair),-( _parse_date(_date(pair[1])) or date.min).toordinal(),pair[0].id))
    return index


def directional_trends(index,limit=28):
    """Minimum 3 publishers and >=45-day spread; diagnose group, not a slope."""
    out=[]
    for object_,rows in sorted(index.items()):
        for direction in ('expands','contracts','becomes_conditional','becomes_contested'):
            chosen=[];seen=set()
            for e,c in rows:
                if c.get('kind')!='diagnosis' or c.get('mechanism') not in DIAGNOSES or c.get('direction')!=direction:continue
                if e.source_family in seen:continue
                if chosen and not _same_scope(chosen[0][1],c):continue
                chosen.append((e,c));seen.add(e.source_family)
                if len(chosen)>=7:break
            if len(chosen)<3:continue
            dates=[_parse_date(_date(c)) for e,c in chosen]
            if (max(dates)-min(dates)).days<45:continue
            opposite=[(e,c) for e,c in rows if c.get('kind')=='diagnosis'
                      and c.get('mechanism') in DIAGNOSES and c.get('direction')!=direction
                      and _same_scope(chosen[0][1],c) and e.source_family not in seen]
            # Measured/evaluated proof is preferable to interpretation-only convergence.
            technical=sum(c.get('mechanism') in {'measures','evaluates','detects'} for e,c in chosen)
            q=min(_weight(e,c) for e,c in chosen)
            idx=min(74,round(52+q*14+min(6,len(chosen)-3)*1.4+2*technical/len(chosen)))
            title=f"{pretty(object_)} — {HUMAN_DIRECTION[direction].capitalize()} across independent assessments"
            inference=(f"At least {len(chosen)} separate admitted publication families describe {HUMAN_DIRECTION[direction]} "
                       f"in {pretty(object_)} over a period of {(max(dates)-min(dates)).days} days. "
                       f"The aligned direction identifies a structural pressure across the evidence base. A shared quantitative rate or underlying cause is not established.")
            alternative=(f"{len(opposite)} other admitted claim(s) report different directions. " if opposite else '')+(
                'Measures, study populations and reporting incentives may differ; reports may share underlying data.')
            out.append(_mk('trends',(object_,direction,_scope(chosen[0][1])),title,inference,
                'The same system variable shows a repeatable direction across distinct dated evidence; this is a temporal evidence network, not a single-source assertion.',
                chosen[:5],['Maintain common geography and observation window.',
                'Distinguish measured outcomes from assessments and announcements.',
                'Compare underlying measurements before estimating a common slope.'],
                alternative,'Compare independent longitudinal indicators using harmonized baselines, populations and measurement definitions.',
                idx,'T1_CONVERGENT_VERIFIED_CLAIMS'))
    # Prefer one dominant direction per topic; other direction may be valuable only when explicit tensions.
    best={}
    for v in sorted(out,key=lambda v:-v['priority']): best.setdefault((v['subject'],v['scope']),v)
    return _select(list(best.values()),limit,3)



def topological_trends(index, bridges, limit=28):
    """Infer emerging system directions from converging drivers, not keyword counts.

    Fan-in motif A -> Z <- B requires three different verified publications:
    1 action in driver A, 1 action in driver B, 1 diagnosis of the SAME target Z.
    Both model edges are explicit, separately inspectable hypotheses.
    This is a formal topology inference, not a proven causal effect.
    """
    incoming=defaultdict(list)
    for b in bridges:
        if b['relation'] in {'enables','substitutes'}:
            incoming[b['to']].append(b)
    out=[]
    for target,edges in sorted(incoming.items()):
        if len(edges)<2:continue
        diagnostics=[p for p in index.get(target,[])[:45]
                     if p[1].get('kind')=='diagnosis' and p[1].get('mechanism') in DIAGNOSES]
        if not diagnostics:continue
        for i,first in enumerate(edges):
            for second in edges[i+1:]:
                if first['from']==second['from']:continue
                aa=[p for p in index.get(first['from'],[])[:28]
                    if p[1].get('kind')=='action' and p[1].get('mechanism') in CAPACITY_ACTS and p[1].get('direction')=='expands']
                bb=[p for p in index.get(second['from'],[])[:28]
                    if p[1].get('kind')=='action' and p[1].get('mechanism') in CAPACITY_ACTS and p[1].get('direction')=='expands']
                if not aa or not bb:continue
                aa=[p for p in aa if _edge_fit(p,first)]
                bb=[p for p in bb if _edge_fit(p,second)]
                if not aa or not bb:continue
                best=None
                for pair in product(aa[:10],bb[:10],diagnostics[:12]):
                    if not _compatible(pair):continue
                    value=_score(pair,penalty=.96)
                    if not best or value>best[0]:best=(value,pair)
                if not best:continue
                pr,pairs=best
                if pr<20:continue
                d1,d2,z=pretty(first['from']),pretty(second['from']),pretty(target)
                title=f"Converging change: {d1} + {d2} -> {z}"
                insight=(f"The evidence establishes separate interventions in {d1} and {d2}, "
                    f"alongside an independent assessment of {z}. The system-level trend is "
                    f"convergence of two capacity-building forces on a common outcome: {z}. "
                    f"The two routes expose a shared dependency; realization of their combined downstream effect depends on specific transmission conditions, "
                    f"which are tested separately below.")
                obj=_mk('trends',(first['id'],second['id'],_scope(pairs[0][1])),'',
                    insight,f"FAN-IN topology: {d1} --enables--> {z} <--enables-- {d2}. "
                    "Two different upstream actions target the same observed system condition; this is not based on keyword co-occurrence.",
                    list(pairs),[first['condition'],second['condition'],
                        'Both pressures must reach comparable downstream populations and dates.'],
                    'One upstream pathway could be delayed, substituted, or offset; the target assessment may not describe the beneficiaries of either action.',
                    'Route A: '+first['indicator']+'. Route B: '+second['indicator']+'. Compare these with an independently measured target outcome.',
                    pr,'T2_CONVERGENT_CAUSAL_TOPOLOGY')
                obj['title']=title
                obj['topology']='fan_in'
                obj['network_path']=[first['from'],target,second['from']]
                out.append(obj)
    # Select no more than two topology variants for the same target to avoid redundant lists.
    chosen=[];bytarget=defaultdict(int)
    for x in sorted(out,key=lambda z:(-z['priority'],z['id'])):
        if bytarget[x['subject']]>=2:continue
        bytarget[x['subject']]+=1
        chosen.append(x)
    return _select(chosen,limit,6)


def trends(index,bridges,limit=28):
    # Both temporal-directional and genuinely causal-topological trends are full
    # trend inferences, not separate quality grades. Evidence limits still apply.
    structural=topological_trends(index,bridges,limit)
    directional=directional_trends(index,limit)
    # Give causal topological reasoning substantial representation (at least 20
    # when available). These are two complementary rules at the same inferential
    # level: no vague or 'second-class' trend category is produced.
    top_count=min(len(structural),max(0,limit-8))
    selected=structural[:top_count]
    seen={x['id'] for x in selected}
    other=sorted(structural[top_count:]+directional,key=lambda x:(-x['priority'],x['id']))
    for x in other:
        if x['id'] not in seen:
            selected.append(x);seen.add(x['id'])
        if len(selected)>=limit:break
    return selected



# Weakly coupled sectors must NOT be stitched together just because they share
# an abstract object tag. These positive-domain constraints target bridges that
# otherwise generate high-priority but semantically unsupported combinations.
SPECIFIC_TARGET_TERMS = {
    'green.innovation': ('green','climate','clean energy','renewable','decarbon','environment','circular','emission','low-carbon','sustainab'),
    'innovation.dual_use': ('dual-use','dual use','defence','defense','security','military'),
    'ai.research_use': ('artificial intelligence',' ai ','machine learning','dataset','data infrastructure','model'),
    'industrial.technology_complexity': ('chip','semiconductor','technology','manufactur','fabricat','industrial'),
}


def _edge_fit(pair, bridge):
    """Demand substantive target-sector relevance in an upstream premise.

    Causal direction is still a bridge hypothesis; this check merely blocks a
    plainly unrelated publication from being interpreted as an intervention in
    the relevant sector (e.g. defence finance = green finance). When the source
    *is already about the target* its object tag is itself a typed admission.
    """
    _, c = pair
    target=bridge['to']
    terms=SPECIFIC_TARGET_TERMS.get(target)
    if terms is None:return True
    if c.get('object')==target:return True
    material=' '+str(c.get('text') or '').lower()+' '
    return any(k in material for k in terms)

def _bridge_pool(index,bridge):
    left=[(e,c) for e,c in index.get(bridge['from'],[])[:70]
          if c.get('kind')=='action' and c.get('mechanism') in CAPACITY_ACTS|RESTRICT_ACTS
          and (c.get('direction')=='expands' if bridge['relation']!='constrains'
               else c.get('direction') in ADVERSE)]
    right=[(e,c) for e,c in index.get(bridge['to'],[])[:70]
           if c.get('kind')=='diagnosis' and c.get('mechanism') in DIAGNOSES]
    left=[p for p in left if _edge_fit(p,bridge)]
    return left,right


def opportunities_and_risks(index,bridges,limit=28):
    opp=[];risk=[]
    for b in bridges:
        left,right=_bridge_pool(index,b)
        usable=[]
        for a,c in product(left[:45],right[:45]):
            if _compatible([a,c]):
                usable.append((a,c))
        usable.sort(key=lambda z:(-_score(z),z[0][0].id,z[1][0].id))
        if not usable:continue
        # Keep a few sources per mechanism without treating correlated publication counts as numeric confirmation.
        good=usable[0]
        a,z=good; ea,ca=a;ez,cz=z
        pairs=[a,z]
        strength=_score(pairs)
        if strength<=0:continue
        fromlabel=pretty(b['from']); tolabel=pretty(b['to'])
        maturity=ca.get('status','unknown')
        if b['relation'] in ('enables','substitutes'):
            title=f"Capability pathway: {fromlabel} -> {tolabel}"
            insight=(f"A workbook-verified source reports an enabling measure in {fromlabel} "
                     f"(recorded status: {maturity}); a separate verified assessment concerns {tolabel}. "
                     f"The two findings identify an actionable capability pathway to {tolabel}. "
                     f"The causal transmission condition is: {b['condition']}. "
                     "The evidence establishes the intervention and the assessed target, not a delivered outcome.")
            opp.append(_mk('opportunities',(b['id'],_scope(ca)),title,insight,
                 f"CAUSAL BRIDGE: {fromlabel} -> {tolabel}. The link is a testable mechanism, distinct from the verified premise claims.",
                 pairs,[b['condition'],'The targeted groups and implementation period must overlap.',
                        'Deployment, uptake and measurable downstream outcomes must be checked separately.'],
                 b['risk_if_absent'],b['indicator'],strength,'O1_VERIFIED_ACTION_AND_DIAGNOSIS'))
            if maturity in UNREALIZED or _projected_action(ca) or cz.get('direction') in ADVERSE:
                title=f"Implementation exposure: {fromlabel} -> {tolabel}"
                inference=(f"Even if the reported {fromlabel} initiative proceeds, the separately documented "
                   f"condition of {tolabel} creates implementation or absorption risk. The verified material "
                   f"does not show that proposed capacity has already solved this problem. "
                   f"The decisive dependency is: {b['condition']}.")
                risk.append(_mk('risks',(b['id'],_scope(ca),'gap'),title,inference,
                   f"Reported investment or institutional action -> implementation and adoption bottleneck -> uncertain effect on {tolabel}.",
                   pairs,['Upstream action and downstream diagnosis must concern compatible populations.',
                          'A funded proposal is not evidence of delivery.'],
                   'The initiative may be operating effectively and already changing outcomes, but the reviewed sources do not independently establish that.',
                   b['indicator'],max(1,strength-3),'R1_IMPLEMENTATION_AND_ABSORPTION_GAP'))
        elif b['relation']=='constrains':
            title=f"Restriction exposure: {fromlabel} -> {tolabel}"
            inference=(f"A separately reported restrictive action in {fromlabel} may affect {tolabel} "
             f"if {b['condition']}. The evidence establishes the action and the relevance of the target domain, "
             "not that net harm has already occurred.")
            risk.append(_mk('risks',(b['id'],_scope(ca)),title,inference,
                 f"Restriction or screening in {fromlabel} -- potentially limits -> {tolabel}.",
                 pairs,[b['condition'],'Affected partnerships or transfers must be verified in the relevant jurisdiction.'],
                 b['risk_if_absent'],b['indicator'],strength,'R2_CONDITIONAL_RESTRICTION_EXPOSURE'))
    return _select(opp,limit,5),_select(risk,limit,5)


def congestion_disruptions(index, bridges, limit=28):
    """Three verified claims reveal a shared stressed chokepoint.

    Motif A --> Z <-- B; A and B are expanding interventions while Z has a
    separately diagnosed adverse state. Both typed edges must exist in the
    version-controlled causal-bridge registry. A crowding shock is an inference,
    never an assertion that saturation has already been measured.
    """
    incoming=defaultdict(list)
    for b in bridges:
        if b['relation'] in {'enables','substitutes'}:
            incoming[b['to']].append(b)
    candidates=[]
    for target,links in sorted(incoming.items()):
        adverse=[pair for pair in index.get(target,[])[:60]
                 if pair[1].get('kind')=='diagnosis'
                 and pair[1].get('mechanism') in DIAGNOSES
                 and pair[1].get('direction') in ADVERSE]
        if not adverse:continue
        for i,a in enumerate(links):
            for b in links[i+1:]:
                if a['from']==b['from']:continue
                left=[p for p in index.get(a['from'],[])[:36]
                      if p[1].get('kind')=='action' and p[1].get('mechanism') in CAPACITY_ACTS
                      and p[1].get('direction')=='expands' and _edge_fit(p,a)]
                right=[p for p in index.get(b['from'],[])[:36]
                       if p[1].get('kind')=='action' and p[1].get('mechanism') in CAPACITY_ACTS
                       and p[1].get('direction')=='expands' and _edge_fit(p,b)]
                if not left or not right:continue
                best=None
                for pairs in product(left[:12],right[:12],adverse[:12]):
                    if not _compatible(pairs):continue
                    score=_score(pairs,penalty=.84)
                    if best is None or score>best[0]:best=(score,pairs)
                if not best or best[0]<18:continue
                score,pairs=best
                l,r,t=pretty(a['from']),pretty(b['from']),pretty(target)
                entry=_mk('disruptions',(a['id'],b['id'],_scope(pairs[0][1]),'chokepoint'),
                    f'Convergent bottleneck: {l} + {r} -> {t}',
                    f'Two separate programmes expand {l} and {r} while a third independent report '
                    f'identifies an adverse condition at their common downstream interface, {t}. '
                    f'The combined pressure creates a potential discontinuity: system performance becomes '
                    f'limited by the shared interface rather than by either upstream input.',
                    f'STRESSED FAN-IN: {l} -> {t} <- {r}. Distinct upstream routes converge on '
                    f'one diagnosed pressure point. A failure or congestion at the centre can transmit '
                    f'back to both routes; no numerical capacity threshold is presumed.',
                    list(pairs),[a['condition'],b['condition'],
                        'Both interventions must place material, overlapping demand on the same capacity-limited interface.'],
                    'The two programmes may serve different beneficiaries, create additional capacity '
                    'rather than use it, or relieve rather than intensify the reported constraint.',
                    f'Directly measure shared-interface queueing, utilization and access rationing; '
                    f'check {a["indicator"]}; {b["indicator"]}.',
                    score,'D2_CONVERGENT_CHOKEPOINT_RECONFIGURATION')
                entry['topology']='stressed_fan_in'
                entry['network_path']=[a['from'],target,b['from']]
                candidates.append(entry)
    # Preserve variation in stressed systems and mechanisms.
    selected=[];seen_target=defaultdict(int)
    for item in sorted(candidates,key=lambda x:(-x['priority'],x['id'])):
        if seen_target[item['subject']]>=2:continue
        seen_target[item['subject']]+=1;selected.append(item)
    return _select(selected,limit,6)


def disruptions(index,bridges,limit=28):
    """Three-claim / two-bridge propagation hypotheses, not observed tipping points.

    No claim is made that a threshold was crossed; thresholds are flagged as unknown.
    """
    enabling=[b for b in bridges if b['relation'] in {'enables','substitutes'}]
    outgoing=defaultdict(list)
    for b in bridges:outgoing[b['from']].append(b)
    candidates=[]
    for first in enabling:
        for second in outgoing[first['to']]:
            a_obj,m_obj,z_obj=first['from'],first['to'],second['to']
            if len({a_obj,m_obj,z_obj})<3:continue
            # We need an enacted OR announced action at A, observed pressure at B and diagnostic at C.
            a_pool=[p for p in index.get(a_obj,[])[:45] if p[1].get('kind')=='action' and
                    p[1].get('mechanism') in CAPACITY_ACTS and p[1].get('direction')=='expands']
            m_pool=[p for p in index.get(m_obj,[])[:45] if p[1].get('kind')=='diagnosis' and
                    p[1].get('mechanism') in DIAGNOSES]
            z_pool=[p for p in index.get(z_obj,[])[:45] if p[1].get('kind')=='diagnosis' and
                    p[1].get('mechanism') in DIAGNOSES]
            a_pool=[p for p in a_pool if _edge_fit(p,first)]
            m_pool=[p for p in m_pool if _edge_fit(p,second)]
            if not (a_pool and m_pool and z_pool):continue
            best=None
            # B or C must record a friction, contestation or condition; not three positive announcements.
            for a,m,z in product(a_pool[:14],m_pool[:14],z_pool[:14]):
                if m[1].get('direction') not in ADVERSE and z[1].get('direction') not in ADVERSE:continue
                pairs=[a,m,z]
                if not _compatible(pairs):continue
                score=_score(pairs,penalty=.88)
                if not best or score>best[0]:best=(score,pairs)
            if best is None:continue
            score,pairs=best
            if score<18:continue
            le,me,ze=pretty(a_obj),pretty(m_obj),pretty(z_obj)
            label=f"System reconfiguration: {le} -> {me} -> {ze}"
            hypothesis=(f"Three vetted claims, from separate publication families, describe a {le} initiative, "
              f"a condition affecting {me}, and a downstream issue in {ze}. The path has two specific "
              f"propagation gates: (1) {first['condition']}; (2) {second['condition']}. "
              "The combined structure identifies a system-reconfiguration mechanism. Its magnitude and threshold remain unmeasured.")
            vals=_mk('disruptions',(first['id'],second['id'],_scope(pairs[0][1])),label,hypothesis,
              f"TWO-HOP CASCADE topology: {le} -> {me} -> {ze}. Each arrow is a declared causal hypothesis with a separate transmission test.",pairs,
              [first['condition'],second['condition'],
               'The intermediate dependency must transmit a real, sufficiently strong effect.',
               'No numerical tipping threshold has been identified.'],
              'The system may absorb the action; alternative pathways, policy buffers and non-overlapping populations could neutralize propagation.',
              f"Stage 1: {first['indicator']}. Stage 2: {second['indicator']}. Detect a regime change only with independent outcome time series.",
              score,'D1_THREE_SOURCE_TWO_STAGE_DISRUPTION_WATCH')
            candidates.append(vals)
    cascades=_select(candidates,limit,6)
    congestion=congestion_disruptions(index,bridges,limit)
    # No weak padding: all motifs require three dated, verified, distinct-family
    # premises. Mix different topologies to avoid monopolising the results.
    primary=cascades[:min(len(cascades),max(0,limit-8))]
    seen={x['id'] for x in primary}
    merged=primary[:]
    for item in sorted(cascades[len(primary):]+congestion,key=lambda v:(-v['priority'],v['id'])):
        if item['id'] not in seen:
            merged.append(item);seen.add(item['id'])
        if len(merged)>=limit:break
    return merged


def synthesize(evidence,bridges,axes,limit=28):
    if not (1<=limit<=30):raise ValueError('Limit must be between 1 and 30')
    ix=_index(evidence)
    t=trends(ix,bridges,limit)
    o,r=opportunities_and_risks(ix,bridges,limit)
    d=disruptions(ix,bridges,limit)
    s=generate_scenarios(evidence,axes,'master-v2')
    bridge_by_id={b['id']:b for b in bridges}
    for item in t+d+o+r:
        keys=item['rule_key']
        if item['rule']=='T2_CONVERGENT_CAUSAL_TOPOLOGY':
            reason=deductions.convergence(bridge_by_id[keys[0]],bridge_by_id[keys[1]],item['network_path'][1],item['proof'])
        elif item['rule']=='D1_THREE_SOURCE_TWO_STAGE_DISRUPTION_WATCH':
            reason=deductions.cascade(bridge_by_id[keys[0]],bridge_by_id[keys[1]],item['proof'])
        elif item['rule']=='D2_CONVERGENT_CHOKEPOINT_RECONFIGURATION':
            reason=deductions.chokepoint(bridge_by_id[keys[0]],bridge_by_id[keys[1]],item['network_path'][1],item['proof'])
        elif item['rule']=='O1_VERIFIED_ACTION_AND_DIAGNOSIS':
            reason=deductions.enabling(bridge_by_id[keys[0]],item['proof'][0])
        elif item['rule']=='R1_IMPLEMENTATION_AND_ABSORPTION_GAP':
            reason=deductions.conversion_risk(bridge_by_id[keys[0]],item['proof'][0])
        elif item['rule']=='R2_CONDITIONAL_RESTRICTION_EXPOSURE':
            reason=deductions.constraint_risk(bridge_by_id[keys[0]])
        else:
            # Multiple independent, dated diagnoses permit a reasoned change in
            # the constraint landscape but do not prove a quantitative slope.
            object_=keys[0]
            direction=keys[1]
            outcome=pretty(object_)
            reason={'inference':f"Across separate assessment systems, {outcome} exhibits recurring {HUMAN_DIRECTION.get(direction,direction)}. The inferred structural implication is a change in the pressure on dependent activities: institutions planning around the previous baseline face growing mismatch between assumed and reported conditions.",
                'mechanism':f"Temporal corroboration network: at least three separated source families, consistent target and geography, distinct dated claims about {outcome}. This is a cross-study direction, not an estimated rate.",
                'second_order':f"Planning, funding and capability commitments based on a stable {outcome} baseline become increasingly exposed to timing and allocation errors.",
                'decision':f"Reconcile baselines and independently measure {outcome} across consecutive periods before estimating a trajectory.",
                'topology':'temporal multi-source alignment'}
        item.update(reason)
    # Counter-directions, negative paths and braking interfaces are inferred
    # only after main trends pass their own evidence gate.
    from .counterforces import attach_counterforces
    attach_counterforces(t, evidence, bridges)
    out={'trends':t,'disruptions':d,'risks':r,'opportunities':o,'scenarios':s}
    # Assertions become an enforced admission gate, not just a prose assurance.
    for key in ('trends','disruptions','risks','opportunities'):
        for item in out[key]:
            proof=item['proof']
            if len(proof)<(3 if key in ('trends','disruptions') else 2):
                raise AssertionError('Too few evidence anchors for '+item['id'])
            if len({p['source_family'] for p in proof})!=len(proof):
                raise AssertionError('Publisher-family overlap in '+item['id'])
            if not all(p['verification']=='workbook_verified' for p in proof):
                raise AssertionError('Unverified anchor in '+item['id'])
            if not item['disconfirmation_test'] or not item['counter_explanation']:
                raise AssertionError('Untestable inference '+item['id'])
    for item in t:
        for counter in item['counterforces']:
            cp=counter['proof']
            if any(p['verification']!='workbook_verified' for p in cp):
                raise AssertionError('Unverified counterforce: '+item['id'])
            if len({p['source_family'] for p in cp})!=len(cp):
                raise AssertionError('Dependent counterforce: '+item['id'])
            if counter['kind']=='counter_direction' and len(cp)<2:
                raise AssertionError('Counter-direction without two independent sources')
            if not cp and counter['kind']!='structural_gate':
                raise AssertionError('Non-conditional counterforce without evidence')
    assert len(s)==8
    return out
