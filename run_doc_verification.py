import os
import sys
import re
import json

root = r"C:\Users\arhan\PycharmProjects\hdgrafcehennemi"
doc_rel = "docs/ARCHITECTURE.md"
doc_full = os.path.join(root, doc_rel.replace('/', os.sep))

with open(doc_full, 'r', encoding='utf-8') as f:
    doc_lines = f.readlines()

claims = []

def record(line, claim, expected, actual, passed):
    claims.append({
        "line": line,
        "claim": claim,
        "expected": expected,
        "actual": actual,
        "passed": passed
    })

def check_file_path(line, path_str):
    full_path = os.path.join(root, path_str.replace('/', os.sep))
    exists = os.path.exists(full_path)
    expected = f"Path '{path_str}' exists on disk"
    actual = f"Path '{path_str}' {'exists' if exists else 'DOES NOT exist'}"
    record(line, f"Path claim: {path_str}", expected, actual, exists)
    return exists

def check_frontend_dep(line, pkg_name):
    p = os.path.join(root, "frontend", "package.json")
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
    exists = pkg_name in deps
    ver = deps.get(pkg_name, "")
    expected = f"Dependency '{pkg_name}' in frontend/package.json"
    actual = f"Found '{pkg_name}': '{ver}'" if exists else f"'{pkg_name}' NOT found in frontend/package.json"
    record(line, f"Frontend dependency claim: {pkg_name}", expected, actual, exists)

def check_backend_dep(line, pkg_name):
    p = os.path.join(root, "pyproject.toml")
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()
    exists = pkg_name.lower() in content.lower()
    expected = f"Dependency '{pkg_name}' in pyproject.toml"
    actual = f"Found '{pkg_name}' in pyproject.toml" if exists else f"'{pkg_name}' NOT found in pyproject.toml"
    record(line, f"Backend dependency claim: {pkg_name}", expected, actual, exists)

def grep_symbol(line, symbol_name, search_path=""):
    target_path = os.path.join(root, search_path.replace('/', os.sep)) if search_path else root
    regex = re.compile(r'(?:\b|_)' + re.escape(symbol_name) + r'(?:\b|_)')
    found_files = []
    
    if os.path.isfile(target_path):
        try:
            with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                if regex.search(f.read()):
                    rel = os.path.relpath(target_path, root).replace(os.sep, '/')
                    found_files.append(rel)
        except Exception:
            pass
    else:
        for r, d, files in os.walk(target_path):
            if any(ignored in r for ignored in ['.git', 'node_modules', '__pycache__', '.venv', '.planning', 'dist']):
                continue
            for file in files:
                fp = os.path.join(r, file)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        if regex.search(f.read()):
                            rel = os.path.relpath(fp, root).replace(os.sep, '/')
                            found_files.append(rel)
                except Exception:
                    pass

    exists = len(found_files) > 0
    expected = f"Symbol '{symbol_name}' exists in codebase"
    actual = f"Found '{symbol_name}' in {found_files[:2]}" if exists else f"Symbol '{symbol_name}' NOT found in codebase"
    record(line, f"Symbol claim: {symbol_name}", expected, actual, exists)

def check_script_claim(line, script_name):
    p = os.path.join(root, "pyproject.toml")
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()
    exists = script_name in content
    expected = f"Script '{script_name}' registered in pyproject.toml"
    actual = f"Found '{script_name}' in pyproject.toml" if exists else f"'{script_name}' NOT found in pyproject.toml"
    record(line, f"Script claim: {script_name}", expected, actual, exists)

# Section 1: Stack Summary
check_frontend_dep(56, "react")
check_frontend_dep(56, "typescript")
check_frontend_dep(56, "vite")
check_frontend_dep(56, "cytoscape")
check_frontend_dep(56, "cytoscape-cose-bilkent")
check_frontend_dep(56, "cytoscape-fcose")
check_frontend_dep(57, "radix-ui")
check_frontend_dep(57, "shadcn")
check_frontend_dep(57, "tailwindcss")
check_frontend_dep(57, "lucide-react")
check_backend_dep(58, "fastapi")
check_backend_dep(58, "uvicorn")
check_backend_dep(58, "pydantic-settings")
grep_symbol(59, "neo4j:2026.06.0-community")
check_backend_dep(60, "neo4j")
check_backend_dep(61, "google-auth")
check_backend_dep(63, "redis")

# Section 2 Component Diagram & Directory Structure
check_file_path(91, "spoilerless/app/api")
check_file_path(98, "spoilerless/app/services")
check_file_path(105, "spoilerless/app/repository")
check_file_path(113, "spoilerless/app/graph")
check_file_path(113, "spoilerless/app/spoiler")
check_file_path(115, "spoilerless/app/spoiler/filter.py")
check_file_path(119, "spoilerless/app/retrieval")
check_file_path(119, "spoilerless/app/llm")
check_file_path(124, "spoilerless/app/cache")
check_file_path(125, "spoilerless/app/services/rate_limit.py")
check_file_path(150, "spoilerless/app/domain")
check_file_path(152, "spoilerless/app/api/candidates.py")
check_file_path(152, "spoilerless/app/api/revisions.py")
check_file_path(152, "spoilerless/app/api/user_content.py")
check_file_path(152, "spoilerless/app/api/share.py")
check_file_path(152, "spoilerless/app/api/chat.py")

# Section 3 Directory Structure Rationale
check_file_path(160, "spoilerless/app/api")
check_file_path(163, "spoilerless/app/cache")
check_file_path(163, "spoilerless/app/cache/redis_client.py")
check_file_path(164, "spoilerless/app/cache/graph_cache.py")
check_file_path(166, "spoilerless/app/core")
check_file_path(167, "spoilerless/app/domain")
check_file_path(167, "spoilerless/app/domain/share.py")
check_file_path(168, "spoilerless/app/graph")
check_file_path(172, "spoilerless/app/llm")
check_file_path(173, "spoilerless/app/repository")
check_file_path(176, "spoilerless/app/retrieval")
check_file_path(177, "spoilerless/app/revisions")
check_file_path(178, "spoilerless/app/services")
check_file_path(178, "spoilerless/app/services/rate_limit.py")
check_file_path(180, "spoilerless/app/spoiler")
check_file_path(181, "spoilerless/app/main.py")
check_file_path(181, "spoilerless/scripts/zombie_sweep.py")
check_file_path(184, "spoilerless/tests")
check_file_path(185, "frontend")
check_file_path(186, "frontend/src")
check_file_path(187, "frontend/src/api")
check_file_path(187, "frontend/src/api/share.ts")
check_file_path(188, "frontend/src/components")
check_file_path(189, "frontend/src/hooks")
check_file_path(190, "frontend/src/lib/searchIndex.ts")
check_file_path(190, "frontend/src/lib/byok.ts")
check_file_path(191, "frontend/src/providers")
check_file_path(192, "frontend/src/types")
check_file_path(193, "data/dexter")
check_file_path(194, "data/dexter/metadata")
check_file_path(195, "data/dexter/seed")
check_file_path(196, "ontology")
check_file_path(197, "docs")
check_file_path(198, "docker-compose.yml")
check_file_path(199, "pyproject.toml")
check_file_path(200, ".env.example")
check_script_claim(201, "spoilerless-setup")

# Section 4.1 Frontend
check_file_path(217, "frontend/src/api/client.ts")
check_file_path(218, "frontend/src/api/graph.ts")
check_file_path(218, "frontend/src/api/series.ts")
check_file_path(219, "frontend/src/api/auth.ts")
check_file_path(219, "frontend/src/api/revisions.ts")
check_file_path(219, "frontend/src/api/progress.ts")
check_file_path(219, "frontend/src/api/chat.ts")
check_file_path(219, "frontend/src/api/changeSet.ts")
check_file_path(220, "frontend/src/api/share.ts")
check_file_path(220, "frontend/src/api/userContent.ts")
check_file_path(222, "frontend/src/components/auth/LoginPage.tsx")
check_file_path(223, "frontend/src/components/chat/ChatLauncher.tsx")
check_file_path(223, "frontend/src/components/chat/ChatSheet.tsx")
check_file_path(223, "frontend/src/components/chat/ChatPanel.tsx")
check_file_path(223, "frontend/src/components/chat/SessionPicker.tsx")
check_file_path(224, "frontend/src/components/chat/MessageList.tsx")
check_file_path(224, "frontend/src/components/chat/MessageBubble.tsx")
check_file_path(224, "frontend/src/components/chat/CitationChip.tsx")
check_file_path(224, "frontend/src/components/chat/ChangeSetCard.tsx")
check_file_path(225, "frontend/src/components/detail/DetailPanel.tsx")
check_file_path(225, "frontend/src/components/detail/BacklinksTab.tsx")
check_file_path(225, "frontend/src/components/detail/StructuralEdgeCard.tsx")
check_file_path(225, "frontend/src/components/detail/RevisionHistoryPanel.tsx")
check_file_path(226, "frontend/src/components/episode/EpisodeSelector.tsx")
check_file_path(226, "frontend/src/components/episode/SeriesSelect.tsx")
check_file_path(226, "frontend/src/components/episode/ConfirmAdvanceModal.tsx")
check_file_path(227, "frontend/src/components/graph/GraphCanvas.tsx")
check_file_path(227, "frontend/src/components/graph/graphElements.ts")
check_file_path(227, "frontend/src/components/graph/graphStylesheet.ts")
check_file_path(228, "frontend/src/components/graph/GraphControls.tsx")
check_file_path(228, "frontend/src/components/graph/GraphLegend.tsx")
check_file_path(228, "frontend/src/components/graph/GraphFocusIndicator.tsx")
check_file_path(228, "frontend/src/components/graph/GraphFilterPanel.tsx")
check_file_path(229, "frontend/src/components/graph/GraphStatus.tsx")
check_file_path(229, "frontend/src/components/graph/NodeHoverCard.tsx")
check_file_path(229, "frontend/src/components/graph/NodeSearch.tsx")
check_file_path(230, "frontend/src/components/graph/PathFinder.tsx")
check_file_path(230, "frontend/src/components/graph/relationshipStyles.ts")
check_file_path(230, "frontend/src/components/layout/AppShell.tsx")
check_file_path(230, "frontend/src/components/layout/HeaderNavAction.tsx")
check_file_path(231, "frontend/src/components/palette/CommandPalette.tsx")
check_file_path(232, "frontend/src/components/series/SeriesDashboard.tsx")
check_file_path(233, "frontend/src/components/settings/SettingsPage.tsx")
check_file_path(234, "frontend/src/components/share/ShareDialog.tsx")
check_file_path(234, "frontend/src/components/share/ShareView.tsx")
check_file_path(235, "frontend/src/components/timeline/TimelineView.tsx")
check_file_path(235, "frontend/src/components/timeline/TimelineEventRow.tsx")
check_file_path(236, "frontend/src/components/ui/SpoilerGuard.tsx")
check_file_path(237, "frontend/src/hooks/useGraph.ts")
check_file_path(237, "frontend/src/hooks/useWatchProgress.ts")
check_file_path(237, "frontend/src/hooks/useSeries.ts")
check_file_path(237, "frontend/src/hooks/useEpisodes.ts")
check_file_path(238, "frontend/src/hooks/useNotes.ts")
check_file_path(238, "frontend/src/hooks/useRevisions.ts")
check_file_path(238, "frontend/src/hooks/useChatSessions.ts")
check_file_path(238, "frontend/src/hooks/useChatMessages.ts")
check_file_path(239, "frontend/src/hooks/useHotkey.ts")
check_file_path(240, "frontend/src/lib/searchIndex.ts")
check_file_path(240, "frontend/src/lib/byok.ts")
check_file_path(240, "frontend/src/lib/nodeTypes.ts")
check_file_path(243, "frontend/src/providers/AuthContext.ts")
check_file_path(243, "frontend/src/providers/AuthProvider.tsx")
check_file_path(244, "frontend/src/types/graph.ts")
check_file_path(244, "frontend/src/types/series.ts")
check_file_path(244, "frontend/src/types/revision.ts")
check_file_path(244, "frontend/src/types/settings.ts")
check_file_path(244, "frontend/src/types/share.ts")

# Key Component prose references
check_file_path(250, "frontend/src/components/graph/GraphCanvas.tsx")
check_file_path(251, "frontend/src/components/graph/graphElements.ts")
check_file_path(252, "frontend/src/components/graph/graphStylesheet.ts")
check_file_path(253, "frontend/src/hooks/useWatchProgress.ts")
check_file_path(254, "frontend/src/providers/AuthProvider.tsx")
check_file_path(255, "frontend/src/App.tsx")
check_file_path(256, "frontend/src/components/graph/NodeSearch.tsx")
check_file_path(257, "frontend/src/components/graph/PathFinder.tsx")
check_file_path(258, "frontend/src/components/share/ShareDialog.tsx")
check_file_path(258, "frontend/src/components/share/ShareView.tsx")
check_file_path(259, "frontend/src/components/graph/GraphControls.tsx")
check_file_path(259, "frontend/src/components/graph/GraphLegend.tsx")
check_file_path(260, "frontend/src/components/palette/CommandPalette.tsx")
check_file_path(261, "frontend/src/components/timeline/TimelineView.tsx")
check_file_path(261, "frontend/src/components/series/SeriesDashboard.tsx")
check_file_path(262, "frontend/src/hooks/useHotkey.ts")
check_file_path(263, "frontend/src/lib/searchIndex.ts")

# Section 4.2 API layer
check_file_path(303, "spoilerless/app/cache/graph_cache.py")
check_file_path(306, "docs/reference/frontend-api-contract.md")

# Section 4.3 Services & Repositories
grep_symbol(315, "GraphService", "spoilerless/app/services/graph.py")
grep_symbol(315, "fetch_graph", "spoilerless/app/services/graph.py")
grep_symbol(316, "SeriesService", "spoilerless/app/services/series.py")
grep_symbol(317, "AuthService", "spoilerless/app/services/auth.py")
grep_symbol(317, "ProductionGoogleVerifier", "spoilerless/app/services/auth.py")
grep_symbol(318, "ProgressService", "spoilerless/app/services/progress.py")
grep_symbol(318, "ProgressNotFoundError", "spoilerless/app/services/progress.py")
grep_symbol(320, "ChatService", "spoilerless/app/services/chat.py")
grep_symbol(321, "ChangeSetService", "spoilerless/app/services/change_set.py")
grep_symbol(322, "SettingsService", "spoilerless/app/services/settings.py")
check_file_path(324, "spoilerless/app/services/rate_limit.py")

grep_symbol(330, "Neo4jDatabase", "spoilerless/app/graph/database.py")
grep_symbol(331, "UserRepository", "spoilerless/app/repository/user.py")
grep_symbol(332, "SessionRepository", "spoilerless/app/repository/session.py")
grep_symbol(332, "Neo4jSessionRepository", "spoilerless/app/repository/session.py")
grep_symbol(332, "InMemorySessionRepository", "spoilerless/app/repository/session.py")
grep_symbol(332, "sweep_expired", "spoilerless/app/repository/session.py")
grep_symbol(335, "ShareRepository", "spoilerless/app/repository/share.py")
grep_symbol(335, "Neo4jShareRepository", "spoilerless/app/repository/share.py")
grep_symbol(335, "InMemoryShareRepository", "spoilerless/app/repository/share.py")
grep_symbol(336, "UserContentRepository", "spoilerless/app/repository/user_content.py")
grep_symbol(337, "ChangeSetRepository", "spoilerless/app/repository/change_set.py")
grep_symbol(337, "ChatRepository", "spoilerless/app/repository/chat.py")
grep_symbol(337, "SettingsRepository", "spoilerless/app/repository/settings.py")
check_file_path(339, "spoilerless/scripts/zombie_sweep.py")

check_file_path(345, "spoilerless/app/graph/seed.py")
grep_symbol(385, "setup_database", "spoilerless/app/graph/setup.py")
check_file_path(388, "spoilerless/app/graph/setup.py")
grep_symbol(388, "_check_visibility_schema", "spoilerless/app/graph/setup.py")

# Section 5 Abstractions
check_file_path(396, "spoilerless/app/spoiler/filter.py")
check_file_path(397, "spoilerless/app/graph/database.py")
check_file_path(398, "spoilerless/app/graph/ontology.py")
grep_symbol(398, "require_node_type", "spoilerless/app/graph/ontology.py")
grep_symbol(398, "require_relationship_type", "spoilerless/app/graph/ontology.py")
grep_symbol(398, "require_claim_type", "spoilerless/app/graph/ontology.py")
grep_symbol(398, "user_safe_node_types", "spoilerless/app/graph/ontology.py")
grep_symbol(398, "user_safe_relationship_types", "spoilerless/app/graph/ontology.py")
check_file_path(399, "spoilerless/app/domain/graph.py")
check_file_path(401, "spoilerless/app/llm/provider.py")
grep_symbol(401, "LLMProvider", "spoilerless/app/llm/provider.py")
grep_symbol(401, "OpenAICompatibleProvider", "spoilerless/app/llm/provider.py")
grep_symbol(401, "GeminiProvider", "spoilerless/app/llm/provider.py")
check_file_path(402, "spoilerless/app/retrieval/pipeline.py")
grep_symbol(402, "RetrievalPipeline", "spoilerless/app/retrieval/pipeline.py")
check_file_path(403, "spoilerless/app/services/change_set.py")
check_file_path(404, "spoilerless/app/revisions/__init__.py")
grep_symbol(404, "log_revision", "spoilerless/app/revisions/__init__.py")
check_file_path(405, "spoilerless/app/repository/share.py")
check_file_path(406, "spoilerless/app/api/deps.py")
grep_symbol(406, "require_admin", "spoilerless/app/api/deps.py")
grep_symbol(406, "RequireAdminDependency", "spoilerless/app/api/deps.py")
check_file_path(407, "spoilerless/app/cache/redis_client.py")
grep_symbol(407, "get_redis", "spoilerless/app/cache/redis_client.py")
check_file_path(408, "spoilerless/app/services/rate_limit.py")
grep_symbol(408, "RateLimiter", "spoilerless/app/services/rate_limit.py")

# Section 7 Cross-cutting concerns
check_file_path(524, "ontology/node_types.yaml")
check_file_path(524, "ontology/relation_types.yaml")
check_file_path(524, "ontology/claim_types.yaml")
check_file_path(526, "spoilerless/app/graph/ontology.py")
grep_symbol(526, "load_ontology", "spoilerless/app/graph/ontology.py")
grep_symbol(526, "Ontology", "spoilerless/app/graph/ontology.py")

check_file_path(545, "spoilerless/app/core/errors.py")
grep_symbol(545, "ERROR_CODES", "spoilerless/app/core/errors.py")
grep_symbol(568, "install_database_error_handlers", "spoilerless/app/core/errors.py")
grep_symbol(568, "install_llm_error_handlers", "spoilerless/app/llm/provider.py")
grep_symbol(570, "_security_headers_middleware", "spoilerless/app/main.py")

check_file_path(572, "spoilerless/app/revisions")

check_file_path(587, "spoilerless/app/retrieval/pipeline.py")
check_file_path(587, "spoilerless/app/retrieval/tools.py")
check_file_path(587, "spoilerless/app/llm/provider.py")
check_file_path(587, "spoilerless/app/llm/system_prompt.py")
check_file_path(587, "spoilerless/app/services/chat.py")

tools = [
    "search_entities", "get_entity", "get_neighborhood", "find_path",
    "get_timeline", "get_character_context", "get_claims", "get_evidence",
    "get_sources", "get_current_visible_graph_summary", "get_user_notes"
]
for t in tools:
    grep_symbol(629, t, "spoilerless/app/retrieval/tools.py")

check_file_path(646, "spoilerless/app/api/change_set.py")
check_file_path(646, "spoilerless/app/services/change_set.py")
check_file_path(646, "spoilerless/app/repository/change_set.py")

grep_symbol(681, "assemble_context", "spoilerless/app/retrieval/pipeline.py")

check_file_path(692, "spoilerless/app/api/settings.py")
check_file_path(692, "spoilerless/app/services/settings.py")
check_file_path(692, "spoilerless/app/repository/settings.py")
check_file_path(692, "spoilerless/app/domain/settings.py")
check_file_path(692, "frontend/src/components/settings/SettingsPage.tsx")

check_file_path(706, "spoilerless/app/api/candidates.py")
check_file_path(706, "spoilerless/app/graph/candidates.py")
check_file_path(706, "spoilerless/app/domain/extraction.py")
grep_symbol(709, "ExtractionBatchEnvelope", "spoilerless/app/domain/extraction.py")
grep_symbol(709, "ExtractionClaim", "spoilerless/app/domain/extraction.py")

check_file_path(727, "spoilerless/app/api/deps.py")
check_file_path(727, "spoilerless/app/services/auth.py")
check_file_path(727, "spoilerless/app/repository/user.py")
check_file_path(727, "spoilerless/app/domain/auth.py")
grep_symbol(728, "UserPublic", "spoilerless/app/domain/auth.py")

check_file_path(737, "spoilerless/app/cache/redis_client.py")
check_file_path(737, "spoilerless/app/cache/graph_cache.py")
check_file_path(737, "spoilerless/app/services/rate_limit.py")
grep_symbol(737, "get_redis", "spoilerless/app/cache/redis_client.py")
grep_symbol(744, "login_rate_limiter", "spoilerless/app/services/rate_limit.py")
grep_symbol(744, "chat_send_rate_limiter", "spoilerless/app/services/rate_limit.py")
grep_symbol(744, "content_write_rate_limiter", "spoilerless/app/services/rate_limit.py")
grep_symbol(748, "rate_limit_identifier", "spoilerless/app/services/rate_limit.py")
grep_symbol(748, "init_rate_limiter", "spoilerless/app/services/rate_limit.py")
grep_symbol(750, "DEFAULT_GRAPH_TTL_SECONDS", "spoilerless/app/cache/graph_cache.py")
grep_symbol(750, "invalidate_series", "spoilerless/app/cache/graph_cache.py")

check_file_path(754, "spoilerless/app/api/share.py")
check_file_path(754, "spoilerless/app/repository/share.py")
check_file_path(754, "spoilerless/app/domain/share.py")
check_file_path(754, "frontend/src/api/share.ts")
check_file_path(754, "frontend/src/components/share/ShareDialog.tsx")
check_file_path(754, "frontend/src/components/share/ShareView.tsx")

check_file_path(844, "docs/CONFIGURATION.md")

passed_count = sum(1 for c in claims if c['passed'])
failed_count = sum(1 for c in claims if not c['passed'])
total_count = len(claims)

print(f"Total claims checked: {total_count}")
print(f"Passed: {passed_count}")
print(f"Failed: {failed_count}")

failures = [
    {
        "line": c["line"],
        "claim": c["claim"],
        "expected": c["expected"],
        "actual": c["actual"]
    }
    for c in claims if not c["passed"]
]

out = {
    "doc_path": doc_rel,
    "claims_checked": total_count,
    "claims_passed": passed_count,
    "claims_failed": failed_count,
    "failures": failures
}

tmp_dir = os.path.join(root, ".planning", "tmp")
os.makedirs(tmp_dir, exist_ok=True)
out_file = os.path.join(tmp_dir, "verify-ARCHITECTURE.md.json")
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)

print(f"Result written to {out_file}")
