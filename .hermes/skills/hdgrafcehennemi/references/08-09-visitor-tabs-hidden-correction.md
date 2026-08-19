# CORRECTION (2026-08-09, commit `bbddde9`)

The design described in this reference — "Notes tab degrades to a sign-in
hint since GET /notes is auth-gated too" — was REVERSED by the user on
08-09. Notes AND History tabs are now **hidden entirely** in visitor
(readOnly) mode, because both are auth-gated surfaces (note writes +
revision revert 401 for guests) and showing them is a dead end.

Fix that shipped: in `DetailPanel.tsx`, gate both `TabsTrigger`s on
`!readOnly` (`{!readOnly && noteTargetType && ...}` / `{!readOnly &&
(selectedNode || activeClaim) && ...}`), delete the sign-in-hint branch in
the Notes tab body as dead code. Browse-only tabs (Overview/Backlinks/
Claims/Evidence) remain. Test: DetailPanel.test.tsx visitor case asserts
Notes + History absent, browse tabs present. Full FE suite 329/329 + build
green; Vercel deploy success.

The rest of this reference (TooltipProvider crash diagnosis, pre-existing-reds
technique, gsd-quick-on-this-repo notes) remains valid.
