"""Cross-domain abductive recombination of *verified anchors* over reviewed causal bridges.

Important ontology:
  * source assertions are evidence; their verification is inherited from adapter/core
  * bridges are defeasible analyst-specified conditional mechanisms, not source facts
  * the output is a new, exploratory system hypothesis, not an empirical effect

No lower bound on the number of combined findings defines a good inference.
A bounded node budget is solely a deterministic report-computation guardrail, not an
ontological definition of sophistication. The system weighs cross-domain reach,
surprise, causal closure, possible displacement, opposed paths and counterfactual cuts.
This is not numeric PID, causal discovery from raw interventions or a statistical
hypergraph; those would require longitudinal/interventional observations.
"""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import date
from .infer import _index, _p, pretty
from .systemic import _claim_eligible, _compatible_with
from .core import _same_scope, _parse_date, _date, _weight


def _field(o):
    return o.split('.',1)[0]


def _rank(edge,new,pair,existing,focus):
    e,c=pair
    seen_domains={_field(n) for n in existing}
    # cross-domain, inhibitory and downstream *displacements* are given a search
    # preference, rather than merely collecting the highest-volume source topic.
    return (7 if _field(new) not in seen_domains else 0) + (5 if edge['relation']=='constrains' else 0) + \
           (4 if edge['from'] in existing else 0) + (3 if edge['to']==focus else 0) + \
           (3 if c.get('kind')=='diagnosis' else 0) + _weight(e,c)*2


def _reach(edges,source,blocked=None,max_steps=12,positive_only=False):
    graph=defaultdict(list)
    for b in edges:
        if b['from']==blocked or b['to']==blocked:continue
        if positive_only and b['relation']=='constrains':continue
        graph[b['from']].append(b['to'])
    got={source};queue=deque([(source,0)])
    while queue:
        x,d=queue.popleft()
        if d>=max_steps:continue
        for y in graph.get(x,[]):
            if y not in got:got.add(y);queue.append((y,d+1))
    return got


def _distances(edges,focus):
    # Undirected distance is used for positional drawing only, never as a claim
    # about causal direction. Signed edges and actual direction are retained.
    undir=defaultdict(set)
    for b in edges:
        undir[b['from']].add(b['to']);undir[b['to']].add(b['from'])
    dist={focus:0};todo=deque([focus])
    while todo:
        x=todo.popleft()
        for y in sorted(undir[x]):
            if y not in dist:dist[y]=dist[x]+1;todo.append(y)
    return dist


def _choose(item,index,bridges,max_extra=14):
    proof=item.get('proof') or []
    if not proof:return None
    focus=(item.get('systemic') or {}).get('focus') or item.get('subject')
    if not focus:return None
    nodes={p['object'] for p in proof if p.get('object')}
    if focus not in nodes:
        # Do not draw an unverified focus node merely because it sits between
        # other observed system nodes.
        return None
    used={p.get('source_family') for p in proof}
    selected=[];selected_dates=[_parse_date(p['date']) for p in proof if _parse_date(p.get('date',''))]
    allowed={b['id']:b for b in bridges}
    # Include known edges only when BOTH endpoints are anchored by verified claims.
    edges={b['id']:b for b in bridges if b['from'] in nodes and b['to'] in nodes}
    for _ in range(max_extra):
        candidates=[]
        for b in bridges:
            inward=(b['from'] in nodes and b['to'] not in nodes)
            outward=(b['to'] in nodes and b['from'] not in nodes)
            if inward == outward:continue
            new=b['to'] if inward else b['from']
            # In a graph of policy statements, a downstream diagnosis anchors a
            # consequence variable, while upstream actions anchor interventions.
            role='diagnosis' if inward else ('restrictor' if b['relation']=='constrains' else 'driver')
            for e,c in index.get(new,[])[:32]:
                if e.source_family in used or not _claim_eligible(e,c,b if role=='driver' else None,role):continue
                if not _compatible_with(item,e,c,used):continue
                if selected_dates:
                    when=_parse_date(_date(c))
                    if not when or (max(selected_dates+[when])-min(selected_dates+[when])).days>1095:continue
                candidates.append((_rank(b,new,(e,c),nodes,focus),b['id'],e.id,new,(e,c)))
                break
        if not candidates:break
        candidates.sort(key=lambda x:(-x[0],x[1],x[2]))
        _,bid,_,new,pair=candidates[0]
        e,c=pair
        nodes.add(new);used.add(e.source_family);selected.append(pair)
        selected_dates.append(_parse_date(_date(c)))
        edges.update({b['id']:b for b in bridges if b['from'] in nodes and b['to'] in nodes})
    return focus, nodes, list(edges.values()), selected


def _analyse(focus,nodes,edges):
    incoming=[b for b in edges if b['to']==focus and b['relation']!='constrains']
    opposing=[b for b in edges if b['relation']=='constrains']
    out=[b for b in edges if b['from']==focus and b['relation']!='constrains']
    domains={_field(n) for n in nodes}
    in_nodes=list(dict.fromkeys(b['from'] for b in incoming))
    downstream=list(dict.fromkeys(b['to'] for b in out))
    # The focus is a shared cut only if graph reachability changes after removal.
    sources=[n for n in nodes if n!=focus and not any(b['to']==n for b in edges if b['relation']!='constrains')]
    all_reach=set().union(*[_reach(edges,n,positive_only=True) for n in sources]) if sources else set()
    cut_reach=set().union(*[_reach(edges,n,blocked=focus,positive_only=True) for n in sources]) if sources else set()
    cut_effects=sorted((all_reach-cut_reach)-{focus})
    # Search distinct structural features; none is an observed causal magnitude.
    path_lengths=[]
    for root in sources:
        stack=[(root,0,{root})]
        while stack:
            x,d,seen=stack.pop()
            path_lengths.append(d)
            if d>=9:continue
            for b in edges:
                if b['from']==x and b['to'] not in seen and b['relation']!='constrains':
                    stack.append((b['to'],d+1,seen|{b['to']}))
    longest=max(path_lengths,default=0)
    return {'incoming':in_nodes, 'downstream':downstream,
        'opposing':opposing,'domains':sorted(domains),'n_domains':len(domains),
        'longest_path':longest,'cut_effects':cut_effects,
        'cross_domain_links':sum(_field(e['from'])!=_field(e['to']) for e in edges),
        'breadth':len(nodes),'edge_count':len(edges),
        'tensions':len(opposing)}


def _join(xs,maxn=4):
    vals=[pretty(x) for x in xs]
    if len(vals)>maxn:return ', '.join(vals[:maxn])+f' and {len(vals)-maxn} further interfaces'
    if not vals:return ''
    if len(vals)==1:return vals[0]
    return ', '.join(vals[:-1])+' and '+vals[-1]


def _abduce(item,focus,nodes,edges,metrics):
    who=pretty(focus)
    up=metrics['incoming']; down=metrics['downstream']; opp=metrics['opposing']
    is_cut=bool(metrics['cut_effects'])
    adversary=[b['from'] for b in opp]
    # Systemic novelty is different from verified source merit. This is a
    # qualitative ranking signal for discovery, not a probability or confidence.
    novelty=(2*metrics['n_domains'] + metrics['cross_domain_links'] +
             2*min(metrics['longest_path'],4) + 3*int(is_cut) +
             2*len(opp) + 2*int(len(up)>1 and len(down)>0))
    if is_cut and len(up)>1 and down:
        pattern='common-cause inversion'
        title=f'When {who} becomes the hidden governor of {_join(down[:2])}'
        surprise=(f'The paradox is that several separate successes can make the wider system *more* vulnerable. '
                  f'As {_join(up)} expand, {who} becomes a common conversion point; downstream exposure '
                  f'then reaches {_join(down)}. The original investments could all succeed on their own '
                  f'metrics while the wider system becomes dependent on one interface.')
    elif opp and len(down)>=1:
        pattern='constraint rerouting'
        title=f'The unintended geography of control around {who}'
        surprise=(f'The counterintuitive outcome is not simply slower {who}. A constraint transmitted through '
                  f'{_join(adversary[:3])} changes which routes remain accessible, redirecting capability '
                  f'and bargaining power toward the still-open links with {_join(down)}. A policy designed '
                  f'to protect one part of the system could reorganise dependencies elsewhere.')
    elif len(up)>1 and len(down)>1:
        pattern='multi-sector coupling'
        title=f'How {who} could couple formerly separate systems'
        surprise=(f'The emerging change is a new joint system rather than a stronger version of any one input. '
                  f'{_join(up)} converge on {who}, and the possible consequences extend simultaneously '
                  f'into {_join(down)}. Choices once made in different sectors become interdependent, '
                  f'so a local gain can create a remote cost and the location of leverage shifts.')
    elif metrics['longest_path']>=3 and down:
        pattern='delayed bottleneck migration'
        title=f'The next bottleneck beyond {who}'
        surprise=(f'The striking possibility is that fixing {who} does not solve the system problem. '
                  f'It allows previously blocked activity to travel further along a multi-stage chain, '
                  f'where a later interface becomes the controlling limitation. A visible improvement at '
                  f'one stage can therefore precede deteriorating performance elsewhere.')
    elif opp:
        pattern='competing control logics'
        title=f'Two incompatible operating logics converge on {who}'
        surprise=(f'The structurally surprising outcome is a contested operating regime. Efforts to strengthen '
                  f'{who} encounter restrictive mechanisms through {_join(adversary)}; the resulting system '
                  f'may bifurcate into channels that satisfy different rules rather than converge on one common model.')
    else:
        pattern='abductive network recombination'
        title=f'The system-level consequence of reorganising {who}'
        surprise=(f'The potential transformation is not simply a greater quantity of {who}. It is a shift in '
                  f'who controls access, who can combine resources, and which downstream interfaces become '
                  f'scarce as linked arrangements adjust together.')
    seed=[]
    for proof in item.get('proof',[]):
        obj=proof.get('object')
        if obj and obj!=focus and obj not in seed:seed.append(obj)
    # Each report entry must retain the initiating collision, not collapse into
    # another identical story about the same central node.
    if not seed and item.get('network_path'):
        seed=[x for x in item['network_path'] if x!=focus][:2]
    if not seed:
        seed=[item.get('subject') or focus]
    if len(seed)>=2:
        fingerprint=f'{pretty(seed[0])} × {pretty(seed[1])}'
    else:
        fingerprint=pretty(seed[0])
    title=(f'{who.capitalize()} — the {fingerprint} paradox' if item.get('category')=='trends'
           else f'{title} — {fingerprint}')
    if up:
        genesis=f'An initially local interaction between {fingerprint} becomes part of a larger network. Changes in {_join(up)} reach the common interface of {who}. '
    else:
        genesis=f'The assembled network places {who} within several separately documented system conditions. '
    if down:genesis+=f'From that point, the model transmits effects toward {_join(down)}. '
    if adversary:genesis+=f'At the same time, {_join(adversary)} supply competing controls or constraints. '
    consequence=(f'What follows is a shift in the organisation of the system, not a forecast that the published '
                 f'initiatives automatically achieve their intentions. {surprise}')
    if is_cut:
        consequence+=(f' In the stated causal model, removing the {who} interface disconnects routes to '
                      f'{_join(metrics["cut_effects"][:3])}; removing an individual upstream measure does '
                      f'not necessarily have the same effect. This structural asymmetry is the leverage point.')
    elif metrics['longest_path']>=3:
        consequence+=(f' Consequences can emerge with a delay because multiple transmission stages must '
                      f'change before downstream actors experience them.')
    # No discovered counterfactual should be advertised as a measured event.
    test=(f'Challenge the hypothesis by measuring the proposed transmission at {who}, then track independent '
          f'outcomes in {_join(down[:3]) if down else who}; compare activity under constraints and under '
          f'viable alternative routes. If the supposed transmission does not appear, the system reading fails.')
    decision=(f'Do not assess this change only through upstream spending or programme announcements. '
              f'Test the cross-sector consequences at {who} and the downstream interfaces, including '
              f'which actors acquire or lose options when links change.')
    return dict(pattern=pattern,title=title,narrative=genesis+consequence,
                further=(f'The mechanism that matters is the interaction between '
                         f'{_join(up[:3]) if up else who} and the receiving systems '
                         f'{_join(down[:3]) if down else who}. A response optimised for just one '
                         f'programme could displace the constraint or redistribute dependency.'),
                strategic=decision,stress_test=test,novelty_index=novelty)


def reconstruct(item,index,bridges,max_extra=14):
    found=_choose(item,index,bridges,max_extra)
    if not found:return None
    focus,nodes,edges,added=found
    if not edges:return None
    metrics=_analyse(focus,nodes,edges)
    theory=_abduce(item,focus,nodes,edges,metrics)
    proof=list(item.get('proof') or [])+[_p(e,c) for e,c in added]
    assert len({p['source_family'] for p in proof})==len(proof), 'Duplicate evidence families in abductive reconstruction'
    return dict(focus=focus,nodes=sorted(nodes),edges=sorted(edges,key=lambda b:b['id']),
       metrics=metrics,proof=proof,added_proof=[_p(e,c) for e,c in added],
       epistemic_status='exploratory abductive inference built on verified observations and conditional analyst causal bridges',
       **theory)


def enrich_frontiers(results,evidence,bridges,max_extra=14):
    index=_index(evidence)
    totals={}
    for cat in ('trends','disruptions','risks','opportunities'):
        totals[cat]=0
        for item in results.get(cat,[]):
            extension=reconstruct(item,index,bridges,max_extra=max_extra)
            if extension:
                item['frontier']=extension
                # The source anchors remain visible without turning the reading
                # into a dump of claims. The audit path is kept in the model.
                item['proof_extended']=extension['proof']
                totals[cat]+=1
    return totals
