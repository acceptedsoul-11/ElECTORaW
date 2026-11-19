
import argparse
import hashlib
import os
import re
import sys
import unicodedata
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "data" / "processed" / "candidate_import_preview.csv"

REQUIRED_COLUMNS = {
    "election_year",
    "source_file",
    "source_row_number",
    "state_name",
    "constituency_name",
    "candidate_name",
    "party_name_source",
    "votes_received",
    "total_electors",
    "vote_share_polled_pct",
}

def clean(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()

def normalized(value):
    value = unicodedata.normalize("NFKC", clean(value))
    return value.casefold()

def identity_key(year, state, constituency, candidate, party, symbol):
    raw = "|".join(
        normalized(x)
        for x in (year, state, constituency, candidate, party, symbol)
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def read_preview():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Preview CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")

    # The candidate preview must never contain NOTA.
    nota_names = df["candidate_name"].map(normalized).isin(
        {"nota", "none of the above"}
    )
    nota_parties = df["party_name_source"].map(normalized).eq("nota")

    if nota_names.any() or nota_parties.any():
        raise ValueError(
            "NOTA-like rows found in candidate preview. "
            "No import was attempted."
        )

    for col in ("election_year", "votes_received"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df["election_year"].isna().any():
        raise ValueError("Some rows have a missing/invalid election year.")
    if df["votes_received"].isna().any():
        raise ValueError("Some rows have missing/invalid candidate votes.")
    if (df["votes_received"] < 0).any():
        raise ValueError("Negative vote counts found.")
    if not df["election_year"].isin([2014, 2019, 2024]).all():
        raise ValueError("Unexpected election year found.")

    for col in ("state_name", "constituency_name", "candidate_name"):
        if df[col].map(clean).eq("").any():
            raise ValueError(f"Missing required value in {col}.")

    df["source_identity_key"] = df.apply(
        lambda r: identity_key(
            int(r["election_year"]),
            r["state_name"],
            r["constituency_name"],
            r["candidate_name"],
            r["party_name_source"],
            r.get("party_symbol", ""),
        ),
        axis=1,
    )

    # Do not silently remove possible duplicate source records.
    duplicates = df[df.duplicated("source_identity_key", keep=False)].copy()
    return df, duplicates

def connect_db():
    load_dotenv(ROOT / ".env")

    required = (
        "MYSQL_HOST",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
    )
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError(
            f"Missing values in .env: {', '.join(missing)}. "
            "Check variable names; do not paste passwords into chat."
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "electoraw"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        connection_timeout=10,
    )

def inspect_database(conn):
    tables = [
        "elections", "states", "constituencies",
        "constituency_versions", "parties", "candidates",
        "election_constituencies", "candidate_results",
    ]
    cursor = conn.cursor()
    counts = {}

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        counts[table] = cursor.fetchone()[0]

    cursor.execute("SHOW COLUMNS FROM candidates")
    candidate_columns = {row[0] for row in cursor.fetchall()}
    cursor.close()

    if "source_identity_key" not in candidate_columns:
        raise ValueError(
            "candidates.source_identity_key is missing. "
            "Stop and check the schema."
        )

    return counts

def main():
    parser = argparse.ArgumentParser(
        description="ELECTORaW ECI candidate-results importer"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Enable database writes. Dry-run is the default.",
    )
    args = parser.parse_args()

    try:
        df, duplicates = read_preview()

        print("\nELECTORaW IMPORT PRECHECK")
        print("=" * 50)
        print(f"Preview file: {CSV_PATH}")
        print(f"Candidate rows: {len(df):,}")
        print("Rows by year:")
        print(df.groupby("election_year").size().to_string())
        print(f"NOTA rows in candidate preview: 0")
        print(
            "Missing total_votes_polled:",
            int(df["total_votes_polled"].isna().sum()),
        )
        print(
            "Missing valid_votes:",
            int(df["valid_votes"].isna().sum()),
        )
        print(f"Repeated candidate identity keys: {len(duplicates):,}")

        if not duplicates.empty:
            print(
                "\nPotential duplicate identities require review. "
                "Nothing will be imported."
            )
            cols = [
                "election_year", "state_name", "constituency_name",
                "candidate_name", "party_name_source",
                "party_symbol", "source_file", "source_row_number",
            ]
            print(duplicates[cols].head(40).to_string(index=False))
            report = ROOT / "data" / "processed" / "import_identity_review.csv"
            duplicates[cols].to_csv(report, index=False)
            print(f"\nReview report saved to: {report}")
            sys.exit(2)

        conn = connect_db()
        try:
            counts = inspect_database(conn)
            print("\nCurrent database row counts:")
            for table, count in counts.items():
                print(f"  {table}: {count:,}")

            if not args.commit:
                print(
                    "\nDRY RUN ONLY: no database records were changed."
                )
                print(
                    "This precheck does not yet perform the actual import."
                )
                print(
                    "Do not use --commit until the identity review and "
                    "full import mapping are approved."
                )
            else:
                print(
                    "\nSTOP: write mode is intentionally not implemented "
                    "in this precheck version."
                )
                print(
                    "No records were inserted. Use the dry run and share "
                    "its output so the final importer can be prepared."
                )
        finally:
            conn.close()

    except Exception as exc:
        print(f"\nPRECHECK FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
