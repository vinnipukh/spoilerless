---
quick_id: 260812-gra
status: complete
---

# Summary

Graph launch refresh now waits for Cytoscape's declarative startup layout to emit `layoutstop`, then invokes `runLayout(..., true, ...)`, matching Refresh graph's forced re-layout and fit. This removes the startup race: the prior microtask launched two asynchronous layouts concurrently, allowing the first layout to finish last and restore the diagonal cold-open state.

## Verification

- `NODE_ENV=test CI=1 npm run test -- --run src/components/graph/GraphCanvas.test.tsx`: 25 passed.
- Full `NODE_ENV=test CI=1 npm run test -- --run`: 335 passed, 2 unrelated timing-sensitive tests timed out at default 5s; each passed independently with 15s timeout.
- `npm run lint`: passed.
- `npm run build`: passed; Vite emitted existing chunk-size warning.
- `git diff --check`: passed.
- Live Chrome cold-open test: user confirmed the graph opens in the refreshed layout without pressing Refresh graph.

## Commit

Committed with the final quick-task fix.
