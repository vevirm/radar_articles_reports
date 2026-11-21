"""Evidence-anchored multi-path system interaction layer, not a causal estimator.

Model claims and source claims have separate ontological status.  A node is admitted
only when a qualifying, independently sourced verified claim is available.
A directed edge means an analyst-reviewed *hypothesis* from bridges.json, never a
measured causal effect.  No observed correlation -> edge rule is used.

We use small, evidence-anchored, signed temporal subgraphs to identify competing
routes, shared gates, downstream exposure and graph counterfactuals. No change in
verification admission or to any upstream workbook.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from .core import (_same_scope, _date, _parse_date, _weight, _verified,
                   CAPACITY_ACTS, RESTRICT_ACTS, _projected_action)
from .infer import _index, _p, _edge_fit, pretty, DIAGNOSES, ADVERSE

REL_POS={'enables','substitutes'}


def _claim_eligible(e,c,edge=None,role='driver'):
    if not _verified(e,c) or not _parse_date(_date(c)):return False
    if role=='driver':
        return (c.get('kind')=='action' and c.get('mechanism') in CAPACITY_ACTS and
                c.get('direction')=='expands' and (edge is None or _edge_fit((e,c),edge)))
    if role=='restrictor':
        return c.get('kind')=='action' and c.get('mechanism') in RESTRICT_ACTS
    if role=='diagnosis':
        return c.get('kind')=='diagnosis' and c.get('mechanism') in DIAGNOSES
    return False


def _compatible_with(item,e,c,used,span_days=1095):
    if e.source_family in used or e.source_family=='unknown':return False
    proof=item.get('proof') or []
    if not proof:return False
    if not _same_scope(proof[0],c):return False
    observed=[_parse_date(p.get('date') or '') for p in proof]
    cand=_parse_date(_date(c))
    if not cand or not all(observed):return False
    return (max(observed+[cand])-min(observed+[cand])).days<=span_days


def _select_source(index,object_,role,item,used,edge=None):
    pool=index.get(object_,())
    for e,c in pool:
        if _claim_eligible(e,c,edge,role) and _compatible_with(item,e,c,used):
            return e,c
    return None


def _focus(item,bridges_by_id):
    path=item.get('network_path') or []
    if len(path)>=3:
        if item['category']=='trends':return path[1]
        if item.get('rule')=='D2_CONVERGENT_CHOKEPOINT_RECONFIGURATION':return path[1]
    return item.get('subject')


def _involved_pair(item,bridge):
    path=item.get('network_path') or []
    return bridge['from'] in path or bridge['to'] in path


def assemble(item,index,bridges,cap_extra=5):
    """Build an independently anchored signed subgraph around an existing inference.

    Requires an existing verified, independently sourced primary inference. It is
    never used to launder a nonverified claim into primary evidence. An absence of
    richer paths remains visible as `depth=ordinary`, not fictional complexity.
    """
    focus=_focus(item,{b['id']:b for b in bridges})
    if not focus:return None
    orig=item.get('proof') or []
    if len(orig)<2:return None
    used={p.get('source_family') for p in orig}
    selected=[]; seen_objects={p.get('object') for p in orig}
    incoming=[b for b in bridges if b['to']==focus]
    outgoing=[b for b in bridges if b['from']==focus]
    diagram_nodes=set(seen_objects)|{focus}
    edges=[]
    # Base bridge hypotheses: drawn only when both endpoints are already observed.
    def edge_add(edge):
        if edge['from']==edge['to']:return
        k=(edge['from'],edge['to'],edge['relation'],edge['id'])
        if k not in {(z['from'],z['to'],z['relation'],z['id']) for z in edges}:
            edges.append({key:edge[key] for key in ('id','from','to','relation','condition','indicator')})
    for b in bridges:
        if b['from'] in diagram_nodes and b['to'] in diagram_nodes:edge_add(b)
    # Drivers provide genuinely different upstream causal routes, not repeat text.
    drivers=[]; constraints=[]; downstream=[]
    driver_edges=sorted([b for b in incoming if b['relation'] in REL_POS],key=lambda b:b['id'])
    for b in driver_edges:
        if b['from'] in diagram_nodes:
            drivers.append((b,None));edge_add(b)
            continue
        if len(selected)>=cap_extra:break
        pair=_select_source(index,b['from'],'driver',item,used,edge=b)
        if pair:
            selected.append(pair);used.add(pair[0].source_family);seen_objects.add(b['from'])
            diagram_nodes.add(b['from']);drivers.append((b,pair));edge_add(b)
    # Opposing restrictions are separately admitted only if an enacted/reported action exists.
    for b in sorted([b for b in incoming if b['relation']=='constrains'],key=lambda z:z['id']):
        if b['from'] in diagram_nodes:
            constraints.append((b,None));edge_add(b)
            continue
        if len(selected)>=cap_extra:break
        pair=_select_source(index,b['from'],'restrictor',item,used,edge=b)
        if pair:
            selected.append(pair);used.add(pair[0].source_family);diagram_nodes.add(b['from'])
            constraints.append((b,pair));edge_add(b)
    # A genuinely observed dependent system adds a *second-stage* consequence.
    for b in sorted(outgoing,key=lambda z:z['id']):
        if b['to'] in diagram_nodes:
            downstream.append((b,None));edge_add(b)
            continue
        if len(selected)>=cap_extra:break
        pair=_select_source(index,b['to'],'diagnosis',item,used,edge=b)
        if pair:
            selected.append(pair);used.add(pair[0].source_family);diagram_nodes.add(b['to'])
            downstream.append((b,pair));edge_add(b)
    # If the focal observation is contested, an independent adverse diagnosis is
    # a second perspective, not automatically an observed net reversal.
    adverse=[]
    for e,c in index.get(focus,()):
        if c.get('kind')=='diagnosis' and c.get('mechanism') in DIAGNOSES and c.get('direction') in ADVERSE and _compatible_with(item,e,c,used):
            adverse.append((e,c));used.add(e.source_family)
            if len(selected)<cap_extra:selected.append((e,c))
            break
    # Check all anchored endpoints; a hypothetical unanchored edge is never drawn.
    endpoints={p.get('object') for p in orig}|{c.get('object') for e,c in selected}
    edges=[b for b in edges if b['from'] in endpoints and b['to'] in endpoints]
    positives=[b for b in edges if b['to']==focus and b['relation'] in REL_POS]
    negative=[b for b in edges if b['to']==focus and b['relation']=='constrains']
    tail=[b for b in edges if b['from']==focus and b['to']!=focus]
    nodes=set().union(*[{b['from'],b['to']} for b in edges]) if edges else {focus}
    support=list(orig)+[_p(e,c) for e,c in selected]
    unique_families={p.get('source_family') for p in support}
    # `complex` means >=4 separately verified source families, 4 graph nodes,
    # >=3 evidenced structural links and >=2 separate enabling routes.
    complex_=(len(unique_families)>=4 and len(nodes)>=4 and
              len(edges)>=3 and len(positives)>=2)
    tested_edges={b['id'] for b in edges}
    pathway_list=[pretty(b['from']) for b in positives]
    stopper_list=[pretty(b['from']) for b in negative]
    effects_list=[pretty(b['to']) for b in tail]
    # A network cut is an *edge/topology* property, NOT proof of observed capacity.
    main_route_count=len(set(b['from'] for b in positives))
    structural_class=('contested common gate' if negative else
                      'multi-stage convergence' if tail else
                      'multiple routes to a common interface')
    if complex_:
        lead=(f"A wider causal configuration is visible around {pretty(focus)}. "
            f"{', '.join(pathway_list[:4])} constitute {main_route_count} separately anchored upstream routes. "
            f"These routes share the {pretty(focus)} conversion interface, so expansion in one channel "
            f"does not establish that the system can absorb all of them together. ")
        if stopper_list:lead+=(f"A separately documented control route through {', '.join(stopper_list[:2])} "
                               f"can interrupt that convergence. ")
        if effects_list:lead+=(f"The model also exposes a second transmission step into {', '.join(effects_list[:2])}; "
                              f"the downstream effect is conditional on its own gate. ")
        if adverse:lead+=(f"An independent assessment of {pretty(focus)} already reports "
                         f"{adverse[0][1].get('direction','adverse conditions').replace('_',' ')}, "
                         f"which must be distinguished from an observed network-wide outcome. ")
        counterfactual=(f"In the structural model, removing one incoming channel leaves "
                        f"{max(0,main_route_count-1)} other documented routes, but removing "
                        f"the shared {pretty(focus)} interface disconnects every modeled route "
                        f"from its common destination. This is a topological sensitivity test, "
                        f"not a measured economic effect.")
        if negative:
            counterfactual+=(f" Removing the inhibitory route tests whether the inferred friction "
                            f"is caused by control design rather than by intrinsic {pretty(focus)} capacity.")
    else:
        lead='';counterfactual=''
    # The exact three route/edge tests can be inspected independently of the DOCX.
    return {'depth':'higher_order' if complex_ else 'ordinary','focus':focus,'classification':structural_class,
        'nodes':sorted(nodes),'edges':edges,'drivers':pathway_list,'constraints':stopper_list,
        'downstream':effects_list,'adverse_target':bool(adverse),'route_count':main_route_count,
        'expanded_proof':support, 'added_proof':[_p(e,c) for e,c in selected],
        'family_count':len(unique_families),'network_reading':lead,'counterfactual':counterfactual,
        'bridge_ids':sorted(tested_edges)}


def enrich(results,evidence,bridges):
    index=_index(evidence)
    details={'trends':0,'disruptions':0,'risks':0,'opportunities':0}
    for cat in details:
        for item in results.get(cat,[]):
            sys=assemble(item,index,bridges)
            if sys:
                item['systemic']=sys
                if sys['depth']=='higher_order':
                    details[cat]+=1
                    # Broaden displayed verification anchors without replacing the
                    # initiating evidence that established the initial hypothesis.
                    item['proof_extended']=sys['expanded_proof']
    return details
