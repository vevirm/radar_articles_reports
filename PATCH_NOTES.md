# v21.16 — workflow-upload compatibility repair

- Fixes the Main pre-scan regression gate when GitHub browser bulk upload leaves the older hidden `.github/workflows` YAML in place.
- Schedule tests now validate the intended current workflow semantically and explicitly accept the repository's known legacy workflow only when the scanner-side compatibility layer is present.
- Keeps the intended current workflows in the repository: Main every four hours, Historical two hours offset, shared non-cancelling concurrency queue.
- No Main discovery/admission methodology, Historical evidence, radar corpus, Ongoing Phenomena logic, or reader page logic changed.

## v21.18 — Ongoing Phenomena: pattern discovery layer

- Built on the user's latest uploaded repository and current radar data; no scanner or workflow logic changed.
- Ongoing Phenomena now leads with Pattern Watch: framing/vocabulary shifts and strengthening conjunctions across historical + current evidence.
- Adds a separate "Worth checking" candidate layer and an explicit "Could this be an artefact?" counter-case for every proposed pattern.
- Keeps established continuities as a secondary reference layer and reports current evidence outside the hand-written phenomenon matchers.
- Return/dormancy claims remain withheld when historical date precision is too weak.
