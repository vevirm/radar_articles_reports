"""Reader-facing names for the reasoning engine's controlled vocabulary.

One table, used by the card writer, the trend builder and (mirrored in JS) the
reader pages.  Every controlled object, family and cluster gets a natural noun
phrase so that cards never show engine keys ("materials advanced", "funding
route", "innovation regional capacity") or produce tautologies.

The labels are presentation only.  They do not change objects, claims, scores or
selection.  Keep them short, concrete and grammatical in these frames:

    "{X} is only as strong as {Y}"      "Europe may already own a lever for {X}"
    "{X} keeps coming back"              "access to {X}"
"""
from __future__ import annotations

import re
from typing import Any

OBJECT_LABELS: dict[str, str] = {
    # compute and AI infrastructure
    "compute.public_procurement": "joint public purchasing of AI compute",
    "compute.gigafactory": "Europe's AI gigafactories",
    "compute.access_time": "access to public AI compute",
    "compute.capacity": "European computing capacity",
    "compute.private_investment": "private investment in AI compute",
    "compute.gigafactory_cofinancing": "public co-financing for AI gigafactories",
    "datacentre.permitting": "data-centre permitting",
    "datacentre.energy_supply": "power for data centres",
    "datacentre.local_opposition": "local opposition to data centres",
    "datacentre.siting": "where data centres can be built",
    # quantum
    "quantum.equipment": "quantum equipment",
    "quantum.testing_infrastructure": "open quantum testing facilities",
    "quantum.machine": "European quantum computers",
    "quantum.standards": "quantum standards",
    "quantum.pilot_line": "quantum pilot lines",
    "quantum.communication_infrastructure": "quantum communication infrastructure",
    "quantum.governance": "quantum governance",
    # chips
    "chips.eu_inference_supplier": "European AI-chip suppliers",
    "chips.nvidia_gpu": "access to Nvidia GPUs",
    "chips.fab": "chip manufacturing in Europe",
    "chips.pilot_line": "chip pilot lines",
    "chips.international_cooperation": "international chip cooperation",
    # export controls and EU competence
    "export_control.regulation": "export-control rules",
    "export_control.competence": "national export-control powers",
    "export_control.licence_decision": "export-licence decisions",
    "eu_entities.export_access": "European access to controlled exports",
    "eu_bilateral_agreements": "the EU's bilateral agreements",
    # openness and research security
    "research.openness": "open science",
    "research.open_access": "open access to research",
    "research_security.self_assessment": "research-security self-assessment",
    "research_security.screening": "research-security screening",
    "research_security.espionage_case": "espionage in research",
    "grant.admissibility": "who may receive research grants",
    # talent
    "talent.recruitment_abroad": "recruiting researchers from abroad",
    "talent.retention": "researcher retention",
    "talent.career_structure": "research careers",
    # EU funding programmes
    "horizon.association": "association to Horizon Europe",
    "horizon.access": "access to Horizon Europe",
    "horizon.exclusion": "exclusion from Horizon Europe",
    "horizon.budget_2028_34": "the next Horizon budget",
    "horizon.success_rate": "Horizon Europe success rates",
    "funding.route": "research funding",
    # materials and energy
    "materials.critical_raw": "critical raw materials",
    "materials.advanced": "advanced materials",
    "energy.grid": "the power grid",
    "energy.zinc_air_cell": "zinc-air batteries",
    # capital
    "finance.us_hyperscaler_debt_exposure": "exposure to US hyperscaler debt",
    "finance.gulf_capital": "Gulf capital in European technology",
    "finance.strategic_investment": "strategic investment",
    "finance.venture_capital": "venture capital",
    "finance.digital_market_infrastructure": "digital financial-market infrastructure",
    # strategic goals
    "goal.strategic_autonomy": "strategic autonomy",
    # research system
    "research.collaboration": "research collaboration",
    "research.system_capacity": "research capacity",
    "research.system_governance": "research governance",
    "research.assessment": "research assessment",
    "research.system_efficiency": "research-system efficiency",
    "research.knowledge_transfer": "knowledge transfer",
    "research.workforce_quality": "the research workforce",
    "research.infrastructure": "research infrastructure",
    "research.infrastructure_access": "access to research infrastructure",
    "research.public_support": "public support for research",
    # AI governance
    "ai.governance": "AI governance",
    "ai.adoption": "AI adoption",
    "ai.public_sector_capacity": "public-sector AI capacity",
    "ai.research_use": "AI in research",
    "ai.research_governance": "rules for AI in research",
    "ai.workforce_evaluation": "AI in hiring and evaluation",
    # digital
    "digital.sovereignty": "digital sovereignty",
    "digital.governance": "digital regulation",
    "digital.infrastructure": "digital infrastructure",
    "digital.international_partnerships": "international digital partnerships",
    "digital.public_procurement": "public digital procurement",
    # defence and dual use
    "defence.innovation_funding": "defence-innovation funding",
    "defence.drone_capability": "European drone capability",
    "defence.drone_research": "drone research",
    "innovation.dual_use": "dual-use innovation",
    # innovation and industry
    "innovation.regional_capacity": "regional innovation capacity",
    "innovation.deep_tech_startups": "deep-tech start-ups",
    "innovation.system_performance": "innovation performance",
    "innovation.green_technology": "green technology",
    "industrial.ev_capacity": "electric-vehicle production",
    "industrial.technology_complexity": "industrial sophistication",
    "industrial.competitiveness": "industrial competitiveness",
    # other domains
    "cybersecurity.sme_resilience": "small firms' cyber resilience",
    "green.circular_economy": "the circular economy",
    "green.innovation": "green innovation",
    "health.microbiome_project": "microbiome research",
    "health.stem_cell_platform": "stem-cell platforms",
    "health.data_infrastructure": "health-data infrastructure",
    "critical_infrastructure.resilience": "critical-infrastructure resilience",
    # methods (never used in world reasoning; labelled for completeness)
    "methods.creativity": "creativity methods",
    "methods.foresight": "foresight",
    "methods.horizon_scanning": "horizon scanning",
    "methods.delphi": "Delphi studies",
    "methods.scenario": "scenario methods",
    "methods.roadmapping": "roadmapping",
    "methods.technology_detection": "technology detection",
    "methods.evaluation": "evaluation methods",
    "methods.anticipatory_governance": "anticipatory governance",
    "methods.robust_policy": "robust policy design",
    "methods.system_modelling": "system modelling",
}

# "family:<prefix>" groups every object sharing a prefix.
FAMILY_LABELS: dict[str, str] = {
    "research": "the European research system",
    "research_security": "research security",
    "talent": "research talent",
    "digital": "digital policy",
    "ai": "AI",
    "compute": "AI compute",
    "quantum": "quantum technology",
    "chips": "semiconductors",
    "horizon": "Horizon Europe",
    "export_control": "export controls",
    "finance": "technology finance",
    "innovation": "innovation",
    "industrial": "industrial capacity",
    "defence": "defence R&I",
    "green": "green innovation",
    "health": "health research",
    "goal": "strategic goals",
    "funding": "research funding",
    "datacentre": "data centres",
    "materials": "materials",
    "cybersecurity": "cybersecurity",
    "critical_infrastructure": "critical infrastructure",
    "energy": "energy",
    "grant": "research grants",
    "eu_entities": "EU exports",
}

CLUSTER_LABELS: dict[str, str] = {
    "compute_ai": "AI and compute",
    "permitting_siting": "data-centre siting",
    "quantum": "quantum technology",
    "chips": "semiconductors",
    "startups_chips_industry": "chip start-ups",
    "export_controls": "export controls",
    "eu_competence": "EU powers",
    "openness": "open science",
    "research_security": "research security",
    "talent": "research talent",
    "funding_programme": "EU research funding",
    "programme_association": "programme association",
    "exclusion_conditionality": "exclusion and conditionality",
    "materials_energy": "materials and energy",
    "capital_markets": "capital for European technology",
    "strategic_goals": "strategic autonomy",
    "health": "health research",
    "research_system": "the research system",
    "research_infrastructure": "research infrastructure",
    "ai_governance": "AI governance",
    "digital_governance": "digital governance",
    "defence_dual_use": "defence and dual-use R&I",
    "innovation_ecosystem": "innovation",
    "industrial_competitiveness": "industrial competitiveness",
    "cybersecurity": "cybersecurity",
    "green_transition": "the green transition",
    "critical_infrastructure": "critical infrastructure",
    "methods": "foresight methods",
}

# What is concretely at stake when something moves in a cluster.  Used for the
# one-line "so what" so that a consequence names the thing Europe could gain or
# lose instead of a generic "capacity, access or room to act".
CLUSTER_STAKES: dict[str, str] = {
    "compute_ai": "what European researchers and firms can train and run, and on whose hardware",
    "permitting_siting": "where Europe's compute can physically be built, and how fast",
    "quantum": "whether European quantum science turns into machines Europe controls",
    "chips": "Europe's access to the chips everything else runs on",
    "startups_chips_industry": "whether European chip start-ups grow at home",
    "export_controls": "who decides which technology Europe may share or receive",
    "eu_competence": "whether Europe can act as one",
    "openness": "how open European science can stay",
    "research_security": "whom European labs can work with, and on what",
    "talent": "who does Europe's research, and where they choose to do it",
    "funding_programme": "what Europe can afford to research, and with whom",
    "programme_association": "which countries do research with Europe on equal terms",
    "exclusion_conditionality": "who is left out of European research",
    "materials_energy": "what Europe can build without outside suppliers",
    "capital_markets": "whether European technology firms can grow without selling abroad",
    "strategic_goals": "Europe's room to act without asking permission",
    "health": "Europe's capacity to research and produce health technology",
    "research_system": "the output and resilience of European research",
    "research_infrastructure": "which researchers get to use Europe's big facilities",
    "ai_governance": "who sets the rules for AI used in Europe",
    "digital_governance": "who controls Europe's data and digital services",
    "defence_dual_use": "how fast new defence technology reaches the field",
    "innovation_ecosystem": "whether European research becomes European companies",
    "industrial_competitiveness": "whether Europe keeps making what it invents",
    "cybersecurity": "whether European systems stay up under attack",
    "green_transition": "the pace and cost of Europe's clean-tech transition",
    "critical_infrastructure": "whether essential systems keep running under stress",
}

COUNTRY_CODES: dict[str, str] = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia", "CY": "Cyprus",
    "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia", "FI": "Finland", "FR": "France",
    "DE": "Germany", "GR": "Greece", "EL": "Greece", "HU": "Hungary", "IE": "Ireland",
    "IT": "Italy", "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta",
    "NL": "the Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SK": "Slovakia", "SI": "Slovenia", "ES": "Spain", "SE": "Sweden", "NO": "Norway",
    "CH": "Switzerland", "UK": "the United Kingdom", "GB": "the United Kingdom",
    "US": "the United States", "USA": "the United States", "CN": "China", "UA": "Ukraine",
    "JP": "Japan", "KR": "South Korea", "CA": "Canada", "IS": "Iceland", "TR": "Turkey",
    "Netherlands": "the Netherlands", "United Kingdom": "the United Kingdom",
    "United States": "the United States",
}

EU_MEMBER_STATES = {
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia",
    "Finland", "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia",
    "Lithuania", "Luxembourg", "Malta", "the Netherlands", "Poland", "Portugal", "Romania",
    "Slovakia", "Slovenia", "Spain", "Sweden",
}

# Short, familiar names for frequent actors and sources.
_SHORT_NAMES: tuple[tuple[str, str], ...] = (
    (r"^EuroHPC(?: Joint Undertaking| JU)?$", "EuroHPC"),
    (r"^European Commission\b.*", "European Commission"),
    (r"^European Union$", "the EU"),
    (r"^Council of the European Union$", "EU Council"),
    (r"^European Parliament\b.*", "European Parliament"),
    (r"^(?:European Commission,? )?Joint Research Centre\b.*|^JRC Publications Repository$", "JRC"),
    (r"^EU Publications Office$|^Publications Office of the European Union$", "EU Publications Office"),
    (r"^European Research Council(?: Executive Agency.*)?$", "European Research Council"),
    (r"^European Research Executive Agency$", "REA"),
    (r"^European Innovation Council and SMEs Executive Agency$", "EISMEA"),
    (r"^European Health and Digital Executive Agency$", "HaDEA"),
    (r"^Marie Skłodowska-Curie Actions$", "MSCA"),
    (r"^Finnish Institute of International Affairs$", "FIIA"),
    (r"^European Council on Foreign Relations$", "ECFR"),
    (r"^The Hague Centre for Strategic Studies$", "HCSS"),
    (r"^CERRE\b.*", "CERRE"),
    (r"^Hybrid CoE\b.*", "Hybrid CoE"),
    (r"^Sitra\b.*", "Sitra"),
    (r"^EU Digital Strategy$|^European Commission — Digital Strategy$", "European Commission"),
    (r"^Research Council of Finland$", "Research Council of Finland"),
    (r"^ERA Portal Austria$", "ERA Portal Austria"),
)


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def family_of(key: str) -> str:
    key = clean(key)
    return key.split(":", 1)[1] if key.startswith("family:") else ""


def cluster_of_key(key: str) -> str:
    key = clean(key)
    return key.split(":", 1)[1] if key.startswith("cluster:") else ""


def label(key: Any, *, fallback: str = "European research and innovation") -> str:
    """Natural noun phrase for an object, family or cluster key."""
    key = clean(key)
    if not key:
        return fallback
    if key in OBJECT_LABELS:
        return OBJECT_LABELS[key]
    fam = family_of(key)
    if fam:
        return FAMILY_LABELS.get(fam, fam.replace("_", " "))
    cl = cluster_of_key(key)
    if cl:
        return CLUSTER_LABELS.get(cl, cl.replace("_", " "))
    if key.startswith("shock_pressure."):
        return key.split(".", 1)[1].replace("_", " ")
    # Unknown key: build a readable phrase rather than exposing the key order.
    parts = key.split(".")
    if len(parts) == 2:
        head, tail = parts
        tail = tail.replace("_", " ")
        return tail if head in tail or head in {"goal", "finance", "research"} else f"{tail} ({head.replace('_', ' ')})"
    return key.replace(".", " ").replace("_", " ")


def cap(text: str) -> str:
    text = clean(text)
    if not text:
        return text
    # Keep brand-like words (e.g. "eIF", "iPhone") as they are.
    if len(text) > 1 and text[0].islower() and text[1].isupper():
        return text
    return text[0].upper() + text[1:]


def cluster_label(cluster: str) -> str:
    return CLUSTER_LABELS.get(clean(cluster), clean(cluster).replace("_", " "))


def stake(cluster: str) -> str:
    return CLUSTER_STAKES.get(clean(cluster), "")


def country_name(value: Any) -> str:
    v = clean(value)
    return COUNTRY_CODES.get(v, COUNTRY_CODES.get(v.upper(), v))


def short_name(value: Any) -> str:
    """Short, familiar name for an actor or a source."""
    v = clean(value)
    if not v:
        return ""
    for rx, repl in _SHORT_NAMES:
        if re.match(rx, v):
            return repl
    # "Study authors", "Study author" are not names.
    if re.match(r"^study authors?$", v, re.I):
        return ""
    # Long journal / proceedings names: keep up to the first separator.
    v = re.split(r"\s+[—–]\s+|\s*\(|,\s+Directorate", v)[0].strip()
    return v


def join_names(items: list[str], conj: str = "and") -> str:
    items = [clean(x) for x in items if clean(x)]
    items = list(dict.fromkeys(items))
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return ", ".join(items[:-1]) + f" {conj} {items[-1]}"
