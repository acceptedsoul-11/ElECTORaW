
from pathlib import Path
import csv
import re
import unicodedata

from python_calamine import CalamineWorkbook

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

DETAIL_FILES = {
    2014: "Constituency wise detailed result.xlsx",
    2019: "33. Constituency Wise Detailed Result.xls",
    2024: "33-Constituency-Wise-Detailed-Result.xls",
}


def normalize_header(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def number(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        result = float(value)
        return int(result) if result.is_integer() else result
    except (TypeError, ValueError):
        return None


def normalized_identity(value):
    value = unicodedata.normalize("NFKD", clean_text(value))
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def find_header(rows):
    for index, row in enumerate(rows):
        cells = {normalize_header(cell) for cell in row}
        has_state = any(cell in {"state name", "state"} for cell in cells)
        has_constituency = any(
            cell in {"pc name", "pc name ", "constituency"}
            for cell in cells
        )
        has_candidate = any(
            "candidate name" in cell or "candidates name" in cell
            for cell in cells
        )
        if has_state and has_constituency and has_candidate:
            return index
    raise ValueError("Could not identify the detailed-results header row")


def process_year(year, filename):
    path = RAW / str(year) / filename
    workbook = CalamineWorkbook.from_path(str(path))
    sheet = workbook.get_sheet_by_index(0)
    rows = sheet.to_python()

    header_index = find_header(rows)
    headers = [normalize_header(value) for value in rows[header_index]]

    # Preserve each original row as a dictionary keyed by its source headers.
    records = []
    for row_number, row in enumerate(rows[header_index + 1:], start=header_index + 2):
        padded = row + [None] * (len(headers) - len(row))
        raw = dict(zip(headers, padded[:len(headers)]))

        state = clean_text(raw.get("state name") or raw.get("state"))
        constituency = clean_text(raw.get("pc name") or raw.get("constituency"))
        candidate = clean_text(
            raw.get("candidate name") or raw.get("candidates name")
        )

        # Skip report titles, state headings, and completely empty rows.
        if not state or not constituency or not candidate:
            continue

        candidate_key = normalized_identity(candidate)
        is_nota = candidate_key == "nota"

        party = clean_text(raw.get("party name"))
        if not party and not is_nota:
            party = clean_text(raw.get("party"))

        # Column labels vary slightly by election year.
        total_votes = number(raw.get("total"))
        if total_votes is None:
            total_votes = number(raw.get("total votes"))

        general_votes = number(raw.get("general"))
        postal_votes = number(raw.get("postal"))

        total_electors = number(raw.get("total electors"))
        if total_electors is None:
            total_electors = number(
                raw.get("total electors in constituency")
            )

        total_votes_polled = number(
            raw.get("total votes polled in the constituency")
        )
        if total_votes_polled is None:
            total_votes_polled = number(
                raw.get("total votes polled in the constituency ")
            )

        vote_share_electors = number(
            raw.get("over total electors in constituency")
        )
        vote_share_polled = number(
            raw.get("over total votes polled in constituency")
        )
        vote_share_valid = number(
            raw.get("over total valid votes polled in constituency")
        )

        records.append({
            "election_year": year,
            "source_file": filename,
            "source_row_number": row_number,
            "state_name": state,
            "constituency_name": constituency,
            "candidate_name": candidate,
            "is_nota": is_nota,
            "gender": clean_text(raw.get("gender") or raw.get("sex")) or None,
            "age": number(raw.get("age")),
            "category": clean_text(raw.get("category")) or None,
            "party_name_source": party or None,
            "party_symbol": clean_text(raw.get("party symbol")) or None,
            "general_votes": general_votes,
            "postal_votes": postal_votes,
            "votes_received": total_votes,
            "total_votes_polled": total_votes_polled,
            "valid_votes": number(raw.get("valid votes")),
            "total_electors": total_electors,
            "vote_share_electors_pct": vote_share_electors,
            "vote_share_polled_pct": vote_share_polled,
            "vote_share_valid_pct": vote_share_valid,
        })

    OUT.mkdir(parents=True, exist_ok=True)
    output_path = OUT / f"candidate_results_{year}.csv"

    if records:
        with output_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

    print(
        f"{year}: {len(records)} candidate/NOTA rows -> "
        f"{output_path.name}"
    )
    return records


def main():
    all_records = []
    issues = []

    for year, filename in DETAIL_FILES.items():
        path = RAW / str(year) / filename

        if not path.exists():
            issues.append({
                "election_year": year,
                "issue_type": "MISSING_SOURCE_FILE",
                "state_name": "",
                "constituency_name": "",
                "candidate_name": "",
                "details": str(path),
            })
            print(f"WARNING: Missing source file: {path}")
            continue

        try:
            records = process_year(year, filename)
            all_records.extend(records)
        except Exception as exc:
            issues.append({
                "election_year": year,
                "issue_type": "WORKBOOK_READ_ERROR",
                "state_name": "",
                "constituency_name": "",
                "candidate_name": "",
                "details": f"{type(exc).__name__}: {exc}",
            })
            print(f"ERROR processing {year}: {exc}")

    # Flag duplicates without deleting them.
    seen = set()
    for record in all_records:
        key = (
            record["election_year"],
            normalized_identity(record["state_name"]),
            normalized_identity(record["constituency_name"]),
            normalized_identity(record["candidate_name"]),
        )

        if key in seen:
            issues.append({
                "election_year": record["election_year"],
                "issue_type": "POSSIBLE_DUPLICATE",
                "state_name": record["state_name"],
                "constituency_name": record["constituency_name"],
                "candidate_name": record["candidate_name"],
                "details": (
                    f"Source: {record['source_file']}; "
                    f"row: {record['source_row_number']}"
                ),
            })
        else:
            seen.add(key)

    issue_path = OUT / "data_quality_issues.csv"
    OUT.mkdir(parents=True, exist_ok=True)

    fields = [
        "election_year", "issue_type", "state_name",
        "constituency_name", "candidate_name", "details"
    ]

    with issue_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(issues)

    print(f"\nTotal normalized rows: {len(all_records)}")
    print(f"Quality issues flagged: {len(issues)}")
    print(f"Issues report: {issue_path}")


if __name__ == "__main__":
    main()
