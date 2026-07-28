from neo4j import Driver, GraphDatabase

from app.core.config import get_settings


class Neo4jDatabase:
    def __init__(self) -> None:
        settings = get_settings()

        self._database = settings.neo4j_database
        self._driver: Driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(
                settings.neo4j_username,
                settings.neo4j_password,
            ),
        )

    def verify_connection(self) -> None:
        self._driver.verify_connectivity()

    def close(self) -> None:
        self._driver.close()

    @property
    def driver(self) -> Driver:
        return self._driver

    @property
    def database(self) -> str:
        return self._database


neo4j_db = Neo4jDatabase()