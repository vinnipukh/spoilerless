# Quick Task PLAN — 20260814-security-audit

**Description:** Full adversarial security audit of the hdgrafcehennemi (Spoilerless) application — frontend, backend/API, LLM/GraphRAG agent, Neo4j, Redis cache, auth/session, deployment (Render/Vercel/Cloudflare), dependencies, abuse/DoS, privacy/logging. Deliverables: SECURITY_AUDIT.md, SECURITY_ATTACK_SURFACE.md, SECURITY_TEST_PLAN.md.

**Mode:** quick (skips research/discussion — task spec provided in full by user; no code changes, audit only)

## Tasks

1. **Dispatch 10 specialized audit subagents** (waves of ≤3 parallel):
   - S1 Architecture & Attack Surface Mapper
   - S2 Backend/API Security Auditor
   - S3 Frontend Security Auditor
   - S4 LLM/Agent Security Red Team
   - S5 GraphRAG/Neo4j Security Auditor
   - S6 Secrets, Infrastructure & Deployment Auditor
   - S7 Dependency/Supply Chain Auditor
   - S8 Abuse/DoS/Resource Exhaustion Auditor
   - S9 Privacy/Logging/Information Disclosure Auditor
   - S10 Independent Adversarial Reviewer (after findings exist)
   - Each writes findings to `.planning/quick/20260814-security-audit/findings/S{n}-{name}.md`
2. **Synthesize** three deliverables at repo root:
   - `SECURITY_AUDIT.md` (exec summary, architecture, trust boundaries, entry-point inventory, LLM capability map, findings, attack chains, spoiler boundary analysis, remediation roadmap P0-P3)
   - `SECURITY_ATTACK_SURFACE.md` (living endpoint/input doc)
   - `SECURITY_TEST_PLAN.md` (regression test plan)
3. **GSD closeout:** SUMMARY.md (status: complete), STATE.md quick-task entry, atomic docs commit.

## Constraints

- Static analysis + safe local reproduction only. NO destructive/live prod actions.
- Never mutate live Neo4j AuraDB; never touch real user rows; no brute force; no uncontrolled load.
- No code changes (audit only). Do not commit user's dirty working tree — stage only audit deliverables.
- Findings format: ID (SEC-XXX-nnn), title, severity, confidence, component, relevant code (file:line), entry point, data flow, vulnerability, attack scenario, impact, reproduction, existing defenses, recommended fix, verification.
