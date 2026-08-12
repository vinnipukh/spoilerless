---
quick_id: 260812-gra
status: complete
---

# Refresh graph automatically on website open

Run the same forced Cytoscape layout and fit used by the Refresh graph button when each live graph canvas instance is created.

## Tasks

1. Update `frontend/src/components/graph/GraphCanvas.tsx` so launch refresh is scheduled from the `cy` callback after the Cytoscape instance exists, guarded by cy identity and live-instance checks.
2. Verify focused GraphCanvas tests, full frontend tests, lint, build, and diff hygiene.
