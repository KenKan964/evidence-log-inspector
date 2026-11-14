# Security / 安全条件

Log values are data; URLs, filesystem paths and commands inside events are never executed.
Product code has no subprocess or network access. Comparison script launches only fixed local parser tools with synthetic input.
Use operator-controlled input/output directories. Protect reports containing selected IDs and input paths.
Do not publish real logs. Supplied samples and all tests are anonymous synthetic data.
No repair, event invention or missing-file discovery. Internal consistency does not prove event truth, completeness or non-tampering.
A trusted pre-existing external hash is required for meaningful byte comparison. Bundled sample hashes are not trust anchors.
Output directory races and concurrent modification by a hostile same-user process are outside the isolation guarantee.
GitHub private vulnerability reporting is proposed but its activation has not been verified. Do not publish sensitive logs or vulnerability details in public issues.
MIT attribution is set to the repository owner KenKan964, subject to the publisher confirming applicable third-party rights. Check actual GitHub Actions results before public release.

FIX-01: test evidence creation is exclusive; existing artifacts and symlink paths fail the suite.
Use operator-owned fresh directories. No same-user path-race isolation claim.
Comparison fixtures and regression child runs contain synthetic markers only.
