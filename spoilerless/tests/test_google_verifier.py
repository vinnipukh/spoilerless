"""Behavioral tests for ProductionGoogleVerifier (PROB-23 / PROBLEMS #42, #47).

The verifier's failure paths are locked here at the httpx.MockTransport level
so the #42 regression class can never ship again: a verification failure
surfacing as a NameError — an unbound ``google`` name inside the
``except google.auth.exceptions.TransportError`` clause of ``verify()`` — which
the login route would misreport as a 503 ``AUTH_SERVICE_UNAVAILABLE`` instead
of the documented 401/verification-error contract.

Every case runs over ``httpx.MockTransport``: zero network access to Google,
zero cost (threat model T-09-02-01 / T-09-02-03). The valid-token happy path
is NOT testable offline (it requires Google's live JWKS plus a token signed by
a key in it) and is documented/skipped below — the regression value of this
net is the failure paths.

Error-mapping contract under test (spoilerless/app/services/auth.py:59-93 and
api/auth.py:208-226):

* ``GoogleVerificationError`` (a ValueError)  -> 401 AUTH_INVALID_GOOGLE_CREDENTIAL
* ``GoogleTransportError``                    -> 503 AUTH_SERVICE_UNAVAILABLE

google-auth 2.56.2 note: ``verify_token`` fetches the signing certificates
BEFORE decoding the token, so a non-200 cert response is a *transport* error
(``google.auth.exceptions.TransportError``), while a 200-but-unverifiable
token is a *verification* error (``ValueError``/``MalformedError``).
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from spoilerless.app.services.auth import (
    GoogleTransportError,
    GoogleVerificationError,
    ProductionGoogleVerifier,
)

CLIENT_ID = "test-client-id.apps.googleusercontent.com"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _fake_id_token(*, kid: str = "fake-kid-1") -> str:
    """A structurally-valid JWT (header.payload.signature) with a known kid.

    The signature is bogus — that is the point: the failure must map to the
    documented error classes without ever touching a real Google endpoint.
    """
    header = _b64url(json.dumps({"alg": "RS256", "kid": kid}).encode())
    payload = _b64url(
        json.dumps(
            {
                "sub": "1234567890",
                "aud": CLIENT_ID,
                "iss": "accounts.google.com",
                "exp": 4_102_444_800,
            }
        ).encode()
    )
    signature = _b64url(b"\x00" * 256)
    return f"{header}.{payload}.{signature}"


class _FakeGoogleResponse:
    """google.auth.transport.Response-shaped object (``status`` + ``data`` bytes)."""

    def __init__(self, status: int, data: bytes) -> None:
        self.status = status
        self.data = data


def _install_mock_google_request(
    monkeypatch: pytest.MonkeyPatch, handler: object
) -> None:
    """Swap ``google.auth.transport.requests.Request`` for a MockTransport shim.

    ``ProductionGoogleVerifier.verify`` lazy-imports
    ``google.auth.transport.requests`` inside the function body, so patching
    the module attribute before the call is sufficient — no settings or
    lru_cached instance replacement needed (get_settings() pitfall avoided).

    httpx.TransportError from the MockTransport is translated to
    ``google.auth.exceptions.TransportError`` exactly like the real
    requests-based transport does (``except requests.exceptions.RequestException
    -> raise google.auth.exceptions.TransportError``), so the verifier's
    documented ``except google.auth.exceptions.TransportError`` branch — the
    branch that NameError'd in #42 — is the one under test.
    """
    from google.auth import exceptions as google_exceptions
    from google.auth.transport import requests as google_requests_module

    class _MockGoogleRequest:
        def __call__(
            self,
            url: str,
            method: str = "GET",
            headers: object = None,
            body: object = None,
            timeout: object = None,
        ) -> _FakeGoogleResponse:
            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                try:
                    response = client.request(
                        method, url, headers=headers, content=body, timeout=timeout
                    )
                except httpx.TransportError as exc:
                    raise google_exceptions.TransportError(str(exc)) from exc
            return _FakeGoogleResponse(response.status_code, response.content)

    monkeypatch.setattr(google_requests_module, "Request", _MockGoogleRequest)


def _certs_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cert endpoint answers 200 with an empty JWKS so token decode proceeds."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.googleapis.com", (
            f"cert fetch hit unexpected URL: {request.url}"
        )
        return httpx.Response(200, json={})

    _install_mock_google_request(monkeypatch, handler)


# ---------------------------------------------------------------------------
# Failure paths — the regression net for #42/#47
# ---------------------------------------------------------------------------


async def test_garbage_token_raises_verification_error_not_name_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An opaque garbage token maps to GoogleVerificationError — never NameError.

    google-auth 2.56.2 fetches certs before decoding, so the transport answers
    200 with an empty JWKS and the decode itself fails on the malformed token
    (ValueError) -> GoogleVerificationError.
    """
    _certs_200(monkeypatch)
    verifier = ProductionGoogleVerifier()

    with pytest.raises(GoogleVerificationError) as exc_info:
        await verifier.verify("garbage-not-a-jwt", CLIENT_ID)

    # The #42 regression: a verification failure must never surface as a
    # NameError (which the route would misreport as 503 AUTH_SERVICE_UNAVAILABLE).
    assert not isinstance(exc_info.value, NameError)
    # Route-level mapping: GoogleVerificationError is a ValueError, so the
    # login route answers 401 AUTH_INVALID_GOOGLE_CREDENTIAL, never 503.
    assert isinstance(exc_info.value, ValueError)


async def test_unverifiable_signature_raises_verification_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A structurally-valid token no known cert can verify -> GoogleVerificationError.

    Covers the 'invalid signature' verification-failure class (kid lookup
    fails against the empty JWKS -> MalformedError, a ValueError subclass).
    """
    _certs_200(monkeypatch)
    verifier = ProductionGoogleVerifier()

    with pytest.raises(GoogleVerificationError) as exc_info:
        await verifier.verify(_fake_id_token(), CLIENT_ID)

    assert not isinstance(exc_info.value, NameError)
    assert isinstance(exc_info.value, ValueError)


async def test_transport_failure_maps_to_google_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """httpx.MockTransport raising httpx.TransportError -> GoogleTransportError.

    This exercises the exact ``except google.auth.exceptions.TransportError``
    branch that NameError'd in #42: the transport shim translates the httpx
    failure the way google-auth's real requests transport does, and the
    verifier must map it to the documented 503-class error, not crash.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TransportError("connection reset by peer")

    _install_mock_google_request(monkeypatch, handler)
    verifier = ProductionGoogleVerifier()

    with pytest.raises(GoogleTransportError) as exc_info:
        await verifier.verify(_fake_id_token(), CLIENT_ID)

    assert not isinstance(exc_info.value, NameError)
    assert "Failed to fetch Google signing certificates" in str(exc_info.value)


async def test_cert_fetch_http_error_maps_to_google_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-200 cert response (400 Invalid value for id_token) -> GoogleTransportError.

    Mirrors the plan's canned error response. google-auth 2.56.2 raises
    ``google.auth.exceptions.TransportError`` whenever the cert endpoint does
    not answer 200 — a transport-class failure, never a verification error.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"error_description": "Invalid value for id_token"}
        )

    _install_mock_google_request(monkeypatch, handler)
    verifier = ProductionGoogleVerifier()

    with pytest.raises(GoogleTransportError) as exc_info:
        await verifier.verify(_fake_id_token(), CLIENT_ID)

    assert not isinstance(exc_info.value, NameError)


async def test_missing_google_auth_import_maps_to_google_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lazy google-auth import failing -> GoogleTransportError (auth.py:63-67)."""

    import builtins

    real_import = builtins.__import__

    def _block_google(name: str, *args: object, **kwargs: object) -> object:
        if name == "google" or name.startswith("google."):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_google)
    verifier = ProductionGoogleVerifier()

    with pytest.raises(GoogleTransportError) as exc_info:
        await verifier.verify("any-token", CLIENT_ID)

    assert not isinstance(exc_info.value, NameError)
    assert "failed to import" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Happy path — not testable offline
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "A valid-token success path requires google-auth to fetch Google's "
        "live JWKS and verify a token actually signed by one of its keys — "
        "not testable over MockTransport without spending real network. The "
        "regression value of this net is the #42/#47 failure paths; the "
        "success path is covered by FakeGoogleVerifier in test_auth.py."
    )
)
async def test_valid_token_happy_path_requires_live_google_certs() -> None:
    """Documented, skipped: success requires Google's live signing certs."""
