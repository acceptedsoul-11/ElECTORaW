
import os
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

config = {
    "host": os.getenv("MYSQL_HOST") or os.getenv("DB_HOST") or "localhost",
    "port": int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or "3306"),
    "user": os.getenv("MYSQL_USER") or os.getenv("DB_USER"),
    "password": os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME") or "electoraw",
}

if not config["user"] or config["password"] is None:
    raise RuntimeError("MySQL settings missing. Check .env variable names locally.")

conn = mysql.connector.connect(**config)

try:
    cursor = conn.cursor(dictionary=True)

    print("WINNER FLAG COUNTS BY YEAR")
    cursor.execute("""
        SELECT e.election_year,
               COUNT(*) AS candidate_rows,
               SUM(CASE WHEN cr.is_winner = 1 THEN 1 ELSE 0 END)
                   AS flagged_winners
        FROM candidate_results cr
        JOIN election_constituencies ec
          ON ec.election_constituency_id = cr.election_constituency_id
        JOIN elections e
          ON e.election_id = ec.election_id
        GROUP BY e.election_year
        ORDER BY e.election_year
    """)
    for row in cursor.fetchall():
        print(row)

    print("\nWINNER FLAGS BY PARTY AND YEAR")
    cursor.execute("""
        SELECT e.election_year,
               p.party_name,
               COUNT(*) AS flagged_rows
        FROM candidate_results cr
        JOIN election_constituencies ec
          ON ec.election_constituency_id = cr.election_constituency_id
        JOIN elections e
          ON e.election_id = ec.election_id
        JOIN parties p
          ON p.party_id = cr.party_id
        WHERE cr.is_winner = 1
        GROUP BY e.election_year, p.party_name
        ORDER BY e.election_year, flagged_rows DESC
    """)
    for row in cursor.fetchall():
        print(row)

    print("\nRead-only audit complete. No records changed.")

finally:
    conn.close()
