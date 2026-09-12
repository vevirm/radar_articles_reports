UPLOAD THIS PATCH FROM THE GITHUB REPOSITORY ROOT.

1. Extract/unzip radar_v24.7.6_exceptional_c_patch.zip on your computer.
2. Open the extracted folder.
3. In GitHub, go to the ROOT of vevirm/radar_articles_reports (not /tests, /scripts or another folder).
4. Choose Add file -> Upload files.
5. Upload ALL contents of this extracted folder.
6. Confirm GitHub paths look like:
   scripts/scan_radar.py
   tests/test_v2476_exceptional_c_release.py
   tests/all_tests.zip
   radar_config.json
   VERSION.txt
   V2476_EXCEPTIONAL_C_BYPASS.md
   FILES_TO_UPLOAD.txt
   UPLOAD_README_EXCEPTIONAL_C.txt
7. There must NOT be a radar_v24.7.6_exceptional_c_patch/ prefix in the GitHub paths.
8. Commit directly to main.

Suggested commit message:
Add exceptional C urgency bypass

IMPORTANT:
- This patch deliberately does NOT contain radar.json, so it will not overwrite the live corpus, pending-C queue or current publication ledger.
- Do NOT unzip tests/all_tests.zip. GitHub's regression runner expects that file to remain zipped.
