# 09-02: Google verifier behavioral net + progress wire-shape nets (verified 2026-08-05)

Plan 09-02 built the two regression nets for the audit's worst shipped-green
bug classes. Session-specific detail beyond the SKILL.md section.

## The #42 correction (the plan premise was wrong)

09-RESEARCH.md and the pre-09-02 skill claimed the NameError was already fixed:
"`from google.auth.transport import requests as google_requests` binds
`google` in function scope". **False.** `from X.Y import Z as n` binds only `n`.

Empirical proof (run on the live tree):
```python
def f():
    from google.auth.transport import requests as google_requests
    print(sorted(k for k in locals() if not k.startswith("__")))
# -> ['google_requests']   # no 'google'
```
And the first run of the new regression net failed with:
`NameError: name 'google' is not defined` at `spoilerless/app/services/auth.py:73`
(the `except google.auth.exceptions.TransportError` clause), raised as the
outer exception of the chain whenever ANY exception escaped the try block —
in production this replaced the real `google.auth.exceptions.TransportError`
with a NameError the route cannot map → 500 instead of 503/401.

Fix (commit `a36676a`, one line):
```python
try:
    import google.auth.exceptions  # noqa: F401  # binds `google` for the except clause below (#42)
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ImportError as exc:
    raise GoogleTransportError(...) from exc
```

## The MockTransport shim (test_google_verifier.py)

`ProductionGoogleVerifier.verify` lazy-imports `google.auth.transport.requests`
inside the function body → patching the module attribute pre-call is enough:

```python
def _install_mock_google_request(monkeypatch, handler):
    from google.auth import exceptions as google_exceptions
    from google.auth.transport import requests as google_requests_module

    class _MockGoogleRequest:
        def __call__(self, url, method="GET", headers=None, body=None, timeout=None):
            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                try:
                    response = client.request(method, url, headers=headers,
                                              content=body, timeout=timeout)
                except httpx.TransportError as exc:
                    raise google_exceptions.TransportError(str(exc)) from exc
            return _FakeGoogleResponse(response.status_code, response.content)

    monkeypatch.setattr(google_requests_module, "Request", _MockGoogleRequest)
```
`_FakeGoogleResponse` carries `.status` and `.data` (bytes) — google-auth's
`_fetch_certs` reads those two attributes, NOT `.content`.

## google-auth 2.56.2 behavior that shaped the expectations

- `verify_oauth2_token` → `verify_token` → `_fetch_certs(request, certs_url)`
  runs FIRST, before any token decode.
- `_fetch_certs`: `response = request(certs_url, method="GET")`; if
  `response.status != 200` → `raise exceptions.TransportError("Could not fetch
  certificates ...")`; else `json.loads(response.data.decode("utf-8"))`.
- Then `jwt.decode(token, certs=...)`: garbage (1-segment) token →
  `MalformedError("Wrong number of segments in token")`; well-formed token
  whose kid is absent from the JWKS → `MalformedError("Certificate for key id
  ... not found.")`. `MalformedError` extends `ValueError`, so the verifier's
  `except ValueError` branch catches it → `GoogleVerificationError`.
- Cert URL constant is `https://www.googleapis.com/oauth2/v1/certs` (v1).

Resulting test matrix (5 passed + 1 documented skip):

| Case | MockTransport handler | Expected |
|---|---|---|
| garbage token | 200 `{}` JWKS | `GoogleVerificationError`, NOT NameError, isinstance ValueError (route → 401) |
| well-formed unsigned token, empty JWKS | 200 `{}` JWKS | `GoogleVerificationError` |
| transport failure | `raise httpx.TransportError` | `GoogleTransportError` (exercises the #42 branch) |
| cert endpoint 400 | `400 {"error_description": "Invalid value for id_token"}` | `GoogleTransportError` (transport class, not verification) |
| google-auth missing | block `google.*` via `builtins.__import__` monkeypatch | `GoogleTransportError` ("failed to import") |
| valid token happy path | — | `@pytest.mark.skip` (needs Google's live JWKS; FakeGoogleVerifier covers success) |

## Progress wire-shape tests (frontend/src/api/progress.test.ts)

Three shapes asserted against `JSON.parse` of the captured fetch body + URL /
`method: 'POST'` / `credentials: 'include'`:
1. forward confirm `{watchedThroughOrder, viewAsOfOrder}` →
   body `{watched_through_order, view_as_of_order}`, `visible_until_order` ABSENT
2. view-only `{viewAsOfOrder}` → body `{view_as_of_order}` ALONE
3. plain `updateProgress(id, n)` → body `{visible_until_order}` alone

`progress.ts` needed NO change (the 08-04 per-intent builder was already
correct). The file already had stringified-body assertions from `600ce48`;
the 09-02 additions are parsed-body + explicit `not.toHaveProperty` checks.

rg gate: `rg -n "vi\.mock\(" src/api/progress.test.ts` must be empty —
`vi.mocked(globalThis.fetch)` is the fetch-stub type helper and is allowed.

## Verification commands (all green, zero network)

```
uv run pytest spoilerless/tests/test_google_verifier.py -q   # 5 passed, 1 skipped
uv run pytest spoilerless/tests/test_auth.py -q              # 42 passed
cd frontend && NODE_ENV=test CI=1 npx vitest run src/api/progress.test.ts  # 8 passed
cd frontend && npm run build                                 # tsc -b + vite build green
```

## Commits

- `a36676a` fix(09-02): bind google in ProductionGoogleVerifier.verify scope — #42 NameError is LIVE
- `86bcb50` test(09-02): behavioral ProductionGoogleVerifier test (garbage token + MockTransport)
- `082cb79` test(09-02): progress payload wire-shape contract tests (fetch-level, no client mock)
- `63665ce` docs(09): summary for 09-02 + STATE/ROADMAP/REQUIREMENTS tracking

Requirement closure: PROB-14, PROB-15, PROB-23 marked complete; ROADMAP 2/18.
