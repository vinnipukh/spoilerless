# Frontend UX iteration with this user (graph overlay controls)

Learned 2026-08-13 from live-testing feedback on graph overlays (legend, Filters pill).

## User gives positions in cm — convert, apply literally
- 1cm ≈ 37.8px @96dpi ≈ **2.36rem** (16px rem). 2.5cm ≈ 5.9rem; 5cm ≈ 11.8rem.
- Apply the literal conversion, keep the commit tiny, let the user eyeball it in HMR and correct. Do NOT re-interpret or "fix" their units.
- Direction mistakes happen ("2.5cm left" then "ooops sorry i meant right... 5cm right"). When the corrected instruction conflicts with your previous move, prefer a value that satisfies BOTH readings (in that case 21.4rem = original+2.5cm right = current+5cm right — one commit, no churn).

## Click-target sizing is a recurring complaint
- User said the legend close target was "too small". Graph overlay pills/buttons start at `px-2.5 py-1.5 text-xs` — those are too small for this user. Default to `px-3.5..4 py-2..2.5 text-sm` with `gap-2`, icon `h-4 w-4`, on any new overlay control; audit existing small pills when touching a file.
- Test flow: edit → HMR is live (vite dev running) → user clicks immediately → commit only after they confirm position/size ("ok its good now"). Do not batch UX-tweak commits with logic commits; each gets its own `fix(ux):` commit so position history is readable.

## The "works locally, broken in prod" overlay trap
Graph overlay elements are `fixed` (viewport coords) and can sit under/over other `fixed` elements (legend bottom-left vs Create-node FAB vs GraphControls — z-40 stack). When a user reports a control "can't be clicked", first suspect hit-area/overlap, not state logic: check the CollapsibleTrigger size and z-order before touching component logic.
