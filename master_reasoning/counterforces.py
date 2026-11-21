"""Infer source-backed trend counter-directions, restraints and failed-transmission gates.

This is downstream of the existing verified-only gate. A counterforce is not
called a measured trend unless independent source-family diagnoses actually
support a counter-direction. Typed bridge conditions are model assumptions;
never launder them into observed empirical effects.
"""
from __future__ import annotations
from collections import defaultdict
from .core import (_verified, _weight, _same_scope, _parse_date, _date,
                   RESTRICT_ACTS)
from .infer import _index, _p, _compatible, _edge_fit, DIAGNOSES, ADVERSE, pretty


def _distinct(pairs, avoid=(), n=2):
    used=set(avoid); selected=[]; works=set()
    for evidence, claim in sorted(pairs, key=lambda p: (-_weight(*p), str(p[0].id))):
        if evidence.source_family in used or evidence.source_key in works: continue
        if not _verified(evidence,claim) or not claim.get('text'): continue
        used.add(evidence.source_family); works.add(evidence.source_key)
        selected.append((evidence,claim))
        if len(selected)>=n:break
    return selected


def _status(pairs):
    return [dict(_p(e,c), role='counterforce_anchor') for e,c in pairs]


def _time_scope_compatible(anchor, other):
    a=anchor[1]; b=other[1]
    da=_parse_date(_date(a)); db=_parse_date(_date(b))
    return bool(da and db and abs((da-db).days)<=1095 and _same_scope(a,b))


def _make(kind, heading, explanation, route, support, check):
    return {'kind':kind,'title':heading,'inference':explanation,
            'network_route':route, 'proof':_status(support), 'what_to_watch':check}


def attach_counterforces(trends, evidences, bridges, max_items=2):
    """Attach up to 2 non-duplicative inferred countermoves to each trend.

    Priority: observed opposing diagnosis -> observed restrictive path -> diagnosed
    friction at common target -> alternative positive channel to offset a
    constrained trend -> model-only conversion gate. No unsupported cross-scope join.
    """
    ix=_index(evidences)
    incoming=defaultdict(list); negative=defaultdict(list)
    for b in bridges:
        (negative if b['relation']=='constrains' else incoming)[b['to']].append(b)
    registry={b['id']:b for b in bridges}
    for trend in trends:
        target=trend.get('network_path',[None,trend['subject']])[1]
        direction=trend.get('rule_key',[None,'expands'])[1] if trend['rule'].startswith('T1_') else 'expands'
        primary_families={p['source_family'] for p in trend['proof']}
        primary_ids={p['record_key'] for p in trend['proof']}
        anchor_claim=next((p for p in trend['proof'] if p.get('object')==target), trend['proof'][-1])
        # All trend premises are known to be source-verified. Seek independent
        # observations from the same affected geography and comparable period.
        target_anchor=None
        for e,c in ix.get(target,[]):
            if e.source_key==anchor_claim.get('record_key'):
                target_anchor=(e,c);break
        if target_anchor is None:
            trend['counterforces']=[];continue
        diagnostics=[(e,c) for e,c in ix.get(target,[]) if c.get('kind')=='diagnosis'
                     and c.get('mechanism') in DIAGNOSES and _time_scope_compatible(target_anchor,(e,c))
                     and e.source_key not in primary_ids]
        reverse={'expands':{'contracts'},'contracts':{'expands'},
                 'becomes_contested':{'expands'},'becomes_conditional':{'expands'}}
        counter=[]
        # Two different primary-verified publisher families make a cross-source
        # counter-direction; one publication alone cannot certify its direction.
        opposing=_distinct([p for p in diagnostics if p[1].get('direction') in reverse.get(direction,set())],
                           primary_families,2)
        if len(opposing)==2:
            title=(f"Opposing expansion in {pretty(target)}" if direction!='expands' else
                   f"Contraction of {pretty(target)}")
            counter.append(_make('counter_direction',title,
                 f"Independent verified assessments describe a contrasting direction in {pretty(target)}. "
                 f"Their joint implication is that the main trajectory is not uniform: a competing development "
                 f"can narrow its reach, change who benefits, or reverse the aggregate outcome if it spreads. "
                 f"The assessments do not by themselves establish the size or dominance of that opposing movement.",
                 [target,'reverse_diagnosis'],opposing,
                 f"Use comparable outcomes and cohorts to determine whether this counter-direction changes {pretty(target)} at system scale."))
        # A restriction is a counterforce only when the restrictive claim itself
        # is verified and its typed edge actually terminates at the trend target.
        for edge in negative[target]:
            restrictive=[p for p in ix.get(edge['from'],[]) if p[1].get('kind')=='action'
                         and p[1].get('mechanism') in RESTRICT_ACTS
                         and _time_scope_compatible(target_anchor,p)]
            selected=_distinct(restrictive,primary_families,1)
            if not selected: continue
            # Different publisher for downstream response and restriction, so
            # one source cannot generate both halves of a causal proposal.
            z=_distinct([p for p in diagnostics if p[0].source_family!=selected[0][0].source_family],
                        {selected[0][0].source_family},1)
            if not z:continue
            if any(not _compatible([selected[0],z[0]]) for _ in [0]):continue
            counter.append(_make('restrictive_path',
               f"Access restriction could interrupt {pretty(target)}",
               f"A verified restrictive action in {pretty(edge['from'])} intersects an independently "
               f"documented condition in {pretty(target)}. The inferred negative path is a changed "
               f"access or collaboration interface: it could interrupt the supporting network even while "
               f"the positive trend's drivers continue to expand. The extent of interference is not established.",
               [edge['from'],target],selected+z,
               f"Test the pathway: {edge['indicator']}"))
            break
        # Observed friction at the target is a 'brake', not automatically a
        # counter-trend: an adverse target assessment may coexist with growth.
        adverse=_distinct([p for p in diagnostics if p[1].get('direction') in ADVERSE],
                          primary_families,2)
        if len(counter)<max_items and adverse:
            model_edges=[registry[k] for k in trend.get('rule_key',[])[:2] if k in registry and registry[k]['to']==target]
            if not model_edges: model_edges=incoming[target][:2]
            if model_edges:
                edge=model_edges[0]
                counter.append(_make('conversion_brake',
                   f"Absorption bottleneck in {pretty(target)}",
                   f"Verified adverse or conditional assessments of {pretty(target)} confront the positive "
                   f"pathway from {pretty(edge['from'])}. That is a structural brake: additional upstream "
                   f"effort need not increase downstream outcomes if the conversion interface remains constrained. "
                   f"The specified gate is {edge['condition'].rstrip('.')}. "
                   f"This is an inferred limit, not proof that this intervention caused the documented difficulty.",
                   [edge['from'],target],adverse,
                   edge['indicator']))
        # A counter-pressure diagnosis of the same target needs no positive edge
        # to be meaningful: independently observed institutional fragmentation or
        # new restrictions can limit a documented opening, even when the typed
        # causal graph has no downstream 'enables' edge into this topic.
        if len(counter)<max_items and adverse and not incoming[target]:
            counter.append(_make('target_side_friction',
                f"Structural resistance to change in {pretty(target)}",
                f"Separate verified diagnoses describe adverse or conditional conditions "
                f"inside {pretty(target)}. Read together with the principal trend, they "
                f"imply a boundary: improvements can remain confined to particular "
                f"institutions or channels while access, permissions, or uptake elsewhere "
                f"continue to be constrained. This inference does not claim the two "
                f"reported developments causally generated one another.",
                [target,'friction'],adverse,
                f"Compare diffusion, participation and independent outcome measures for {pretty(target)}."))
        # For trends whose direction is already adverse/conditional, demonstrate
        # an independently evidenced ENABLING counter-movement if one exists.
        if len(counter)<max_items and direction in {'contracts','becomes_conditional','becomes_contested'}:
            for edge in incoming[target]:
                actions=[p for p in ix.get(edge['from'],[]) if p[1].get('kind')=='action'
                         and p[1].get('direction')=='expands' and _edge_fit(p,edge)
                         and _time_scope_compatible(target_anchor,p)]
                actions=_distinct(actions,primary_families,1)
                if not actions:continue
                support=_distinct([p for p in diagnostics if p[0].source_family!=actions[0][0].source_family],
                                  {*primary_families,actions[0][0].source_family},1)
                if not support or not _compatible([actions[0],support[0]]):continue
                counter.append(_make('offsetting_path',
                    f"An alternative route could offset constraints on {pretty(target)}",
                    f"A verified intervention in {pretty(edge['from'])} acts through a separately "
                    f"specified enabling pathway toward {pretty(target)}. If translated into "
                    f"actual use, that route can counteract the diagnosed contraction or conditionality; "
                    f"the verified sources establish the intervention and target diagnosis, not the net offset.",
                    [edge['from'],target],actions+support,
                    edge['indicator']))
                break
        # Every trend retains the route-specific limiting gate, but it is shown
        # explicitly as an UNVERIFIED CONDITION if no source-backed counterforce
        # is available. This is not represented as a verified countertrend.
        if not counter:
            edge=next((registry[k] for k in trend.get('rule_key',[]) if k in registry),None)
            if edge:
                counter=[_make('structural_gate',
                    f"Implementation gate limiting {pretty(target)}",
                    f"The trend depends on transmission from {pretty(edge['from'])} into "
                    f"{pretty(target)}. Failure of this interface—{edge['risk_if_absent'].rstrip('.')}—"
                    f"would prevent upstream expansion becoming a system-level gain. This is a "
                    f"causal-model condition, not an independently observed countertrend.",
                    [edge['from'],target],[],edge['indicator'])]
        # Guard: do not duplicate the same downstream source as multiple
        # incompatible 'independent' countertrends within an entry.
        used=set(); unique=[]
        for cf in counter:
            marker=(cf['kind'],tuple(cf['network_route']))
            if marker in used:continue
            used.add(marker);unique.append(cf)
        trend['counterforces']=unique[:max_items]
    return trends
