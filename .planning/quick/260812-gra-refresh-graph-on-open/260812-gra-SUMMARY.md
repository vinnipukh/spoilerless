---
quick_id: 260812-gra
status: complete
---

# Summary

Graph launch refresh now runs from the Cytoscape `cy` callback, after the live instance exists. A microtask invokes `runLayout(..., true, ...)`, matching Refresh graph's forced re-layout and fit. The callback guards by cy identity and confirms the instance remains live, avoiding missed cold loads and stale-instance refreshes.

## Verification

- `NODE_ENV=test CI=1 npm run test -- --run src/components/graph/GraphCanvas.test.tsx`: 25 passed.
- Full `NODE_ENV=test CI=1 npm run test -- --run`: 335 passed, 2 unrelated timing-sensitive tests timed out at default 5s; each passed independently with 15s timeout.
- `npm run lint`: passed.
- `npm run build`: passed; Vite emitted existing chunk-size warning.
- `git diff --check`: passed.

## Commit

Code commit pending final staging.
