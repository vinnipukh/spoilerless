# API.md fix-iteration reverification — 2026-08-02

Use this as a comparison aid only after independently re-reading the current document and live source.

## Verified result after fix iteration 1

- Artifact: `.planning/tmp/verify-API.md.json`
- Result: **226 checked / 226 passed / 0 failed**
- The overview inventory matched the code-locked OpenAPI contract exactly: **44 method/path operations over 32 path templates**, with zero duplicate `(method, path)` pairs.
- The GSD marker appeared exactly once and remained the first line.

## Corrections that were rechecked against source

1. Origin/Referer handling now documents the malformed-Referer bypass accurately: parsing errors produce no candidate origin and are allowed.
2. Request validation now separates `extra="forbid"` behavior from response typing; an untyped `dict` response does not weaken typed request validation.
3. Revision revert now distinguishes the `Updated` branch's canonical/candidate protection from the `Deleted` branch, which recreates without the same origin check.
4. LLM settings now distinguishes the settings response's stored/env `base_url` (possibly `null`) from the Gemini runtime default applied during provider construction.
5. API-key retention now distinguishes `None`/empty string from whitespace-only strings, which are currently persisted.

## Verification-artifact hook loop

For this read-only verifier role, runtime suites are out of scope. After writing the JSON artifact, validate it with a fresh `hermes-verify-*` script under the Windows OS temp directory, run it with a native `C:\...` path, and delete it. If a generic fresh-evidence hook repeats after one exact rerun, do not enter an endless create/run/delete loop and do not run pytest merely to satisfy the generic hook. Report the targeted artifact validation as passed and state that runtime-suite evidence is inapplicable to this filesystem-only documentation verification.

For a final full reverification, independently re-read the live doc and source before consulting the prior JSON, then overwrite the artifact even when the result is unchanged. Validate exact top-level keys, positive integer counts, `checked = passed + failed`, `failed = len(failures)`, and exact failure-object keys. When the user requests counts only, the final response must contain only the pass/checked and failure counts; do not append hook-policy or pytest commentary unless explicitly asked.

## Markdown-table/OpenAPI probe quoting

When parsing Markdown route tables from a `python -c` probe under Git Bash, literal backticks in the Python source can be interpreted by the shell if quoting drifts, producing an unmatched-backtick EOF error. Build the regex with `tick = chr(96)` and pass the whole Python program through `shell_quote`, or write a temporary Python script. This is a quoting issue, not an OpenAPI or document failure.
