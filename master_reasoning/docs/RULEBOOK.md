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

## 13. Verified counter-directions and structurally inferred brakes (`counterforces.py`)

Every selected trend is now checked for **credible movements or mechanisms that can prevent, offset, localize, or reverse its development**. These are generated from the latest admissible records during each *manual* `master` run, not hand-written objections. The report visualizes the driving route and a separately labeled blocking route.

### CF1 — Independently diagnosed counter-direction

**Admission:** two verified diagnoses from two distinct publisher families that are *not used as principal trend anchors*, concerning the same target, compatible geography and no more than 1,095 days from the principal target observation. Both diagnostics must have a direction opposed to the analyzed trend (`expands` vs `contracts`, `contracts` vs `expands`). For `becomes_conditional` and `becomes_contested`, an independent `expands` direction is an **offsetting expansion**, not proof that conditionality or contestation disappeared.

**Inference:** the assessed trajectory faces a differently directed, independently visible development. The two reports establish their diagnoses, while the net balance or actual reversal requires matched outcome indicators. Counts are never interpreted as measurement of aggregate change.

### CF2 — Verified restrictive action plus diagnosed downstream exposure

**Topology:** restrictive action in `A` **limits** target `Z`. It requires a versioned `constrains` edge, a verified `restricts / excludes / screens / opposes / requires` action at `A`, and a separately sourced verified diagnosis at `Z`; source families and scopes cannot overlap improperly. The action's **actual** jurisdiction, time and application matter. A published rule does not establish a measurable negative effect or an aggregate decline.

**Inference:** an access or collaboration interruption threatens the main pathway. **Failure test:** inspect the edge-specific observable (permits, actual project refusals, delays, affected people, activity). No action premise, no claimed observed restrictive counterforce.

### CF3 — Verified adverse target diagnosis + typed conversion gate

**Topology:** an enabling action in `A` targets a common `Z`; a verified *independent* target diagnosis reports `contracts`, `becomes_conditional` or `becomes_contested`. A two-source diagnosis of downstream stress is preferred, but a single independent verified diagnosis can identify a **brake**, not a quantitative countertrend.

**Inference:** new upstream resources cannot automatically shift outcomes because the shared absorption, adoption or access interface can remain constraining. The model's `condition`, `indicator`, and `risk_if_absent` specify the falsifiable transmission link. The diagnosis is verified; the causal attribution of the brake to a particular programme is not.

### CF4 — Target-side friction without a registered enabling edge

Independent verified adverse/conditional diagnoses of `Z` can imply a boundary to an expanding trend in `Z` even when the declared causal-bridge registry contains no enabling input leading to `Z`. The engine labels this **structural resistance**, not a proved inhibition or countertrend. The observations must pass geography/time checks. The analyst can later add a reviewed causal bridge if warranted, rather than inventing one.

### CF5 — Explicitly unverified causal gate (last-resort safeguard)

When there is no independently verified opposing movement, the engine can describe the audited positive edge's `risk_if_absent` as a **model condition**. It contains no counter-evidence citations and is never presented as an observed countertrend. The system does not manufacture negative findings simply to give each trend a full pair of enemies.

### Audit and graphical interpretation

- Counter-directions and brakes never borrow provisional or unverified workbook leads.
- A cross-study counter-direction requires **two** independent verified families. A brake grounded in a target assessment may rest on one verified independent diagnosis but is labelled as a structural inference.
- All counter-premise claims must share a compatible geography and date window with the trend's target premise. Same-document/publisher duplicates do not increase evidence count.
- The infographic displays *positive pathways on the upper line* and *the selected counter-direction / braking interface on a lower line*. **Arrow shapes indicate the authored network model, not an estimated causal effect.**
- All graphics, including the two 2x2 slices of the eight-scenario cube, are generated afresh from the selected inferences on each run. They introduce no extra scores, probabilities or external data.
- Only the consolidated DOCX is written to the repository output folder. The PNGs are transient in-memory illustrations inside that DOCX.

**Boundary:** mismatched definitions, reporting times, different affected populations and common underlying datasets can make opposing diagnoses compatible rather than contradictory. Genuine causal identification still requires outcome measurement. A counterforce is a reasoned alternative future path, not a forecast of its inevitability.

## 14. Experimental abductive / conjunctive interaction search (v7)

This layer is deliberately more exploratory than the original fan-in and two-hop templates. **It does not make causal claims more certain.** It asks whether an entire network of *source-anchored* conditions can generate a surprising development that is not present in any one record.

The executable mechanisms are in `frontier.py`, `hyperedges.py` and `config/hyperedges.json`.

**R14.1 — No numeric minimum defines sophistication.** A high-order system inference is not admitted because it joins at least four publications. Relevance of the proposed mechanism matters. A bounded expansion budget of 14 *additional* source anchors is a computational and graphical guardrail, **not** a definition of explanatory depth. The model can represent more than the figure displays; increasing this budget should not be mistaken for improving the quality of ideas.

**R14.2 — Every incorporated network node needs an actual verified anchor.** Starting with a previously admitted outcome and its verified premises, the engine traverses the reviewed `enables/substitutes/constrains` network. For each additional node it demands an eligible, independently published, dated structured claim in the same scope and temporal window. It never uses unverified lead counts to compensate for weak premises or adds a node only because its name sounds relevant.

**R14.3 — Expansion is directed toward structural novelty.** The search gives preference to documented cross-domain interfaces, competing restrictive routes and downstream consequences. It closes a predeclared edge only when both endpoints are anchored. The resulting `frontier` object preserves all original and added evidence, source families, dates, bridge IDs and signed edges.

**R14.4 — Counterfactual network cuts are tests of a model.** The engine compares graph reachability with and without a shared interface. Disconnected modeled routes identify an exposure for investigation. This is a network property, not proof that the real economy would fail after losing that interface.

**R14.5 — Higher-order conjunctive rules are AND-gates.** The independent interaction atlas (`config/hyperedges.json`) contains 24 authored hypotheses such as “compute access AND venture capital AND deep-tech firms” or “infrastructure access AND retained talent AND finance.” A rule fires only if the full antecedent set is independently source-anchored and at least one antecedent belongs to the initiating inference. This is more demanding than composing a few pairwise edges into a sentence. A maximum of one entry per interaction rule per chapter prevents one conjecture from masquerading as dozens of different discoveries.

**R14.6 — Separate what is verified from what is newly imagined.** The workbook verifies source status and classifications. It does **not** verify the rulebook's conditional transmission mechanism, an AND-gate's synergy, the non-additive consequence, or the magnitude, timing or probability of the proposed change. Inference objects label those as analyst-authored conditional structural interpretations. The report avoids printing technical rule identifiers under each entry; the rulebook and source code are the audit trail.

**R14.7 — Keep incompatible worlds alive.** A countertrend, restrictive route, or missing conversion stage can negate a system reading, reroute it or produce a different winner/loser distribution. A disconfirmation test and rival route remain in the underlying objects; the report concentrates on the emerging consequence rather than reproducing a scoring checklist.

**R14.8 — Re-run rather than silently update.** The `master` GitHub Action remains manual-only. Every dispatch reloads both repository workbooks, rebuilds eligible claims and all five outcome chapters, and commits only `reasoning outcomes as planned/Master_Foresight_Reasoning.docx`. The rule atlas is version-controlled and changes only if you edit it; no external text-generation API receives your evidence.

**Scientific boundary.** The 2024–2026 literature on higher-order causal hypergraphs and synergistic information demonstrates that multivariate interactions can be irreducible to pairwise associations. But this workbook-based engine **does not calculate partial information decomposition, estimate hyperedge coefficients, learn a causal graph from interventions, or test actual causal emergence**. Those require suitable numerical, longitudinal or interventional data. The v7 implementation is *auditable abductive theory generation*, rather than empirical higher-order causal identification.

Selected scientific context (background, not a claim that these algorithms are implemented):

- `https://arxiv.org/abs/2409.08295` — higher-order causality / causal hypernetworks.
- `https://arxiv.org/abs/2512.20552` — information-theoretic signatures in causal networks and hypergraphs.
- `https://arxiv.org/abs/2511.03831` — higher-order causal structure learning with additive models.
- `https://www.nature.com/articles/s41467-025-57664-2` — empirical hypergraph reconstruction from dynamics.

---

## v8: Collective and nonlinear-dynamics reasoning

The new `collective.py` module runs **after** verified-anchored causal-network reconstruction and AND-gated rules. It composes conditional interaction mechanisms rather than treating collective dynamics, cascades, phase transitions and self-organization as separate output categories. It does **not** claim observed contagion, phase transition, synchronization, swarm coordination, positive feedback or hysteresis without appropriate measurements. Only selected entries receive this additional inference; absence of a justified mechanism is not padded.

For the complete gate logic, concept-by-concept status, formal conditional patterns C1–C7, counterfactual checks and research pointers, see [`COLLECTIVE_DYNAMICS_RULES.md`](COLLECTIVE_DYNAMICS_RULES.md). The generated outcomes DOCX remains free of methodological checklists.
