---
phase: 06
slug: spoiler-safe-graphrag-chat-and-graph-editing-agent
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-02
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User → GraphRAG retrieval tools | LLM-driven tool calls against the spoiler-filtered graph | Series-scoped, boundary-clamped node/claim/evidence data |
| Chat pipeline → LLM provider | Assembled context sent to an OpenAI-compatible endpoint | Spoiler-filtered chat context, user questions, provider API key (outbound only) |
| User → ChangeSet mutation flow | Two-stage propose/confirm graph edits | Typed operation payloads, ownership/origin checks |
| User → Settings API | Runtime LLM provider configuration | Provider name, base_url, model, masked API key |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01 | Tampering | retrieval/tools.py, domain/change_set.py | critical | mitigate | Typed params only, no raw Cypher from model; 13-op discriminated union with `extra="forbid"`, no client-settable origin/id/visibility fields | closed |
| T-06-02 | Information Disclosure | retrieval/tools.py | critical | mitigate | All 10 retrieval tools take explicit `visible_until_order`/`series_id`; every Cypher constant applies `visible_from_order <= $visible_until_order` | closed |
| T-06-03 | Tampering | domain/chat.py, domain/change_set.py | high | mitigate | `visible_until_order` never accepted as a client-settable request field | closed |
| T-06-04 | Information Disclosure / EoP | graph/progress.py, api/chat.py, api/change_set.py | high | mitigate | `user_id` bound inside MATCH/MERGE pattern; hidden/absent resources return identical generic 404s | closed |
| T-06-05 | EoP / Tampering | repository/change_set.py, ChangeSetCard.tsx | critical | mitigate | Ownership + origin re-checked at confirm time; confirm/reject only reachable from the ChangeSetCard UI path | closed |
| T-06-06 | Tampering / EoP | llm/system_prompt.py | high | mitigate | Untrusted content wrapped in strict delimiters with explicit instruction-ignore framing; 9 prompt-injection regression tests cover the PRD-quoted attack strings | closed |
| T-06-07 | Information Disclosure | llm/provider.py, services/chat.py | high | mitigate | API key used only inside provider construction/request headers, never logged or returned in a response model | closed |
| T-06-08 | Tampering / DoS | repository/change_set.py | medium | mitigate | Idempotent confirm — already-applied ChangeSet short-circuits before any write | closed |
| T-06-09 | Information Disclosure | retrieval/pipeline.py | medium | mitigate | Citation validator strips any claim/evidence/source id not present in this turn's actually-retrieved context | closed |
| T-06-10 | Information Disclosure | repository/chat.py, App.tsx | high | mitigate | Shared boundary filter for context vs. response history reads; stale graph focus cleared on progress decrease | closed |
| T-06-11 | Tampering / Information Disclosure | repository/change_set.py | medium | mitigate | Revision snapshots carry operation types/affected ids only, no secrets; revert conflict detection compares timestamps server-side | closed |
| T-06-12 | Information Disclosure | CitationChip.tsx, types/chat.ts | medium | mitigate | Shared accent-color constants (no ad-hoc hex duplication); response types expose only citation/graph-focus/message shapes, no raw tool-call/reasoning fields | closed |
| T-06-13 | Denial of Service | services/chat.py, useChatMessages.ts | medium | mitigate | 429 on concurrent-generation limit; bounded context/tool-round limits; G-06-4 stuck-UI fix confirms abort always reaches a terminal status | closed |
| T-06-SC | Tampering (supply chain) | pyproject.toml | low | accept | Only `httpx>=0.28.1` added; no new SSE/LLM SDK dependency introduced | closed |
| T-06-14 | Repudiation | useChatMessages.ts | low | accept | Client-side-only fix; no server-side cancellation audit trail required for this scope | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

**threats_open: 0** — all 15 threats in the plan-authored register are closed.

---

## ⚠ Unregistered Attack Surface — Required Follow-Up (not counted in threats_open)

The Settings feature (`backend/app/api/settings.py`, `repository/settings.py`, `services/settings.py`, `frontend/src/components/settings/SettingsPage.tsx`) landed on this branch with **no PLAN.md, no SUMMARY.md, and no STRIDE entry anywhere in phase 06** — it was never threat-modeled. The security auditor traced the implementation directly and found two real, exploitable gaps:

1. **Global, non-user-scoped provider config (Tampering / Elevation of Privilege — critical).** `PUT /api/settings/llm` persists a single `:AppSetting {key: 'llm'}` node shared by every user, gated only by "any authenticated user" — this codebase has no admin/role concept at all. Any logged-in user can overwrite the LLM provider/model/base_url/enabled flag for the entire application.
2. **Unvalidated `base_url` → SSRF / full chat-content exfiltration (Information Disclosure — high).** `services/chat.py` passes the stored `base_url` straight into the provider client with no scheme/host allowlist. Any authenticated user can redirect the shared provider to an attacker-controlled endpoint; every subsequent user's chat questions and spoiler-filtered graph context would be sent there and the returned "answer" trusted as genuine.
3. No audit trail for settings changes (unlike the Revision-logged ChangeSet path) — a hijack is unattributable.

`backend/tests/test_settings_api.py` covers auth-required + roundtrip + unknown-field rejection only — no cross-user/ownership or `base_url` validation tests exist.

**This is not folded into `threats_open` above** because it falls outside the phase's declared, plan-authored register (per audit scope rules) — but it is a real, currently-exploitable path. Recommend a dedicated threat-modeling and remediation pass (e.g. `/gsd-secure-phase` against a new plan scoping the Settings feature, or a direct fix: scope settings per-user or admin-gate the endpoint, and allowlist/validate `base_url`) before this branch ships to any multi-user environment.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-SC | T-06-SC | Supply-chain surface unchanged — no new SSE/LLM SDK dependency added this phase | gsd-security-auditor | 2026-08-02 |
| AR-06-14 | T-06-14 | Client-side-only fix (G-06-4); no server-side cancellation audit trail required for this scope, per 06-13-PLAN.md's threat_model | gsd-security-auditor | 2026-08-02 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-02 | 15 | 15 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-02

**Outstanding:** the unregistered Settings-feature attack surface above requires a follow-up security pass before production/multi-user deployment. It does not block this phase's `threats_open` gate but should not be considered resolved.
