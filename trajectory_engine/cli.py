"""CLI: build reproducible evidence-first historical trajectory reports."""
import argparse
import json
import sys
from pathlib import Path
from .storage import connect
from .engine import import_workbook,make_graph,evaluate_chains
from .render import render
from .llm import reason,synthesize
from .storage import rows
from .journeys import discover
from .presentation import write_page

def workbook_path(value):
    if value!='auto':
        p=Path(value)
        if not p.is_file():raise FileNotFoundError(str(p))
        return p
    matches=[p for p in Path('.').rglob('radar_all_publication_data.xlsx') if '.git' not in p.parts]
    if len(matches)!=1:raise FileNotFoundError('Need exactly one radar_all_publication_data.xlsx; found '+str(len(matches))+'. Pass --workbook explicit/path.xlsx')
    return matches[0]

def build(args):
    workbook=workbook_path(args.workbook)
    dest=Path(args.out);dest.mkdir(parents=True,exist_ok=True)
    db=connect(dest/'historical_evidence.sqlite')
    snapshot,sheets,warnings=import_workbook(db,workbook,args.synthetic)
    chains=make_graph(db,snapshot)
    evaluate_chains(db,snapshot,chains)
    if args.ollama:
        try:
            count=reason(db,snapshot,model=args.ollama,url=args.ollama_url,limit=args.llm_chains)
            print('LLM passes attempted on',count,'chains')
            print('Adversarial overall synthesis generated:',synthesize(db,snapshot,model=args.ollama,url=args.ollama_url))
        except Exception as ex:
            warnings.append('Optional local LLM failed: '+str(ex))
    # Preserve the audit output, but make the *first page* the requested
    # automatically discovered expectation-to-outcome journeys.
    obj=render(db,snapshot,dest/'evidence-audit.html')
    evidence=[e for e in rows(db,'evidence') if e['snapshot_id']==snapshot]
    journeys=discover(evidence,n_topics=args.topics,min_members=6 if args.synthetic else 12)
    write_page(dest/'index.html',journeys,evidence)
    (dest/'topic_journeys.json').write_text(json.dumps(journeys,indent=2,ensure_ascii=False),encoding='utf8')
    print('Automatically discovered topic journeys:',len(journeys))
    obj['import_warnings']=warnings
    (dest/'report.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
    (dest/'import_log.json').write_text(json.dumps({'source':str(workbook),'snapshot':snapshot,'warnings':warnings,'sheet_rows':{k:len(v) for k,v in sheets.items()}},indent=2),encoding='utf8')
    print('Historical evidence import finished:')
    print(json.dumps({'files':str(dest),'snapshot_id':snapshot,'rows':obj['counts']['raw_records'],'publications':obj['counts']['evidence'],'candidate_chains':len(chains),'warnings':warnings},indent=2))
    if warnings:print('WARNING: '+'; '.join(warnings),file=sys.stderr)
    return 0

def main():
    p=argparse.ArgumentParser(description='Evidence-first historical reasoning; no paid API necessary')
    sp=p.add_subparsers(dest='command',required=True)
    b=sp.add_parser('build',help='Import workbook, build graph and make an offline HTML report')
    b.add_argument('--workbook',default='auto',help='Path, or auto finds the named xlsx in current repo')
    b.add_argument('--out',default='trajectory-output')
    b.add_argument('--topics',type=int,default=20,help='Number of data-derived broad topics to discover')
    b.add_argument('--synthetic',action='store_true',help='Mark output clearly as a test fixture')
    b.add_argument('--ollama',default='',help='Optional local Ollama model, e.g. llama3.1')
    b.add_argument('--ollama-url',default='http://localhost:11434/api/generate')
    b.add_argument('--llm-chains',type=int,default=8)
    args=p.parse_args()
    if args.command=='build':return build(args)

if __name__=='__main__':sys.exit(main())
