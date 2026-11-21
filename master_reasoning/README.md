# `master` — isolated, verified-first foresight reasoning

This is a **new, manually run, standalone GitHub Actions workflow**. It does not alter scanners, Excel inputs, Pages, existing workflows, or previously generated reports.

## Where to place the files

Upload the directory tree in `master_upload_only.zip` **into the root of the existing repository**, preserving the relative paths. Do **not** upload the ZIP as a single file and expect GitHub to unpack it.

```text
.github/
  workflows/
    master.yml                        NEW — action display name: master
master_reasoning/                   NEW — isolated Python package
  __init__.py
  _xlsx_rows.py
  adapter.py
  core.py
  infer.py
  deductions.py
  context.py
  report.py
  main.py
  config/
    bridges.json                     Versioned causal assumptions; editable
    axes.json                        Three scenario axes and indicator rules
  docs/
    RULEBOOK.md                      Exact formal inference rules and tests
    GENERAL_RULES_PLAIN_LANGUAGE.md  Standalone readable explanation
    GENERAL_RULES_PLAIN_LANGUAGE.docx  Standalone Word guide for your own reading
  tests/
    __init__.py
    test_master.py
reasoning outcomes as planned/
  .gitkeep                           Empty output directory
```

**Inputs used, read-only on every run:**

- `stuff/source_merit_ranking.xlsx`
- `Relevance Stuff/relevance_stuff.xlsx`

Both paths were checked against the uploaded repository archive. If moved, the code can locate a uniquely named XLSX elsewhere in the repo; ambiguous duplicates cause a safe failure rather than choosing the wrong source.

**Only intended Git write** (created or replaced after each manual run):

`reasoning outcomes as planned/Master_Foresight_Reasoning.docx`

## To run

1. Upload the extracted **new** files and folders, preserving the paths above; keep all existing files unchanged.
2. Commit the addition to the default branch in your GitHub repository.
3. Go to **Actions → master → Run workflow**, choose the branch and the maximum per-section count (default **28**), then click **Run workflow**.
4. After the action succeeds, find the Word report in **`reasoning outcomes as planned/`** on that branch. Every manual run re-reads the latest committed content of both input workbooks and overwrites that one DOCX in a new Git commit.

There is **no scheduled trigger, push trigger, published site, Pages step, artifact upload, or external AI call**. The code uses only local committed files, built-in Python, and the `python-docx` dependency installed in the workflow. It never pushes the Excel workbooks or a copy of evidence to any external service.

**Privacy warning:** a GitHub repository and its committed files are visible to anyone who can read that repository. In a *public repository*, this DOCX would be publicly downloadable from GitHub **even though it is not published to GitHub Pages**. Use a **private repository** if the document is truly for your eyes only.

## What the report contains

One DOCX, with five clearly separated substantive sections: **trends, disruptions, risks, opportunities, and 8 scenarios (2×2×2)**. The default ceiling is 28 per non-scenario section; the engine produces fewer if available verified evidence cannot justify 28. No "preliminary trend" or lower-grade substitute is added to reach a quota. Example snapshot from the uploaded archive: **28 trends, 28 disruptions, 23 risks, 25 opportunities, 8 scenarios**.

The outcomes DOCX is deliberately written as a readable foresight analysis: each entry discusses an inferred development, wider consequences, a strategic implication and discreet source anchors. It does not print the rule name, score, checklist, diagram, rival-model audit, or verification caveats repeatedly. Those details remain available in the separate reference guide and Python source. The hypotheses are new reasoning: they are not restatements of source findings, but the model's **causal edges remain explicit, defeasible assumptions**; workbook verification does *not* independently verify inferred causality.

### Updating the reasoning model without editing Python

- Add/modify mechanism edges in `master_reasoning/config/bridges.json`. Each edge has a directed source and target object, an `enables` / `substitutes` / `constrains` relation, transmission condition, failure alternative, and a measurable indicator. Edges are **model assumptions**, not automatically discovered causal facts.
- Change the three uncertainties in `master_reasoning/config/axes.json`, including their non-overlapping object tags and the proxy rules. The eight scenarios are generated from all binary combinations of these axes. If axes change substantially, the eight hand-authored **scenario interaction narratives** in `master_reasoning/deductions.py` must also be reviewed so their meanings correspond to the selected axes.
- Add newly classified objects and edges as the evidence taxonomy expands. New verified findings in **already modeled objects** are incorporated automatically on the next run, with no code edit.

The model is **not an LLM** and does not infer semantic causal mechanisms from unreviewed words. The price of that transparency is an explicit analyst-governed causal ontology; the safeguards intentionally prevent a completely new topic from silently acquiring an unreviewed causal link.

### Reproducibility / limitations

The generated entries are **formal, testable structural hypotheses**, *not* measured causal effects or calibrated scenario probabilities. Publisher-family separation and scope checks reduce obvious false evidence joins but do not prove source-data independence or causal sufficiency. There is no secret model, external upload, uncontrolled prompt, or invented numerical tipping threshold. For the readable rules explanation, read `docs/GENERAL_RULES_PLAIN_LANGUAGE.docx` or `.md`. For the exact formulas and motif conditions, see [docs/RULEBOOK.md](docs/RULEBOOK.md). None of these rule explanations are inserted into the generated outcomes DOCX.

### Local run (optional)

```bash
python -m pip install python-docx==1.2.0
python -m unittest discover -s master_reasoning/tests -p 'test_*.py' -v
python -m master_reasoning.main --root . --max-per-section 28
```

Requires the two Excel inputs to be present. Running this command writes only the DOCX at its target path. Running on GitHub is the intended route, because it also commits that one output.

## Countertrends, braking mechanisms and refreshed figures

The inference engine now generates **counterforces for the trend chapter** using
`counterforces.py`. CF1 requires two independent verified opposing/offsetting
diagnoses. CF2 demands a verified restrictive action and compatible downstream
evidence on a declared negative network edge. CF3/CF4 identify verified-anchored
constraints and target-side friction, distinctly from an observed reversal.
CF5 is a model-only failure condition, marked as such. Counterforces are
recomputed every manual run and never use unverified leads as supporting proof.

The Word generator uses `graphics.py` (Pillow) to embed dynamically generated
in-memory graphics: a category overview, one compact network figure per selected trend (28 in the tested snapshot), three
causal mechanism maps, and two 2×2 slices of the eight-scenario cube. **No images
are separately committed to GitHub.** The general rules remain in `docs/`,
separate from the readable outcome DOCX.

The only additional Python runtime dependency is `Pillow==11.3.0`. See the full
admission conditions and scientific limits in `docs/RULEBOOK.md`, section 13.

## v7: more adventurous abductive inference, still auditable

The new `frontier.py` explores broader, evidence-anchored directed networks and model counterfactual cuts. `hyperedges.py` applies 24 explicit cross-domain **AND-gated interaction hypotheses** from `config/hyperedges.json` when all the antecedents are grounded in independent verified claims. These are analyst-encoded conjunctive mechanisms, not statistically detected synergies. The chapter report uses the resulting consequences as its narrative; the testable rule conditions remain in separate documentation.

**Important:** the novelty search is not a generic language model or an autonomous causal discovery method. The mechanism registry and 24 conjunctive rules are authored, readable and editable. Completely new causal domains still require adding their mechanism rules. The report must not be interpreted as verified causality or numerical scenario likelihoods.

All earlier isolation guarantees remain: a manual-only `master` action, read-only Excel inputs, no external AI API, and only one committed DOCX in the `reasoning outcomes as planned` folder.

## New in v8: emergent and collective dynamics in the mix

`collective.py` integrates higher-order collective-dynamics motifs with the existing causal, topology, counterforce and AND-gate engine. It only adds a synthesis when independently verified source anchors and the explicitly modelled network support the relevant mechanisms. It also supplies eight different, conditional collective-dynamics interpretations for the existing 2×2×2 scenarios. No changes to source workbooks or to the manual-only workflow trigger are needed. General rules are separate from the outcome report: `docs/COLLECTIVE_DYNAMICS_RULES.md`.
