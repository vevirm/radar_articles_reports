"""Collective and nonlinear interaction mechanisms integrated into existing inferences.

The ten conceptual lenses are *not* ten automatic findings. Their implications
are combined only when the verified-anchored causal topology can support the
specified structural premises. We distinguish a structural possibility from
empirically observed contagion, phase transition, synchronization or feedback.

Source assertions, conditional analyst bridges and inferred consequences are
three different kinds of knowledge. This module never creates evidence, nodes,
bridges, weights or probabilities. Its only report effect is a more ambitious
interpretation of the already admitted evidence-anchored network.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from .deductions import name


def _domain(node: str) -> str:
    return str(node).split('.', 1)[0]


def _word(node: str) -> str:
    return name(node)


def _join(nodes, k=3):
    terms=[_word(x) for x in list(dict.fromkeys(nodes))[:k]]
    if not terms:return 'the affected system'
    if len(terms)==1:return terms[0]
    return ', '.join(terms[:-1])+' and '+terms[-1]


def _cycle(links):
    """Only return a cycle if it is present in the explicit, anchored directed edges."""
    adj=defaultdict(list)
    for e in links:
        if e['relation']!='constrains':adj[e['from']].append(e['to'])
    seen=set(); active=set()
    def visit(x):
        if x in active:return True
        if x in seen:return False
        seen.add(x);active.add(x)
        for nxt in adj[x]:
            if visit(nxt):return True
        active.remove(x)
        return False
    return any(visit(x) for x in sorted(adj) if x not in seen)


def _verified_proof(proofs):
    """A stricter, derived-module gate: no weak/unknown claims can fuel a new mechanism."""
    if not proofs:return False
    families=[]; scopes=[]; dates=[]
    for p in proofs:
        if p.get('verification')!='workbook_verified':return False
        if not isinstance(p.get('evidential_weight'),(float,int)) or p['evidential_weight']<=0:return False
        family=p.get('source_family')
        if not family or family=='unknown':return False
        families.append(family)
        s=p.get('scope') or {}
        scopes.append((s.get('level'),tuple(sorted(s.get('countries') or []))))
        try:dates.append(date.fromisoformat(str(p.get('date',''))[:10]))
        except ValueError:return False
    return (len(families)==len(set(families)) and len(set(scopes))==1 and
            scopes[0][0] not in ('',None) and
            (scopes[0][0]=='eu' or bool(scopes[0][1])) and
            (max(dates)-min(dates)).days<=1095)


def _longest_path(links,focus,max_depth=9):
    graph=defaultdict(list)
    for e in links:
        if e['relation']!='constrains':graph[e['from']].append(e['to'])
    best=[]
    for start in sorted(graph):
        stack=[(start,[start])]
        while stack:
            n,path=stack.pop()
            if len(path)>len(best) and focus in path:best=path
            if len(path)>=max_depth:continue
            for target in sorted(graph[n]):
                if target not in path:stack.append((target,path+[target]))
    return best


def _compressed_independent_actions(proofs, days=180):
    """A bounded coincidence window, not evidence of actor synchronization."""
    actions=sorted((date.fromisoformat(p['date'][:10]),p.get('object'))
        for p in proofs if p.get('kind')=='action' and p.get('direction')=='expands'
        and p.get('status') in {'operating','in_force','implemented','deployed','active'}
        and not p.get('projected_action_language',False)
        and p.get('object') and p.get('date'))
    for i,(start,_) in enumerate(actions):
        group={obj for d,obj in actions[i:] if (d-start).days<=days}
        if len(group)>=3:return sorted(group)
    return []


def interpret(item):
    """Infer one *compound* collective consequence from interacting mechanisms.

    No minimum number of findings is asserted. Each pattern has its own
    necessary structural premises, all endpoints are already evidence-anchored.
    The narrative is about a future conditional mechanism, not an observed law.
    """
    f=item.get('frontier') or {}
    proof=f.get('proof') or []
    if not _verified_proof(proof):return None
    nodes=set(f.get('nodes') or [])
    links=[e for e in (f.get('edges') or []) if e.get('from') in nodes and
           e.get('to') in nodes and e.get('relation') in ('enables','substitutes','constrains')]
    if not links:return None
    focus=f.get('focus')
    if not focus or focus not in nodes:return None
    positive=[e for e in links if e['relation']!='constrains']
    restrict=[e for e in links if e['relation']=='constrains']
    incoming=list(dict.fromkeys(e['from'] for e in positive if e['to']==focus and e['from']!=focus))
    downstream=list(dict.fromkeys(e['to'] for e in positive if e['from']==focus and e['to']!=focus))
    inhibitors=list(dict.fromkeys(e['from'] for e in restrict if e['to']==focus))
    metrics=f.get('metrics') or {}
    breadth=len({_domain(x) for x in nodes})
    cut_effects=metrics.get('cut_effects') or []
    multi_stage=metrics.get('longest_path',0)>=3
    branching=len(downstream)>=2
    convergence=len(incoming)>=2
    conjunction=f.get('conjunction')
    cycle=_cycle(positive)
    compression=_compressed_independent_actions(proof)
    path=_longest_path(positive,focus)
    candidates=[]

    # No invented behavior: each entry represents a conditional model mechanism.
    if convergence and (inhibitors or restrict) and (downstream or cut_effects):
        candidates.append(dict(id='adaptive_rerouting', family='adaptation', priority=10,
            consequence=(f'Actors facing competing enabling routes into {_word(focus)} and controls through '
                f'{_join(inhibitors or [restrict[0]["from"]])} could shift their activity toward the still-open route. '
                f'That change would redistribute downstream access to {_join(downstream or cut_effects)}, '
                f'potentially making a restriction the cause of a new, self-organized dependency rather than simply less activity.'),
            test=(f'Track actual rerouting, new partner choices and access shares around {_word(focus)}; '
                'a documented restriction without behavioural adaptation does not establish the mechanism.'),
            concepts=['complex adaptive systems','self-organization','collective dynamics']))
    if conjunction and convergence:
        inputs=conjunction.get('inputs') or [p['object'] for p in proof[:3]]
        input_names=_join(inputs)
        candidates.append(dict(id='conjunctive_threshold',family='transition',priority=11,
            consequence=(f'In the interaction between {input_names}, the last scarce complement can determine '
                f'which already-funded activities actually become usable. If that complement is supplied, '
                f'control can shift toward the {_word(focus)} interface and away from the original investors; '
                f'if it stays scarce, independently successful programmes can coexist with a system-level shortfall.'),
            test=(f'Observe the uptake of all conditions in {conjunction["id"]} together, and compare '
                'outcomes before and after the last binding complement becomes usable. No numerical tipping point is inferred.'),
            concepts=['emergent behavior','phase transitions','nonlinear social dynamics']))
    elif convergence and inhibitors and downstream:
        candidates.append(dict(id='conditional_regime_shift',family='transition',priority=7,
            consequence=(f'A gradual accumulation of demand at {_word(focus)} could produce a sudden change '
                f'from open access to selective allocation when the separately evidenced controlling route '
                f'through {_join(inhibitors)} binds. That is a regime-shift hypothesis, not an observed critical point.'),
            test=('Measure demand, queueing, access decisions and realized throughput through the same time series; '
                  'without them this is not a demonstrated phase transition.'),
            concepts=['phase transitions','nonlinear social dynamics']))
    if len(path)>=4 and (branching or convergence):
        candidates.append(dict(id='dependent_cascade',family='propagation',priority=8,
            consequence=(f'A change beginning in {_word(path[0])} can travel through {_join(path[1:-1])} '
                f'before reaching {_word(path[-1])}. Its practical effect would therefore depend on '
                f'every intermediate conversion step, and delays at one stage could shift the visible '
                f'consequence far from the original initiative.'),
            test=('Follow dated changes through each intermediate link. A chain of documented subjects is not '
                  'evidence that the effects have already cascaded.'),
            concepts=['cascade dynamics']))
    if convergence and branching and breadth>=3:
        candidates.append(dict(id='distributed_coordination',family='emergence',priority=9,
            consequence=(f'Independent adjustments in {_join(incoming)} can become coupled at {_word(focus)}, '
                f'with effects jointly reaching {_join(downstream)}. As actors adapt to one another, an allocation '
                f'or coordination role may emerge without any one intervention having designed it.'),
            test=('Identify actual linked users, decisions and institutions across the branches; '
                  'shared vocabulary or publication frequency alone cannot demonstrate collective coordination.'),
            concepts=['collective dynamics','emergent behavior','self-organization','swarm dynamics']))
    if cut_effects and convergence:
        candidates.append(dict(id='collective_lock_in',family='adaptation',priority=8,
            consequence=(f'Even if individual participants diversify into {_join(incoming)}, '
                f'the collectively chosen routes still depend on {_word(focus)}. Once institutions adapt their '
                f'contracts and practices around that interface, its influence could outlast the initial policy '
                f'or investment shock—a path-dependence conjecture, not observed hysteresis.'),
            test=(f'Measure switching costs and reversibility after a change in {_word(focus)}; '
                  'do not claim hysteresis without evidence of persistent state dependence.'),
            concepts=['complex adaptive systems','self-organization','nonlinear social dynamics']))
    if compression and (convergence or len(path)>=4):
        candidates.append(dict(id='compressed_parallel_action',family='tempo',priority=6,
            consequence=(f'Independently reported expansion in {_join(compression)} falls within a compact '
                f'publication-era interval. If implementation timing also coincides, demand at {_word(focus)} '
                'could arrive faster than adaptation capacity, producing synchronised pressure rather than '
                'independent gradual change.'),
            test=('Verify implementation dates and actor-level timing; dated reports alone establish neither '
                  'synchronization nor measured acceleration.'),
            concepts=['synchronization','collective dynamics']))
    if cycle:
        candidates.append(dict(id='conditional_feedback',family='feedback',priority=10,
            consequence=(f'Explicitly connected routes around {_word(focus)} form a directed cycle. '
                'If actors reinforce the links as modeled, an initial response can feed back into the '
                'original pressure, magnifying or stabilizing it depending on intervention design.'),
            test=('Measure the return pathway and direction of response. An explicit modeled cycle '
                  'does not prove positive feedback or specify its strength.'),
            concepts=['nonlinear social dynamics','complex adaptive systems']))
    if not candidates:return None
    candidates.sort(key=lambda x:(-x['priority'],x['id']))
    first=candidates[0]
    # The second mechanism must change the interpretation, not repeat its family.
    second=next((c for c in candidates[1:] if c['family']!=first['family']),None)
    if second:
        # A *compound inference* states a new consequence from the conjunction.
        fusion={
            frozenset(('adaptation','propagation')):
                'The resulting paradox is that the effort to control one pathway can reorganize others and transmit pressure to a more distant dependency.',
            frozenset(('adaptation','transition')):
                'This can turn an initially temporary constraint into a new operating regime as actors adapt to the changed access structure.',
            frozenset(('emergence','propagation')):
                'A local coordination arrangement can consequently become a system-wide transmission channel, enlarging both its usefulness and its vulnerability.',
            frozenset(('emergence','transition')):
                'The collectively created interface can change who holds leverage when one essential complement becomes binding.',
            frozenset(('tempo','transition')):
                'Coincident adoption could compress a long adjustment into a short period of bottleneck formation; actual timing must be tested.',
            frozenset(('feedback','transition')):
                'If the modeled return channel activates, a discontinuous change can persist even after the original input weakens.',
        }
        joint=fusion.get(frozenset((first['family'],second['family'])),
                         f'Together these mechanisms can shift who controls {_word(focus)} and who bears the costs of its downstream adjustments.')
        narrative=first['consequence']+' '+second['consequence']+' '+joint
        tests=[first['test'],second['test']]
        lenses=first['concepts']+second['concepts']
    else:
        narrative=first['consequence']; tests=[first['test']]; lenses=first['concepts']
    return {'pattern_ids':[first['id']]+([second['id']] if second else []),
        'model_status':'conditional collective-dynamics abduction; not observed nonlinear dynamics',
        'narrative':narrative,
        'disconfirmation_tests':tests,
        'concepts_in_play':sorted(set(lenses)),
        'observed_cycles':cycle, 'dated_action_compression':bool(compression),
        'verified_anchor_count':len(proof),
        'supports_no_measured_threshold':True}


def _scenario_interaction(scenario):
    """Explore collective consequences of each 2x2x2 state, without implying data-fitted rates."""
    s=scenario.get('axis_states') or {}
    if set(s)!= {'ARCH','OPEN','SCALE'}:return None
    arch,open_,scale=(s[x] for x in ('ARCH','OPEN','SCALE'))
    parts=[]
    if arch=='high' and open_=='high':
        parts.append('Interoperable infrastructure and preserved research cooperation can permit distributed actors to align through shared standards rather than a central coordinator.')
    elif arch=='low' and open_=='low':
        parts.append('Lock-in and cooperation restrictions can make locally rational exit decisions reinforce the fragmentation of a wider network.')
    elif arch=='low':
        parts.append('Where systems remain proprietary, individually sensible investments may select the same controlled gateways and create collective lock-in.')
    else:
        parts.append('Portable interfaces can help excluded or constrained actors reorganize through alternative connections, changing the network of dependencies.')
    if scale=='high':
        parts.append('If funded capacities actually become usable, adoption can propagate through connected organizations; any cascade depends on real demand, complementarity and access.')
    else:
        parts.append('If funding does not convert into usable capacity, joint demand can accumulate at shared conversion gates; gradual spending need not produce gradual benefit.')
    if open_=='low' and scale=='high':
        parts.append('A further interaction is concentration in the institutions able to operate secure corridors: scaling can strengthen a selective network rather than broad openness.')
    elif open_=='high' and scale=='low':
        parts.append('The counterintuitive risk is that open connections spread demand faster than the system can absorb it, moving scarcity to integration capacity.')
    return {'narrative':' '.join(parts),'model_status':'conditional scenario mechanics, not observed transitions or likelihoods'}


def enrich_collective(results):
    counts={}
    pairs={}
    for category in ('trends','disruptions','risks','opportunities'):
        count=0;combos=defaultdict(int)
        for item in results.get(category,[]):
            result=interpret(item)
            if not result:continue
            item['collective_dynamics']=result
            count+=1
            combos['+'.join(result['pattern_ids'])]+=1
        counts[category]=count;pairs[category]=dict(sorted(combos.items()))
    scen=0
    for item in results.get('scenarios',[]):
        result=_scenario_interaction(item)
        if result:item['collective_dynamics']=result;scen+=1
    counts['scenarios']=scen
    return {'counts':counts,'combined_pattern_families':pairs}
