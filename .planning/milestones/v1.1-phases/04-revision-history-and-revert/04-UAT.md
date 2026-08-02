---
status: complete
phase: 04-revision-history-and-revert
source: 04-SUMMARY.md
started: 2026-07-30T14:40:00.000Z
updated: 2026-07-30T15:08:00.000Z
---

## Current Test

[testing complete]

## Tests

### 1. History tab shows revisions for notes on the selected node
expected: Creating/editing a note on a node shows Created/Updated revisions in the History tab
result: pass
fix: Changed RevisionHistoryPanel to fetch all series revisions (no resource filter) and client-side filter for revisions involving the selected node (by target_id, source, target in before/after JSON). Previously it only fetched exact resource_type+resource_id matches, which never matched because note revisions have resource_type=UserNote, not the character's type.

### 2. Action badges show correct colors
expected: Revisions show colored badges: Created=green, Updated=amber, Deleted=red, Reverted=blue — with text labels, never color-only
result: pass

### 3. Diff summary shows changed fields
expected: Each revision shows which fields changed (e.g. "content: 'new content'", "label changed") as monospace chips
result: pass

### 4. Revert button only on UPDATED/DELETED
expected: Revert button appears only on Updated and Deleted revisions. Created and Reverted revisions have no revert button.
result: pass

### 5. Revert confirm dialog
expected: Clicking "Revert" opens a confirmation dialog with explanatory text and Cancel/Revert buttons
result: pass

### 6. One-shot revert flow
expected: After confirming revert, button shows "Reverting…", POST completes, success toast "Revision reverted successfully" appears, revision list refreshes
result: pass

### 7. No regression: graph functions normally
expected: Selecting/deselecting nodes, viewing Overview/Claims/Evidence/Notes tabs, editing/creating notes all continue to work as before
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Creating/editing a note on a node shows Created/Updated revisions in the History tab"
  status: fixed
  reason: "User reported: no history doesn't track those changes"
  severity: major
  test: 1
  root_cause: "RevisionHistoryPanel fetched revisions filtered by exact resource_type+resource_id match. Note revisions have resource_type=UserNote and resource_id=note.id, not the character node's id, so they never matched when viewing a character's history."
  artifacts:
    - path: "frontend/src/components/detail/RevisionHistoryPanel.tsx"
      issue: "useRevisions called with resourceType/resourceId matching the selected node, but revisions for notes on that node have different resource_type/resource_id"
  missing:
    - "Client-side filter to match revisions by target_id, source, target in before/after JSON"
  debug_session: "In-session diagnosis: inspected component code, identified that resource_type+resource_id filter was too narrow for node history. Added isRevisionRelatedTo() helper and changed hook call to omit resource filter for non-Claim resources."
