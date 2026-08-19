# React/Cytoscape scene-transition debugging

Use when real browser UAT reaches an ErrorBoundary while mocked React tests stay green, especially when switching graph projections without remounting Cytoscape.

## Validated diagnostic sequence

1. **Reproduce in real browser.** Prefer a driver-owned isolated Chrome profile so existing tabs, cookies, and extensions do not affect evidence. Bind typed browser control only after exact `(pid, window_id)` targeting reports `binding_quality: exact` and `mutation_allowed: true`.
2. **Capture visible failure.** Record action that triggered it, ErrorBoundary copy, selected series/episode/view, and before/after screenshot.
3. **Read runtime console, not fallback copy.** For driver-owned Chrome, inspect process command line only to locate its ephemeral `--user-data-dir`. Read `<profile>/DevToolsActivePort`, fetch `http://127.0.0.1:<port>/json/list`, select target page, then connect to its `webSocketDebuggerUrl`. Send `Runtime.enable` and `Log.enable`; Chrome replays buffered console/network entries. Print only `Runtime.consoleAPICalled`, `Runtime.exceptionThrown`, and `Log.entryAdded`. Never print cookies, storage, request headers, or credentials.
4. **Validate both payloads independently.** Compare source and destination scenes. For each payload, build node-ID set and assert every edge source/target exists. Compare shared IDs and endpoint/data changes across scenes.
5. **Inspect transition algorithm.** `react-cytoscapejs` patches in this order: remove old-only elements, add new-only elements, then patch shared IDs through `cyEle.json(...)`. Cytoscape removal can cascade through incident edges. Shared IDs whose shape changes across scenes require a real transition test; static payload validity alone cannot prove safe rendering.
6. **Build red loop before fixing.** Existing tests that mock `react-cytoscapejs` prove wiring only. Add a real Cytoscape/headless or browser transition test that renders scene A, updates to scene B, asserts no exception, verifies all edges resolve, and checks required camera/selection preservation.

## Observed HD Graf signature

Story to Characters UAT produced:

`Can not create edge dexter:claim:s01e01:camilla_works_dexter:edge with nonexistent target dexter:character:dexter_morgan`

Both backend payloads contained that edge and target; destination `character_network` payload had zero dangling edges. This rules out a simple serialized dangling-edge explanation. Treat frontend incremental transition/identity handling as investigation target, not proven fix.

## Fix guardrails

- Do not mask crash in ErrorBoundary.
- Do not filter valid edges client-side without proving backend contract violation.
- Do not force a keyed remount as default: HD Graf requires shared canvas, camera/selection preservation, and no global relayout across top-tab switches.
- Rank fixes only after red test reproduces exact transition.
- Re-run real browser path after tests; mocked unit tests are insufficient.
- Preserve unrelated working-tree changes and never mutate shared live Neo4j during diagnosis.
