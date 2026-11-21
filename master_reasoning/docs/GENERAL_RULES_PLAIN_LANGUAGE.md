# How `master` reasons: a guide to the general inference rules

**Private working reference · Separate from the foresight outcomes DOCX**

The generated foresight report is meant to be read as an interpretation of the future. This document is different: it explains the reasoning machinery behind that interpretation, including the formal restrictions. It is intended for an owner who wants to inspect, challenge and eventually extend the model without treating it as a black box.

## The central idea: consequences emerge from relationships

Imagine three well-sourced observations: one institution expands research infrastructure access; another strengthens routes for transferring research into practice; an independent study identifies weaknesses in innovation performance. Each observation is useful on its own. Together, they suggest something more consequential: the decisive competition may shift away from announcing more infrastructure or programmes and toward institutions able to connect infrastructure users, knowledge-transfer systems and real-world adopters. The *interaction* is the inference. No individual source needs to have made that claim.

A credible inference has to do more than notice that all three texts mention innovation. It must identify **which actor or resource influences which outcome, along what pathway, and under what conditions**. That is why the system uses explicit connections among evidence rather than word-frequency clustering alone.

This approach is deliberately ambitious. It can discover common bottlenecks, chains of dependencies, unanticipated distributional effects, research and investment complementarities, regulatory spillovers and alternative futures. It does not equate ambition with permission to invent causal observations: the underlying records establish the premises; the model states the proposed causal connection; future evidence can test it.

## The seven questions every inference must survive

1. **What is actually known?** The sources report an action, observation or diagnosis at a particular time and maturity. A plan is evidence of a plan; an operational system is evidence of an operational system.
2. **Are the sources genuinely usable together?** They must be verified in the workbook, sufficiently distinct, compatible in geography and chronology, and relevant to the same system.
3. **What kind of relationship connects them?** They can converge on one outcome, form a multi-step dependency, compete at a shared bottleneck, or transmit constraints.
4. **Which connecting assumptions are required?** An arrow such as *compute capacity → AI adoption* is not free magic: it has a written requirement such as accessible compute, usable data and skilled staff.
5. **What new system change follows?** The inferred conclusion must identify a change in capability, access, incentives, dependence, institutional leverage or the location of the binding constraint—not merely restate the input findings.
6. **What other consequences unfold?** Actors respond; scarce resources shift; new coordination roles and inequalities can emerge; adaptations in one place reshape another.
7. **What would make us change our minds?** There must be a rival explanation, an indicator, and a conceivable outcome that contradicts the proposed chain.

The source evidence and the resulting inference are intentionally not conflated. The connection is a *reasoned proposition* and becomes stronger if subsequent observations demonstrate the links.

## Six relationship patterns that yield foresight

| Pattern | Simple topology | What the model can discover |
|---|---|---|
| Converging drivers | A → Z ← B | Complementarities and a changed bottleneck at the shared destination |
| Dated directional agreement | Z at t₁, t₂, t₃ | A structural direction when comparable independent observations agree |
| Two-step cascade | A → M → Z | An upstream change acquiring system-wide consequences through an intermediate dependency |
| Stressed shared node | A → Z ← B, with stress at Z | Competition, queueing or unequal access created by two pressures meeting a constrained interface |
| Conversion gap | A → imperfect uptake → Z | A programme or resource expanding without the hoped-for system benefit |
| Constraint and rerouting | A ┤ Z | A regulation or institutional restriction changing access, partnerships or movement of capability |

A topology is a concise map of proposed influence, not a proof that every arrow already operates. For example, **funding → research capacity → innovation performance** suggests a dependency cascade. The strategic question becomes whether research capacity is the bottleneck, rather than whether more funding was announced. The model must still check funding delivery and downstream results separately.

## Why verified records dominate

The verification gate is asymmetric. A source approved by the workbook can become a supporting premise if the claim itself is also eligible. Unverified leads can guide discovery or future review, but no number of them can substitute for a missing verified premise. A source can be verified while a particular causal claim remains untested; these are different statements.

The system also avoids treating ten summaries of the same study as ten independent reasons. It groups repeated works and demands distinct source families for the combinations used here. This is an initial dependence safeguard, not a substitute for tracing shared datasets or citation chains. Three publications may ultimately rest on one observation, so the analyst still has something to audit.

## Why the engine reasons beyond first-order effects

A first-order statement might say that an investment increases available infrastructure. A second-order statement asks how capacity changes who can participate. A third-order statement asks how actors reorganize themselves when access becomes a competitive advantage. This is often where interesting foresight resides: an apparently technical investment creates new gatekeepers, the gatekeepers alter collaboration patterns, and collaboration patterns eventually reshape research or industrial competitiveness.

The engine currently generates these moves through explicit structural motifs and authored consequence logic, not by unconstrained imaginative generation. That is an important strength for transparency and a limitation for novel relationships absent from the causal bridge registry. A future research release can propose new connections automatically, but should require separate review before promoting them into the verified evidence graph.

## What the 2×2×2 scenarios mean

A scenario is **not** a probability forecast. Three consequential uncertainties each have two materially different states. Here they concern: whether digital systems become portable or remain locked in; whether research access is relatively open or restricted; and whether investments become functioning capabilities or remain underused. Combining all states gives eight worlds, not eight predictions.

The interaction among axes matters more than simply listing the three states. A world with open research but closed platforms differs from one with both openness and portability, even if investment is strong in both. The same spending can build distributed European capability in one world and consolidate gatekeepers in another. Verified observations can support or challenge aspects of each world, and the eight worlds remain visible even when the evidence changes.

## What changes on a manual rerun

Running **Actions → master → Run workflow** reloads the latest Excel workbooks and re-evaluates the candidate relationships. Newly admitted evidence can change premise selection; new contradictions can weaken an inference; changes to the bridge registry alter the causal space considered; and changed observations update the scenario indicators. The workflow then replaces just one DOCX in `reasoning outcomes as planned`. It does not update the report automatically or publish it to GitHub Pages.

The rules remain in this folder and can be read without running the workflow. They are not inserted into the outcomes report, whose job is to present the analysis rather than defend every modeling decision in its margins.

---

# Detailed reference: exact gates, rules, calculations and limitations

# `master` inference engine — transparent, rigorous decision rules

**Purpose.** Generate **new foresight intelligence** (not a list or paraphrase of findings) by connecting verified source claims through explicit, inspectable causal and network hypotheses. Each conclusion must lead to an interpretable system consequence, a decision implication, and a way of being wrong.

**Technical boundary.** The mechanism bridges are version-controlled **model propositions**. The Excel workbooks establish the status of their supporting observations according to upstream review. **They do not prove the connecting causal edges**. These outputs are conditional deductions, not estimated causal effects, observed disruptions, numerical forecasts, or calibrated probabilities. That distinction is a rule, not a disclaimer attached after the fact.

The engine is deterministic: same files, bridge registry, scenario axes, settings and timestamp => same substantive inferences and evidence anchors. No network services, LLM, hidden embedding model, external prompts, or opaque topic similarity engine are used.

## 0. Start with epistemic types, not keywords

Each upstream structured claim includes some or all of: the **object** it concerns, secondary objects, actor, mechanism (e.g., builds, assesses, restricts), direction, implementation status, status date, country/scope, merit, qualification, original text, confidence, and claim ID. A claim is not a document, and a document is not a proven causal statement.

We treat five objects as fundamentally distinct:

1. **Source** — a named publication, publisher, URL, date and workbook-level verdict.
2. **Claim** — what the source is actually reporting, typed as an **action**, **diagnosis**, or **advocacy**; advocacy is not admitted as an action/diagnosis premise.
3. **Bridge** — an **analyst-specified, defeasible** proposition of the form `A --[enables|substitutes|constrains, conditions, indicator]--> B`.
4. **Topology** — a small graph constructed from **several claims and their allowed bridges**.
5. **Foresight outcome** — a new system-level inference derived from the topology, with implications, rival explanation and empirical test.

There is deliberately no rule saying that similar vocabulary, similar publication titles, or high mention frequency implies causation.

## 1. Verification is an admission gate, not an incremental bonus

A claim is eligible for causal support only when the **parent record passes the workbook's strict `KEEP`/authoritative verification criteria** AND the individual claim is not marked provisional. In the current source-merit schema:

- Live sheet: `admission_status == keep` AND `deep_scan_authoritative == true`.
- Historical sheet: `Authoritative historical == yes`, `Deep Scan decision == keep`, and `deep_scan.verification.identity_verified == true`.
- Global relevance sheet: entries in its explicitly verified global `KEEP` sheet are eligible **only as labeled external comparisons**, not as extra EU causal premises. Review, provisional and regional leads are excluded.
- Repeated snapshots of a document are deduplicated by DOI/URL/work ID so one work cannot become multiple corroborators.

**Formal rule:** `support(claim) = 0` unless it is workbook-verified. `Σ 1,000 × provisional = 0 supported premises`. This does **not** assert that a workbook-approved publication is infallible, nor that its predictions were observed.

The engine does not itself visit URLs and redo verification; it respects the upstream pipeline's stored decisions and makes that dependency visible.

## 2. Independence, chronology, geography and causal roles are constraints

For each pair/triple of premises, the engine requires:

- Unique **source keys** and different **source-family identifiers**. Different family labels are a minimum filter, **not proof of independent underlying data**; documents may quote the same underlying dataset.
- Compatible explicit geography. EU is matched to EU; a named-country scope requires matching country sets. An unspecified external scope cannot stand in for a European claim.
- Dated claim observations within a **three-year maximum separation** (`1095` days); temporal order is inspected for implementation versus outcome and never silently assumed to prove causation.
- The prescribed roles: a capacity intervention must be an `action`, a downstream assessment a `diagnosis`, and a restriction an applicable restrictive `action`. Merely advocating a policy cannot instantiate an implemented action.
- Claim-specific source qualifications. A verified announcement confirms an *announcement*, not that funds were disbursed or results achieved. Conservative future-tense checks reduce the maturity assigned to apparent deployment.
- Limited sector-fit checks for known high-risk bridges (e.g., generic strategic finance cannot automatically be treated as green finance).

**Failure behavior:** if any required gate fails, that evidence combination is rejected outright; its lower score is *not* traded off against additional mentions.

## 3. Typed edges make the causal assumptions inspectable

Every proposed edge in `config/bridges.json` has:

```json
{
  "id": "B02",
  "from": "compute.capacity",
  "to": "ai.adoption",
  "relation": "enables",
  "condition": "accessible computing is affordable, utilized and complemented by data and staff skills",
  "risk_if_absent": "Announced computing supply does not imply usable AI capability or productivity.",
  "indicator": "Utilisation, access wait-times, realised firm uptake and skill availability"
}
```

In ordinary language: *additional computing capacity can increase real AI use **only when** computing is reachable and other complements exist; access and adoption, not announced capacity, distinguish realization from an attractive story*.

Edge direction matters. `A -> B` does not mean `B -> A`. An enabling edge is not identical to a constraint, and an institutional action is not identical to a measured effect. The bridge inventory is reviewed and extensible: new evidence can enlarge the object map by adding justified edges without editing the inference algorithms. **Completely new causal edges are never invented silently** by an unexplained model.

## 4. Trend inference rules (full trends, not lesser-grade signals)

### T2. Convergent causal topology: `A -> Z <- B`

**When accepted:** verified independent action in `A`, verified independent action in `B`, verified independent diagnosis of `Z`; distinct source families; compatible scope/dates; two declared enabling or substitution bridges; and sector relevance. At least **three** premises are required.

**What is inferred:** two levers are converging on the same system outcome. The strategic bottleneck can migrate from increasing either input independently to managing the *interface* that converts both into a useful downstream result. A strong institution may exploit access to both routes; uncoordinated expansion may produce fragmented benefits rather than additional system capacity.

**Why this is a new conclusion:** no single publication needs to identify the joint bottleneck or the actor that controls the intersection. The inference arises from a **fan-in graph**, implementation status of each intervention, and independently diagnosed downstream context.

**Conditions / failure test:** both levers must reach an overlapping population and the same output measure. Check each edge's separately specified indicator and observe the common target. If either lever has no uptake, the supposed convergence has not materialized; a source about one lever does not validate the other.

The model can produce several different trends with the same target when the incoming route pairs, constraints and evidence genuinely differ. It caps repeated variants to avoid replacing breadth with rewordings.

### T1. Independent directional diagnosis over time

**When accepted:** at least **three** distinct publisher-family diagnoses of the same variable, geography and direction, over at least **45 days**, using admitted verified claims; contrary assessments are recorded for audit.

**What is inferred:** repeated, dated observations exert pressure on actors whose investment or operational assumptions depend on a stable baseline. This is a structural direction requiring a harmonized measurement test, **not a fabricated annual growth rate, regression slope, or rate of acceleration**.

**Failure test:** harmonize metrics, denominators, periods and datasets; reassess the direction. Mere increase in publication frequency is never treated as a trend.

T1 and T2 are **both real trend inference rules**, not stronger and weaker buckets. They test different structures (temporal concordance versus interacting levers); their limitations are stated individually.

## 5. Disruption inference rules

### D1. Propagating two-stage dependency: `A -> M -> Z`

**When accepted:** verified action in `A`, verified diagnosis of intermediate dependency `M`, verified diagnosis of downstream system `Z`; **three independent families**, same scope/time, two declared causal bridges, and adverse/contested/conditional evidence at `M` or `Z`.

**Inference:** what begins as change at `A` can reconfigure `Z` **through** `M`. If the intermediate gate becomes the binding constraint, policy failure migrates downstream even while investments in `A` continue. The central inference is the *location and propagation of disruption*, rather than a summary of the initial intervention.

**Second-order inference:** new queueing, unequal access or budget diversion becomes possible at the newly critical intermediate node.

**Test:** separately measure the first link `A -> M` and second `M -> Z`. Without evidence for both links, do not claim an observed cascade. **No quantitative tipping point is invented**.

### D2. Convergent chokepoint: `A -> Z <- B`, with adverse diagnosis at `Z`

**When accepted:** verified independent expanding actions in `A` and `B`, and a third independently verified adverse/contested diagnosis at shared system node `Z`. Both mechanism bridges are specified in the registry. These claims must concern compatible scopes and time windows.

**Inference:** the shared access/throughput point can become strategically more important than either upstream investment. Growth in the two upstream systems may coexist with congestion, exclusion, concentration, or allocation conflicts at `Z`. This is a *potential regime reconfiguration*, not proof that a crisis has already happened.

**Failure alternatives:** the programmes may address different beneficiaries, relieve rather than add pressure to the diagnosed constraint, or be too small to matter. Check queueing, utilization, participant distribution and the two link-specific observables before asserting an actual shock.

This rule produces disruption mechanisms **different from** ordinary convergence trends: it specifically requires independently documented *stress at the common receiving node*.

## 6. Risk inference rules

### R1. Implementation / absorption gap

**Inputs:** a verified enabling intervention plus an independent verified downstream diagnosis. Usually the action remains proposed, announced, conditional, or its outcome is not substantiated.

**Deduction:** programme activity can rise while the target problem persists, because the necessary delivery or adoption link is not established. Under a capacity-scarce environment, additional upstream spending can even worsen queueing or concentration. The key loss pathway is *resource growth without outcome conversion*.

**Disconfirmation:** show independently measured, sustained downstream benefits among the affected users. Evidence of disbursement is not evidence of impact.

### R2. Restrictive network exposure

**Inputs:** a verified applicable restrictive action in `A`, plus a verified diagnosis of affected system `B`, connected by an explicit `constrains` edge.

**Deduction:** a control at one node can change which actors can access the network, moving partnerships, specialized skills and knowledge along alternative routes. The second-order risk is not simply less activity; it is a **reconfiguration of centrality, concentration, compliance costs and collaboration pathways**.

**Disconfirmation:** check actual transfers, denials, cancellations, new alternatives and benefits from reduced security exposure. A published rule is not an observed loss, and the *net* benefit/harm is not assumed.

## 7. Opportunity inference rule

### O1. Capability conversion interface: `A -> B`

**Inputs:** a verified enabling/substitution action in `A`, an independent verified diagnosis of `B`, and a declared bridge requiring a measurable conversion condition.

**Deduction:** an investment opportunity exists at the interface **where resources become usable**, rather than necessarily in expanding raw funding, infrastructure or programme counts. This points to complementarities such as skills, interoperability, procurement, follow-on funding, access allocation or pilots with independent outcome measurement.

**Second-order consequence:** system coordination and complementary capability can acquire more strategic value than one more announced initiative. It also reveals *who* may capture value: actors controlling the critical cross-system interface.

**Test:** disaggregate *committed*, *deployed*, *used*, and *effective* capacity. Compare outcome adoption with a suitable baseline; discard the opportunity claim if the conversion route does not work.

## 8. Evidence support and prioritization are not probability

After the hard gates, eligible source anchors receive an **evidential directness score**, not a forecast likelihood. For each claim:

```
confidence     = 1.00 / 0.78 / 0.50 for high / medium / low
merit_factor   = 0.55 + 0.45 × clamp(merit,0,100)/100
directness     = 1.00 for measurement; ~0.95 detection; 0.86 evaluation;
                 0.74 assessment; 0.92 implemented action (before maturity);
                 much lower for advocacy or untyped statements
w(claim)       = 0 when not verified; else confidence × merit_factor × directness
maturity       = weakest relevant action implementation-state weight,
                 reduced further when the claim text still describes targets/plans
priority       = min(74, round(100 × min_i w(claim_i)
                 × (0.52 + 0.48 × maturity) × motif_penalty))
```

The **minimum** rule is deliberate. A beautifully verified claim cannot numerically compensate for a tenuous or unverifiable supporting premise. Adding large volumes of unverified material cannot move the priority. A score near 74 means *high review priority under these heuristics*, not a 74% probability, a 74% confidence level, or proof of a causal effect. There is **no calibrated impact/likelihood product**.

The selector also caps repetition by topic and target so one heavily covered field cannot dominate every section.

## 9. Three interacting uncertainties => eight scenarios

The current three axes are **digital portability / lock-in (ARCH)**, **research openness / restrictive screening (OPEN)**, and **investment-to-capability conversion (SCALE)**. Their tags must be disjoint so they are *conceptually distinct*, although statistical independence is not claimed. Each axis has two states, producing the full Boolean cube `2 × 2 × 2 = 8`.

Each combination has (1) a logically specified conditional world, (2) a **cross-axis interaction inference**, (3) a **second-order systemic consequence**, (4) a decision response, and (5) verified indicator proxies aligned with and opposed to its assumed states. Eight named interaction logics are maintained in `deductions.py`; these are deliberate analyst-explainable deductions, not fill-in-the-blank paraphrases of three axes.

| Code (ARCH, OPEN, SCALE) | Emergent world | Key interaction |
| --- | --- | --- |
| 000 | Fortress without scale | Closed platforms, restricted knowledge, no conversion reinforce an isolation trap |
| 001 | Domestic islands of excellence | Conversion occurs but access and research routes concentrate benefits |
| 010 | Open science, closed platforms | Ideas circulate but compute/platform control blocks broad operational impact |
| 011 | Platform-mediated acceleration | Open science plus scaling succeeds but entrenches platform dependence |
| 100 | Sovereign infrastructure, stranded value | Open architecture without talent links or conversion sits underused |
| 101 | Strategic autonomy with knowledge bottlenecks | Effective domestic scale sacrifices diversity of discovery inputs |
| 110 | Open but underconverted ecosystem | Knowledge and access thrive while delivery finance and adoption remain the brake |
| 111 | Distributed European capability | Portable systems, open research and scaled capability reinforce diffusion, with governance risks |

**Live update of scenarios:** the six proxy rule sets read today's committed workbook on every manual run. For each scenario the report shows verified proxies for and against its required states, an explicit **aligned / mixed / opposed / coverage gap** diagnostic, and early tests. These counts are not probabilities. The eight worlds are always shown; data conflict does not secretly delete an unfavorable world.

When axes themselves change, the authored eight cross-axis interaction explanations must be reviewed as a scientific model change. It is not defensible to recycle old narratives silently for fundamentally different axes.

## 10. Transparent counterfactual reasoning and the route to decisions

Every entry must answer these questions in order:

1. **Observed premises:** What *exactly* do the independently accepted claims report? Where, when, at what implementation stage?
2. **Topology:** Is the system a fan-in, temporal convergence, two-hop cascade, constraint, stressed chokepoint or conversion interface?
3. **Connecting mechanism:** What *would have to be true* for each arrow to operate? What indicator would show it?
4. **Derived system change:** Which system variable, binding constraint, network position, access route or behavioral incentive changes if the premises and model edges jointly operate? This step is the **new inference**.
5. **Second-order or strategic consequence:** What changes after actors respond to that system change? Who gains leverage? What bottleneck migrates?
6. **Countermodel:** What credible alternative would explain the same observations or prevent transmission?
7. **Decision / falsification:** Which operational choice follows, and what observation would make us revise or reject the inference?

A report item is only accepted if it has enough verified anchors, unique source families, a named rule, a model path, an explicit rival explanation, and a test. Simply quoting source material or finding repeated words does **not** meet the requirement.

## 11. What changes when you manually run `master`?

1. The workflow starts **only** from GitHub Actions → **master** → Run workflow. No cron, automated event, Pages, external inference service, or upstream file write.
2. It reads the **current committed bytes** of both Excel inputs, using the canonical locations or a unique-name fallback. It streams structured XLSX XML without editing workbooks.
3. It re-applies verification, deduplication, source-role, scope, chronology, independence and semantic-fit checks. Previously admitted claims can disappear when no longer verified. New claims can enter as soon as their stored verification gate permits them.
4. It rebuilds the claim graph and candidate motifs using all current qualifying records and the versioned `bridges.json` registry. New evidence can change which premises are selected, which hypotheses enter the top 20–30, and their priority.
5. It updates the eight scenarios' live indicator diagnostics. It generates a **single Word file** with distinct chapters, evidence links, alternative explanations, decisions and tests; the input/config SHA-256 fingerprints are included for audit.
6. It commits **only** `reasoning outcomes as planned/Master_Foresight_Reasoning.docx` to the branch you manually ran. No other repository file is staged for the output commit. A hypothesis leaving the report means it was **not selected in the current evidence/config snapshot**—not that the historical world disproved it.

## 12. Red-team failure modes and scientific limitations

- **Verified record ≠ verified prediction.** This model is rigorous about source admission but does not independently re-verify every upstream claim.
- **Three sources ≠ three independent datasets.** Publisher-family separation is a useful minimum; full citation-lineage independence needs a later provenance audit.
- **A typed edge ≠ a measured causal coefficient.** Bridge conditions are explicit analyst assumptions. Causal effects require controlled designs, natural experiments, intervention evidence or appropriate identification strategies.
- **Saturation ≠ measured tipping point.** D2 identifies a bottleneck topology and adversarial conditions. It does not estimate physical network capacities, tipping thresholds, or discontinuity magnitude.
- **Scenario consistency ≠ scenario probability.** Three qualitatively different axes do not establish statistical independence. Proxy balance is descriptive, not a Bayesian posterior.
- **Absence from the top 28 ≠ absence of importance.** Capping and diversity logic are review design choices. Increase max to 30 or inspect the code if you wish to compare selected sets.
- **A static bridge registry is not universal semantic discovery.** New topics are absorbed automatically into evidence indexing, and temporally corroborated claims can yield a trend without an edge. New causal subject-to-object connections require explicit reviewed bridges, preventing unsupported cross-sector leaps.
- **Unknown or incompatible context cannot be traded away with scoring.** It must be clarified upstream; the engine does not fabricate scope, time or mechanism.

**Bottom line:** the system is not a black box because every transformation has a visible input, typed rule, condition, output, and disconfirmation test. Nor is it a simple rule-of-thumb summarizer: it generates new consequences from the *structure of interacting evidence*, while maintaining a strict line between what the sources established and what the model inferred.

## 13. What the engine now asks about every trend: what could stop it?

A trend should not appear as if the world had only one direction. The engine therefore looks for forces that oppose its direction, prevent its benefits from reaching their destination, or trap its effects inside one part of a wider system. These challenges are **inferred from evidence** rather than added as generic caveats.

A genuine **counter-direction** needs at least two independently vetted assessments showing an opposing movement in the *same system* and compatible geography and time. An assessment of expansion and one of contraction can both be true in different places or populations, so the engine does **not** automatically declare that the counter-direction has won. If the original trend concerns increasing conditionality or contestation, an independently observed expansion is treated as an **offsetting movement**; expansion can coexist with more conditions.

Another category is an **inhibiting pathway**. Suppose separately verified records establish a new restrictive policy and a downstream condition. If the reviewed causal map shows that this policy can interrupt the trend's network of people, capital, equipment, or knowledge, the engine traces the negative route. It still does not claim that the policy has already stopped the trend; actual interruption requires evidence.

Often the dominant brake is at the **conversion interface**. Two investments may converge on the same system, yet independent assessments describe that system as contested, conditional, or constrained. The new deduction is that upstream expansion can continue while the aggregate outcome stalls. The wider consequence is that actors controlling adoption, delivery, access or coordination gain influence. This brake is a substantive structural inference, but it is **not** a directly measured reversal.

Some topics have independently documented adverse conditions without a corresponding registered causal edge. These can show **structural resistance to diffusion**. If no counter-evidence is independently verified, the engine may show an explicitly labeled **model constraint** that would have to fail for the trend to be blocked. That is a limit of the causal hypothesis, not an observed countertrend.

In the report these ideas appear as a reader-friendly **countertrend or braking-force section** for every trend. Small causal diagrams distinguish supporting routes from opposing forces. The methodological gates and formal details remain in this separate guide and in `RULEBOOK.md`, not in every report entry.

## 14. How to read the new graphics

The upper arrows of each trend map show which independently documented drivers converge on the inferred system change. The lower line names the strongest available opposing movement or bottleneck. It shows **where the logic could be defeated**, not a claim that a measured causal impact has been identified.

The opening graphic compares how many reasoned entries appear in the four main chapters. These are **counts of selected interpretations**, not statistics about how many trends or crises exist in the real world. Disruption, risk and opportunity chapters also open with simple dependency maps. The scenario chapter uses **two separate 2×2 grids**, one for each state of the third uncertainty; together they display all eight logically possible worlds without inventing probabilities.

On the next manual run, the workbooks are read again. Source verification, counterpart evidence, model routes, visual diagrams and scenario indicators are recalculated. The workbooks are never edited. Only the one DOCX is replaced in the output folder.

## 15. Taking bigger intellectual risks—without pretending they are verified facts

The experimental v7 rules aim for discoveries, not a familiar catalogue of findings. The number of documents combined is no longer our definition of depth. Two findings can yield a profound conditional insight; fifteen can yield noise. The decisive questions are whether the combination exposes a **new system arrangement**, whether each moving part has evidence behind it, and whether the connection would remain interesting if it were shown to be false.

The new engine looks for system rearrangements. It investigates when separate good ideas compete for the same missing resource; when fixing one bottleneck moves scarcity somewhere less visible; when a new regulation changes the routes through which people, ideas and technology can flow; and when supporting several initiatives at once creates a new controlling institution or intermediary.

A new set of twenty-four *conjunctive* rules asks more demanding questions: **what happens only when these three, four or more preconditions occur together?** This differs from saying that A influences B and B influences C. For instance, compute capacity, usable financing and ambitious deep-tech firms together can create an entirely new market for priority of access. No one of those developments alone is enough to define that market. That is a reasoned, potentially surprising system hypothesis—not a verified statement that this market has already formed.

The rules also test the opposite case. They ask who wins when the expected sequence fails, which intervention unexpectedly becomes a chokepoint, which assumptions depend on the same hidden interface, and whether a competitor could route around the supposed constraint. Verified countertrends remain part of the trend chapter when the evidence supports them.

**Where the engine must remain humble:** these are conditional conjectures grounded in verified observations and deliberately specified mechanisms. The underlying Excel sheets cannot establish every interaction coefficient, feedback loop or tipping point. Even a very elegant network diagram is a hypothesis about transmission, not proof that the world is wired that way.

You can read or edit the exact cross-domain hypotheses in `master_reasoning/config/hyperedges.json`. The outcome DOCX does not explain these rules repeatedly; it focuses on their consequences. The GitHub workflow still runs only when manually started and produces only the internal Word document.

---

## The new collective-dynamics layer (v8)

Collective dynamics, emergence, self-organization, contagion, synchronization, cascades, phase transitions, swarm-like adaptation, complex adaptive systems and nonlinear response now inform the **same** inference process; they do not create ten separate categories or ten obligatory paragraphs. The engine asks whether a particular configuration of independently verified observations and explicit, fallible causal bridges implies a change that no single observation describes. Its strongest new pattern is a *composition of mechanisms*—for example, joint activation of complementary conditions followed by a delayed downstream cascade, or control-induced rerouting followed by a new institutional dependence.

It remains important to distinguish a **conditional mechanism inferred from a network** from a **dynamic phenomenon measured in real actors or time series**. The current workbooks support the former much more readily than the latter. This prevents imaginative reasoning from becoming invented quantitative evidence. The precise rules and failure conditions are in `COLLECTIVE_DYNAMICS_RULES.md`.
