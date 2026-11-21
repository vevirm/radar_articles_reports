"""Entry point for the manually invoked, isolated `master` GitHub Actions workflow."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from .adapter import read_all
from .infer import synthesize
from .systemic import enrich
from .frontier import enrich_frontiers
from .hyperedges import attach_hyperedges
from .collective import enrich_collective
from .context import attach_external_comparators
from .report import write_report

MERIT='stuff/source_merit_ranking.xlsx'
RELEVANCE='Relevance Stuff/relevance_stuff.xlsx'
OUTPUT='reasoning outcomes as planned/Master_Foresight_Reasoning.docx'
MODEL_VERSION='master.v8.collective-adaptive-recombination'


def sha256_file(path:Path) -> str:
    state=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            state.update(block)
    return state.hexdigest()


def validate_bridges(bridges):
    ids=set()
    for b in bridges:
        if b['id'] in ids:raise ValueError('Duplicate causal-edge id: '+b['id'])
        ids.add(b['id'])
        if b['relation'] not in {'enables','substitutes','constrains'} or b['from']==b['to']:
            raise ValueError('Invalid causal edge: '+b['id'])
        if not all(isinstance(b.get(k),str) and b[k].strip()
                   for k in ('from','to','condition','indicator','risk_if_absent')):
            raise ValueError('Incomplete auditable causal edge: '+b['id'])


def find_input(root:Path,relative:str)->Path:
    preferred=root/relative
    if preferred.is_file():return preferred
    target=Path(relative).name.lower()
    matches=[p for p in root.rglob('*.xlsx') if p.name.lower()==target and
             not any(part in {'.git','backups','_backup','archive','archives'} for part in p.relative_to(root).parts)]
    if len(matches)==1:return matches[0]
    if not matches:raise FileNotFoundError(f'Cannot find Excel input {relative}. Must be committed to repository.')
    raise RuntimeError(f'Ambiguous Excel file name {target}: '+', '.join(str(p.relative_to(root)) for p in matches))


def generate(root:Path,limit=28,at=None):
    root=root.resolve()
    merit=find_input(root,MERIT)
    relevance=find_input(root,RELEVANCE)
    config=Path(__file__).resolve().parent/'config'
    bridges=json.loads((config/'bridges.json').read_text(encoding='utf8'))['bridges']
    axes=json.loads((config/'axes.json').read_text(encoding='utf8'))['axes']
    hyperedges=json.loads((config/'hyperedges.json').read_text(encoding='utf8'))['hyperedges']
    validate_bridges(bridges)
    seen=set()
    for rule in hyperedges:
        if rule['id'] in seen:raise ValueError('Duplicate conjunctive rule id: '+rule['id'])
        seen.add(rule['id'])
        if len(set(rule['inputs']))<3:raise ValueError('Conjunctive rule needs 3 different antecedents: '+rule['id'])
        for field in ('title','mechanism','emergence','counter','test'):
            if not isinstance(rule.get(field),str) or not rule[field].strip():
                raise ValueError('Incomplete conjunctive rule: '+rule['id'])

    fingerprints={'source_merit_sha256':sha256_file(merit),
        'relevance_sha256':sha256_file(relevance),
        'causal_bridges_sha256':sha256_file(config/'bridges.json'),
        'scenario_axes_sha256':sha256_file(config/'axes.json'),
        'conjunctive_rules_sha256':sha256_file(config/'hyperedges.json')}
    evidence,counts=read_all(str(merit),str(relevance))
    if counts['admitted_structured_claims']<3:raise RuntimeError('Insufficient admitted structured claims to infer any hypotheses')
    results=synthesize(evidence,bridges,axes,limit)
    systemic_counts=enrich(results,evidence,bridges)
    frontier_counts=enrich_frontiers(results,evidence,bridges,max_extra=14)
    conjunctive_counts=attach_hyperedges(results,hyperedges)
    collective_counts=enrich_collective(results)
    comparator_count=attach_external_comparators(evidence,results)
    target=root/OUTPUT
    write_report(target,results,counts,axes,
      [{'display':str(merit.relative_to(root))},{'display':str(relevance.relative_to(root))}],at,
      fingerprints=fingerprints,model_version=MODEL_VERSION)
    if not target.exists() or target.stat().st_size<15000:raise RuntimeError('DOCX output missing or unexpectedly short')
    return {'output':str(target.relative_to(root)), 'bytes':target.stat().st_size,
       'inputs':{'source_merit':str(merit.relative_to(root)),'relevance':str(relevance.relative_to(root))},
       'input_counts':counts,'output_counts':{k:len(v) for k,v in results.items()},
       'external_verified_comparators':comparator_count,
       'multi_path_reconstructions':systemic_counts,
       'cross_domain_abductive_reconstructions':frontier_counts,
       'conjunctive_high_order_matches':conjunctive_counts,
       'collective_dynamics':collective_counts,
       'model_version':MODEL_VERSION,'fingerprints':fingerprints,
       'rules':'Verified claims support signed cross-domain causal configurations and conditional collective-dynamics mechanisms; synchronization, contagion, feedback and phase transitions are not presented as observed without measurement.'}


def main():
    parser=argparse.ArgumentParser(description='Read two source Excel files and generate an internal verified-first DOCX')
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--max-per-section',type=int,default=28)
    args=parser.parse_args()
    print(json.dumps(generate(args.root,args.max_per_section),indent=2,ensure_ascii=False))

if __name__=='__main__':main()
