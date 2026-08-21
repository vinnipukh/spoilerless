---
name: deslopify
description: Comprehensive codebase simplification, aggressive de-bloating, surgical refactoring, and architectural deepening. Scans for 1k+ line god-files, dead code, and code smells, catalogs issues, searches the web for canonical best practices, and delivers visual architectural reports or automated behavioral-preserving fixes.
---

# Deslopify: Codebase Simplification, Refactoring & Architectural Deepening

`deslopify` is an end-to-end skill for eliminating code bloat ("slop"), modularizing oversized files (especially 1k+ line god-files), removing dead code, establishing clean architectural seams, and simplifying codebases so they are intuitive to understand, explain, and maintain—all while strictly preserving functional parity.

---

## The 4-Step Core Workflow

When invoked on a codebase, module, or specific subsystem, execute these 4 phases in sequence:

```
┌──────────────────────────────────────────────────────────┐
│  STEP 1: SCAN THE PROJECT                                │
│  • Hot spot analysis & Git history                       │
│  • File line count & god-module audit (>1k lines)         │
│  • Code smell & dead code detection                      │
│  • Architectural depth & seam evaluation (Deletion Test) │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 2: MAKE A LIST OF ISSUES                           │
│  • Categorized audit by severity & locality              │
│  • God-files, shallow wrappers, leaky seams              │
│  • Redundant abstractions & complexity debt              │
│  • Structural breakdown of 1k+ line files                │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 3: SEARCH THE WEB TO SOLVE ISSUES                  │
│  • Search canonical design patterns & recipes            │
│  • Framework & library idioms (FastAPI, React, Neo4j)    │
│  • Modern syntax benchmarks & zero-dependency solutions  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 4: CREATE SUGGESTIONS / SOLVE THEM                 │
│  • Option A: Self-contained Visual HTML Report (Mermaid) │
│  • Option B: Surgical, step-by-step refactoring          │
│  • Option C: Aggressive simplification & dead code wipe  │
│  • Mandatory verification: behavior parity & tests       │
└────────────────────────────┘
```

---

## Step 1: Scan the Project

Exhaustively explore the codebase to identify bloat, complexity, and structural friction:

1. **Scope & Hot Spot Analysis**:
   - Check `git log --oneline` to find recent hot spots and frequently churned files.
   - Read domain glossaries (`CONTEXT.md`, `README.md`, or architecture docs) and ADRs (`docs/adr/`) to understand intended boundaries.
2. **File Size & God-Module Audit**:
   - Locate every file with high line counts (flagging all files with **1,000+ lines**).
   - Identify god-classes and god-functions (>50 lines, multi-responsibility methods).
3. **Dead Code & Redundancy Scan**:
   - Unused imports, orphaned helper functions, deprecated variables, commented-out code blocks.
   - Duplicate logic across controllers, services, or UI components.
4. **Architectural Depth & Friction Analysis**:
   - Identify **shallow modules** whose interface is nearly as complex as their implementation.
   - Find **leaky seams** where internals or external client details bleed across layers.
   - Apply the **Deletion Test**: *"Would deleting or inlining this helper/module concentrate complexity, or just move it around?"* (If it just moves it, it is a shallow abstraction to eliminate or consolidate).

---

## Step 2: Make a List of Issues

Synthesize findings into an organized inventory categorized by impact:

1. **Oversized / God Modules**:
   - Files >1,000 lines that mix multiple responsibilities (e.g. state management, serialization, network requests, DOM rendering, or database queries in a single file).
2. **Code Smells & Complexity**:
   - Arrow code (deeply nested `if/else`, nested ternaries).
   - Primitive obsession (untyped dicts/tuples passing domain concepts).
   - Long parameter lists (>4 parameters without parameter objects/DTOs).
   - Inappropriate intimacy / Feature envy (functions reaching deep into foreign objects).
3. **Architectural Shallowness & Seam Leaks**:
   - Pointless passthrough wrappers that add boilerplate without leverage.
   - Cross-boundary state leakage.
4. **Dead Code & Duplication**:
   - Redundant logic repeated across different files.
   - Dead code paths and obsolete configuration.

---

## Step 3: Search the Web to See How to Solve This

Before redesigning or rewriting, consult up-to-date industry best practices and canonical recipes:

- **Web Search Query Formulation**:
  - Search for proven patterns for specific libraries/frameworks (e.g., `FastAPI service layer best practices`, `Cytoscape React modular graph canvas patterns`, `Neo4j Cypher query modular repository python`).
  - Search for standard refactoring recipes (e.g., `decompose large React component sub-hooks`, `Python pipeline decomposition strategy pattern`).
- **Validate Against Standards**:
  - Prefer official framework guidelines and authoritative software engineering patterns.
  - Verify modern language capabilities (Python 3.11+ type hints/dataclasses, modern TypeScript ES modules) to avoid writing custom boilerplate for things standard libraries already provide.

---

## Step 4: Create Suggestions / Solve Them

Depending on user preference, provide either an interactive visual proposal or proceed directly with surgical implementation.

### Mode A: Visual HTML Architecture Report
Generate a standalone HTML file in the OS temp directory (`%TEMP%/architecture-review-<timestamp>.html` or `/tmp/...`) with CDN Tailwind CSS and Mermaid.js diagrams. Open it for the user (`start <path>`, `open <path>`, or `xdg-open <path>`).

Report includes:
- **Header**: Repo name, date, visual legend (solid box = module, dashed line = seam, red arrow = leakage, thick box = deep module).
- **Candidate Cards**: Side-by-side **Before** vs **After** diagrams (Mermaid flowchart, sequence, mass diagram, or cross-section), Problem statement, Solution statement, Wins bullets (≤6 words each using domain vocabulary), Recommendation badge (`Strong`, `Worth exploring`, `Speculative`).
- **Top Recommendation**: Single most impactful candidate to tackle first.

### Mode B: Direct Surgical Refactoring & Simplification
Execute refactoring in small, verifiable steps following the Golden Rules:
1. **Preserve exact external behavior** (zero functional regression).
2. **Break down 1k+ line files** into focused, cohesive, single-responsibility modules (<500 lines target, strictly <1k lines).
3. **Eliminate dead code, unnecessary wrappers, and nested conditionals**.
4. **Run existing test suites** after each change to verify green status.

---

## Architectural Principles & Vocabulary

Always use exact architectural vocabulary:

| Term | Definition |
| :--- | :--- |
| **Module** | A cohesive unit of code behind a distinct boundary. |
| **Interface** | The public surface area through which callers interact with a module. |
| **Implementation** | The internal logic and private data hidden behind the interface. |
| **Depth** | The ratio of functionality (implementation) to interface complexity. **Deep modules** have small, simple interfaces that hide substantial internal complexity. **Shallow modules** have complex interfaces that do little work. |
| **Seam** | The boundary where two modules meet. A seam allows independent modification or substitution. |
| **Adapter** | Code that translates between two interfaces. *"One adapter = hypothetical seam; two adapters = real seam."* |
| **Leverage** | The multiplier gained when a simple interface coordinates many complex internal operations across multiple call sites. |
| **Locality** | Keeping related concepts and state changes together so understanding or changing a feature requires touching only one place. |

---

## Code Simplification & Consistency Guidelines

1. **Clarity Over Brevity**:
   - Explicit, readable code is always superior to dense, clever one-liners.
   - **Never use nested ternary operators** (`a ? b : c ? d : e`). Use `if/else` chains, `match/case` (Python), or `switch` statements.
2. **Eliminate Redundant Abstractions**:
   - If a class or wrapper function simply delegates to another single function without adding validation, transformation, or caching, delete it and inline the call.
3. **Consolidate Related Logic**:
   - Co-locate related types, constants, and helper functions with the module that owns them instead of scattering them into generic `utils/` buckets.
4. **Clean Error Handling**:
   - Use guard clauses and early returns to handle error conditions up front.
   - Avoid catching exceptions unless you can meaningfully recover or add context.

---

## Common Code Smells & Refactoring Recipes

### 1. Long Method / God Function (>50 lines)
```diff
# BAD: 200-line monolithic function mixing DB, validation, formatting
- async function handleGraphQuery(request) {
-   // 50 lines: validate request & auth
-   // 60 lines: raw cypher query construction & DB execution
-   // 50 lines: node projection, layout calculation & filtering
-   // 40 lines: response serialisation
- }

# GOOD: Composed pipeline of single-responsibility steps
+ async function handleGraphQuery(request) {
+   const query = validateGraphQuery(request);
+   const rawGraph = await graphRepo.executeQuery(query);
+   const projected = projectGraphView(rawGraph, query.filters);
+   return formatGraphResponse(projected);
+ }
```

### 2. Duplicated Logic
```diff
# BAD: Repeated filtering/calculation logic across endpoints
- function getActiveNodeCount(nodes) {
-   return nodes.filter(n => n.status === 'active' && !n.isDeleted).length;
- }
- function filterVisibleNodes(nodes) {
-   return nodes.filter(n => n.status === 'active' && !n.isDeleted && n.isVisible);
- }

# GOOD: Centralized domain predicate
+ const isActiveNode = (node) => node.status === 'active' && !node.isDeleted;
+
+ function getActiveNodeCount(nodes) {
+   return nodes.filter(isActiveNode).length;
+ }
+ function filterVisibleNodes(nodes) {
+   return nodes.filter(n => isActiveNode(n) && n.isVisible);
+ }
```

### 3. God Class / Monolithic Service (>1,000 lines)
```diff
# BAD: Single service managing graph fetching, layouting, caching, export, auth
- class GraphService:
-     # 1,200 lines handling 7 different domains

# GOOD: Focused modular domain services behind a clean facade
+ class GraphQueryEngine: ...
+ class GraphLayoutProjector: ...
+ class GraphExportService: ...
+ class GraphFacade:
+     """Single intuitive interface coordinating specialized engines"""
```

### 4. Arrow Code & Deep Nesting (Guard Clauses)
```diff
# BAD: Nested pyramid
- function processNode(node) {
-   if (node) {
-     if (node.isValid) {
-       if (!node.isLocked) {
-         return executeNode(node);
-       }
-     }
-   }
-   return null;
- }

# GOOD: Early guard returns
+ function processNode(node) {
+   if (!node || !node.isValid || node.isLocked) return null;
+   return executeNode(node);
+ }
```

### 5. Primitive Obsession → Strong Domain Modeling
```diff
# BAD: Unstructured string dictionaries passed through 10 functions
- def update_edge(source_id: str, target_id: str, props: dict): ...

# GOOD: Type-safe Domain Model / Pydantic / dataclass
+ class EdgeRelationship(BaseModel):
+     source_id: NodeId
+     target_id: NodeId
+     kind: RelationType
+     weight: float = 1.0
+
+ def update_edge(edge: EdgeRelationship) -> None: ...
```

### 6. Magic Numbers & Strings
```diff
# BAD: Raw unexplained literals
- if node.type == 3 and score > 0.85:
-     time.sleep(300)

# GOOD: Typed enumerations and constants
+ DEFAULT_CACHE_TTL_SEC = 300
+ MIN_CONFIDENCE_THRESHOLD = 0.85
+
+ if node.kind == NodeKind.ENTITY and score > MIN_CONFIDENCE_THRESHOLD:
+     time.sleep(DEFAULT_CACHE_TTL_SEC)
```

---

## Design Patterns Reference Table

| Pattern | Before Refactoring | After Refactoring | Benefit |
| :--- | :--- | :--- | :--- |
| **Strategy** | Massive `switch/if-else` blocks selecting algorithms | Interface + polymorphic strategy classes | Open/Closed principle, easy testing |
| **Chain of Responsibility** | Monolithic multi-stage validation block | Pipeline of discrete step validators | Composable, isolated step checks |
| **Facade** | Callers orchestrating 5 low-level services manually | 1 high-level deep entrypoint method | Low coupling, simple interface |
| **Builder / Parameter Object** | Functions with 6+ parameters | Strongly typed Config or Spec object | Readable call sites, extensible |
| **Result / Either Pattern** | Nested `try/catch` and ambiguous `None` returns | Explicit `Result[Success, Failure]` return | Predictable type-safe error branches |

---

## Refactoring Operations Checklist

- [ ] **Function Size**: Functions do one thing and stay concise (<50 lines).
- [ ] **File Size**: No file exceeds **1,000 lines**. Target modular files between 100–400 lines.
- [ ] **Dead Code Elimination**: All unused imports, variables, commented code, and unreferenced functions deleted.
- [ ] **Type Safety**: All public module interfaces have explicit type annotations.
- [ ] **No Magic Values**: Constants and enums replace arbitrary string/number literals.
- [ ] **Single Responsibility**: Modules represent a single clear domain concept.
- [ ] **Test Verification**: All pre-existing test suites run and pass with 0 regressions.
