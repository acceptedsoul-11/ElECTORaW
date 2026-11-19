
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"

keys = [
    "election_year",
    "state_name",
    "constituency_name",
    "candidate_name",
]

detail_columns = [
    *keys,
    "party_name_source",
    "party_symbol",
    "general_votes",
    "postal_votes",
    "votes_received",
    "total_votes_polled",
    "valid_votes",
    "total_electors",
    "is_nota",
    "source_file",
    "source_row_number",
]

frames = []

for year in (2014, 2019, 2024):
    path = PROCESSED / f"candidate_results_{year}.csv"
    df = pd.read_csv(path)

    for col in keys:
        df[col] = df[col].fillna("").astype(str).str.strip().str.upper()

    # Exclude NOTA from candidate-duplicate detection.
    nota = df["is_nota"].astype(str).str.strip().str.lower().isin(
        ["true", "1", "yes"]
    )
    candidates = df.loc[~nota].copy()

    repeated_mask = candidates.duplicated(keys, keep=False)
    repeated = candidates.loc[repeated_mask, detail_columns].copy()

    if not repeated.empty:
        frames.append(repeated)

    print(f"{year}: NOTA rows detected by is_nota = {int(nota.sum())}")

if frames:
    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values(keys + ["source_row_number"])

    output = PROCESSED / "duplicate_candidate_details.csv"
    result.to_csv(output, index=False)

    print("\nSuspicious rows:", len(result))
    print("Saved:", output)
    print(result.to_string(index=False))
else:
    print("No repeated candidate keys found.")
