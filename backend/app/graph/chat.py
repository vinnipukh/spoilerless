"""Parameterized Cypher for chat sessions and messages (RAG-09, RAG-10).

Schema shape (06-PATTERNS.md / 06-RESEARCH.md):
``(:AppUser)-[:HAS_CHAT_SESSION]->(:ChatSession)-[:IN_SERIES]->(:Series)`` and
``(:ChatSession)-[:HAS_MESSAGE]->(:ChatMessage {id, role, content, created_at,
visible_until_order_snapshot, status, citations_json, graph_focus_json,
change_set_id})``.

The authenticated user node is always ``(:AppUser)`` — never ``(:User)``.
``citations``/``graph_focus`` are stored as JSON text properties because Neo4j
node properties cannot hold nested objects.  All values are ``$params``.
"""

from __future__ import annotations

CHAT_SESSION_CREATE_QUERY = """\
MERGE (u:AppUser {id: $user_id})
MERGE (s:Series {id: $series_id})
CREATE (u)-[:HAS_CHAT_SESSION]->(session:ChatSession {
    id: $session_id,
    user_id: $user_id,
    series_id: $series_id,
    title: $title,
    created_at: $created_at,
    updated_at: $created_at
})-[:IN_SERIES]->(s)
RETURN session.id AS id,
       session.series_id AS series_id,
       session.title AS title,
       session.created_at AS created_at,
       session.updated_at AS updated_at
"""

CHAT_SESSION_GET_QUERY = """\
MATCH (u:AppUser {id: $user_id})-[:HAS_CHAT_SESSION]->(session:ChatSession {id: $session_id, series_id: $series_id})
RETURN session.id AS id,
       session.series_id AS series_id,
       session.title AS title,
       session.created_at AS created_at,
       session.updated_at AS updated_at
"""

CHAT_SESSION_LIST_QUERY = """\
MATCH (u:AppUser {id: $user_id})-[:HAS_CHAT_SESSION]->(session:ChatSession {series_id: $series_id})
RETURN session.id AS id,
       session.series_id AS series_id,
       session.title AS title,
       session.created_at AS created_at,
       session.updated_at AS updated_at
ORDER BY session.updated_at DESC, session.id
"""

# One shared message-list query.  Both the API response path and the LLM
# conversation-memory path use the SAME ``visible_until_order_snapshot <=
# $visible_until_order`` filter (06-RESEARCH.md Pitfall 1 — never two
# independently maintained filters).  The only difference between the two
# callers is what they do with the rows.
CHAT_MESSAGE_LIST_QUERY = """\
MATCH (u:AppUser {id: $user_id})-[:HAS_CHAT_SESSION]->(session:ChatSession {id: $session_id, series_id: $series_id})-[:HAS_MESSAGE]->(message:ChatMessage)
WHERE message.visible_until_order_snapshot <= $visible_until_order
RETURN message.id AS id,
       message.role AS role,
       message.content AS content,
       message.created_at AS created_at,
       message.visible_until_order_snapshot AS visible_until_order_snapshot
ORDER BY message.created_at, message.id
"""

CHAT_MESSAGE_CREATE_QUERY = """\
MATCH (u:AppUser {id: $user_id})-[:HAS_CHAT_SESSION]->(session:ChatSession {id: $session_id, series_id: $series_id})
CREATE (session)-[:HAS_MESSAGE]->(message:ChatMessage {
    id: $message_id,
    role: $role,
    content: $content,
    created_at: $created_at,
    visible_until_order_snapshot: $visible_until_order_snapshot,
    status: $status,
    citations_json: $citations_json,
    graph_focus_json: $graph_focus_json,
    change_set_id: null
})
RETURN message.id AS id,
       message.role AS role,
       message.content AS content,
       message.created_at AS created_at,
       message.visible_until_order_snapshot AS visible_until_order_snapshot
"""
