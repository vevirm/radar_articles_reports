"""Automatically discover *topics*, then present expectations -> developments -> outcomes.

Data-derived NMF topics are navigation hypotheses, not semantic or causal proof.
Each displayed claim is attached to source evidence. No predictions of success are
inferred from publication order alone. The optional LLM prompt can challenge the
first reading against full original publications.
"""
from __future__ import annotations
from collections import Counter
import json, re

NOISE = '''europe european union commission council parliament policy policies strategic
research study studies paper papers article articles report reports source sources
publication publications office data analysis analyses analytical method framework
based evidence result results findings aims aim concerning work working recent
examines authors argues notes suggests examines impact impacts new towards future
study project projects public eu eur countries country findings technology technologies
technological related approach approaches available discussed including evidence
record records historical scanner scanning deep scan claims claimed structured
verified source verifies admitted strand package criteria admission central underlying
primary secondary recovered reads provides document documents major later earlier
applications general perspectives context european research and innovation
investigation published information focus across possible analysis reader labels
proposal proposes years journal published publication original discussion content
mechanism description discusses developed developing status latest
'''.split()
PREFIX = set(NOISE)
EXPECT = re.compile(r'\b(will|would|should|expected|expects|forecast|predict|propos|plan|aim|target|envisag|recommend|intend|call[s]? for|commitment|warning|risk[s]?)\b',re.I)
DOING = re.compile(r'\b(implemented|inaugurated|operat|opened|established|launched|constructed|enacted|adopted|approved|delivered|began|completed|achieved|measured|observed|demonstrat|found|reported|evaluat|assessed)\b',re.I)
REVISE = re.compile(r'\b(revis|replac|repeal|update|reform|renew|rework|second phase|2\.0|reconsider|revamp)\b',re.I)


def _display_date(e):
    return e.get('event_date') or e.get('publication_date') or 'Undated'


def _stage(e):
    # Terms in a secondary abstract are only hints about what the source discusses.
    cls=e['evidence_type']
    text=(e['title']+' '+e['claim_text'])[:2500]
    if cls in ('prediction','warning','proposed_action','announced_decision'):
        return 'expectation'
    if cls in ('implemented_action','measurable_outcome','observation'):
        return 'reported_change'
    if EXPECT.search(text) and not DOING.search(text):return 'expectation'
    if DOING.search(text) and not EXPECT.search(text):return 'reported_change'
    return 'context'


def _sample_rows(rows,maximum=4):
    """Pick spread-out items for a readable card, not a fabricated linked chain."""
    if len(rows)<=maximum:return rows
    positions={0,len(rows)-1}
    for j in range(1,maximum-1):positions.add(round(j*(len(rows)-1)/(maximum-1)))
    return [rows[i] for i in sorted(positions)]


def _payload(e):
    return dict(id=e['evidence_id'],title=e['title'],claim=(e['claim_text'] or e['title'])[:500],
         published=e['publication_date'],event=e['event_date'],url=e['source_url'],
         source=e['source_family'],quality=e['source_quality'],kind=_stage(e),
         evidence_type=e['evidence_type'],classification_basis=e['classification_basis'],
         origin=e['origin_sheet'],meaning='Publication note — not independently verified as an outcome')


def _topic_title(component,terms):
    choices=[(terms[i],float(component[i])) for i in component.argsort()[::-1][:30]]
    phrases=[s for s,w in choices if ' ' in s and all(t not in PREFIX for t in s.split())]
    if phrases:
        phrase=phrases[0]
    else:
        tok=[s for s,w in choices if ' ' not in s and s not in PREFIX]
        phrase=' / '.join(tok[:2]) if tok else choices[0][0]
    return phrase.replace(' ai ',' AI ').replace(' eu ',' EU ').title()[:65]


def discover(evidence,n_topics=19,min_members=8):
    """Find wide topics from the workbook itself (no manually selected topics).

    Uses TF-IDF/NMF and repeatable random seed. This is a semantic *approximation*
    based on word co-occurrence; LLM / embeddings needed for deep synonym matching.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
        from sklearn.decomposition import NMF
        import numpy as np
    except ImportError as ex:
        raise RuntimeError('Topic discovery requires scikit-learn. Run pip install -r trajectory-requirements.txt') from ex
    docs=[]
    for e in evidence:
        # Prefer narrative and title; exclude artificial A/B/C product groups and
        # standard Radar admission rationale. A source cannot be represented by
        # artificially curated global themes.
        docs.append((e['title']+' '+e['title']+' '+(e['claim_text'] or '')[:1300]).strip())
    if len(docs)<4:return []
    # Terms tied almost entirely to a single publisher often describe a feed,
    # association or website rather than a subject. Discover these dynamically.
    family_by_word={}
    for e in evidence:
        for word in set(re.findall(r"[a-z]{4,}",(e['title'] or '').lower())):
            family_by_word.setdefault(word,[]).append(e['source_family'])
    publisher_noise=({term for term,families in family_by_word.items()
        if len(families)>=9 and Counter(families).most_common(1)[0][1]/len(families)>=.82}
        if len(evidence)>=100 and len({e['source_family'] for e in evidence})>=5 else set())
    stops=ENGLISH_STOP_WORDS.union(PREFIX).union(publisher_noise)
    vec=TfidfVectorizer(strip_accents='unicode',stop_words=list(stops),ngram_range=(1,2),
                         min_df=2 if len(docs)<100 else 3,max_df=.50,max_features=7500,sublinear_tf=True)
    X=vec.fit_transform(docs)
    n_components=min(max(2,n_topics),len(docs),X.shape[1])
    model=NMF(n_components=n_components,init='nndsvda',random_state=42,max_iter=300)
    W=model.fit_transform(X); words=vec.get_feature_names_out()
    winners=W.argmax(axis=1)
    raw=[]
    for j,component in enumerate(model.components_):
        inds=[i for i,n in enumerate(winners) if n==j and W[i,j]>0]
        if len(inds)<min_members:continue
        members=[evidence[i] for i in inds]
        families=Counter(e["source_family"] for e in members)
        # A large publisher/template-specific component is not a research topic.
        if len(evidence)>=100 and len(families)>0 and families.most_common(1)[0][1]/len(members)>.70:continue
        members.sort(key=lambda x:(x['publication_date'] or '9999',x['evidence_id']))
        before=[e for e in members if e['publication_date'] and e['publication_date'][:4]<'2026']
        current=[e for e in members if e['publication_date'] and e['publication_date'][:4]>='2026']
        expectations=[e for e in before if _stage(e)=='expectation']
        # if only 2026 coverage, still capture intrayear expectations, labelled accurately
        if not expectations:
            expectations=[e for e in members if _stage(e)=='expectation']
        later=[e for e in members if _stage(e)=='reported_change' and (
            not expectations or e['publication_date'] and e['publication_date']>min(
               (x['publication_date'] or '9999' for x in expectations)))]
        before_detail=_sample_rows(expectations[:30],3)
        if not before_detail:before_detail=_sample_rows(before,3) if before else members[:2]
        middle=_sample_rows(members[1:-1],4)
        observed=_sample_rows(later[-30:],3)
        if not observed:observed=_sample_rows(current[-15:],3) if current else members[-2:]
        independent_sources=len(set(e['source_family'] for e in members))
        earlier_years=len({e['publication_date'][:4] for e in members if e['publication_date'] and e['publication_date'][:4]<'2026'})
        has_old=bool(before)
        old_prediction=any(x['publication_date'] and x['publication_date'][:4]<'2026' for x in expectations)
        if not has_old:
            verdict='Earlier benchmark not found'
            rationale='The selected records are concentrated in 2026. A claim about what was expected years earlier cannot be established from these notes.'
        elif not old_prediction:
            verdict='Historical context found, but no clear older expectation'
            rationale='Older publications are present, but the extracted notes do not document a comparable earlier prediction or commitment.'
        elif not later:
            verdict='Earlier expectations identified; outcome not established'
            rationale='Older expectations are present, but no later source note is classified as reporting a matching realised outcome.'
        else:
            verdict='Some earlier expectations have later reported developments'
            rationale='The records contain earlier forward-looking statements and later reports of action or change. This does not yet show that the expected outcome was delivered: the original targets and independent result measures must be compared.'
        term_indices=component.argsort()[-12:][::-1]
        kws=[words[i] for i in term_indices]
        title = _topic_title(component, words)
        # Suppress publisher banners, navigation text and stock phrases that the
        # corpus clusters together. This is NOT a list of preferred storylines.
        banner_labels = {'independent think','intranet newsletter','area era',
                         'way makes','eureka network','cutting edge'}
        if title.lower() in banner_labels: continue
        raw.append(dict(id='topic-'+str(j),title=title,keywords=kws,
            span_start=min((e['publication_date'] for e in members if e['publication_date']),default=None),
            span_end=max((e['publication_date'] for e in members if e['publication_date']),default=None),
            count=len(members),count_older=len(before),count_current=len(current),
            distinct_families=independent_sources,older_years=earlier_years,
            verdict=verdict,reason=rationale,
            earlier=[_payload(e) for e in before_detail],
            through=[_payload(e) for e in middle],
            now=[_payload(e) for e in observed],
            evidence_ids=[e['evidence_id'] for e in members],
            evidence_types=dict(Counter(_stage(e) for e in members)),
            cautions=(['The workbook does not give separate historical event dates for most records.']
                      if any(not e['event_date'] for e in members) else [])+
                     (['Only one source family is represented.'] if independent_sources<2 else [])+
                     (['The pre-2026 record is sparse compared with 2026 coverage.'] if len(before)<3 else [])))
    # Arrange by cross-year coverage and topic support, not by an assumed narrative.
    raw.sort(key=lambda x:(x['count_older']>0,x['count_older'],x['count']),reverse=True)
    for x in raw:
        x['prompt']=prompt_for(x)
    return raw


def prompt_for(x):
    packets=[];seen=set()
    for key in ('earlier','through','now'):
        for e in x[key]:
            if e['id'] in seen:continue
            seen.add(e['id'])
            packets.append(f"[{e['id']}] {e['published'] or 'undated'} — {e['title']}\nSource: {e['url'] or '(none)'}\nNote: {e['claim']}")
    return ('HISTORICAL DEVELOPMENT RESEARCH. Topic was discovered automatically from the workbook: '+x['title']+\
        '\n\nAsk: WHAT WAS EXPECTED, WHAT ACTUALLY HAPPENED, AND WHY?\n\n'
        'Use these records as leads, not proof. Check original publications, identify exact earlier predictions, plans or warnings and dates, then independent later implementation and outcome evidence. '
        'Separate genuine matching development from merely sharing topic vocabulary. Determine whether broad aims were achieved, partly achieved, not achieved, or fundamentally reworked—only where the record supports it. '
        'Do not declare failure because a deadline has not passed. Treat later new proposals as evidence to investigate, not automatic failure. '
        'Test alternative explanations, including reporting bias and changed terminology. Seek counterevidence and external sources when necessary. '
        'Write a short conclusion, chronological development, reasons, source links, and best counterargument. '
        'If the available record cannot support the conclusion, explain exactly what is missing.\n\nSOURCE LEADS:\n'+\
        '\n\n'.join(packets))
