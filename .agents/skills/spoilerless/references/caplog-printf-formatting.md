# pytest caplog: `getMessage()` vs `str(msg)` with printf-style logs

## Problem

When asserting log content from `caplog.records`, using `str(r.msg)` gives only the
raw format string, not the formatted message. This silently fails assertions when
logs use printf-style formatting (`%s`, `%d`, etc.).

## Root cause

Python's `logging.LogRecord` stores the format string in `msg` and the positional
arguments in `args`.  `str(record.msg)` extracts the template, while
`record.getMessage()` applies `msg % args` to produce the human-readable message.

Pytest's `caplog.records` exposes the raw `LogRecord` objects — same semantics apply.

## Example

```python
import logging

log = logging.getLogger(__name__)

# In production code:
log.info("%s %s %d %.0fms", "GET", "/health", 200, 1.5)

# In test:
with caplog.at_level(logging.INFO):
    client.get("/health")

# WRONG — msg is the format string "%s %s %d %.0fms"
for r in caplog.records:
    assert "GET" in str(r.msg)   # FAILS — msg = "%s %s %d %.0fms"

# CORRECT — getMessage() combines msg + args
for r in caplog.records:
    assert "GET" in r.getMessage()   # PASSES — message = "GET /health 200 2ms"
```

## Fix

Always use `r.getMessage()` when inspecting log content in caplog tests.  The one
exception is when you're deliberately testing that the format string itself is
correct (rare).

## Encountered

08-07 Task 2 (request-logging middleware): the middleware logs
`log.info("%s %s %d %.0fms %s", method, path, status, elapsed_ms, safe_headers)`.
Tests asserting `"GET" in str(r.msg)` silently passed through to the wrong branch
until corrected to `r.getMessage()`.
