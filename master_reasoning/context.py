"""Use the verified global workbook as scoped external comparison, not EU causal proof.

External records are never used to upgrade a model-bridge assertion into an
observed effect, nor to override the geography and independence gates.
"""
from __future__ import annotations
from collections import defaultdict
from .core import VERIFIED_CLASSES

TOPIC_TAGS={
    'Artificial intelligence':'ai',
    'Critical technology: Artificial intelligence':'ai',
    'AI regulation':'ai',
    'Critical technology: Advanced semiconductors':'chips',
    'Critical technology: Quantum technologies':'quantum',
    'Critical technology: Energy technologies':'green',
    'Union for the Mediterranean: Renewable energies':'green',
    'Africa: Green transition':'green',
    'Critical technology: Advanced materials, manufacturing and recycling technologies':'materials',
    'Research funding':'funding',
    'Technology transfer':'innovation',
    'Open science':'research',
    'Research data':'research',
    'Start-ups':'innovation',
    'Supply chains':'industrial',
    'Science diplomacy':'research',
    'Cybersecurity':'cybersecurity',
    'Health research':'health',
    'Critical technology: Robotics and autonomous systems':'industrial',
    'Bibliometrics':'research',
}


def attach_external_comparators(evidence, results):
    """Attach up to one independent comparison with a canonical thematic match.

    Ranking is based on recorded observation status, source class, availability
    of a citation URL, and deterministic ordering; it is NOT semantic verification.
    Every attachment clearly declares a different geography and context-only role.
    """
    bytag=defaultdict(list)
    for e in evidence:
        if e.source_type!='global_verified' or e.quality_class not in VERIFIED_CLASSES:
            continue
        tag=TOPIC_TAGS.get(e.aboutness)
        if not tag or not e.url or not e.context:
            continue
        score={'observed':3,'mixed':2,'possible':1}.get(e.observation_status.lower(),0)
        if not score:continue
        bytag[tag].append((-score,e.source_key,e))
    for tag in bytag:bytag[tag].sort()
    used=set();count=0
    for section in ('trends','disruptions','risks','opportunities'):
        for item in results.get(section,[]):
            labels=[item['subject'].split('.')[0]]
            for a in item.get('proof',[]):
                obj=a.get('object') or ''
                if obj:labels.append(obj.split('.')[0])
            candidate=None
            for tag in dict.fromkeys(labels):
                for _,_,e in bytag.get(tag,[])[:100]:
                    if e.source_key not in used and e.source_family not in {p['source_family'] for p in item['proof']}:
                        candidate=e;break
                if candidate:break
            if candidate:
                item['external_comparator']={
                    'title':candidate.title,'publisher':candidate.publisher,
                    'geography':candidate.geography,'mechanism':candidate.context,
                    'url':candidate.url,'source_class':candidate.quality_class,
                    'observation_status':candidate.observation_status,
                    'role':'verified external comparison; excluded from causal score'}
                used.add(candidate.source_key);count+=1
    return count
