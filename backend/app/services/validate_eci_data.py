
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"

YEARS = (2014, 2019, 2024)

REQUIRED_COLUMNS = [
    "state_name",
    "constituency_name",
    "candidate_name",
    "votes_received",
    "source_file",
    "source_row_number",
]

all_summaries = []
all_issues = []

for year in YEARS:
    path = PROCESSED / f"candidate_results_{year}.csv"

    if not path.exists():
        print(f"\nERROR: Missing file: {path}")
        continue

    df = pd.read_csv(path)
    issues = []

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        print(f"\n{year}: Missing columns: {missing_columns}")
        continue

    df["votes_received"] = pd.to_numeric(
        df["votes_received"], errors="coerce"
    )

    # Required identifying fields
    for col in [
        "state_name",
        "constituency_name",
        "candidate_name",
    ]:
        missing = (
            df[col].isna()
            | df[col].astype(str).str.strip().eq("")
        )

        for idx in df.index[missing]:
            issues.append({
                "year": year,
                "issue": f"MISSING_{col.upper()}",
                "csv_row": int(idx) + 2,
                "candidate": str(df.at[idx, "candidate_name"]),
                "details": f"{col} is blank",
            })

    # Invalid vote values
    invalid_votes = (
        df["votes_received"].isna()
        | (df["votes_received"] < 0)
    )

    for idx in df.index[invalid_votes]:
        issues.append({
            "year": year,
            "issue": "INVALID_VOTES_RECEIVED",
            "csv_row": int(idx) + 2,
            "candidate": str(df.at[idx, "candidate_name"]),
            "details": str(df.at[idx, "votes_received"]),
        })

    # Identify NOTA for counting only; do not modify source data.
    nota_mask = pd.Series(False, index=df.index)

    for col in ["candidate_name", "party_name_source", "party_symbol"]:
        if col in df.columns:
            values = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )
            nota_mask |= values.isin([
                "NOTA",
                "NONE OF THE ABOVE",
            ])

    # Exact duplicate rows only — not repeated candidate names.
    exact_duplicate_mask = df.duplicated(keep=False)
    exact_duplicate_rows = int(exact_duplicate_mask.sum())

    summary = {
        "year": year,
        "total_rows": len(df),
        "missing_state": int(df["state_name"].isna().sum()),
        "missing_constituency": int(
            df["constituency_name"].isna().sum()
        ),
        "missing_candidate": int(
            df["candidate_name"].isna().sum()
        ),
        "invalid_vote_rows": int(invalid_votes.sum()),
        "nota_rows_detected": int(nota_mask.sum()),
        "exact_duplicate_rows": exact_duplicate_rows,
        "distinct_states": int(df["state_name"].nunique()),
        "distinct_constituencies": int(
            df[["state_name", "constituency_name"]]
            .dropna()
            .drop_duplicates()
            .shape[0]
        ),
    }

    all_summaries.append(summary)
    all_issues.extend(issues)

    print(f"\n{'=' * 45}")
    print(f"ELECTION YEAR: {year}")
    print(f"{'=' * 45}")

    for key, value in summary.items():
        if key != "year":
            print(f"{key}: {value}")

    print(f"Rows requiring review: {len(issues)}")

summary_path = PROCESSED / "validation_summary.csv"
issues_path = PROCESSED / "validation_issues.csv"

pd.DataFrame(all_summaries).to_csv(
    summary_path, index=False
)

pd.DataFrame(
    all_issues,
    columns=[
        "year", "issue", "csv_row", "candidate", "details"
    ],
).to_csv(issues_path, index=False)

print("\nValidation finished.")
print("Summary:", summary_path)
print("Issues:", issues_path)
print("No source CSV rows were changed.")
