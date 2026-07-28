import json
from pathlib import Path
from typing import Any

from app.graph.database import neo4j_db


PROJECT_ROOT = Path(__file__).resolve().parents[3]
METADATA_DIR = PROJECT_ROOT / "data" / "dexter" / "metadata"


def read_json(filename: str) -> Any:
    path = METADATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Seed dosyası bulunamadı: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def create_constraints() -> None:
    queries = [
        """
        CREATE CONSTRAINT series_id_unique IF NOT EXISTS
        FOR (series:Series)
        REQUIRE series.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT episode_id_unique IF NOT EXISTS
        FOR (episode:Episode)
        REQUIRE episode.id IS UNIQUE
        """,
    ]

    with neo4j_db.driver.session(database=neo4j_db.database) as session:
        for query in queries:
            session.run(query).consume()


def seed_series_and_episodes() -> None:
    series = read_json("series.json")
    episodes = read_json("episodes.json")

    query = """
    MERGE (series:Series {id: $series.id})
    SET series.title = $series.title,
        series.slug = $series.slug

    WITH series
    UNWIND $episodes AS episode_data

    MERGE (episode:Episode {id: episode_data.id})
    SET episode.series_id = episode_data.series_id,
        episode.season_number = episode_data.season_number,
        episode.episode_number = episode_data.episode_number,
        episode.episode_order = episode_data.episode_order,
        episode.code = episode_data.code,
        episode.title = episode_data.title,
        episode.visible_from_order = episode_data.visible_from_order

    MERGE (episode)-[:PART_OF]->(series)
    """

    with neo4j_db.driver.session(database=neo4j_db.database) as session:
        session.run(
            query,
            series=series,
            episodes=episodes,
        ).consume()


def create_episode_order() -> None:
    query = """
    MATCH (first:Episode {series_id: $series_id})
    MATCH (second:Episode {series_id: $series_id})
    WHERE second.episode_order = first.episode_order + 1
    MERGE (first)-[:PRECEDES]->(second)
    """

    with neo4j_db.driver.session(database=neo4j_db.database) as session:
        session.run(
            query,
            series_id="series_dexter",
        ).consume()


def main() -> None:
    neo4j_db.verify_connection()

    try:
        create_constraints()
        seed_series_and_episodes()
        create_episode_order()
        print("Dexter metadata seed işlemi tamamlandı.")
    finally:
        neo4j_db.close()


if __name__ == "__main__":
    main()