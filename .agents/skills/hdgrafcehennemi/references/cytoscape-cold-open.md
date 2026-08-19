# Cytoscape cold-open refresh lifecycle

## Trigger

Use when Spoilerless/hdgrafcehennemi opens with the graph diagonal or otherwise stale, but clicking **Refresh graph** fixes it.

## Root cause

`react-cytoscapejs` starts its declarative layout before invoking the `cy` callback. Starting the button-equivalent forced layout concurrently—including from `queueMicrotask`—races two asynchronous layouts. The startup layout may stop last and overwrite the forced refresh result.

## Proven fix

1. Keep the declarative layout object stable and set `fit: false`.
2. In the live `cy` callback, mark that Cytoscape instance and graph as handled so effects do not start a competing layout.
3. Register `cy.one('layoutstop', handler)` on the startup layout.
4. In that handler, verify the Cytoscape instance is still live.
5. Call the exact Refresh graph path: `runLayout(..., forceRelayout=true)`.
6. Test doubles must model one-shot `layoutstop` delivery.

## Verification

- Run focused GraphCanvas tests, lint, and production build.
- Use computer-use to cold-open/reload the real app without pressing Refresh graph.
- Compare with the Refresh graph result.
- Treat automated tests as supporting evidence only; obtain user acceptance for this visual lifecycle bug.
