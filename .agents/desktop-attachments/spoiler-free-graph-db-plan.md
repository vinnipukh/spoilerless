# Spoiler-Free IMDb — Project Plan & Graph Database Schema

## 1. Core Principle: "Reveal Point"

The crux of the system is: **every piece of potentially spoiler-sensitive data is stamped with an episode sequence number (`safe_at_order`) indicating when that information becomes safe to reveal.** Every query filters and compares this value against the user's watch progress for that series.

```
display(data) = IF data.safe_at_order <= user.watch_progress THEN display ELSE hide / generalize
```

This single rule covers actor episode counts, character status (alive, deceased, departed), episode titles, trivia, reviews, and ratings under one unified paradigm. The primary benefit of selecting a Graph DB is here: stamping this attribute as a property directly on relationships (`ACTED_AS`, `APPEARS_IN`, `RELATIONSHIP_WITH`) enables querying and reusing it universally with a single Cypher `WHERE` clause.

**How is user progress calculated?**
- **Simple (MVP):** `highest watched air_order` — fast, but causes gaps if a user skips episodes (e.g., marking episode 7 without marking episode 3).
- **Safe (Recommended):** `highest CONTIGUOUS watched air_order` (starting from episode 1 up to the first gap) — skipped episodes are never treated as watched. For spoiler elimination, this is the strictly correct model.

---

## 2. Graph Schema

### Node Types

| Label | Key Properties |
|---|---|
| **Show** | id, title, type (movie/tv), start_year, end_year, synopsis_short (spoiler-free logline) |
| **Season** | id, season_number |
| **Episode** | id, air_order (global, season-agnostic sequence), episode_number_in_season, air_date, runtime, title, **title_is_spoiler** (bool), synopsis (shown only when watched) |
| **Person** | id, name, birth_year, photo_url |
| **Character** | id, name, **last_appearance_order** (departure/death point — gated), status (alive/dead/unknown), photo_url |
| **Genre** | id, name |
| **User** | id, username |
| **Review** | id, body, created_at, **spoiler_up_to_order** (author-specified episode threshold up to which the review contains spoilers) |
| **Trivia** | id, text, **safe_at_order** |

### Relationship Types

```
(Show)-[:HAS_SEASON]->(Season)
(Season)-[:HAS_EPISODE]->(Episode)
(Episode)-[:NEXT]->(Episode)                         // global air_order sequence
(Person)-[:ACTED_AS {character_id}]->(Character)
(Character)-[:APPEARS_IN {order}]->(Episode)          // order = episode.air_order, for rapid indexing/filtering
(Person)-[:DIRECTED]->(Episode)
(Person)-[:WROTE]->(Episode)
(Show)-[:HAS_GENRE]->(Genre)
(Character)-[:RELATIONSHIP_WITH {type, revealed_at_order}]->(Character)   // kinship, romance, allegiance, etc. — gated
(User)-[:FOLLOWS]->(Show)
(User)-[:WATCHED {watched_at}]->(Episode)
(User)-[:PROGRESS {last_contiguous_order}]->(Show)    // cached progress indicator
(User)-[:RATED {score}]->(Episode)                    // ratings restricted to watched episodes
(User)-[:WROTE_REVIEW]->(Review)-[:ABOUT]->(Episode)
(Trivia)-[:ABOUT]->(Show|Episode|Character|Person)
```

**Critical Design Decision:** Never store the total episode count as a static property on `Person-[:ACTED_AS]->Character`. This metric must always be computed dynamically across `APPEARS_IN` edges based on the user's progress. Otherwise, seeing "appeared in 5 of 24 episodes" spoils that the character departs prematurely.

---

## 3. Sample Cypher Queries

### a) User Progress in a Show
```cypher
MATCH (u:User {id:$userId})-[p:PROGRESS]->(s:Show {id:$showId})
RETURN p.last_contiguous_order AS progress
```

### b) Actor Page — Dynamic Episode Count (Spoiler-Free)
```cypher
MATCH (u:User {id:$userId})-[prog:PROGRESS]->(s:Show {id:$showId})
MATCH (p:Person {id:$personId})-[:ACTED_AS]->(c:Character)-[:APPEARS_IN]->(e:Episode)
      <-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(s)
WHERE e.air_order <= prog.last_contiguous_order
RETURN c.name AS character, count(e) AS episodes_seen_so_far
```
Total planned episode count is never returned — only "how many episodes they have appeared in up to the user's current progress."

### c) Character Status (Alive / Dead) — Gated Field
```cypher
MATCH (c:Character {id:$characterId})<-[:HAS_SEASON|HAS_EPISODE*]-(s:Show)
MATCH (u:User {id:$userId})-[prog:PROGRESS]->(s)
RETURN CASE
  WHEN c.last_appearance_order IS NOT NULL AND c.last_appearance_order <= prog.last_contiguous_order
  THEN c.status ELSE 'unknown'
END AS status
```

### d) Episode List — Masked Spoiler Titles
```cypher
MATCH (s:Show {id:$showId})-[:HAS_SEASON]->(:Season)-[:HAS_EPISODE]->(e:Episode)
MATCH (u:User {id:$userId})-[prog:PROGRESS]->(s)
RETURN e.air_order,
  CASE WHEN e.air_order <= prog.last_contiguous_order OR NOT e.title_is_spoiler
       THEN e.title ELSE 'Episode ' + toString(e.episode_number_in_season) END AS title,
  CASE WHEN e.air_order <= prog.last_contiguous_order THEN e.synopsis ELSE null END AS synopsis
ORDER BY e.air_order
```

### e) "Users Who Watched This Also Watched" (Collaborative Graph Traversal)
```cypher
MATCH (u:User {id:$userId})-[:WATCHED]->(:Episode)<-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(s:Show)
MATCH (other:User)-[:WATCHED]->(:Episode)<-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(s)
WHERE other <> u
MATCH (other)-[:WATCHED]->(:Episode)<-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(rec:Show)
WHERE NOT (u)-[:FOLLOWS]->(rec)
RETURN rec.title, count(DISTINCT other) AS shared_watchers
ORDER BY shared_watchers DESC LIMIT 10
```

---

## 4. Phased Project Plan

**Phase 0 — Scope & Data Source**
- Complete inventory of spoiler pitfalls (see §5)
- Data ingestion: API import (TMDb / OMDb) vs manual entry (ToS compliance check)
- Local Docker environment setup for Graph DB (Memgraph / Neo4j)

**Phase 1 — MVP**
- Schema: Show, Season, Episode, Person, Character, User
- Basic authentication + `WATCHED` tracking
- Show detail page + episode list (unwatched episodes = locked / generic titles)

**Phase 2 — Spoiler Engine**
- `ACTED_AS` / `APPEARS_IN` relationships
- Dynamic episode count calculation, character status gating
- `last_contiguous_order` calculation logic (gap & skip prevention)

**Phase 3 — Social Layer**
- Review / Rating + mandatory spoiler gating (`spoiler_up_to_order`)
- Watchlist and graph-based recommendation queries

**Phase 4 — Advanced Spoiler Protection**
- Trivia gating, character relationship gating (`RELATIONSHIP_WITH.revealed_at_order`)
- Spoiler filtering in search & autocomplete
- Visual asset filtering (posters / thumbnails)

**Phase 5 — Performance & Optimization**
- Indexing & constraints on `id` and lookup properties
- Query cache layer for frequently traversed paths (Redis)
- Early traversal filtering (`WHERE` predicate pushdown in query planner)

---

## 5. Spoiler Pitfalls Checklist

Every entity must be evaluated against the question *"What does this reveal prematurely?"* before entering the system:

- **Episode titles** (e.g., a finale named after a character's demise or departure)
- **Abnormal episode/season runtimes** (extended finale runtimes signal major climaxes)
- **Actor total / remaining episode counts** (indicates premature departures)
- **Cast billing order changes** (actors added to "starring" credits mid-season)
- **Character prominence status** (main vs recurring / guest transitions)
- **Character death / departure status**
- **Hidden character relationships** (surprise family ties, undercover roles, betrayals)
- **Trivia / "Did You Know" facts**
- **User reviews and average ratings** (a spike in a finale rating is itself an indicator — ratings must be computed relative to user progress)
- **Visual assets** (posters, thumbnails — absence of a character on a season poster spoils their fate)
- **Search autocomplete suggestions** (e.g. searching "Character X" suggesting "Character X death scene")
- **"Next episode / season" trailers and teasers**
- **Award / nomination announcements** (post-broadcast award tags)
- **External links / Wiki references**

---

## 6. Recommended Tech Stack

- **Database:** Neo4j / Memgraph (Docker), via Bolt protocol
- **Backend:** Python + FastAPI + Async driver / GQLAlchemy
- **Frontend:** React / Next.js + Cytoscape.js / Canvas
- **Authentication:** JWT / Session tokens
- **Cache:** Redis (Phase 5)

---

## 7. Authoritative Product Decisions

- **No episode skipping:** The UI does not permit arbitrary gap-skipping. Unlocking Episode 5 explicitly marks Episodes 1 through 5 as unlocked.
- **Film franchises:** Each movie in a series is modeled as an episode node in sequence (e.g., Star Wars Episode 1, 2, 3...).
- **Broadcast / release order is authoritative:** Chronological timeline lore is disregarded. If Episode 1 depicts narrative events occurring after Episode 5, Episode 1 is still processed first according to its broadcast release order.
