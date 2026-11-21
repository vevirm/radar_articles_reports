"""Pure, auditable mechanism reasoning over verified premise tuples.

These are not summaries of the underlying publications. They are *deductions from
causal-graph structures* plus explicitly reviewed conditional bridges. Causal
edges remain model assumptions until their observables are tested. Any changed
premise or bridge produces changed narratives on the next manual run.
"""
from __future__ import annotations
from .core import _projected_action, UNREALIZED


def name(identifier: str) -> str:
    words=identifier.replace('_', ' ').replace('.', ' ').split()
    acronyms={'ai':'AI','eu':'EU','sme':'SME','r&d':'R&D','smes':'SMEs'}
    return ' '.join(acronyms.get(w.lower(),w) for w in words)


def _proper(txt: str) -> str:
    txt = str(txt).strip().rstrip('.')
    return txt[:1].lower() + txt[1:] if txt else txt


def _stage(claim: dict) -> str:
    status = (claim.get('status') or '').lower()
    if status in UNREALIZED or _projected_action(claim):
        return 'commitment-to-delivery'
    if status in {'operating','in_force','delivered'}:
        return 'delivery-to-diffusion'
    return 'institutional-action-to-uptake'


def convergence(a: dict, b: dict, target: str, claims: list[dict]) -> dict:
    x, y, z = name(a['from']), name(b['from']), name(target)
    a_stage, b_stage = _stage(claims[0]), _stage(claims[1])
    if a_stage==b_stage=='commitment-to-delivery':
        phase_impact='Both routes are presently in the commitment-to-delivery stage: complementary announcements create an option to coordinate, not yet joint capacity.'
    elif a_stage==b_stage=='delivery-to-diffusion':
        phase_impact='Both routes are already at the delivery-to-diffusion interface: access design, not programme announcement, determines how widely their effects spread.'
    else:
        phase_impact='The routes are at different institutional stages, so the slower route sets the earliest point at which their combined contribution can be judged.'
    return {
        'inference': (f"The system is acquiring two distinct routes into {z}: {x} and {y}. "
           f"That changes the strategic problem from expanding either input in isolation to converting their "
           f"combined availability into usable {z}. The binding constraint shifts toward the interfaces "
           f"between programmes, users and downstream capabilities, rather than the simple number of initiatives. "
           f"{phase_impact}"),
        'mechanism': (f"CONVERGENCE / FAN-IN: {x} → {z} ← {y}. Route one transmits only when "
           f"{_proper(a['condition'])}; route two transmits only when {_proper(b['condition'])}. "
           f"The observed intervention stages are {a_stage} and {b_stage}, so the common downstream "
           f"measurement is the decisive arbiter. This is an inference from two pathways, not a third source claim."),
        'second_order': (f"A coordination market emerges at the interface of {x} and {y}: institutions "
            f"able to align the two routes gain leverage over {z}. An apparent increase in upstream activity "
            f"can coexist with weak aggregate impact when either route stalls; success therefore becomes "
            f"uneven rather than proportional to aggregate spending."),
        'decision': (f"Evaluate the marginal effect of coordinating {x} and {y} on a common {z} metric, "
           f"rather than ranking each initiative by its own input or expenditure."),
        'topology': 'two-source fan-in',
    }


def cascade(first: dict, second: dict, claims: list[dict]) -> dict:
    x, mid, z = name(first['from']), name(first['to']), name(second['to'])
    return {
        'inference': (f"A two-stage reconfiguration connects {x} to {z} through {mid}. "
           f"The disruptive feature is not the first intervention by itself: {mid} becomes a "
           f"transmission point. Changes that accumulate there alter the distribution, pace or accessibility "
           f"of {z} across the wider system. If that intermediate gate saturates, system-wide effects can "
           f"change abruptly even while upstream activity continues to rise."),
        'mechanism': (f"DEPENDENCY CASCADE: {x} → {mid} → {z}. First gate: "
           f"{_proper(first['condition'])}. Second gate: {_proper(second['condition'])}. "
           f"Both steps must function for the full cascade; evidence of upstream activation alone "
           f"does not establish downstream transformation."),
        'second_order': (f"The policy exposure moves one step downstream: once {x} is activated, "
           f"failures at {mid} become more consequential for {z}. A previously local bottleneck "
           f"becomes a system constraint, with resource diversion and uneven access as plausible secondary effects."),
        'decision': (f"Monitor the first and second gate separately. Prioritise mitigation at {mid} "
           f"before interpreting investments in {x} as a shift in {z}."),
        'topology': 'two-hop dependency cascade',
    }


def chokepoint(first:dict, second:dict, target:str, claims:list[dict])->dict:
    x,y,z=name(first['from']),name(second['from']),name(target)
    stage_x,stage_y=_stage(claims[0]),_stage(claims[1])
    return {
      'inference':(f'The critical vulnerability moves to a shared {z} interface. '
          f'Additional effort in {x} and {y} can cease to deliver proportional system-wide progress '
          f'once both pathways depend on constrained {z}. The disruption is a shift of the binding '
          f'constraint from upstream capacity creation to shared downstream allocation and throughput. '
          f'That shift redistributes access and bargaining power before total investment falls.'),
      'mechanism':(f'STRESSED FAN-IN / COMPETITION FOR A SHARED NODE: {x} → {z} ← {y}. '
          f'Route one requires {first["condition"]}; route two requires {second["condition"]}. '
          f'Currently evidenced stages are {stage_x} and {stage_y}; the adverse diagnosis at the '
          f'target alone does not establish that either programme has caused a queue or crisis.'),
      'second_order':(f'When a shared {z} gate is capacity-limited, locally successful programmes can '
          f'create system-wide displacement: stronger users obtain the scarce interface first, '
          f'weaker users lose effective access, and budgets shift from innovation to securing slots. '
          f'A new bottleneck can emerge without a decline in upstream inputs.'),
      'decision':(f'Monitor common {z} capacity, queueing, and distribution of access by beneficiary. '
          f'Expand the shared gate or coordinate the two routes before scaling either {x} or {y} alone.'),
      'topology':'stressed two-source fan-in and choke point'
    }


def enabling(bridge:dict, claim:dict) ->dict:
    x, z = name(bridge['from']), name(bridge['to'])
    status=_stage(claim)
    return {
        'inference': (f"The strategic opening is a conversion interface between {x} and {z}. "
          f"The verified intervention establishes an upstream resource or institutional lever; "
          f"the separately documented target establishes the problem to solve. Linking them creates "
          f"an advantage for actors who make that resource usable in {z}, rather than for actors who "
          f"only expand the headline supply of {x}."),
        'mechanism': (f"CAPABILITY CONVERSION / {status}: {x} → tested interface → {z}. "
          f"The conversion interface is operational only when {_proper(bridge['condition'])}. "
          f"What is inferred is a location for intervention, not a claim of realized downstream benefits."),
        'second_order': (f"Demand shifts toward interoperability, access design, evaluation and complementary "
          f"skills at the {x}–{z} interface; coordination can become more valuable than another "
          f"upstream funding announcement."),
        'decision': (f"Back cross-system pilots that demonstrate transfer from {x} into independently "
          f"measured {z}, and discontinue scaling based only on inputs."),
        'topology': 'enabler-to-adoption bridge',
    }


def conversion_risk(bridge:dict, claim:dict) ->dict:
    x,z=name(bridge['from']),name(bridge['to'])
    stage=_stage(claim)
    return {
      'inference':(f"An input–outcome divergence is emerging between {x} and {z}. "
         f"Resources, commitments or institutional activity in {x} can grow faster than the "
         f"ability of {z} to absorb them. The causal risk is misallocated capacity: measured programme "
         f"success rises while the system-level constraint remains in place."),
      'mechanism':(f"CONVERSION BOTTLENECK / {stage}: {x} → missing delivery or uptake "
         f"interface → {z}. Critical condition: {_proper(bridge['condition'])}. The direct failure "
         f"mode is a broken transmission link, not necessarily a lack of upstream investment."),
      'second_order':(f"Further resources can amplify queueing, concentration or reputational "
         f"pressure without shifting {z}; late detection raises the cost of correcting the programme."),
      'decision':(f"Create a threshold for independent {z} outcomes before expanding {x}."),
      'topology':'conversion bottleneck',
    }


def constraint_risk(bridge:dict) ->dict:
    x,z=name(bridge['from']),name(bridge['to'])
    return {
     'inference':(f"A rule or control in {x} creates a cross-system exposure for {z}: "
        f"restrictions imposed at one node can redirect participation and capability formation at another. "
        f"The consequence is not simply slower activity but possible restructuring of who can join, "
        f"which expertise circulates and where networks consolidate."),
     'mechanism':(f"NEGATIVE DEPENDENCY / GATEKEEPING: {x} ┤ {z}. Transmission is material "
        f"when {_proper(bridge['condition'])}. The observed action and assessed target are source facts; "
        f"the scale of cross-node impact is the inferred element."),
     'second_order':(f"Participants can reroute collaborations outside affected channels. This may "
        f"reduce one exposure while creating new concentration, compliance and coordination costs."),
     'decision':(f"Track partner substitution and measured barriers in {z} as well as the "
        f"security objectives of {x}; the net effect is not readable from control counts alone."),
     'topology':'constraint and network rerouting',
    }


# Names, interactions and strategic implications arise from intersections of all
# THREE axes, not from pasting their descriptions into eight text permutations.
SCENARIO_COMBINATIONS={
 '000': ('Fortress without scale',
   'Closed digital platforms, restrictive research links and poor investment conversion reinforce each other. Resources accumulate behind borders and vendors rather than diffusing to users.',
   'A self-reinforcing isolation trap: security/compliance costs suppress cooperation, which weakens the skills and demand needed to exploit infrastructure investment.',
   'Protect interoperable essential interfaces; maintain carefully scoped exchanges; assess actual uptake before large capital commitments.'),
 '001': ('Domestic islands of excellence',
   'Capacity is built and used, but closed platforms and restricted research networks turn it into disconnected domestic or sectoral islands.',
   'Successful scale within a few institutions increases their network power. Talent and equipment can concentrate while spillovers to less-connected actors remain limited.',
   'Make portability, shared access and controlled reciprocity contractual conditions for scaling investments.'),
 '010': ('Open science, closed platforms',
   'Cross-border scientific exchange continues, yet proprietary digital architectures and weak conversion finance prevent knowledge from becoming distributed operating capability.',
   'Open knowledge increases the supply of ideas without reducing control of the computing and deployment interfaces; dependency shifts from publications toward platforms.',
   'Prioritise compute access, neutral standards and pilot-to-scale financing rather than assuming scientific collaboration alone produces strategic autonomy.'),
 '011': ('Platform-mediated acceleration',
   'Open research and effective scale-up produce innovation even while platform lock-in persists. Growth is fast, but gains and bargaining power concentrate around controlling infrastructure.',
   'The innovation system becomes dynamically productive and structurally dependent: success itself increases exposure to platform switching costs and pricing power.',
   'Use procurement and funding leverage to secure portability, data rights and contestable alternatives before network effects harden.'),
 '100': ('Sovereign infrastructure, stranded value',
   'Interoperable infrastructure expands, but restricted research links and poor conversion into usable technologies leave installed capacity underexploited.',
   'Architectural openness does not compensate for absent scientific networks or weak commercialisation; operational utilisation becomes the binding constraint.',
   'Build practical research access channels, shared testing environments and measurable use rather than increasing physical capacity alone.'),
 '101': ('Strategic autonomy with knowledge bottlenecks',
   'Interoperable systems and effective investment generate domestic capabilities, yet tighter research restrictions shrink the variety of inputs and limit recombination.',
   'Increased domestic scale masks reduced exploration diversity; commercial efficiency improves even as long-horizon discovery and skills networks narrow.',
   'Invest in protected but reciprocal research corridors and track diversity of scientific inputs, not only technology output.'),
 '110': ('Open but underconverted ecosystem',
   'Interoperable infrastructure and open research form a broad common knowledge base, but funding and adoption processes fail to turn potential into sustained operational capabilities.',
   'The binding constraint migrates from access and collaboration toward implementation finance, procurement, management capability and scale-up demand.',
   'Reallocate attention from access announcements to uptake metrics, follow-on capital and validated deployment.'),
 '111': ('Distributed European capability',
   'Portable digital infrastructure, risk-proportionate openness and effective investment reinforce one another; knowledge crosses borders, scale is accessible and capabilities diffuse.',
   'Positive feedback between research variety, portable infrastructure and deployment makes the system more resilient; the risk is congestion and governance failure at shared interfaces.',
   'Maintain contestability, transparent access allocation and independent outcome measurement to keep network gains distributed.'),
}
