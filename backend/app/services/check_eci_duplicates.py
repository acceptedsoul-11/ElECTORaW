
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"

KEY_COLUMNS = [
    "election_year",
    "state_name",
    "constituency_name",
    "candidate_name",
]

def normalize(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().upper().split())

all_frames = []

for year in (2014, 2019, 2024):
    path = PROCESSED / f"candidate_results_{year}.csv"

    if not path.exists():
        print(f"MISSING: {path}")
        continue

    df = pd.read_csv(path)
    print(f"\n{'=' * 65}")
    print(f"{year}: {len(df)} rows")
    print("Columns:", df.columns.tolist())

    missing = [c for c in KEY_COLUMNS if c not in df.columns]
    if missing:
        print("Cannot audit this file; missing columns:", missing)
        continue

    df["source_year_file"] = year

    for column in KEY_COLUMNS:
        df[f"_key_{column}"] = df[column].map(normalize)

    # NOTA is not a candidate and must be audited separately.
    is_nota = df["_key_candidate_name"].eq("NOTA")
    print("NOTA rows:", int(is_nota.sum()))

    candidates = df.loc[~is_nota].copy()
    all_frames.append(candidates)

    # Same name in the same election constituency:
    # investigate; do not automatically delete.
    identity_key = [f"_key_{c}" for c in KEY_COLUMNS]
    repeated = candidates[
        candidates.duplicated(identity_key, keep=False)
    ].sort_values(identity_key)

    print("Repeated candidate-key rows:", len(repeated))

    if not repeated.empty:
        display_cols = [
            c for c in KEY_COLUMNS
            + ["party_name", "total_votes", "source_file", "source_row"]
            if c in repeated.columns
        ]
        print(repeated[display_cols].to_string(index=False))

    # Exact duplicates across all original staged columns.
    original_cols = [
        c for c in df.columns if not c.startswith("_key_")
    ]
    exact = df.loc[
        ~is_nota & df[original_cols].duplicated(keep=False)
    ]

    print("Exact repeated candidate rows:", len(exact))

if all_frames:
    combined = pd.concat(all_frames, ignore_index=True)

    # Repeated names across different years are expected.
    cross_year = combined[
        combined.duplicated(
            ["_key_state_name", "_key_constituency_name",
             "_key_candidate_name"],
            keep=False,
        )
    ]

    cross_year = cross_year.sort_values(
        ["_key_candidate_name", "_key_state_name",
         "_key_constituency_name", "election_year"]
    )

    print(f"\n{'=' * 65}")
    print("CROSS-YEAR REPEAT CANDIDATE AUDIT")
    print("These are not duplicates merely because they recur.")
    print("Rows for candidates appearing across years:", len(cross_year))

    if not cross_year.empty:
        cols = [
            c for c in KEY_COLUMNS + ["party_name", "total_votes"]
            if c in cross_year.columns
        ]
        print(cross_year[cols].to_string(index=False))

print("\nAudit complete. No rows were modified or deleted.")
