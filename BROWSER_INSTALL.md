# Radar V25 — easiest full-repository browser installation

You do **not** need to upload hundreds of files individually.

You will use two files supplied with the final ChatGPT answer:

1. `INSTALL_FULL_REPOSITORY.yml`
2. `RADAR_V25_FULL_REPOSITORY_PAYLOAD.zip`

The ZIP contains the complete replacement repository. The installer action unpacks it inside GitHub and commits the full tree.

## Step 1 — upload the installer workflow

In GitHub:

1. Open the Radar repository.
2. Click **Code**.
3. Open **.github** → **workflows**.
4. Click **Add file** → **Upload files**.
5. Upload `INSTALL_FULL_REPOSITORY.yml`.
6. At the bottom choose **Commit directly to the `main` branch** and click **Commit changes**.

## Step 2 — upload the complete repository payload

1. Return to the repository root (**Code**).
2. Click **Add file** → **Upload files**.
3. Upload `RADAR_V25_FULL_REPOSITORY_PAYLOAD.zip`.
4. Commit directly to `main`.

Do not unzip the payload yourself. GitHub will do that in the next step.

## Step 3 — install the complete repository

1. Open **Actions**.
2. Choose **INSTALL — Full Radar V25 Repository**.
3. Click **Run workflow**.
4. In `confirm_replace`, type exactly: `REPLACE`
5. Click **Run workflow**.
6. Wait until the run is green.

The action replaces the repository files from the supplied V25 payload and removes the temporary payload ZIP from the installed repository. Git history remains intact.

## Step 4 — initialise V25 and get the first Deep Scan package

1. Still under **Actions**, open **Radar V2 — Initialise, Validate & Prepare Deep Scan**.
2. Click **Run workflow** → **Run workflow**.
3. Wait for a green run.
4. Open that run.
5. Under **Artifacts**, download **radar-v2-migration-and-deep-scan**.
6. Unzip that artifact and take out `deep_scan_package.zip`.

## Step 5 — your normal Deep Scan cycle

Give `deep_scan_package.zip` to a browsing-capable LLM and say:

> Process this Deep Scan V2 package strictly according to INSTRUCTIONS.md. Go deeply and systematically. Process records in supplied order. Do not cherry-pick. Do not stop early on difficult records. Exhaust the mandatory recovery ladder before declaring a work unverifiable. Return deep_scan_results.json or a ZIP containing it.

When the LLM returns the result:

1. GitHub → **Code** → `deep_scan_inbox`.
2. **Add file** → **Upload files**.
3. Upload `deep_scan_results.json` or the returned ZIP.
4. Commit directly to `main`.
5. GitHub automatically runs **Deep Scan V2 — Import Returned Results**.
6. Wait for green.
7. Open that workflow run and download the **next-deep-scan-package** artifact.
8. Repeat.

New automatic-scanner discoveries remain provisionally active while they wait in the FIFO Deep Scan queue. Once a V2 Deep Scan is validated, its evidence/admission/metadata/interpretation becomes authoritative for the active Radar and the derived reasoning/Excel are rebuilt.
