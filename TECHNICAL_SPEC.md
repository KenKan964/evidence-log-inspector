# Technical specification

API inspect(log_path, policy_dict, expected_sha256=None) returns a deterministic report dictionary.
CLI --log/--policy/--out required, --expected-sha256 optional. No arbitrary target URL or command API.
Same bytes + same path + same policy + same external digest yield identical report data; no wallclock/random identifiers.
report.json is sorted UTF-8 JSON; findings.csv contains the same findings with formula-prefix escaping.
Report printing never includes whole events or arbitrary JSON decode snippets.

Algorithm: bounded binary readline -> strict UTF-8 -> string-aware nesting scan -> duplicate-key/nonfinite rejection ->
version/field validation -> per-stream sequence/timestamp -> per-operation transition/evidence -> terminal coverage.
Malformed input sets sticky UNVERIFIABLE. Known violations set exit1 unless an unverifiable condition takes precedence (exit2).
Sequence state is per stream, operation state is (stream,operation). In-memory sets bounded by the line limit.
No sorting of input to conceal regressions; input file order is the declared order.
End state HOLD can be consistent, always status HOLD; never labelled COMPLETED.

Hash is computed on actual input bytes, including newline differences. Resource truncation disables full-file hash match.
External digest trust and its original timestamp/custodian are caller responsibilities. No signature/trust-store implementation.
Evidence identifier is a syntactic assertion, not validation that referenced business evidence exists.
Source concurrently modified during inspection can yield a mixed observation: caller must supply a quiescent file or trusted digest.
No full filesystem race isolation or protection against malicious same-user output replacement.

Default limits fixed in source: line 65536 bytes, 10000 physical lines, total 10000000 bytes, nesting32, policy65536 bytes.
The total-byte check reads at most one bounded line past the limit; full digest unavailable after limit.
Policy unknown fields, duplicate keys, unsafe transitions, unknown version are rejected.
Unused event fields are ignored and not emitted. Selected IDs/paths may contain sensitive labels, so evidence is private by default.
The CLI creates a new output directory exclusively. Write failures exit2; partial outputs are not successful evidence.
This MVP accepts one file per invocation; multiple streams can be interleaved in that file. Multi-file continuity is not inferred.

## FIX-01: evidence safety

Test preserve_evidence uses open('x',encoding='utf-8') on every output file.
Existing files and file symlinks cannot be opened for replacement; exceptions fail unittest.
Absolute destination and all parent components are checked for symlinks before mkdir.
Static directory symlinks are rejected. Same-user filesystem races remain outside the safety guarantee.
Missing ELI_EVIDENCE means ordinary tests without artifact capture; declared evidence output must actually succeed.
Product eli.py is unchanged. Comparison driver supplies identical, otherwise-valid duplicated-key bytes to every arm.
