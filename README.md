# Evidence Log Inspector

**Inspect JSONL event logs for missing sequence numbers, invalid state transitions, and unsupported or incomplete evidence — without changing the logs.**

**v0.1.0 · Experimental · Python 3.11+ · Standard library only · MIT**

**English** | [日本語](README_ja.md)

## Why use it?

A log can contain valid JSON and still tell an inconsistent story. Events may go missing, a request may be marked `COMPLETED` immediately after an unresolved `UNKNOWN`, or a final result may lack the declared evidence. Evidence Log Inspector (ELI) checks **explicit event contracts**, not just JSON syntax.

ELI is a free, read-only CLI for **controlled local JSONL files**. It does not fill gaps, repair logs, prove that logged events really happened, or establish that unlogged events never occurred.

## Checks at a glance

| Check | Example of an issue |
| --- | --- |
| Per-stream sequence | A missing, duplicate, or decreasing sequence number |
| Per-operation state transitions | `UNKNOWN → COMPLETED` without `RESOLVED` |
| Declared evidence | `RESOLVED` without a nonempty evidence ID; `COMPLETED` without JSON `result: true` |
| Terminal outcomes | An operation ends without `HOLD` or `COMPLETED` |
| JSONL integrity | Duplicate JSON keys, malformed objects, unknown versions, unsupported rules |
| Optional input digest | Log bytes do not match an independently supplied SHA-256 digest |

Sequence numbers are checked **per stream**; operation state belongs to each `(stream_id, operation_id)` pair. A policy may tighten allowed transitions, but cannot relax the tool's built-in `UNKNOWN` safeguards. See [event rules](EVENT_RULES.md).

## Quick start

**Requirements:** Python 3.11 or newer. No third-party Python packages, network connection, or service account.

From the repository root, run the included **synthetic** examples. Use a *new* output directory for each run.

```sh
python eli.py --log samples/normal.jsonl --policy samples/policy.json --out example-normal
python eli.py --log samples/unsafe.jsonl --policy samples/policy.json --out example-unsafe
python eli.py --log samples/hold.jsonl --policy samples/policy.json --out example-hold
```

On Windows, replace `python` with `py -3` if needed. The second command intentionally exits **1** because it detects a violation; this is the expected demonstration. Existing output directories are rejected and never overwritten.

Each run writes `report.json` and `findings.csv` inside its output directory. The program also prints its JSON report to the terminal. Inputs are read-only, never edited or repaired.

## Reading the results

These results were independently observed with the included synthetic examples:

| Example | Status | Exit code | Interpretation |
| --- | --- | ---: | --- |
| `normal.jsonl` | `CONSISTENT_WITH_POLICY` | `0` | Declared checks are consistent |
| `unsafe.jsonl` | `VIOLATION` | `1` | An invalid `UNKNOWN → COMPLETED` transition was found |
| `hold.jsonl` | `HOLD` | `0` | The operation properly stopped; **not** proof of business success |
| Incomplete or unknown input | `UNVERIFIABLE` | `2` | The tool cannot establish a reliable result |

A deliberately bad log producing `VIOLATION` is a **successful negative-control test**, not a safe log. A nonzero exit should be handled by the caller and must not be interpreted as a successful business action.

JSON and CSV reports include selected stream IDs, operation IDs, file paths, sequence evidence, and finding codes. They do **not** copy arbitrary log messages, URLs, or secret fields; selected identifiers and paths may nonetheless be sensitive. CSV values that begin with spreadsheet formula characters are escaped.

## Policy and evidence integrity

The complete sample policy is [samples/policy.json](samples/policy.json). It maps eight logical fields (`stream_id`, `sequence`, `event_type`, `operation_id`, `log_version`, `result`, `evidence`, `timestamp`) to the top-level JSON event fields, defines the initial sequence, clock scope, and permitted state transitions.

The built-in lifecycle includes:

```text
STARTED → RETRY / UNKNOWN / COMPLETED / HOLD
RETRY   → RETRY / UNKNOWN / COMPLETED / HOLD
UNKNOWN → RESOLVED / HOLD
RESOLVED → COMPLETED / HOLD
COMPLETED, HOLD → terminal
```

`RESOLVED` requires a nonempty evidence identifier; ELI checks its **presence**, not the referenced artifact's truth. Timestamps are compared only within a stream when `same_clock` is enabled. It makes no claim about cross-host ordering.

To compare a log against an **independently trusted** SHA-256 of its exact bytes:

```sh
python eli.py --log samples/normal.jsonl --policy samples/policy.json --out example-hash --expected-sha256 YOUR_TRUSTED_64_HEX_DIGEST
```

Without `--expected-sha256`, the report states `NOT_VERIFIED`. A matching digest proves equality to the supplied digest, **not** that the log is complete or truthful. The included `samples/normal.sha256` is only a usage fixture, not a trust anchor.

## Verification

The FIX-01 candidate includes **47 automated tests** (43 original acceptance cases plus four regressions) and an independent comparison using five inputs and four approaches (20 executions). The recorded comparison matched the defined expectations for ELI 5/5, a fixed Python baseline 4/5, and basic `json.tool` / `jq` checks 1/5 each. These approaches have different verification scopes; the results do not establish universal superiority or human time savings.

GitHub Actions is configured for **Ubuntu and Windows × Python 3.11 / 3.12 / 3.13**. Check the [Actions page](https://github.com/KenKan964/evidence-log-inspector/actions) for the latest actual run results. Historical `evidence/ci_status.json` was created before the repository's CI and is **not a live status report**.

```sh
python -m unittest discover -s tests -v
python compare.py > comparison-local.json
```

Optional per-case test evidence requires a **fresh** `ELI_EVIDENCE` directory; an existing evidence filename or symlink causes a test failure instead of silent replacement. Example for POSIX shells:

```sh
ELI_EVIDENCE=acceptance-new python -m unittest discover -s tests -v
```

## Limitations and safety

- JSONL inspection is read-only; ELI never creates missing events or repairs evidence.
- This is not log authentication, forensic chain-of-custody certification, a digital signature system, or proof of the absence of unlogged events.
- One log file is inspected per invocation. Several streams may appear in the same file, but cross-file continuity and multi-host global ordering are **not** inferred.
- Only supported event versions and transitions are evaluated; unsupported conditions are **UNVERIFIABLE**, not safe.
- Size limits include 65,536 bytes per line, 10,000 physical lines, 10 MB total, and maximum JSON nesting of 32. A truncated input cannot produce a full-file digest match.
- Use stable, operator-controlled directories. Concurrent modification or hostile same-user filesystem races are outside the safety guarantee. Keep real event logs and reports private.

## Documentation and license

[日本語 README](README_ja.md) · [Event contract](EVENT_RULES.md) · [Technical specification](TECHNICAL_SPEC.md) · [Security](SECURITY.md) · [Comparison](OSS_COMPARISON.md) · [FIX-01 details](FIX01_CHANGES.md) · [Developer report](REPORT_ja.md) · [Change log](CHANGELOG.md) · [MIT License](LICENSE)

**License:** MIT · Copyright © 2026 KenKan964.
