"""Explicit conjunctive (AND-gated) cross-domain mechanism rules.

The rule 'A AND B AND C -> a new institutional mechanism' differs from
appending separate pairwise effects. It describes a non-additive *hypothesis*,
not a statistically measured synergy. The raw source evidence must separately
anchor every antecedent; observed execution conditions remain distinct.
"""
from __future__ import annotations
from collections import Counter
from .deductions import name


def attach_hyperedges(results,rules):
    matched=Counter()
    for category in ('trends','disruptions','risks','opportunities'):
        used=Counter()
        for item in results.get(category,[]):
            f=item.get('frontier')
            if not f:continue
            anchored={p['object'] for p in f['proof'] if p.get('object')}
            origins={p['object'] for p in item.get('proof',[]) if p.get('object')}
            qualifying=[]
            for r in rules:
                required=set(r['inputs'])
                if not required.issubset(anchored):continue
                original=len(origins&required)
                if not original:continue
                # Base premises influence which interaction dominates; topical
                # fit is more important than the sheer number of found nodes.
                score=12*original+2*len(required)+(4 if f['focus'] in required else 0)
                qualifying.append((score,r['id'],r))
            if not qualifying:continue
            qualifying.sort(key=lambda v:(-v[0],v[1]))
            options=[entry for entry in qualifying if used[entry[2]['id']]<1]
            if not options:continue
            _,_,chosen=options[0]
            used[chosen['id']]+=1
            f['conjunction']={k:chosen[k] for k in ('id','inputs','title','mechanism','emergence','counter','test','status')}
            matched[category]+=1
            initiators=[obj for obj in chosen['inputs'] if obj in origins]
            context=', '.join(name(i) for i in chosen['inputs'])
            lead={'trends':'The deeper direction is a change in the arrangement of actors and dependencies.',
                  'disruptions':'The disruptive break would occur when individually manageable adjustments interact.',
                  'risks':'The exposure lies in the combination, not in any single initiative.',
                  'opportunities':'The opportunity lies in organizing these complementary capabilities as one system.'}[category]
            f['title']=chosen['title']
            if category!='trends' and initiators:
                f['title']+=' — '+name(initiators[0])
            f['narrative']=(lead+f' The interaction involves {context}. '
                f'{chosen["mechanism"]} {chosen["emergence"]}')
            f['further']=(f'The crucial distinction is that these conditions must interact; '
                f'no one of them, considered alone, delivers this system change. '
                f'A competing outcome is also possible: {chosen["counter"]}')
            f['strategic']=('Test the entire conjunction, not only the programmes in isolation. '
                +chosen['test'])
    return dict(matched)
