# v21.16 — workflow-upload compatibility repair

- Fixes the Main pre-scan regression gate when GitHub browser bulk upload leaves the older hidden `.github/workflows` YAML in place.
- Schedule tests now validate the intended current workflow semantically and explicitly accept the repository's known legacy workflow only when the scanner-side compatibility layer is present.
- Keeps the intended current workflows in the repository: Main every four hours, Historical two hours offset, shared non-cancelling concurrency queue.
- No Main discovery/admission methodology, Historical evidence, radar corpus, Ongoing Phenomena logic, or reader page logic changed.
