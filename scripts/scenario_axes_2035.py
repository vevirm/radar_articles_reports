"""Manual 2035 scenario axes.

This file is the small human-curated part of the 2035 scenario system.
To add, remove or revise a lens, edit only the axis definitions here. The
scenario builder selects and recombines current published findings underneath
those axes on every reasoning refresh. Reader-language rewriting is a separate
presentation workflow.

Conventions
-----------
* ``vertical`` is named first in ``title`` (Y axis).
* ``horizontal`` is named second (X axis).
* ``positive_pole`` tells the builder which end opportunities/capacity-building
  findings normally pull toward. Risks and shocks normally pull toward the
  opposite end. This is a scenario-affinity heuristic, not a forecast.
* ``objects`` and ``keywords`` define what evidence belongs to an axis. They are
  part of the axis definition, not scenario copy.
"""

AXIS_FRAMES = (
    {
        "id": "resources-connectedness",
        "title": "Resources × Global connectedness",
        "question": "Can Europe mobilise the resources it needs, and how connected is it to the world?",
        "legacy": True,
        "vertical": {
            "key": "resources",
            "title": "Resources",
            "low": {"id": "fewer_resources", "label": "Fewer resources", "short": "Fewer resources"},
            "high": {"id": "more_resources", "label": "More resources", "short": "More resources"},
            "positive_pole": "high",
            "objects": (
                "compute.", "finance.", "funding.", "horizon.budget", "chips.", "quantum.",
                "innovation.", "industrial.", "research.system_capacity", "research.infrastructure",
                "datacentre.", "ai.", "green.", "health.", "materials.", "family:compute",
                "family:finance", "family:industrial", "family:innovation", "cluster:compute_ai",
            ),
            "keywords": ("funding", "capacity", "investment", "infrastructure", "resources", "budget", "compute"),
        },
        "horizontal": {
            "key": "connectedness",
            "title": "Global connectedness",
            "low": {"id": "less_connected", "label": "Less connected", "short": "Less connected"},
            "high": {"id": "more_connected", "label": "More connected", "short": "More connected"},
            "positive_pole": "high",
            "objects": (
                "research.collaboration", "research.openness", "research.open_access", "horizon.association",
                "horizon.access", "talent.", "digital.international_partnerships", "chips.international_cooperation",
                "research.infrastructure_access", "eu_bilateral_agreements",
            ),
            "keywords": ("collaboration", "international", "association", "partners", "cross-border", "open access"),
        },
    },
    {
        "id": "integration-dependency",
        "title": "European integration × Strategic dependency",
        "question": "Does Europe act together, and how much does it depend on capabilities outside Europe?",
        "vertical": {
            "key": "integration",
            "title": "European integration",
            "low": {"id": "fragmented", "label": "More fragmented", "short": "Fragmented"},
            "high": {"id": "integrated", "label": "More integrated", "short": "Integrated"},
            "positive_pole": "high",
            "objects": (
                "research.collaboration", "research.system_governance", "horizon.", "research.infrastructure",
                "research.infrastructure_access", "digital.international_partnerships", "chips.international_cooperation",
                "eu_bilateral_agreements", "innovation.regional_capacity", "family:research", "family:digital",
            ),
            "keywords": ("collaboration", "common", "european system", "cross-border", "interregional", "association", "governance"),
        },
        "horizontal": {
            "key": "dependency",
            "title": "Strategic dependency",
            "low": {"id": "less_dependent", "label": "Less dependent", "short": "More autonomous"},
            "high": {"id": "more_dependent", "label": "More dependent", "short": "More dependent"},
            "positive_pole": "low",
            "objects": (
                "goal.strategic_autonomy", "digital.sovereignty", "materials.critical_raw", "export_control.",
                "compute.", "chips.", "industrial.competitiveness", "finance.strategic_investment",
                "research_security.", "eu_entities.export_access", "cluster:materials_energy", "cluster:capital_markets",
            ),
            "keywords": ("dependency", "autonomy", "sovereign", "supplier", "chokepoint", "foreign", "export control", "critical raw"),
        },
    },
    {
        "id": "talent-scale-up",
        "title": "Talent × Scale-up capacity",
        "question": "Can Europe attract and keep the people, and can it grow what they create?",
        "vertical": {
            "key": "talent",
            "title": "Talent",
            "low": {"id": "talent_friction", "label": "Talent loss and friction", "short": "Talent friction"},
            "high": {"id": "talent_magnet", "label": "Talent attraction and retention", "short": "Talent magnet"},
            "positive_pole": "high",
            "objects": (
                "talent.", "research.workforce_quality", "research.collaboration", "family:talent",
            ),
            "keywords": ("talent", "researcher", "career", "recruitment", "retention", "brain drain", "workforce"),
        },
        "horizontal": {
            "key": "scale_up",
            "title": "Scale-up capacity",
            "low": {"id": "weak_scale_up", "label": "Weak scale-up capacity", "short": "Weak scaling"},
            "high": {"id": "strong_scale_up", "label": "Strong scale-up capacity", "short": "Strong scaling"},
            "positive_pole": "high",
            "objects": (
                "finance.venture_capital", "finance.strategic_investment", "innovation.system_performance",
                "innovation.deep_tech_startups", "research.knowledge_transfer", "industrial.competitiveness",
                "compute.public_procurement", "funding.route", "family:innovation", "family:industrial", "cluster:capital_markets",
            ),
            "keywords": ("venture capital", "scale-up", "scale up", "commercial", "investment", "procurement", "innovation performance", "competitiveness"),
        },
    },
    {
        "id": "scale-up-dependency",
        "title": "Scale-up capacity × Strategic dependency",
        "question": "Can Europe turn innovation into scale, and whose capabilities make that scale possible?",
        "vertical": {
            "key": "scale_up",
            "title": "Scale-up capacity",
            "low": {"id": "weak_scale_up", "label": "Weak scale-up capacity", "short": "Weak scaling"},
            "high": {"id": "strong_scale_up", "label": "Strong scale-up capacity", "short": "Strong scaling"},
            "positive_pole": "high",
            "objects": (
                "finance.venture_capital", "finance.strategic_investment", "innovation.system_performance",
                "innovation.deep_tech_startups", "research.knowledge_transfer", "industrial.competitiveness",
                "compute.public_procurement", "funding.route", "family:innovation", "family:industrial", "cluster:capital_markets",
            ),
            "keywords": ("venture capital", "scale-up", "scale up", "commercial", "investment", "procurement", "innovation performance", "competitiveness"),
        },
        "horizontal": {
            "key": "dependency",
            "title": "Strategic dependency",
            "low": {"id": "less_dependent", "label": "Less dependent", "short": "More autonomous"},
            "high": {"id": "more_dependent", "label": "More dependent", "short": "More dependent"},
            "positive_pole": "low",
            "objects": (
                "goal.strategic_autonomy", "digital.sovereignty", "materials.critical_raw", "export_control.",
                "compute.", "chips.", "industrial.competitiveness", "finance.strategic_investment",
                "research_security.", "eu_entities.export_access", "cluster:materials_energy", "cluster:capital_markets",
            ),
            "keywords": ("dependency", "autonomy", "sovereign", "supplier", "chokepoint", "foreign", "export control", "critical raw"),
        },
    },
)

FRAME_BY_ID = {frame["id"]: frame for frame in AXIS_FRAMES}
DEFAULT_FRAME_ID = AXIS_FRAMES[0]["id"]
