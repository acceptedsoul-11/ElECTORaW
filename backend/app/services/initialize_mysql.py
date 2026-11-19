"""Initialize the complete MySQL electoraw schema, including workflow tables."""

from __future__ import annotations

import re
from pathlib import Path

import mysql.connector

from ..config import settings


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    files = [
        root / "database" / "mysql" / "01_schema.sql",
        root / "database" / "mysql" / "02_workflow_schema.sql",
        root / "database" / "mysql" / "06_official_winners.sql",
    ]
    try:
        connection = mysql.connector.connect(host=settings.mysql_host, port=settings.mysql_port, database=settings.mysql_database, user=settings.mysql_user, password=settings.mysql_password, connection_timeout=5)
    except mysql.connector.Error as exc:
        if exc.errno != 1049:
            raise
        connection = mysql.connector.connect(host=settings.mysql_host, port=settings.mysql_port, user=settings.mysql_user, password=settings.mysql_password, connection_timeout=5)
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cursor.execute(f"USE `{settings.mysql_database}`")
        cursor.close()
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'elections'")
        analytical_schema_exists = cursor.fetchone() is not None
        for path in files:
            if path.name == "01_schema.sql" and analytical_schema_exists:
                continue
            for raw in path.read_text(encoding="utf-8").split(";"):
                statement = re.sub(r"(?m)^\s*--.*$", "", raw).strip()
                if statement:
                    cursor.execute(statement)
        # Compatibility for databases created before the analytics importer.
        cursor.execute("SHOW COLUMNS FROM candidates LIKE 'source_identity_key'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE candidates ADD COLUMN source_identity_key VARCHAR(64) NULL UNIQUE AFTER gender")
        for statement in (
            "ALTER TABLE parties ADD COLUMN party_symbol VARCHAR(200) NULL AFTER party_abbreviation",
            "ALTER TABLE election_constituencies ADD COLUMN valid_votes INT NULL AFTER total_votes_polled",
            "ALTER TABLE candidate_results ADD COLUMN candidate_age SMALLINT NULL AFTER position_rank",
            "ALTER TABLE candidate_results ADD COLUMN candidate_category VARCHAR(30) NULL AFTER candidate_age",
        ):
            try:
                cursor.execute(statement)
            except mysql.connector.Error as exc:
                if exc.errno != 1060:
                    raise
        cursor.execute("ALTER TABLE constituency_versions MODIFY reservation_category ENUM('GENERAL','SC','ST','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN'")
        connection.commit()
        cursor.close()
        print("MySQL electoraw schema is ready")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
