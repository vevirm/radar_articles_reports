#!/usr/bin/env python3
"""Global region × Main Radar topic discovery, distinct from the EU-focused Radar.

The automatic scanner searches primarily non-EU/UK regions.  Country tags
represent the substantive setting studied, not source/publisher nationality.
Discovery leads are hypotheses; independent global Deep Scan provides verification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
from math import ceil, gcd
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEEP_PROFILE = 'deep-reader-v2-authoritative'

# Exact requested countries and supra-national regions.  Europe as a whole is NOT a
# match: this avoids filling the workbook with ordinary EU-only publications.
GEOGRAPHY = {
 'Europe — enlargement': {
  'Western Balkans':r'\bwestern\s+balkans?\b', 'Albania':r'\balbani(?:a|an)\b', 'Bosnia and Herzegovina':r'\bbosni(?:a|an)\b|\bherzegovin(?:a|ian)\b',
  'Georgia':r'\bgeorgi(?:a|an)\b(?!\s+tech)', 'Kosovo':r'\bkosov(?:o|ar)\b',
  'Moldova':r'\bmoldov(?:a|an)\b', 'Montenegro':r'\bmontenegr(?:o|in)\b',
  'North Macedonia':r'\bnorth\s+macedoni(?:a|an)\b', 'Serbia':r'\bserbi(?:a|an)\b',
  'Ukraine':r'\bukrain(?:e|ian)\b', 'Türkiye':r'\bt[üu]rkiy(?:e|an)\b|\bturk(?:ey|ish)\b'},
 'Americas': {
  'United States':r'\bunited\s+states\b|\bU\.S\.A?\.?\b|(?-i:\bUS\b)|\bamerican\b',
  'Canada':r'\bcanad(?:a|ian)\b', 'Brazil':r'\bbrazil(?:ian)?\b', 'Argentina':r'\bargentin(?:a|ian)\b',
  'Chile':r'\bchil(?:e|ean)\b', 'Mexico':r'\bmexic(?:o|an)\b',
  'Latin America and Caribbean':r'\blatin\s+america(?:n)?\b|\bcaribbean\b|\bLAC\b'},
 'Africa': {'Africa (region)':r'\bafric(?:a|an)\b', 'Egypt':r'\begypt(?:ian)?\b', 'Ethiopia':r'\bethiopi(?:a|an)\b',
  'Kenya':r'\bkeny(?:a|an)\b', 'Morocco':r'\bmorocc(?:o|an)\b', 'Nigeria':r'\bnigeri(?:a|an)\b',
  'Rwanda':r'\brwand(?:a|an)\b', 'South Africa':r'\bsouth\s+afric(?:a|an)\b'},
 'Asia & Pacific': {'ASEAN':r'\bASEAN\b|\bsoutheast\s+asia(?:n)?\b', 'Indonesia':r'\bindonesi(?:a|an)\b',
  'Malaysia':r'\bmalaysi(?:a|an)\b', 'Singapore':r'\bsingapor(?:e|ean)\b',
  'Thailand':r'\bthai(?:land)?\b', 'Viet Nam':r'\bviet\s*nam(?:ese)?\b',
  'Australia':r'\baustrali(?:a|an)\b', 'Central Asia':r'\bcentral\s+asia(?:n)?\b|\bkazakhst(?:an|ani)\b|\buzbekist(?:an|ani)\b|\bkyrgyzst(?:an|ani)\b|\btajikist(?:an|ani)\b|\bturkmenist(?:an|ani)\b',
  'China':r'\bchin(?:a|ese)\b', 'India':r'\bindi(?:a|an)\b'},
 'Middle East': {'Iran':r'\biran(?:ian)?\b','Israel':r'\bisrael(?:i)?\b',
  'Palestine':r'\bpalestin(?:e|ian)\b','Jordan':r'\bjordan(?:ian)?\b',
  'Arabian Peninsula':r'\barabian\s+peninsula\b|\bgulf\s+states?\b|\bGCC\b', 'Saudi Arabia':r'\bsaudi\b','UAE':r'\bUAE\b|\bunited\s+arab\s+emirates\b|\bemirati\b',
  'Qatar':r'\bqatar(?:i)?\b', 'Oman':r'\boman(?:i)?\b', 'Iraq':r'\biraq(?:i)?\b'},
 'EU / UK': {
  'European Union':r'\beuropean union\b|\bEU\b|\bHorizon Europe\b',
  'United Kingdom':r'\bunited kingdom\b|\bUK\b|\bbrit(?:ain|ish)\b|\bengland\b|\bscotland\b',
  'Germany':r'\bgerman(?:y)?\b', 'France':r'\bfranc(?:e|e\x6ech)\b',
  'Italy':r'\bital(?:y|ian)\b', 'Spain':r'\bspain\b|\bspanish\b',
  'Poland':r'\bpoland\b|\bpolish\b', 'Netherlands':r'\bnetherlands\b|\bdutch\b',
  'Sweden':r'\bsweden\b|\bswedish\b', 'Finland':r'\bfinland\b|\bfinnish\b',
  'Denmark':r'\bdenmark\b|\bdanish\b', 'Ireland':r'\bireland\b|\birish\b',
  'Portugal':r'\bportugal\b|\bportuguese\b', 'Romania':r'\bromania\b|\bromanian\b',
  'Czechia':r'\bczech(?:ia| republic)?\b', 'Belgium':r'\bbelgium\b|\bbelgian\b',
  'Austria':r'\baustria\b|\baustrian\b', 'Greece':r'\bgreece\b|\bgreek\b',
  'Estonia':r'\bestonia\b|\bestonian\b', 'Lithuania':r'\blithuania\b|\blithuanian\b',
  'Latvia':r'\blatvia\b|\blatvian\b'},
 'Other Europe': {'Norway':r'\bnorway\b|\bnorwegian\b', 'Switzerland':r'\bswitzerland\b|\bswiss\b',
  'Iceland':r'\biceland\b|\bicelandic\b'},
 'Additional Asia & Pacific': {'Japan':r'\bjapan(?:ese)?\b', 'South Korea':r'\bsouth korea\b|\bkorean\b|\brepublic of korea\b',
  'Taiwan':r'\btaiwan(?:ese)?\b', 'Pakistan':r'\bpakistan(?:i)?\b',
  'Bangladesh':r'\bbangladesh(?:i)?\b', 'Philippines':r'\bphilippin(?:es|e)\b',
  'New Zealand':r'\bnew zealand\b'},
 'Additional Africa': {'Ghana':r'\bghana(?:ian)?\b', 'Uganda':r'\buganda(?:n)?\b',
  'Tanzania':r'\btanzania(?:n)?\b', 'Senegal':r'\bsenegal(?:ese)?\b'},
}

ISSUES = {
 'Critical raw materials × R&I / technology':r'\bcritical\s+(?:raw\s+)?materials?\b|\brare\s+earths?\b|\bcritical\s+minerals?\b|\blithium\b|\bcobalt\b|\bgraphite\b|\bsemiconductor\s+supply\s+chain\b',
 'Research security / dual use':r'\bresearch\s+security\b|\bdual[ -]use\b|\bexport\s+controls?\b|\bknowledge\s+security\b|\bacademic\s+espionage\b|\btechnology\s+transfer\s+controls?\b',
 'Arabian Peninsula knowledge / technology power':r'\b(?:qatar|bahrain|kuwait|oman|saudi|emirat(?:es|i)|UAE|arabian\s+peninsula)\b.{0,115}\b(?:science|research|universit|knowledge|technolog|innovation|AI|digital)\b|\b(?:science|research|universit|knowledge|technolog|innovation)\b.{0,115}\b(?:qatar|bahrain|kuwait|oman|saudi|emirat(?:es|i)|UAE|arabian\s+peninsula)\b',
 'China in Africa / LAC':r'\bchin(?:a|ese)\b.{0,140}\b(?:africa|african|latin\s+america|caribbean|brazil|mexico|argentina|chile)\b|\b(?:africa|african|latin\s+america|caribbean|brazil|mexico|argentina|chile)\b.{0,140}\bchin(?:a|ese)\b',
 'Science diplomacy':r'\bscience\s+diplomac\w*\b|\bscientific\s+diplomac\w*\b|\bdiplomac\w*\s+(?:through\s+)?(?:science|research|innovation)\b|\bresearch\s+diplomac\w*\b',
 'Ocean / deep sea beyond national jurisdiction':r'\bbeyond\s+national\s+jurisdiction\b|\bBBNJ\b|\bdeep[ -]sea\b|\bdeep[ -]ocean\b|\bseabed\b|\bhigh\s+seas\b|\bocean\s+governance\b|\bmarine\s+biodiversity\b',
 'Science-based international organisations':r'\bUNESCO\b|\bIPCC\b|\bWorld\s+Health\s+Organi[sz]ation\b|\b(?-i:WHO)\b|\bintergovernmental\s+science\b|\bscience[ -]based\s+international\s+organi[sz]ations?\b',
 'Transnational R&I and innovation policy':r'\b(?:international|cross[ -]border|bilateral|multilateral|global)\s+(?:scientific\s+|science\s+|research\s+|innovation\s+|technolog\w*\s+)(?:collaboration|cooperation|partnership|policy|governance|diplomacy|networks?)\b|\b(?:scientific|research|science|technology|innovation)\s+(?:relations|partnerships|agreements|diplomacy|cooperation|collaboration)\b|\bresearch\s+and\s+innovation\s+policy\b|\bR&I\s+policy\b',
 'Australia strategic reorientation to Europe':r'\baustrali(?:a|an)\b.{0,135}\b(?:europe|european|EU|UK|US|united\s+states)\b|\b(?:europe|european|EU)\b.{0,135}\baustrali(?:a|an)\b',
 'EU external R&I partnerships / enlargement':r'\b(?:horizon europe|framework programme|european research area|EU[–-](?:africa|india|asean|latin america|balkan|australia)|european union|european commission|european research|european innovation)\b.{0,170}\b(?:partner\w*|cooperat\w*|collaborat\w*|enlarg\w*|accession|integration|talent|research infrastructur\w*|digital ties|science|technology|innovation)\b|\b(?:partner\w*|cooperat\w*|collaborat\w*|enlarg\w*|accession|integration|talent|research infrastructur\w*|digital ties)\b.{0,170}\b(?:horizon europe|european union|european research|european innovation|EU[–-](?:africa|india|asean|latin america|balkan|australia))\b',
 'EU-facing technology standards / regulatory alignment':r'\b(?:european union|european|EU)\b.{0,145}\b(?:AI regulation|AI governance|digital regulation|standards|standardisation|standardization|cybersecurity|supply.chain resilience|technology governance)\b|\b(?:AI regulation|AI governance|digital regulation|standards|standardisation|standardization|cybersecurity|supply.chain resilience|technology governance)\b.{0,145}\b(?:european union|european|EU)\b',
 'Equitable international research partnerships':r'\b(?:african.european|european.african|europe.africa|EU.africa|global south)\b.{0,140}\b(?:research|science|epistemic|collaborat|partnership|infrastructur)\b|\b(?:research|science|epistemic|collaborat|partnership|infrastructur)\b.{0,140}\b(?:african.european|european.african|europe.africa|EU.africa|global south)\b',
}
STAKEHOLDERS = {
 'Universities / research institutions':r'\buniversit\w*\b|\bacademi(?:c|a)\b|\bresearch\s+institut\w*\b',
 'NGOs / civil society':r'\bNGOs?\b|\bnon[ -]governmental\b|\bcivil\s+society\b',
 'Business / industry':r'\b(?:businesses|firms|industr(?:y|ies)|private\s+sector|companies|enterprises)\b',
 'Faith-based communities':r'\bfaith[ -]based\b|\breligious\s+(?:communit\w*|organi[sz]ations?)\b',
 'Foreign-affairs / trade / non-research ministries':r'\b(?:ministr(?:y|ies)|minister)\s+of\s+(?:foreign|trade|economic|industry|education|defen[cs]e|environment|health)\b|\bforeign\s+affairs\b|\btrade\s+ministr\w*\b',
}
RI = re.compile(r'\bresearch\b|\bscience\b|\bscientific\b|\binnovation\b|\btechnolog\w*\b|\bR&D\b|\bR&I\b|\bacademi\w*\b|\buniversit\w*\b|\bknowledge\b|\bforesight\b|\bsemiconductors?\b|\bmicrochips?\b|\bbiodivers\w*\b|\becolog\w*\b|\bAI\b',re.I)
POLICY = re.compile(r'\bpolic\w*\b|\bstrateg\w*\b|\bgeopolit\w*\b|\bgovern\w*\b|\bdiplomac\w*\b|\bcooperat\w*\b|\bcollaborat\w*\b|\bsecurity\b|\bcompetition\b|\bpartnership\w*\b|\bsovereign\w*\b|\bdevelopment\b|\bforesight\b|\bgeoeconom\w*\b|\btransform\w*\b|\btransition\b|\bfuture\b',re.I)
STRONG = set(ISSUES) - {'Transnational R&I and innovation policy','Australia strategic reorientation to Europe'}
COUNTRY_POLICY_ISSUE = 'Country / regional R&I policy or strategic foresight'

# This lane is not a second EU/UK-only Radar.  A source can investigate ONE
# location and ONE issue; it need not compare countries or mention Europe.
# The thematic vocabulary is an existing Radar data asset, while the selected
# topics are recalculated from the actual current A/B/C corpus on each run.
GEO_TOPIC_LABELS = {'China', 'United States', 'Ukraine', 'India', 'Japan',
                    'United Kingdom', 'Taiwan', 'Global South'}
VAGUE_TOPIC_LABELS = {'Universities', 'Research organisations', 'SMEs',
                      'Competitiveness', 'Regulation'}
# Relevance Focus ONLY: no new bibliometrics/scientometrics studies.
# Existing archived, verified and exported findings are not retroactively filtered.
EXCLUDED_FUTURE_TOPICS = {'bibliometrics', 'scientometrics'}
BIBLIOMETRIC_STUDY_TITLE = re.compile(
    r'\b(?:bibliometric(?:s|al)?|scientometric(?:s|al)?|citation\s+analysis|'
    r'co[ -]?citation\s+analysis|science\s+mapping|publication\s+trend\s+analysis)\b', re.I)


def excluded_future_relevance_lead(row):
    """Intake-only rule; never apply to already stored/exported findings."""
    return (clean(row.get('focus_issue')).casefold() in EXCLUDED_FUTURE_TOPICS
            or bool(BIBLIOMETRIC_STUDY_TITLE.search(clean(row.get('title')))))

TOPIC_EXTRA_PATTERNS = {
    'Health research': ['biomedical research', 'biomedical science', 'medical sciences',
                        'biomedical innovation', 'clinical trials', 'medical R&D'],
    'Biotechnology': ['biomedical technology', 'biopharmaceutical', 'biomanufacturing'],
    'Artificial intelligence': ['AI research', 'AI development', 'machine learning'],
    'Research funding': ['science budget', 'scientific funding'],
}
TOPIC_SEARCH_TERMS = {
    'Health research': 'biomedical research',
    'Artificial intelligence': 'artificial intelligence',
    'Biotechnology': 'biotechnology',
    'Science policy': 'science policy',
    'Horizon Europe': 'research framework programmes',
    'Critical materials': 'critical minerals',
    'Computing power': 'advanced computing',
    'Research infrastructure': 'research infrastructure',
    'Research careers': 'research careers',
}
# Hard selection guard, not a claim that the scholarship has been peer reviewed.
# Source reliability and study validity are STILL assessed by normal Radar and
# authoritative Deep Scan, not inferred from Crossref/OpenAlex registration.
ACCEPTED_OPENALEX_TYPES = {'article', 'review', 'book', 'book-chapter', 'report'}
ACCEPTED_CROSSREF_TYPES = {'journal-article', 'book', 'book-chapter', 'report', 'proceedings-article'}
MIN_PUBLICATION_DATE = date(2025, 1, 1)  # All new leads and backfilled workbook rows
OUTSIDE_EU_UK_SHARE = 1.0  # EU/UK are ordinary Radar territory, not a global discovery allocation
TOPIC_EXTRA_DEFINITIONS = {
    # Only activated when corresponding evidence exists in the current Main Radar.
    'Biodiversity': ['biodiversity', 'ecosystem monitoring', 'conservation science',
                     'ecological research', 'species loss', 'genetic resources'],
}
TOPIC_EXTRA_PATTERNS['Semiconductors'] = ['microchips', 'microchip', 'microelectronic',
                                         'chipmaking', 'advanced packaging', 'chip fabrication']
FUTURES_MECHANISMS = {
    'Biodiversity': ('biodiversity science, ecosystem observation, genetic resources or conservation innovation',
                     'Could the documented activity change biodiversity knowledge, research infrastructure or conservation innovation?'),
    'Semiconductors': ('chip research, fabrication capacity, specialist talent or supply-chain resilience',
                       'Could this develop into an important semiconductor research, skills, production or supply-chain capability?'),
}
FUTURES_SIGNAL = re.compile(r'\b(?:capacity|capabilit\w*|invest\w*|infrastructur\w*|fund\w*|'
                            r'partnership\w*|collaborat\w*|research|innov\w*|govern\w*|'
                            r'polic\w*|strateg\w*|technolog\w*|monitor\w*|manufactur\w*|'
                            r'supply.chain|workforce|talent|training|commerciali[sz]\w*|'
                            r'conserv\w*|knowledge|ecosystem|laborator\w*|funding)\b', re.I)
# The country in a publisher, journal, affiliation, credit or syndicated attribution
# is NOT evidence that the work investigates that country.  This also guards
# backfilled Reader summaries where an outlet is repeated in narrative text.
ATTRIBUTION = re.compile(
    r'\b(?:The\s+Austrian\s+online\s+platform\s+for\s+the\s+European\s+Research\s+Area\s*\(ERA\)\s+is\s+a\s+promotion\s+initiative[^.!?]{0,280}|ERA\s+Portal\s+Austria|European\s+Research\s+Area\s+Portal\s+Austria|'
    r'(?:published|distributed|syndicated|hosted|reprinted|written|issued)\s+by\s+[^,;.!?]{0,100}|'
    r'(?:source|publisher|outlet|affiliation|author address|courtesy|via)\s*:\s*[^,;.!?]{0,110}|'
    r'(?:published|hosted)\s+(?:in|at|from)\s+[^,;.!?]{0,70}|'
    r'(?:authors?|publisher|journal|outlet|editors?)\s+(?:(?:are|were)\s+)?(?:based|located|headquartered)\s+in\s+[^,;.!?]{0,60}|'
    r'(?:authors?|affiliations?)\s+from\s+[^,;.!?]{0,60})\b', re.I)
CLAIM_CONTEXT = re.compile(r'\b(?:study|studies|research|investigat\w*|assess\w*|'
                           r'analys\w*|evaluat\w*|examines?|finds?|demonstrat\w*|'
                           r'develop\w*|policy|strateg\w*|fund\w*|capabilit\w*|'
                           r'innov\w*|technolog\w*|scientific|science|govern\w*|'
                           r'ecosystem|biodivers\w*|chip|manufactur\w*|'
                           r'collaborat\w*|invest\w*|infrastructur\w*|biotechnolog\w*|future|outlook)\b', re.I)



def topic_catalogue():
    """Established topic definitions; no topics generated from arbitrary search hits."""
    raw = load('topic_vocabulary.json', [])
    answer = {}
    for row in raw:
        label = clean(row.get('label')) if isinstance(row, dict) else ''
        if (not label or label in GEO_TOPIC_LABELS or label in VAGUE_TOPIC_LABELS
                or label.casefold() in EXCLUDED_FUTURE_TOPICS):
            continue
        pats = [clean(x) for x in row.get('patterns', []) if clean(x)]
        pats.extend(TOPIC_EXTRA_PATTERNS.get(label, []))
        answer[label] = list(dict.fromkeys(pats))
    for label, pats in TOPIC_EXTRA_DEFINITIONS.items():
        answer[label] = list(dict.fromkeys(pats))
    return answer


def _phrase_occurs(text, phrase):
    phrase = phrase.strip()
    if not phrase:
        return False
    # An isolated 'AI', 'EU', or 'US' must not match the interior of a word.
    return bool(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text, re.I))


def _active_rows(raw=None):
    if raw is None:
        raw = load('radar_active.json', {}) or load('radar.json', {})
    return [item for strand in ('strand_a', 'strand_b', 'strand_c')
            for item in raw.get(strand, []) if isinstance(item, dict)
            and clean(item.get('admission_status')).lower() not in
            {'drop', 'drop_unverifiable', 'duplicate'}]


def identified_topics(*, max_topics=44, raw=None):
    """Topics evidenced by existing active Radar results, not invented by hits."""
    catalogue = topic_catalogue()
    scores = Counter()
    for row in _active_rows(raw):
        title = clean(row.get('title'))
        body = clean(row.get('summary') or row.get('core_message'))[:900]
        for label, patterns in catalogue.items():
            if any(_phrase_occurs(title, pat) for pat in patterns):
                scores[label] += 3
            elif any(_phrase_occurs(body, pat) for pat in patterns):
                scores[label] += 1
    # Rotate a broad issue set, including relatively infrequent health research.
    return sorted((k for k, value in scores.items() if value >= 2),
                  key=lambda k: (-scores[k], k))[:max_topics]


ISSUE_SEARCH_TERMS = {
    'Critical raw materials × R&I / technology': 'critical minerals science policy',
    'Research security / dual use': 'research security dual use technologies',
    'Arabian Peninsula knowledge / technology power': 'Gulf science research innovation strategy',
    'China in Africa / LAC': 'China research innovation collaboration',
    'Science diplomacy': 'science diplomacy',
    'Ocean / deep sea beyond national jurisdiction': 'high seas marine science policy',
    'Science-based international organisations': 'international science governance',
    'Transnational R&I and innovation policy': 'international research innovation policy',
    'Australia strategic reorientation to Europe': 'Australia science strategy',
    'EU external R&I partnerships / enlargement': 'international research partnerships',
    'EU-facing technology standards / regulatory alignment': 'technology standards regulation',
    'Equitable international research partnerships': 'equitable international research partnerships',
}


def identified_issues(*, raw=None, max_issues=10):
    scores = Counter()
    for row in _active_rows(raw):
        title = clean(row.get('title'))
        body = clean(row.get('summary') or row.get('core_message'))[:900]
        for label, pattern in ISSUES.items():
            if re.search(pattern, title, re.I):
                scores[label] += 3
            elif re.search(pattern, body, re.I):
                scores[label] += 1
    return sorted((k for k, score in scores.items() if score >= 2),
                  key=lambda k: (-scores[k], k))[:max_issues]


def focus_areas(*, raw=None):
    """Combined, corpus-grounded search priorities (topics + named issues)."""
    topics = identified_topics(raw=raw)
    issues = identified_issues(raw=raw)
    return {label: TOPIC_SEARCH_TERMS.get(label, label.lower()) for label in topics} | {
        label: ISSUE_SEARCH_TERMS[label] for label in issues}


def location_hits(text):
    return [(group, place) for group, names in GEOGRAPHY.items()
            for place, pat in names.items() if re.search(pat, text, re.I)]


# Nationality + research actor in a title is often author provenance, not the
# country under investigation: "Austrian researchers study Kenya's ecosystems".
# This check applies symmetrically to EVERY country, not just Austria.  It does
# not suppress claims about science capacity or R&I policy *in* that country.
AUTHOR_ACTOR = re.compile(
    r'^\s+(?:researchers?|scientists?|academics?|scholars?|authors?|experts?|'
    r'analysts?|research\s+(?:group|team|centre|center|institut\w*|laborator\w*)|'
    r'universit\w*|academ\w*|institut\w*|laborator\w*|'
    r'journals?|publishers?|portals?|think[ -]tanks?|press|centres?|centers?)\b', re.I)
AUTHOR_VERBS = re.compile(
    r'\b(?:stud(?:y|ies|ied)|investigat\w*|examin\w*|assess\w*|'
    r'evaluat\w*|publish\w*|report\w*|review\w*|survey\w*|'
    r'map(?:s|ped|ping)?|conduct\w*|undertak\w*|present\w*|releas\w*|produc\w*|analys\w*|analyz\w*|document\w*|describ\w*)\b', re.I)
LOCAL_CAPACITY_VERBS = re.compile(
    r'\b(?:invest\w*|fund\w*|establish\w*|open\w*|build\w*|'
    r'expand\w*|launch\w*|develop\w*|adopt\w*|deploy\w*|'
    r'implement\w*|manufactur\w*|operat\w*)\b', re.I)


def substantive_location_hits(sentence):
    """Location hits except clear publisher/author-attribution modifiers.

    This is a conservative *discovery* heuristic, not source reading or
    an assertion about the investigators' identity.  Source metadata is never
    passed into this function.  Ambiguous cases remain for Deep Scan review.
    """
    places = []
    for group, names in GEOGRAPHY.items():
        for place, pat in names.items():
            found = False
            for m in re.finditer(pat, sentence, re.I):
                after = sentence[m.end():m.end() + 160]
                actor = AUTHOR_ACTOR.match(after)
                if actor:
                    before = sentence[max(0, m.start() - 36):m.start()]
                    if re.search(r'\b(?:by|from|via|at|courtesy\s+of)\s+(?:a|an|the)?\s*$', before, re.I):
                        continue
                    next_clause = after[actor.end():]
                    # Publishing, investigating or reporting *on* a foreign
                    # subject does not make the authors' home country a setting.
                    # In contrast, investing/building local R&I capabilities can.
                    verb = AUTHOR_VERBS.search(next_clause)
                    capacity = LOCAL_CAPACITY_VERBS.search(next_clause)
                    if verb and (not capacity or verb.start() < capacity.start()):
                        continue
                    if re.match(r'^\s*(?:from|at|based\s+in|working\s+at)\b', next_clause, re.I):
                        continue
                found = True
                break
            if found:
                places.append((group, place))
    return places


def temporal_lens(title, abstract=''):
    evidence = (clean(title) + ' ' + clean(abstract)[:350]).lower()
    if re.search(r'\b(?:prospect(?:s|ive)?|forecast\w*|scenario\w*|outlook|projection\w*|'
                 r'foresight|future|by 20[3-9][0-9]|could|may lead|anticipat\w*)\b', evidence):
        return 'Possible future / scenarios'
    return 'Current state / developments'


def publication_date_in_scope(value):
    """Require an identifiable publication date on/after 2025-01-01.

    Year-only and year/month bibliographic dates are conservatively interpreted
    as their first day. Undated or malformed items are not admitted into this view.
    """
    match = re.fullmatch(r'(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?(?:T.*)?', clean(value))
    if not match:
        return False
    try:
        published = date(int(match[1]), int(match[2] or 1), int(match[3] or 1))
    except ValueError:
        return False
    return MIN_PUBLICATION_DATE <= published <= datetime.now(timezone.utc).date()


def aboutness_locations(title, body='', *, limit=850):
    """Return places actually discussed, with a short traceable context.

    Source names, bibliographic metadata, and affiliations are deliberately
    absent. A title location needs substantive R&I context; a body-only mention
    must appear in a substantive topical sentence near the beginning. The
    latter is a discovery hypothesis, NOT authoritative source verification.
    """
    title = ATTRIBUTION.sub(' ', clean(title))
    body = ATTRIBUTION.sub(' ', clean(body)[:limit])
    # Sentence extraction avoids assigning the geography from an unrelated
    # credit, reference, or background country list in a long Reader summary.
    sentences = re.split(r'(?<=[.!?])\s+|[;\n]+', body)
    about = {}
    if RI.search(title) and CLAIM_CONTEXT.search(title):
        for group, place in substantive_location_hits(title):
            about[(group, place)] = ('title', title[:240])
    for sentence in sentences:
        if not (RI.search(sentence) and CLAIM_CONTEXT.search(sentence)
                and FUTURES_SIGNAL.search(sentence)):
            continue
        for group, place in substantive_location_hits(sentence):
            about.setdefault((group, place), ('substantive abstract / reader claim', sentence[:240]))
    return [(g, p, basis, excerpt) for (g, p), (basis, excerpt) in about.items()]


def future_ri_question(topic, place, evidence=''):
    """A question, not a claim, derived from a real topic/place match."""
    mechanism, question = FUTURES_MECHANISMS.get(topic, (
        'research capabilities, collaboration, infrastructure, regulation or knowledge production',
        'Could these developments change research capacity, scientific cooperation or innovation trajectories?'))
    return f'{place} × {topic}: {question} [Lens: {mechanism}; requires Deep Scan verification.]'


def regional_matching(title, body, *, allowed_topics=None, expected_region=None,
                      expected_topic=None):
    """Match a Main Radar topic to the *substantive* place studied in a work.

    Neither publisher location, EU relevance nor nationality of the author is
    evidence of regional aboutness. A specific searched place must be supported
    by source title/abstract, not merely by the search query.
    """
    title, body = clean(title), clean(body)
    lead = title + '. ' + body[:900]
    if not title or not RI.search(lead):
        return None
    locations = aboutness_locations(title, body)
    if not locations:
        return None
    if expected_region and not any(p == expected_region for _, p, _, _ in locations):
        return None
    catalogue = topic_catalogue()
    topics = allowed_topics if allowed_topics is not None else focus_areas()
    topic_hits = [topic for topic in topics if topic in catalogue
                  and any(_phrase_occurs(lead, p) for p in catalogue[topic])]
    issue_hits = [issue for issue in topics if issue in ISSUES
                  and re.search(ISSUES[issue], lead, re.I)]
    matches = list(dict.fromkeys(topic_hits + issue_hits))
    if not matches or (expected_topic and expected_topic not in matches):
        return None
    # A place can be important for microchips and irrelevant for biodiversity,
    # *within the very same abstract*. Do not transfer an unrelated country's
    # tag onto the query's topic merely because both appear somewhere.
    if expected_topic:
        def has_pair(excerpt):
            if expected_topic in catalogue:
                return any(_phrase_occurs(excerpt, p) for p in catalogue[expected_topic])
            if expected_topic in ISSUES:
                return bool(re.search(ISSUES[expected_topic], excerpt, re.I))
            return False
        paired = [loc for loc in locations if
                  (not expected_region or loc[1] == expected_region) and has_pair(loc[3])]
        if not paired:
            return None
        # Geography on a topic-specific finding belongs ONLY to places whose
        # substantive excerpt also supports THAT topic.  A semiconductor
        # paragraph about India cannot add India to a biodiversity finding
        # about Brazil, even when both paragraphs are in the same abstract.
        locations = paired
    title_topic = [t for t in topic_hits
                   if any(_phrase_occurs(title, p) for p in catalogue[t])]
    title_issue = [t for t in issue_hits if re.search(ISSUES[t], title, re.I)]
    if not any(basis == 'title' for _, _, basis, _ in locations) and not (title_topic or title_issue):
        # A paper with neither a topical title nor a geographic title is more
        # likely a generic cross-country result with an incidental abstract hit.
        return None
    chosen = next((loc for loc in locations if loc[1] == expected_region), None)
    if chosen is None:
        chosen = next((loc for loc in locations if loc[0] != 'EU / UK'), locations[0])
    score = min(99, 48 + 12*any(basis == 'title' for _, _, basis, _ in locations)
                + 12*bool(title_topic or title_issue)
                + min(12, len(matches)*3) + 5*bool(POLICY.search(lead)))
    return {'score': score,
            'regions': '; '.join(dict.fromkeys(g for g, _, _, _ in locations)),
            'countries': '; '.join(dict.fromkeys(p for _, p, _, _ in locations)),
            'issues': '; '.join(matches),
            'stakeholders': '; '.join(hits(lead, STAKEHOLDERS)),
            'match_reason': 'Main Radar topic: ' + ', '.join(matches[:4]) + '; substantive setting: ' +
                            ', '.join(p for _, p, _, _ in locations[:4]),
            'aboutness_basis': chosen[2], 'geographic_evidence': chosen[3],
            'future_ri_question': future_ri_question(expected_topic or matches[0], chosen[1], chosen[3]),
            'temporal_lens': temporal_lens(title, body),
            'matched_topics': matches,
            'matched_locations': [p for _, p, _, _ in locations],
            'primary_group': chosen[0]}


def hits(text: str, dictionary: dict) -> list[str]:
    return [name for name, pat in dictionary.items() if re.search(pat,text,re.I)]


def clean(s):
    return re.sub(r'\s+',' ',str(s or '')).strip()


def matching(title: str, body: str, *, backfill: bool = False) -> dict | None:
    """Backfill with *aboutness*, never with a publisher or source-country tag."""
    title, body = clean(title), clean(body)
    if not title or not RI.search(title + ' ' + body[:800]):
        return None
    locations = aboutness_locations(title, body, limit=700)
    text = title + '. ' + body[:700]
    issues = hits(text, ISSUES)
    people = hits(text, STAKEHOLDERS)
    strong = [issue for issue in issues if issue in STRONG]
    tiss = [issue for issue in issues if re.search(ISSUES[issue], title, re.I)]
    qualifying = bool(strong and (locations or any(i in tiss for i in strong))) or bool(
        locations and POLICY.search(text) and 'Transnational R&I and innovation policy' in issues)
    if not qualifying and backfill and locations and RI.search(text) and POLICY.search(text):
        # A country-specific R&I strategy or a substantive regional policy study
        # is interesting even when it is outside the narrow emerging-issue list.
        qualifying = True
        if not issues:
            issues = [COUNTRY_POLICY_ISSUE]
    if not qualifying:
        return None
    if 'Science-based international organisations' in issues and not locations and len(issues) == 1 and not re.search(
            r'\b(?:withdraw\w*|future|scenario|reform|funding|governance|influence|'
            r'multilateral|geopolit\w*|leadership|institutional|cooperation|diplomac\w*)\b', text, re.I):
        return None
    score = min(99, 40 + (17 if strong else 0) + (11 if locations else 0) +
                min(12, len(tiss)*7) + min(8, len(locations)*4) +
                min(9, len(issues)*3) + (5 if POLICY.search(title) else 0))
    g, p, basis, excerpt = (next((loc for loc in locations if loc[0] != 'EU / UK'), locations[0])
                           if locations else ('', '', '', ''))
    return {'score': score,
            'regions': '; '.join(dict.fromkeys(g for g, _, _, _ in locations)),
            'countries': '; '.join(dict.fromkeys(p for _, p, _, _ in locations)),
            'issues': '; '.join(issues), 'stakeholders': '; '.join(people),
            'aboutness_basis': basis, 'geographic_evidence': excerpt,
            'future_ri_question': future_ri_question(issues[0], p, excerpt) if p else '',
            'match_reason': 'About: ' + (', '.join(p for _, p, _, _ in locations[:8]) or 'transnational / high seas') +
                            '; issue: ' + ', '.join(issues[:6])}


def external_focus_match(match):
    """Return an external-focused copy or None for EU/UK-only backfill.

    EU/UK material still belongs in the Main Radar.  Other countries can be
    studied by EU/UK publishers and are not removed or penalised.  When both
    regions occur, keep the subject geography, not incidental EU comparison.
    """
    if not match:
        return None
    original = [p for p in clean(match.get('countries')).split('; ') if p]
    external = [(g, p) for g, names in GEOGRAPHY.items() if g != 'EU / UK'
                for p in names if p in original]
    if not external:
        return None
    result = dict(match)
    result['countries'] = '; '.join(p for _, p in external)
    result['regions'] = '; '.join(dict.fromkeys(g for g, _ in external))
    result['match_reason'] = 'Global substantive setting: ' + ', '.join(p for _, p in external[:5]) +                              '; ' + clean(match.get('issues'))
    # The question must point to the external subject (never the publisher).
    primary = external[0][1]
    issue = clean(match.get('issues')).split('; ')[0]
    result['future_ri_question'] = future_ri_question(issue, primary)
    return result


def load(rel, default):
    p=ROOT/rel
    try: return json.loads(p.read_text(encoding='utf8'))
    except FileNotFoundError: return default



def doi_identity(row):
    """Stable DOI identity across Crossref/OpenAlex URL spellings and runs."""
    if not isinstance(row, dict):
        return ''
    raw = clean(row.get('doi'))
    if not raw:
        link = clean(row.get('url') or row.get('link'))
        parsed = urlsplit(link)
        if parsed.netloc.casefold() in {'doi.org', 'www.doi.org', 'dx.doi.org'}:
            raw = unquote(parsed.path.lstrip('/'))
    raw = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', raw, flags=re.I)
    raw = re.sub(r'^doi\s*:', '', raw, flags=re.I).strip().rstrip('/')
    return raw.casefold() if re.match(r'^10\.\d{4,9}/\S+$', raw, re.I) else ''


def lead_identity(row):
    """DOI first; preserve any legacy lead that lacks a DOI."""
    doi = doi_identity(row)
    if doi:
        return 'doi:' + doi
    if not isinstance(row, dict):
        return ''
    url = clean(row.get('url') or row.get('link')).casefold().rstrip('/')
    if url:
        return 'url:' + url
    cid = clean(row.get('candidate_id'))
    if cid:
        return 'id:' + cid
    title = clean(row.get('title')).casefold()
    return 'title:' + title + '|' + clean(row.get('date')) if title else ''


def read_discovery_archive(path):
    """Read the scanner-owned archive without silently resetting invalid JSON."""
    path = Path(path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf8'))
    if not isinstance(data, dict) or not isinstance(data.get('candidates'), list):
        raise ValueError(f'Invalid Relevance Focus discovery archive: {path}')
    return data


def historical_discovery_snapshots():
    """One-time migration: recover prior overwritten snapshots from Git history.

    The workflow already checks out full Git history. This only reads the
    Relevance Focus archive; it does not alter Git history or Radar records.
    """
    rel = 'Relevance Stuff/regional_discoveries.json'
    try:
        proc = subprocess.run(['git', '-C', str(ROOT), 'log', '--max-count=200',
                               '--format=%H', '--', rel], capture_output=True,
                              text=True, check=True, timeout=12)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print('Past regional snapshots unavailable; retaining current archive:',
              type(exc).__name__, flush=True)
        return []
    recovered = []
    for sha in proc.stdout.splitlines():
        try:
            old = subprocess.run(['git', '-C', str(ROOT), 'show', f'{sha}:{rel}'],
                                 capture_output=True, text=True, check=True, timeout=12)
            document = json.loads(old.stdout)
            if isinstance(document, dict) and isinstance(document.get('candidates'), list):
                recovered.append(document)
        except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    # Git log is newest-first; restore oldest first so the earliest metadata
    # wins when the same DOI appears in several archived batches.
    return recovered[::-1]


def next_rotation_slot(existing, now):
    """One new search rotation per completed scan, not once per four hours."""
    previous = existing.get('rotation_index') if isinstance(existing, dict) else None
    if isinstance(previous, int) and previous >= 0:
        return previous + 1
    # Legacy latest-run snapshots have no rotation_index. Derive the previous
    # slot from their timestamp so the first upgraded run also advances.
    stamp = clean(existing.get('compiled_at')) if isinstance(existing, dict) else ''
    if stamp:
        try:
            last = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            if last.tzinfo is not None:
                return int(last.timestamp() // (4 * 3600)) + 1
        except ValueError:
            pass
    return int(now.timestamp() // (4 * 3600))


def cumulative_discoveries(existing, batch, *, slot, older_snapshots=()):
    """Cumulative, DOI-deduplicated *leads*; never promotes them to verified.

    The temporary batch passed to Radar admission is kept separate and only
    contains never-seen-in-this-archive candidates. Earlier leads are retained
    even if later searches do not rediscover them.
    """
    combined = {}
    for document in [*older_snapshots, existing, batch]:
        if not isinstance(document, dict):
            continue
        origin = clean(document.get('batch_id'))
        for lead in document.get('candidates', []):
            if not isinstance(lead, dict):
                continue
            key = lead_identity(lead)
            if key and (key not in combined or
                        (lead.get('aboutness_basis') and
                         not combined[key].get('aboutness_basis'))):
                first = combined.get(key, {}).get('first_seen_batch_id')
                combined[key] = {**lead, 'first_seen_batch_id':
                                 first or clean(lead.get('first_seen_batch_id')) or origin}
    archive = {**batch,
               'archive_mode': 'cumulative-doi-deduplicated',
               'rotation_index': slot,
               'candidates': list(combined.values()),
               'work_count': len(combined),
               'latest_batch_work_count': len(batch['candidates']),
               'discovery_stats': {**batch['discovery_stats'],
                                   'cumulative_regional_leads': len(combined)}}
    return archive

def link_key(x):
    # Deep Scan's record_key preserves the case of URL paths, query strings, and
    # Google News opaque article identifiers. A lowercase URL is a DIFFERENT
    # work-state key: never lowercase a lookup key for these stores.
    url=clean(x.get('link') or x.get('url') or x.get('landing_page_url'))
    return 'link:'+url if url else ''


def related_record_keys(x):
    base=[]
    lk=link_key(x)
    if lk:
        # Exact key first. Legacy canonical variants are fallbacks only; do
        # not normalize case on the authoritative lookup path.
        base.extend([lk,lk.replace('https://doi.org/','https://dx.doi.org/')])
        if lk.rstrip('/') != lk:
            base.append(lk.rstrip('/'))
    return list(dict.fromkeys(base))


def compile_records():
    """Audit all previously scanned records, not just today's active Radar slice.

    Priority is active > inactive main > stored Deep Scan. Every
    worksheet row still requires an original item or authoritative Deep Scan
    evidence, and KEEP + verified identity for the verified worksheet. The
    result is a *relevance view*, never a change to the admission/corpus gates.
    """
    active = load('radar_active.json', {}) or load('radar.json', {})
    raw = load('radar.json', {})
    deep = load('deep_scan_work_state.json', {}).get('records', {})
    admissions = load('admission_state.json', {}).get('records', {})
    reader = load('reader_text.json', {}).get('records', {})
    verified, pending, stats = [], [], Counter()
    candidates = []
    for letter in 'ABC':
        candidates.extend((f'Main {letter} — active', i, False, '') for i in active.get('strand_' + letter.lower(), []))
    for letter in 'ABC':
        candidates.extend((f'Main {letter} — outside active view', i, False, '')
                          for i in raw.get('strand_' + letter.lower(), []))

    # Deep Scan and Reader preserve verified material no longer enumerated in
    # radar_active.json.  Their explicit record keys are the source of joins;
    # never invent a verified status from text keywords or an old scan count.
    for key, rt in reader.items():
        if not isinstance(rt, dict):
            continue
        ds = deep.get(key, {})
        # Do not backfill from the historical store or its historical-only reader keys.
        if key.startswith('historical:'):
            continue
        sources = (rt.get('verification') or {}).get('recovered_sources') or []
        recovered = next((z.get('url') for z in sources if isinstance(z, dict) and z.get('url')), '')
        url = clean(ds.get('url') or (key[5:] if key.startswith('link:') else '') or recovered)
        item = {'title': clean(ds.get('title') or rt.get('reader_title')),
                'date': ds.get('date', ''), 'source': ds.get('source_name', ''),
                'url': url, 'strand': rt.get('strand', '')}
        candidates.append(('Stored Deep Scan / Reader', item, False, key))

    selected = {}
    scoped_keys = set()
    for source, item, is_hist, direct_key in candidates:
        if not isinstance(item, dict):
            continue
        stats['source_rows_' + source] += 1
        keys = ([direct_key] if direct_key else []) + related_record_keys(item)
        keys = list(dict.fromkeys(keys))
        rt = next((reader[k] for k in keys if k in reader), {})
        ad = next((admissions[k] for k in keys if k in admissions), {})
        ds = next((deep[k] for k in keys if k in deep), {})
        if not publication_date_in_scope(item.get('date') or ds.get('date')):
            stats['source_rows_before_2025_or_undated'] += 1
            continue
        link = clean(item.get('link') or item.get('url') or item.get('landing_page_url') or ds.get('url'))
        title = clean(item.get('title') or item.get('headline') or ds.get('title') or rt.get('reader_title'))
        if not title:
            continue
        identity = link.lower().rstrip('/') or 'title:' + re.sub(r'[^a-z0-9]', '', title.lower())
        # Preserve single bibliographic identity for audited counts, including
        # inactive/active overlap.
        scoped_keys.add(identity)
        analysis = rt.get('deep_analysis') if isinstance(rt.get('deep_analysis'), dict) else item.get('deep_analysis') or {}
        body = ' '.join(clean(x) for x in [
            item.get('summary'), item.get('core_message'), item.get('reader_point'),
            item.get('reader_what'), rt.get('reader_what'),
            analysis.get('research_question'), analysis.get('main_finding')])
        decision = clean(ad.get('decision') or (rt.get('admission') or {}).get('decision')
                         or item.get('admission_status')).lower()
        deep_ok = (ds.get('status') == 'verified' and rt.get('profile') == DEEP_PROFILE
                   and bool((rt.get('verification') or {}).get('identity_verified')))
        if source == 'Stored Deep Scan / Reader':
            stats['stored_reader_records_evaluated'] += 1
            stats['stored_reader_decision_' + (decision or 'unknown')] += 1
            if deep_ok:
                stats['stored_reader_identity_verified'] += 1
            if deep_ok and decision == 'keep':
                stats['stored_reader_verified_and_kept'] += 1
        if decision in {'drop', 'drop_unverifiable', 'duplicate', 'needs_manual_verification'}:
            stats['source_rows_excluded_nonretained'] += 1
            continue
        match = external_focus_match(matching(title, body, backfill=True))
        if not match:
            stats['source_rows_not_matching_external_focus'] += 1
            continue
        stats['source_rows_matched_focus'] += 1
        if source == 'Stored Deep Scan / Reader':
            stats['stored_reader_focus_matches'] += 1
            if deep_ok and decision == 'keep':
                stats['stored_reader_verified_kept_focus_matches'] += 1
        record = {
            'title': title, 'date': clean(item.get('date') or ds.get('date')),
            'source': clean(item.get('source') or item.get('venue') or ds.get('source_name')),
            'authors': clean(item.get('authors')), 'source_location': source, 'url': link,
            'strand': clean(item.get('strand') or rt.get('strand') or source.removeprefix('Main ')),
            'reader_what': clean(rt.get('reader_what') or item.get('reader_what') or item.get('reader_point')),
            'reader_why': clean(rt.get('reader_why') or item.get('reader_why') or item.get('why_it_matters')),
            'verification': 'Deep Scan verified — retained' if deep_ok and decision == 'keep' else 'Not verified + retained',
            'workflow_state': ('Verified + KEEP' if deep_ok and decision == 'keep'
                               else 'Admission REVIEW — Deep Scan complete' if deep_ok and decision == 'review'
                               else 'Admission decision pending — Deep Scan complete' if deep_ok
                               else 'Deep Scan not complete'),
            'admission': decision or 'not yet checked', 'verified_at': clean(ds.get('verified_at')),
            'deep_scan_package': clean(ds.get('verified_package_id') or rt.get('deep_scan_package_id')),
            **match,
        }
        is_verified = deep_ok and decision == 'keep'
        # Prefer a verified copy, then authoritative primary active
        # records over inactive/stored versions; no duplicate output rows.
        provenance = 4 if '— active' in source else 2 if 'outside active view' in source else 1
        rank = (int(is_verified), provenance, bool(link), match['score'])
        if identity not in selected or rank > selected[identity][0]:
            selected[identity] = (rank, record)
    for _, record in selected.values():
        if record['verification'] == 'Deep Scan verified — retained':
            verified.append(record)
        else:
            pending.append(record)
    verified.sort(key=lambda a: (-a['score'], a['date'], a['title']))
    pending.sort(key=lambda a: (-a['score'], a['date'], a['title']))
    stats['unique_works_evaluated'] = len(scoped_keys)
    stats['unique_focus_matches'] = len(selected)
    stats['verified_kept_focus_matches'] = len(verified)
    stats['review_focus_matches'] = len(pending)
    stats['stored_only_focus_matches'] = sum(x['source_location'] == 'Stored Deep Scan / Reader' for x in verified + pending)
    # The scanner-owned cumulative archive keeps regional discovery leads across
    # runs; none is promoted to verified without the authoritative Deep Scan.
    archive = load('Relevance Stuff/regional_discoveries.json', {})
    latest_leads = archive.get('candidates', []) if isinstance(archive, dict) else []
    test_results = {
        clean(row.get('candidate_id')): clean(row.get('status'))
        for row in (raw.get('curator_candidate_testing', {}).get('results', []) or [])
        if isinstance(row, dict)
    }
    in_main = {
        clean(row.get('link') or row.get('url')).casefold().rstrip('/')
        for strand in ('strand_a', 'strand_b', 'strand_c')
        for row in raw.get(strand, []) if isinstance(row, dict)
    }
    regional_leads = []
    for lead in latest_leads:
        if not isinstance(lead, dict) or not lead.get('title') or not publication_date_in_scope(lead.get('date')):
            continue
        if lead.get('focus_group') == 'EU / UK':
            stats['eu_uk_legacy_leads_excluded_from_global_view'] += 1
            continue
        status = test_results.get(clean(lead.get('candidate_id')))
        if not status:
            status = ('in_main_radar' if clean(lead.get('url')).casefold().rstrip('/') in in_main
                      else 'indexed_lead_not_verified')
        # No grandfathering: v3 country tags came from less selective matching.
        # The underlying DOI stays in the archive, but its old region is NOT a
        # verified tag. Re-evaluate title alone; let a later v4 search confirm
        # body-only aboutness before claiming a country in the workbook.
        if not lead.get('aboutness_basis'):
            title_locations = aboutness_locations(lead.get('title', ''))
            claimed = clean(lead.get('focus_region'))
            valid = next((loc for loc in title_locations if loc[1] == claimed), None)
            if not valid:
                stats['legacy_geography_quarantined'] += 1
                regional_leads.append({**lead, 'legacy_claimed_region': claimed,
                                       'focus_region': '', 'focus_group': '',
                                       'aboutness_status': 'legacy geography quarantined',
                                       'radar_check_status': 'requires_new_aboutness_check'})
                continue
            lead = {**lead, 'aboutness_basis': 'title-only legacy recheck',
                    'geographic_evidence': valid[3],
                    'future_ri_question': future_ri_question(
                        clean(lead.get('focus_issue')), claimed, valid[3])}
        regional_leads.append({**lead,
                               'aboutness_status': 'preliminary — Deep Scan required',
                               'radar_check_status': status})
    # A separate global verification lane keeps the ordinary EU Radar admission
    # contract untouched. These records have actually passed an independent
    # topic/place, source-integrity and future-significance Deep Scan.
    global_review = load('Relevance Stuff/deep_scan/verified_findings.json', {})
    global_records = [r for r in global_review.get('records', []) if isinstance(r, dict)
                      and r.get('decision') == 'keep']
    stats['global_deep_scan_kept'] = len(global_records)
    stats['cumulative_regional_indexed_leads'] = len(regional_leads)
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'verified': verified, 'pending': pending, 'regional_leads': regional_leads,
        'global_verified': global_records,
        'statistics': dict(stats),
        'catalogue': {'countries': list(dict.fromkeys(k for group in GEOGRAPHY.values() for k in group)),
                      'regions': list(GEOGRAPHY), 'issues': list(ISSUES) + [COUNTRY_POLICY_ISSUE],
                      'stakeholders': list(STAKEHOLDERS)},
        'policy': 'Relevance Focus is a global aboutness and R&I futures lane outside the EU/UK as primary study setting: no European relevance needed. Only publications dated 2025-01-01 onward: audited active and inactive Main Radar and retained Deep Scan/Reader records (not historical archive). '
                  'Verified requires Deep Scan identity verification and KEEP admission. '
                  'A geography+explicit R&I-policy focus may also qualify without a named emerging issue. '
                  'Archived records are labelled; this workbook never readmits dropped works.'
    }


# Search geography rotates independently of the ordinary Radar's EU focus.
# Fixed anchors preserve coverage of large research regions, including India;
# rotating countries create new local combinations every run.
REGION_ANCHORS = {
    'Americas': ('United States', 'Brazil'),
    'Asia & Pacific': ('India', 'China'),
    'Africa': ('Africa (region)', 'South Africa', 'Kenya'),
    'Middle East': ('Saudi Arabia', 'UAE'),
    'Europe — enlargement': ('Ukraine', 'Türkiye'),
}
SEARCH_GEOGRAPHY = {
    'Africa (region)': 'Africa',
    'European Union': 'European Union',
    'ASEAN': 'Southeast Asia ASEAN',
    'Arabian Peninsula': 'Arabian Peninsula',
    'Türkiye': 'Turkey',
    'Viet Nam': 'Vietnam',
    'United States': 'United States',
    'United Kingdom': 'United Kingdom',
}
TEMPORAL_QUERIES = (
    ('Current state / developments', ''),
    ('Possible future / scenarios', 'future outlook scenarios'),
)


def regional_targets(slot):
    """Rotate global investigation targets; EU and UK use the ordinary Radar."""
    targets = []
    for group, anchors in REGION_ANCHORS.items():
        targets.extend((group, place) for place in anchors)
    for group, names in GEOGRAPHY.items():
        available = [name for name in names if name not in REGION_ANCHORS.get(group, ())]
        if not available:
            continue
        # Mostly external regions; EU/UK is optional context, not the primary lane.
        # Rotate localities to avoid always searching established science powers.
        if group == 'EU / UK':
            continue
        count = 3 if group in ('Americas','Asia & Pacific','Africa') else 2
        start = slot % len(available)
        targets.extend((group, available[(start + i) % len(available)])
                       for i in range(min(count, len(available))))
    return list(dict.fromkeys(targets))


def focused_search_plan(slot: int, focus=None):
    """Each query connects an active Radar topic to an external world region.

    EU/UK are not target geographies, but their researchers, publishers and
    partners may produce relevant work on external places.  No EU bridge needed.
    """
    focus = focus if focus is not None else focus_areas()
    if not focus:
        return
    items = list(focus.items())
    items = items[slot % len(items):] + items[:slot % len(items)]
    targets = regional_targets(slot)
    if not targets:
        return
    # Coprime stepping touches every target before repeating one, even if the
    # number of currently selected Radar topics changes between runs.
    stride = next(i for i in range(5, 5 + len(targets))
                  if gcd(i, len(targets)) == 1)
    wave_stride = next(i for i in range(7, 7 + len(targets))
                       if gcd(i, len(targets)) == 1)
    seen = set()
    for wave in range(FOCUSED_PAGE_DEPTH):
        for idx, (topic, term) in enumerate(items):
            group, place = targets[(idx * stride + wave * wave_stride + slot) % len(targets)]
            lens_name, suffix = TEMPORAL_QUERIES[(idx + wave + slot) % len(TEMPORAL_QUERIES)]
            query = f'{term} {SEARCH_GEOGRAPHY.get(place, place)} {suffix}'.strip()
            # Alternate provider priority on each run and each topic-region pair.
            # Both providers remain available; this does not privilege a publisher.
            providers = ('openalex', 'crossref') if (slot + idx + wave) % 2 == 0 else ('crossref', 'openalex')
            for provider in providers:
                key = (provider, query)
                if key in seen:
                    continue
                seen.add(key)
                yield group, place, topic, lens_name, query, provider, 1


def openalex_abstract(index):
    if not isinstance(index,dict):return ''
    seq=[]
    for word, positions in index.items():
        if isinstance(positions,list):seq.extend((i,word) for i in positions if isinstance(i,int) and 0<=i<500)
    return ' '.join(w for _,w in sorted(seq))[:5000]


# Run a whole 25 minutes of *focused discovery*.  Candidate admission and the
# workbook generation happen AFTER this period; neither is charged to it.
FOCUSED_DISCOVERY_SECONDS = 25 * 60
FOCUSED_REQUEST_PACING_SECONDS = 5.0   # polite API use, also avoids rate-limit bursts
FOCUSED_PAGE_DEPTH = 24


def publication_venue(row):
    """Normalize a journal/publisher label for diversity tracking, not quality gates."""
    if not isinstance(row, dict):
        return ''
    return re.sub(r'\s+', ' ', clean(row.get('source'))).casefold().strip()


def previous_publication_venues(existing, older_snapshots=()):
    """Count different prior DOI leads per venue, without double-counting snapshots."""
    counts = Counter()
    observed = set()
    for doc in [*older_snapshots, existing]:
        if not isinstance(doc, dict):
            continue
        for row in doc.get('candidates', []):
            identity = lead_identity(row)
            if not identity or identity in observed:
                continue
            observed.add(identity)
            venue = publication_venue(row)
            if venue:
                counts[venue] += 1
    return counts


def balanced_candidates(picked, max_candidates, *, venue_history=None):
    """Region/topic balance and soft journal/publisher diversity across runs.

    Prefer less-used publishing venues among similarly scored candidates, while
    still accepting the only eligible journal if that is what the evidence has.
    This is NOT a whitelist, blacklist, publisher-quality assessment, or
    reason to waive the ordinary Radar / Deep Scan verification gates.
    """
    history = venue_history or Counter()
    core, external = [], []
    for score, _group, row in picked.values():
        (core if row['focus_group'] == 'EU / UK' else external).append((score, row))

    # The source diversity counter is shared across EU and external selections,
    # so a venue already prominent in one region loses preference in another.
    chosen_venues = Counter()
    def diverse_order(entries):
        buckets = {}
        for score, row in entries:
            key = (row['focus_group'], row['focus_region'])
            buckets.setdefault(key, []).append((score, row))
        for rows in buckets.values():
            rows.sort(key=lambda x: (-x[0], x[1]['candidate_id']))
        output = []
        by_topic = Counter()
        while any(buckets.values()):
            for key in sorted(buckets):
                rows = buckets[key]
                if not rows:
                    continue
                # Venue diversity never displaces a much stronger lead. A soft
                # eight-point window preserves the original quality priority.
                best = max(score for score, _ in rows)
                eligible = [i for i, (score, _) in enumerate(rows)
                            if score >= best - 8]
                ix = min(eligible, key=lambda i: (
                    by_topic[rows[i][1]['focus_issue']],
                    chosen_venues[publication_venue(rows[i][1])],
                    history[publication_venue(rows[i][1])],
                    -rows[i][0], rows[i][1]['candidate_id']))
                score, item = rows.pop(ix)
                by_topic[item['focus_issue']] += 1
                chosen_venues[publication_venue(item)] += 1
                output.append(item)
        return output

    core = diverse_order(core)
    external = diverse_order(external)
    # A dedicated GLOBAL scanner does not reserve 15% of its batch for EU/UK.
    # Choose external subjects first, regardless of publisher nationality.
    # EU-only rows are ignored by default in online discovery (no EU targets).
    preferred_external = min(len(external), ceil(max_candidates * OUTSIDE_EU_UK_SHARE))
    selected = external[:preferred_external]
    external = external[preferred_external:]
    n_core = max(0, max_candidates-len(selected))
    selected.extend(core[:n_core])
    core = core[n_core:]
    if len(selected) < max_candidates:
        selected.extend(external[:max_candidates-len(selected)])
    if len(selected) < max_candidates:
        selected.extend(core[:max_candidates-len(selected)])
    return selected[:max_candidates]


def crossref_date(item):
    # Crossref `created` is the registration date, NOT the publication date.
    for field in ('published', 'published-online', 'published-print'):
        parts = (item.get(field) or {}).get('date-parts') or []
        if parts and parts[0]:
            try:
                return '-'.join(f'{int(n):0{4 if i == 0 else 2}d}' for i, n in enumerate(parts[0][:3]))
            except (TypeError, ValueError):
                pass
    return ''


def _first_text(value):
    return clean(value[0] if isinstance(value, list) and value else value if isinstance(value, str) else '')


def relevance_work(source, work, *, allowed_topics=None, expected_region=None,
                   expected_topic=None):
    """Only indexed, identifiable scholarly works become discovery candidates.

    A DOI and identifiable publishing venue are mandatory. That is *not* a
    verification of the full text, quality or integrity: those remain review
    steps, and no unverified item is marked as a retained Radar publication.
    """
    if source == 'openalex':
        kind = clean(work.get('type')).lower()
        if kind not in ACCEPTED_OPENALEX_TYPES or work.get('is_retracted') is True:
            return None
        title = clean(work.get('display_name'))
        abstract = openalex_abstract(work.get('abstract_inverted_index'))
        doi = clean(work.get('doi'))
        venue = clean(((work.get('primary_location') or {}).get('source') or {}).get('display_name'))
        published = clean(work.get('publication_date'))
    elif source == 'crossref':
        kind = clean(work.get('type')).lower()
        if kind not in ACCEPTED_CROSSREF_TYPES or 'is-retraction-of' in (work.get('relation') or {}):
            return None
        title = _first_text(work.get('title'))
        # Crossref abstracts may contain JATS/XML; index text, not markup.
        abstract = re.sub(r'<[^>]+>', ' ', clean(work.get('abstract')))
        doi = clean(work.get('DOI'))
        venue = _first_text(work.get('container-title')) or (
            clean(work.get('publisher')) if kind in {'book','book-chapter','report'} else '')
        published = crossref_date(work)
    else:
        return None
    doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi, flags=re.I)
    doi = re.sub(r'^doi:', '', doi, flags=re.I).strip()
    if not title or not doi or not venue or not re.match(r'^10\.\d{4,9}/\S+$', doi, re.I):
        return None
    if re.search(r'\b(?:retraction|withdrawn|corrigendum|erratum|expression of concern)\b', title, re.I):
        return None
    if not publication_date_in_scope(published):
        return None
    if (BIBLIOMETRIC_STUDY_TITLE.search(title)
            or (expected_topic or '').casefold() in EXCLUDED_FUTURE_TOPICS):
        return None
    match = regional_matching(title, abstract, allowed_topics=allowed_topics,
                              expected_region=expected_region, expected_topic=expected_topic)
    if not match:
        return None
    canonical = doi.casefold()
    link = 'https://doi.org/' + doi
    candidate = {
        'candidate_id': 'REL-'+hashlib.sha256(canonical.encode()).hexdigest()[:14],
        'group_id': 'relevance-focus', 'role_in_group': 'primary',
        'candidate_kind': 'substantive_publication', 'title': title, 'source': venue,
        'date': published, 'doi': doi, 'url': link,
        'publication_type': kind, 'discovery_provider': source,
        'focus_region': expected_region or match['matched_locations'][0],
        'focus_group': match['primary_group'],
        'focus_topics': match['matched_topics'],
        'temporal_lens': match['temporal_lens'],
        'focus_score': match['score'],
        'focus_issue': expected_topic or match['matched_topics'][0],
        'aboutness_basis': match['aboutness_basis'],
        'geographic_evidence': match['geographic_evidence'],
        'future_ri_question': match['future_ri_question'],
        'scope': 'global-topic-place; no EU relevance required',
        'source_integrity_status': 'unverified — mandatory independent Deep Scan',
        'curator_note': 'Global R&I futures question: ' + match['future_ri_question'] +
                        ' Evidence to test: ' + match['geographic_evidence'] +
                        '. Indexed bibliographic lead, not independent verification or evidence of a forecast.',
    }
    return canonical, match['score'], candidate


def discover(path: Path, max_seconds=FOCUSED_DISCOVERY_SECONDS, max_candidates=110,
             *, session=None, clock=None, pause=None, archive_path=None):
    """Sustained focused search, not an optional two-minute preflight.

    `max_seconds` bounds the research-discovery period, NOT validation, admission,
    rebuilding the corpus, workbook generation or the GitHub job.  Empty candidate
    sets do not terminate discovery.  If all providers fail, fail visibly rather
    than reporting a green two-minute scan or idling to disguise the problem.
    """
    import requests  # no network dependency for backfill-only
    if session is None:
        session = requests.Session()
    session.headers.update({'User-Agent':'Global-RI-Relevance-Focus/4.0 (public research discovery)'})
    clock = clock or time.monotonic
    pause = pause or time.sleep
    max_seconds = float(max_seconds)
    if max_seconds <= 0:
        raise ValueError('Focused discovery duration must be positive')
    now = datetime.now(timezone.utc)
    previous_archive = read_discovery_archive(archive_path) if archive_path else {}
    slot = next_rotation_slot(previous_archive, now)
    past_snapshots = (historical_discovery_snapshots()
                      if archive_path and previous_archive.get('archive_mode') !=
                      'cumulative-doi-deduplicated' else [])
    # Pre-v4 leads have never passed the new aboutness check. They can be
    # rediscovered and upgraded rather than being permanently grandfathered in.
    seen_dois = {doi_identity(lead) for document in [*past_snapshots, previous_archive]
                 for lead in document.get('candidates', []) if isinstance(lead, dict)
                 and lead.get('aboutness_basis')}
    seen_dois.discard('')
    api_key = clean(os.environ.get('OPENALEX_API_KEY'))
    crossref_mailto = clean(os.environ.get('CROSSREF_MAILTO'))
    known = {clean(x.get('link') or x.get('url')).lower().rstrip('/')
             for area in ('strand_a','strand_b','strand_c')
             for x in load('radar.json',{}).get(area,[])}
    # The verified Deep Scan store can retain works absent from the current
    # active/scanner lists. Avoid rediscovering an already evaluated URL.
    for key, row in load('deep_scan_work_state.json', {}).get('records', {}).items():
        if key.startswith('link:'):
            known.add(key[5:].lower().rstrip('/'))
        if isinstance(row, dict) and row.get('url'):
            known.add(clean(row['url']).lower().rstrip('/'))
    known.discard('')
    for area in ('strand_a', 'strand_b', 'strand_c'):
        for row in load('radar.json', {}).get(area, []):
            if isinstance(row, dict) and doi_identity(row):
                seen_dois.add(doi_identity(row))
    active_focus = focus_areas()
    if not active_focus:
        raise RuntimeError('No existing active Radar topics/issues to anchor relevance search')
    picked = {}
    per_bucket = {}
    stats = Counter()
    blocked = set()
    cooldown_until = {'openalex': 0.0, 'crossref': 0.0}
    failures = {'openalex': 0, 'crossref': 0}
    start = clock()
    deadline = start + max_seconds
    last_progress = start
    # Iterable covers far more distinct queries/pages than one 25-minute window
    # can consume. Rotate region/issue focus and never reuse a completed search.
    plan = iter(focused_search_plan(slot, focus=active_focus))
    stats['main_radar_topics_issues'] = len(active_focus)
    successful_requests = 0
    while (remaining := deadline - clock()) > 0:
        if len(blocked) == 2:
            raise RuntimeError('Both focused discovery providers unavailable: '+str(dict(stats)))
        try:
            bucket, place, topic, lens, query, provider, page = next(plan)
        except StopIteration:
            raise RuntimeError('All focused searches exhausted before 25-minute window')
        if provider in blocked:
            continue
        now_mono = clock()
        if now_mono < cooldown_until[provider]:
            # Do not spin past hundreds of distinct queries while both services
            # are in a 429 cooldown. Back off before the next attempt.
            pause(min(5.0, cooldown_until[provider] - now_mono,
                      max(0.0, deadline - now_mono)))
            continue
        remaining = deadline - now_mono
        if remaining <= 0:
            break
        # Every attempt has a bounded deadline so no one HTTP call extends the
        # discovery window into the downstream processing time.
        timeout = min(12.0, max(0.25, remaining - 0.2))
        try:
            if provider == 'openalex':
                params = {
                    'search':query,
                    'filter':'from_publication_date:'+MIN_PUBLICATION_DATE.isoformat()+',to_publication_date:'+now.date().isoformat(),
                    'per-page':25, 'page':page,
                    'select':'id,display_name,doi,type,is_retracted,publication_date,primary_location,abstract_inverted_index',
                }
                if api_key: params['api_key'] = api_key
                resp = session.get('https://api.openalex.org/works', params=params, timeout=timeout)
            else:
                params = {
                    'query.bibliographic':query, 'rows':20, 'offset':(page-1)*20,
                    'filter':'from-pub-date:'+MIN_PUBLICATION_DATE.isoformat()+',until-pub-date:'+now.date().isoformat(),
                    'select':'DOI,type,publisher,relation,title,published,published-online,published-print,created,container-title,abstract,URL',
                }
                if crossref_mailto: params['mailto'] = crossref_mailto
                resp = session.get('https://api.crossref.org/works', params=params, timeout=timeout)
            stats['requests'] += 1
            if resp.status_code in (401, 403):
                stats[provider+'_auth_or_access_error'] += 1
                blocked.add(provider)
                print('Focused search provider denied access:',provider,resp.status_code,flush=True)
                continue
            if resp.status_code == 429:
                stats[provider+'_rate_limited'] += 1
                # Switch providers for now; retry this one at a controlled pace.
                cooldown_until[provider] = clock() + 90
                failures[provider] += 1
                if failures[provider] >= 6:
                    blocked.add(provider)
                continue
            if not resp.ok:
                stats[provider+'_http_error'] += 1
                failures[provider] += 1
                if failures[provider] >= 6:
                    blocked.add(provider)
                continue
            results = (resp.json().get('results',[]) if provider=='openalex'
                       else resp.json().get('message',{}).get('items',[]))
            successful_requests += 1
            stats[provider+'_queries_completed'] += 1
            failures[provider] = 0
            if not results:
                stats['empty_results'] += 1
            for work in results:
                if not isinstance(work, dict):
                    stats['malformed_work'] += 1
                    continue
                try:
                    rec = relevance_work(provider, work, allowed_topics=active_focus,
                                         expected_region=place, expected_topic=topic)
                except (ValueError, TypeError, AttributeError):
                    stats['malformed_work'] += 1
                    continue
                if rec is None:
                    continue
                canonical, score, candidate = rec
                if candidate['url'].lower().rstrip('/') in known or canonical in seen_dois:
                    stats['already_seen_doi_or_radar_work'] += 1
                    continue
                if canonical in picked and picked[canonical][0] >= score:
                    continue
                if canonical not in picked:
                    stats['candidate_matches'] += 1
                    per_bucket[bucket] = per_bucket.get(bucket, 0) + 1
                picked[canonical] = (score, bucket, candidate)
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
            stats[provider+'_network_or_payload_error'] += 1
            failures[provider] += 1
            if failures[provider] >= 6:
                blocked.add(provider)
            print('Focused search retryable error:',provider,type(exc).__name__,flush=True)
        if clock()-last_progress >= 60:
            print(f'Focused discovery +{clock()-start:.0f}s / {max_seconds:.0f}s: '
                  f'{successful_requests} successful queries, {len(picked)} relevance candidates',flush=True)
            last_progress = clock()
        # Per-request pacing is part of live discovery; it protects external APIs.
        if deadline-clock() > 0:
            pause(min(FOCUSED_REQUEST_PACING_SECONDS, deadline-clock()))
    if not successful_requests:
        raise RuntimeError('No successful focused discovery queries; no 25-minute scan can be claimed')
    source_history = previous_publication_venues(previous_archive, past_snapshots)
    candidates = balanced_candidates(picked, max_candidates,
                                     venue_history=source_history)
    stats['unique_publication_venues'] = len({publication_venue(row) for row in candidates
                                             if publication_venue(row)})
    stats['publication_venues_previously_seen'] = sum(
        bool(source_history[publication_venue(row)]) for row in candidates)
    stats['candidate_openalex'] = sum(row['discovery_provider'] == 'openalex'
                                      for row in candidates)
    stats['candidate_crossref'] = sum(row['discovery_provider'] == 'crossref'
                                      for row in candidates)
    stats['outside_eu_uk_candidates'] = sum(
        row['focus_group'] != 'EU / UK' for row in candidates)
    stats['eu_uk_candidates'] = len(candidates) - stats['outside_eu_uk_candidates']
    stats['unique_focus_topics'] = len({row['focus_issue'] for row in candidates})
    stats['unique_focus_places'] = len({row['focus_region'] for row in candidates})
    stats['seconds_spent_discovering'] = round(clock()-start,2)
    stats['successful_requests'] = successful_requests
    stats['coverage_buckets'] = len(per_bucket)
    out={'profile_version':'v4-global-aboutness-futures-25m',
         'batch_id':'relevance-'+now.strftime('%Y%m%dT%H%M%SZ'),
         'source_document':'OpenAlex and Crossref DOI-bearing, venue-identified publications; leads only',
         'compiled_at':datetime.now(timezone.utc).isoformat(),
         'policy':{'admission':'Separate global R&I Deep Scan must independently verify aboutness, source integrity and future R&I significance; indexed leads are never auto-admitted',
                   'topic_anchor':'Each matched issue/topic is evidenced in active Main Radar; neither European geography nor EU relevance is required',
                   'outside_eu_uk_target_share':OUTSIDE_EU_UK_SHARE,
                   'earliest_publication_date':MIN_PUBLICATION_DATE.isoformat(),
                   'time_perspectives':['Current state / developments','Possible future / scenarios'],
                   'discovery_seconds_target':max_seconds,
                   'processing_after_discovery':True,
                   'publication_source_rotation':'Soft journal/publisher diversity; publisher location cannot determine aboutness; Deep Scan must reject propaganda and unverifiable claims'},
         'candidates':candidates,'work_count':len(candidates),
         'discovery_stats':dict(stats)}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
    if archive_path is not None:
        archive_path = Path(archive_path)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        merged = cumulative_discoveries(previous_archive, out, slot=slot,
                                        older_snapshots=past_snapshots)
        # Atomic replacement: an interrupted write never truncates prior leads.
        temp_archive = archive_path.with_name(archive_path.name + '.tmp')
        temp_archive.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf8')
        os.replace(temp_archive, archive_path)
        print('Cumulative regional archive:', merged['work_count'], 'unique leads;',
              len(past_snapshots), 'historical Git snapshots examined', flush=True)
    print('Focused discovery complete:',len(candidates),'new candidates;',dict(stats),'->',path,flush=True)


def scan(candidate_path: Path):
    """Fail closed for the retired EU-Radar admission adapter.

    Global Relevance Focus now goes to its OWN source-reviewed Deep Scan.
    The ordinary European Radar is neither bypassed nor broadened by this lane.
    """
    raise RuntimeError(
        'Relevance Focus global candidates must NOT pass through ordinary EU Radar admission. '
        'Run: relevance_focus_deep_scan.py prepare; review its package; '
        'then relevance_focus_deep_scan.py import-inbox.')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['discover','scan','export-json'])  # scan: explicit retired error
    p.add_argument('--output',type=Path,default=Path(os.getenv('RUNNER_TEMP','/tmp'))/'relevance_candidates.json')
    p.add_argument('--candidates',type=Path,default=Path(os.getenv('RUNNER_TEMP','/tmp'))/'relevance_candidates.json')
    p.add_argument('--archive',type=Path,default=None,help='Scanner-owned cumulative, DOI-deduplicated discovery archive')
    p.add_argument('--max-seconds',type=int,default=FOCUSED_DISCOVERY_SECONDS)
    args=p.parse_args()
    if args.command=='discover': discover(args.output,max_seconds=args.max_seconds,archive_path=args.archive)
    elif args.command=='scan': return scan(args.candidates)
    else:
        data=compile_records();args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
        print('Relevance workbook:',len(data['verified']),'verified and retained,',len(data['pending']),'for review',flush=True)
    return 0


if __name__=='__main__':sys.exit(main())
