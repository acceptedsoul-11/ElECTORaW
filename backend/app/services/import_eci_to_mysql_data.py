
import os
import re
import hashlib
import unicodedata
from pathlib import Path
from decimal import Decimal, InvalidOperation

import pandas as pd
import mysql.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "data" / "processed" / "candidate_import_preview.csv"
DELIMITATION_CODE = "LS_2008"


def clean(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def norm(value):
    return unicodedata.normalize("NFKC", clean(value)).casefold()


def identity_key(row):
    fields = [
        str(int(row["election_year"])),
        row["state_name"],
        row["constituency_name"],
        row["candidate_name"],
        row["party_name_source"],
        row.get("party_symbol", ""),
    ]
    raw = "|".join(norm(x) for x in fields)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def integer_or_none(value):
    if pd.isna(value) or clean(value) == "":
        return None
    return int(Decimal(str(value)))


def decimal_or_none(value):
    if pd.isna(value) or clean(value) == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def connect():
    load_dotenv(ROOT / ".env")
    required = ["MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing .env settings: " + ", ".join(missing)
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "electoraw"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        autocommit=False,
    )


def upsert_id(cursor, sql, params):
    cursor.execute(sql, params)
    return cursor.lastrowid


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    required_columns = {
        "election_year", "source_file", "source_row_number",
        "state_name", "constituency_name", "candidate_name",
        "party_name_source", "votes_received",
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")

    # NOTA is intentionally excluded.
    nota_mask = (
        df["candidate_name"].map(norm).isin({"nota", "none of the above"})
        | df["party_name_source"].map(norm).eq("nota")
    )
    if nota_mask.any():
        raise ValueError(
            f"Stopped: {int(nota_mask.sum())} NOTA-like rows found "
            "in the candidate preview. No import performed."
        )

    df["election_year"] = pd.to_numeric(
        df["election_year"], errors="raise"
    ).astype(int)
    df["votes_received"] = pd.to_numeric(
        df["votes_received"], errors="raise"
    )

    if not df["election_year"].isin([2014, 2019, 2024]).all():
        raise ValueError("Unexpected election year in input.")
    if (df["votes_received"] < 0).any():
        raise ValueError("Negative votes found.")
    if df[["state_name", "constituency_name", "candidate_name"]].isna().any().any():
        raise ValueError("Missing state, constituency, or candidate name.")

    df["source_identity_key"] = df.apply(identity_key, axis=1)

    if df["source_identity_key"].duplicated().any():
        raise ValueError(
            "Duplicate identity keys detected. Resolve them before importing."
        )

    # Rank candidates by votes for display; this does NOT verify winners.
    df["position_rank"] = (
        df.groupby(
            ["election_year", "state_name", "constituency_name"]
        )["votes_received"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    conn = connect()
    cursor = conn.cursor()

    try:
        # Represent unknown constituency reservation accurately.
        cursor.execute("""
            ALTER TABLE constituency_versions
            MODIFY reservation_category
            ENUM('GENERAL','SC','ST','UNKNOWN')
            NOT NULL DEFAULT 'UNKNOWN'
        """)

        # Load existing constituency mapping.
        cursor.execute("""
            SELECT s.state_name, cv.constituency_name,
                   cv.delimitation_code, cv.constituency_version_id
            FROM constituency_versions cv
            JOIN constituencies c ON c.constituency_id = cv.constituency_id
            JOIN states s ON s.state_id = c.state_id
        """)
        constituency_map = {
            (norm(state), norm(name), code): version_id
            for state, name, code, version_id in cursor.fetchall()
        }

        cursor.execute("SELECT state_name, state_id FROM states")
        state_map = {norm(name): sid for name, sid in cursor.fetchall()}

        election_map = {}
        party_map = {}
        candidate_map = {}
        contest_map = {}
        source_map = {}
        batch_map = {}

        # One transaction covers the data import.
        for year in sorted(df["election_year"].unique()):
            election_id = upsert_id(
                cursor,
                """
                INSERT INTO elections (election_year, election_name, election_type)
                VALUES (%s, %s, 'Lok Sabha')
                ON DUPLICATE KEY UPDATE
                    election_name=VALUES(election_name),
                    election_id=LAST_INSERT_ID(election_id)
                """,
                (int(year), f"{int(year)} Indian General Election"),
            )
            election_map[int(year)] = election_id

        # Ensure states and constituency versions exist.
        unique_constituencies = (
            df[["state_name", "constituency_name"]]
            .drop_duplicates()
            .sort_values(["state_name", "constituency_name"])
        )

        for _, row in unique_constituencies.iterrows():
            state_name = clean(row["state_name"])
            constituency_name = clean(row["constituency_name"])
            state_key = norm(state_name)
            const_key = (
                state_key, norm(constituency_name), DELIMITATION_CODE
            )

            if state_key not in state_map:
                state_id = upsert_id(
                    cursor,
                    """
                    INSERT INTO states (state_name)
                    VALUES (%s)
                    ON DUPLICATE KEY UPDATE
                        state_id=LAST_INSERT_ID(state_id)
                    """,
                    (state_name,),
                )
                state_map[state_key] = state_id

            if const_key not in constituency_map:
                constituency_id = upsert_id(
                    cursor,
                    "INSERT INTO constituencies (state_id) VALUES (%s)",
                    (state_map[state_key],),
                )
                version_id = upsert_id(
                    cursor,
                    """
                    INSERT INTO constituency_versions
                      (constituency_id, constituency_name,
                       delimitation_code, valid_from_year,
                       reservation_category)
                    VALUES (%s, %s, %s, 2008, 'UNKNOWN')
                    """,
                    (
                        constituency_id,
                        constituency_name,
                        DELIMITATION_CODE,
                    ),
                )
                constituency_map[const_key] = version_id

        # Register source files and import batches.
        for (year, source_file), part in df.groupby(
            ["election_year", "source_file"], dropna=False
        ):
            year = int(year)
            source_file = clean(source_file)

            cursor.execute("""
                SELECT source_id FROM data_sources
                WHERE election_id=%s AND original_filename=%s
                ORDER BY source_id LIMIT 1
            """, (election_map[year], source_file))
            found = cursor.fetchone()

            if found:
                source_id = found[0]
            else:
                source_id = upsert_id(
                    cursor,
                    """
                    INSERT INTO data_sources
                      (election_id, source_title, source_type,
                       original_filename, notes)
                    VALUES (%s, %s, 'ECI_RESULTS', %s, %s)
                    """,
                    (
                        election_map[year],
                        f"ECI constituency detailed results - {year}",
                        source_file,
                        "Imported from normalized ECI candidate preview.",
                    ),
                )

            batch_id = upsert_id(
                cursor,
                """
                INSERT INTO import_batches
                  (source_id, batch_status, rows_read)
                VALUES (%s, 'RUNNING', %s)
                """,
                (source_id, len(part)),
            )
            source_map[(year, source_file)] = source_id
            batch_map[(year, source_file)] = batch_id

        # Create one constituency contest per election and constituency.
        grouped = df.groupby(
            ["election_year", "state_name", "constituency_name"],
            dropna=False,
            sort=False,
        )

        for (year, state_name, constituency_name), part in grouped:
            year = int(year)
            const_key = (
                norm(state_name), norm(constituency_name), DELIMITATION_CODE
            )
            version_id = constituency_map[const_key]

            electors = part["total_electors"].dropna()
            total_polled = part["total_votes_polled"].dropna()

            # Preserve missing totals; do not infer or substitute zero.
            registered_electors = (
                integer_or_none(electors.iloc[0])
                if len(electors) else None
            )
            total_votes_polled = (
                integer_or_none(total_polled.iloc[0])
                if len(total_polled) else None
            )
            valid_votes = part["valid_votes"].dropna()
            valid_votes_value = integer_or_none(valid_votes.iloc[0]) if len(valid_votes) else None

            contest_id = upsert_id(
                cursor,
                """
                INSERT INTO election_constituencies
                  (election_id, constituency_version_id,
                   registered_electors, total_votes_polled, valid_votes,
                   nota_votes, turnout_percentage)
                VALUES (%s, %s, %s, %s, %s, NULL, NULL)
                ON DUPLICATE KEY UPDATE
                  election_constituency_id=
                    LAST_INSERT_ID(election_constituency_id),
                  registered_electors=
                    COALESCE(VALUES(registered_electors), registered_electors),
                  total_votes_polled=
                    COALESCE(VALUES(total_votes_polled), total_votes_polled),
                  valid_votes=
                    COALESCE(VALUES(valid_votes), valid_votes)
                """,
                (
                    election_map[year],
                    version_id,
                    registered_electors,
                    total_votes_polled,
                    valid_votes_value,
                ),
            )
            contest_map[(year, const_key)] = contest_id

        # Insert candidates, parties, and candidate results.
        imported = 0

        for _, row in df.iterrows():
            year = int(row["election_year"])
            state_name = clean(row["state_name"])
            constituency_name = clean(row["constituency_name"])
            candidate_name = clean(row["candidate_name"])
            party_name = clean(row.get("party_name_source", ""))

            const_key = (
                norm(state_name), norm(constituency_name), DELIMITATION_CODE
            )
            contest_id = contest_map[(year, const_key)]

            party_id = None
            if party_name:
                party_key = norm(party_name)
                if party_key not in party_map:
                    party_id = upsert_id(
                        cursor,
                        """
                        INSERT INTO parties (party_name, party_abbreviation, party_symbol)
                        VALUES (%s, NULL, %s)
                        ON DUPLICATE KEY UPDATE
                          party_id=LAST_INSERT_ID(party_id)
                        """,
                        (party_name, clean(row.get("party_symbol", "")) or None),
                    )
                    party_map[party_key] = party_id
                party_id = party_map[party_key]

            key = row["source_identity_key"]
            if key not in candidate_map:
                candidate_id = upsert_id(
                    cursor,
                    """
                    INSERT INTO candidates
                      (candidate_name, gender, source_identity_key)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      candidate_id=LAST_INSERT_ID(candidate_id)
                    """,
                    (
                        candidate_name,
                        clean(row.get("gender", "")) or None,
                        key,
                    ),
                )
                candidate_map[key] = candidate_id

            candidate_id = candidate_map[key]

            vote_share = decimal_or_none(
                row.get("vote_share_polled_pct")
            )
            votes = integer_or_none(row["votes_received"])
            rank = int(row["position_rank"])

            cursor.execute("""
                INSERT INTO candidate_results
                  (election_constituency_id, candidate_id, party_id,
                   votes_received, vote_share_percentage,
                   position_rank, candidate_age, candidate_category, is_winner)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
                ON DUPLICATE KEY UPDATE
                  party_id=VALUES(party_id),
                  votes_received=VALUES(votes_received),
                  vote_share_percentage=VALUES(vote_share_percentage),
                  position_rank=VALUES(position_rank),
                  candidate_age=VALUES(candidate_age),
                  candidate_category=VALUES(candidate_category)
            """, (
                contest_id, candidate_id, party_id,
                votes, vote_share, rank,
                integer_or_none(row.get("age")), clean(row.get("category", "")) or None,
            ))
            imported += 1

        # Mark source batches complete.
        for key, batch_id in batch_map.items():
            count = int(
                ((df["election_year"] == key[0])
                 & (df["source_file"].map(clean) == key[1])).sum()
            )
            cursor.execute("""
                UPDATE import_batches
                SET batch_status='COMPLETED',
                    completed_at=CURRENT_TIMESTAMP,
                    rows_imported=%s,
                    rows_rejected=0
                WHERE import_batch_id=%s
            """, (count, batch_id))

        conn.commit()

        print("\nELECTORaW IMPORT COMPLETED")
        print("=" * 45)
        print(f"Candidate result rows processed: {imported:,}")
        print("Election years: 2014, 2019, 2024")
        print("NOTA rows imported: 0")
        print("Winner flags verified: 0")
        print("Unknown constituency reservations: UNKNOWN")
        print("Missing totals preserved as NULL.")
        print("Database transaction committed successfully.")

        for table in [
            "elections", "states", "constituencies",
            "constituency_versions", "parties", "candidates",
            "election_constituencies", "candidate_results",
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            print(f"{table}: {cursor.fetchone()[0]:,}")

    except Exception:
        conn.rollback()
        print("IMPORT FAILED — transaction rolled back.")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
