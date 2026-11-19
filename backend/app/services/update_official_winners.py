
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd
import mysql.connector
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

FILES = {
    2014: "List of Successful Candidates.xlsx",
    2019: "4. List Of Successful Candidates.xls",
    2024: "4-List-Of-Successful-Candidate.xls",
}

# Official party names mapped to common abbreviations in the
# detailed ECI results. Extend this mapping if needed.
PARTY_ALIASES = {
    "bharatiya janata party": {"bjp"},
    "indian national congress": {"inc"},
    "telugu desam": {"tdp"},
    "telugu desam party": {"tdp"},
    "telangana rashtra samithi": {"trs", "brs"},
    "bharat rashtra samithi": {"brs", "trs"},
    "yuvajana sramika rythu congress party": {"ysrcp"},
    "ysr congress party": {"ysrcp"},
    "all india anna dravida munnetra kazhagam": {"admk", "aiadmk"},
    "anna dravida munnetra kazhagam": {"admk", "aiadmk"},
    "dravidian progressive federation": {"dmk"},
    "dravida munnetra kazhagam": {"dmk"},
    "indian national congress (inc)": {"inc"},
    "communist party of india (marxist)": {"cpi(m)", "cpim"},
    "communist party of india": {"cpi"},
    "aam aadmi party": {"aap"},
    "bahujan samaj party": {"bsp"},
    "samajwadi party": {"sp"},
    "all india trinamool congress": {"aitc", "tmc"},
    "trinamool congress": {"aitc", "tmc"},
    "shiv sena": {"shs", "ss"},
    "shivsena": {"shs", "ss"},
    "nationalist congress party": {"ncp"},
    "rashtriya janata dal": {"rjd"},
    "janata dal (united)": {"jd(u)", "jdu"},
    "janata dal (secular)": {"jd(s)", "jds"},
    "rashtriya lok samta party": {"rlsp"},
    "lok jan shakti party": {"ljp"},
    "independent": {"ind"},
}


def norm(value):
    """Normalize text for candidate, constituency and party matching."""
    if value is None or pd.isna(value):
        return ""

    value = unicodedata.normalize("NFKC", str(value)).casefold().strip()

    # Remove common honorifics and professional titles.
    value = re.sub(
        r"^(?:(?:shri|smt|shrimat|mr|mrs|ms|dr|prof)\.?\s+)+",
        "",
        value,
    )

    # Treat punctuation, hyphens and repeated spaces consistently.
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def find_file(year, expected):
    folder = RAW / str(year)
    exact = folder / expected

    if exact.exists():
        return exact

    if folder.exists():
        matches = [
            p for p in folder.iterdir()
            if p.is_file()
            and p.name.casefold() == expected.casefold()
        ]

        if len(matches) == 1:
            return matches[0]

    raise FileNotFoundError(
        f"Cannot locate {expected} in {folder}"
    )


def find_column(headers, terms):
    for index, header in enumerate(headers):
        header = norm(header)
        if any(term in header for term in terms):
            return index
    return None


def read_winners(path):
    sheets = pd.read_excel(
        path,
        sheet_name=None,
        header=None,
        engine="calamine",
    )

    records = []

    for sheet_name, raw in sheets.items():
        raw = raw.dropna(how="all")

        if raw.empty:
            continue

        header_index = None
        columns = None

        for index in range(min(len(raw), 30)):
            headers = raw.iloc[index].tolist()

            constituency_col = find_column(
                headers, ["constituency", "pc name"]
            )
            winner_col = find_column(
                headers,
                ["winner name", "successful candidate", "winner"],
            )
            party_col = find_column(headers, ["party"])
            state_col = find_column(headers, ["state"])

            if (
                constituency_col is not None
                and winner_col is not None
                and party_col is not None
            ):
                header_index = index
                columns = {
                    "constituency": constituency_col,
                    "winner": winner_col,
                    "party": party_col,
                    "state": state_col,
                }
                break

        if header_index is None:
            continue

        for _, row in raw.iloc[header_index + 1:].iterrows():
            constituency = row.iloc[columns["constituency"]]
            winner = row.iloc[columns["winner"]]
            party = row.iloc[columns["party"]]

            if not norm(constituency) or not norm(winner):
                continue

            state = ""
            if columns["state"] is not None:
                state_value = row.iloc[columns["state"]]
                if not pd.isna(state_value):
                    state = str(state_value).strip()

            records.append({
                "state": state,
                "constituency": str(constituency).strip(),
                "winner": str(winner).strip(),
                "party": "" if pd.isna(party) else str(party).strip(),
                "source_file": path.name,
                "source_sheet": str(sheet_name),
            })

    if not records:
        raise ValueError(f"No official winner rows found in {path}")

    return pd.DataFrame(records)


def party_matches(official_party, database_party):
    official = norm(official_party)
    database = norm(database_party)

    if not official or not database:
        return False

    # Exact normalized party-name match.
    if official == database:
        return True

    # Official full name to known detailed-results abbreviation.
    aliases = PARTY_ALIASES.get(official, set())

    if database in aliases:
        return True

    # Also compare normalized abbreviations against known aliases.
    database_aliases = PARTY_ALIASES.get(database, set())

    if official in database_aliases:
        return True

    return False


def get_candidates_in_constituency(cur, year, winner):
    """
    Fetch candidates by election and constituency first.
    Compare normalized names in Python to avoid SQL exact-name
    failures caused by titles, punctuation or initials.
    """
    sql = """
        SELECT
            cr.candidate_result_id,
            c.candidate_name,
            cv.constituency_name,
            p.party_name,
            s.state_name
        FROM candidate_results cr
        JOIN candidates c
          ON c.candidate_id = cr.candidate_id
        JOIN election_constituencies ec
          ON ec.election_constituency_id =
             cr.election_constituency_id
        JOIN elections e
          ON e.election_id = ec.election_id
        JOIN constituency_versions cv
          ON cv.constituency_version_id =
             ec.constituency_version_id
        JOIN constituencies co
          ON co.constituency_id = cv.constituency_id
        JOIN states s
          ON s.state_id = co.state_id
        LEFT JOIN parties p
          ON p.party_id = cr.party_id
        WHERE e.election_year = %s
    """

    cur.execute(sql, (year,))
    all_rows = cur.fetchall()

    state_key = norm(winner["state"])
    constituency_key = norm(winner["constituency"])
    winner_key = norm(winner["winner"])

    matches = []

    for candidate in all_rows:
        if norm(candidate["constituency_name"]) != constituency_key:
            continue

        if state_key and norm(candidate["state_name"]) != state_key:
            continue

        if norm(candidate["candidate_name"]) != winner_key:
            continue

        matches.append(candidate)

    return matches


def resolve_matches(matches, official_party):
    """Use the official party to distinguish duplicate name records."""
    if len(matches) <= 1:
        return matches

    party_matches_found = [
        candidate for candidate in matches
        if party_matches(official_party, candidate["party_name"])
    ]

    if len(party_matches_found) == 1:
        return party_matches_found

    return matches


def main():
    load_dotenv(ROOT / ".env")

    required = [
        "MYSQL_HOST",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
    ]

    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise RuntimeError(
            "Missing .env settings: " + ", ".join(missing)
        )

    OUT.mkdir(parents=True, exist_ok=True)

    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "electoraw"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        autocommit=False,
    )

    cur = conn.cursor(dictionary=True)

    matched = []
    unmatched = []
    ambiguous = []

    try:
        for year, filename in FILES.items():
            path = find_file(year, filename)
            winners = read_winners(path)

            print(f"{year}: read {len(winners)} official winner rows")

            for _, row in winners.iterrows():
                official = row.to_dict()

                candidates = get_candidates_in_constituency(
                    cur, year, official
                )
                candidates = resolve_matches(
                    candidates, official["party"]
                )

                result = {
                    "year": year,
                    **official,
                    "matched_count": len(candidates),
                }

                if len(candidates) == 1:
                    candidate = candidates[0]

                    result.update({
                        "candidate_name_db": candidate["candidate_name"],
                        "constituency_db": candidate["constituency_name"],
                        "state_db": candidate["state_name"],
                        "party_db": candidate["party_name"],
                        "candidate_result_id":
                            candidate["candidate_result_id"],
                    })

                    matched.append(result)

                elif len(candidates) == 0:
                    unmatched.append(result)

                else:
                    result["possible_matches"] = " || ".join(
                        f'{c["candidate_name"]} | '
                        f'{c["state_name"]} | '
                        f'{c["constituency_name"]} | '
                        f'{c["party_name"]}'
                        for c in candidates
                    )
                    ambiguous.append(result)

        # Save reports before attempting database updates.
        pd.DataFrame(matched).to_csv(
            OUT / "official_winners_matched.csv", index=False
        )
        pd.DataFrame(unmatched).to_csv(
            OUT / "official_winners_unmatched.csv", index=False
        )
        pd.DataFrame(ambiguous).to_csv(
            OUT / "official_winners_ambiguous.csv", index=False
        )

        print("\nMATCHING SUMMARY")
        print("=" * 45)
        print(f"Unique matches: {len(matched)}")
        print(f"Unmatched:      {len(unmatched)}")
        print(f"Ambiguous:      {len(ambiguous)}")

        result_ids = [
            int(row["candidate_result_id"])
            for row in matched
        ]

        if len(result_ids) != len(set(result_ids)):
            raise RuntimeError(
                "Duplicate database result IDs detected. "
                "No winner updates will be committed."
            )

        if not matched:
            raise RuntimeError(
                "No unique matches found. Database unchanged."
            )

        # Only mark uniquely matched official winners.
        # Never reset other flags or guess unmatched candidates.
        for result_id in result_ids:
            cur.execute(
                """
                UPDATE candidate_results
                SET is_winner = 1
                WHERE candidate_result_id = %s
                """,
                (result_id,),
            )

        conn.commit()

        print("\nWINNER UPDATE COMMITTED")
        print(f"Winner flags set: {len(result_ids)}")
        print(f"Reports saved in: {OUT}")

    except Exception:
        conn.rollback()
        print("Database transaction rolled back.")
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
