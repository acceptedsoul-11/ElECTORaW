
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed"

candidates = pd.read_csv(DATA / "candidate_import_preview.csv")
nota = pd.read_csv(DATA / "nota_import_preview.csv")

year = 2024
candidates = candidates[candidates["election_year"] == year].copy()
nota = nota[nota["election_year"] == year].copy()

keys = ["state_name", "constituency_name"]

# Sum candidate votes, excluding NOTA.
candidate_totals = (
    candidates.groupby(keys)["votes_received"]
    .sum()
    .rename("candidate_votes_sum")
)

# Sum NOTA votes separately.
nota_totals = (
    nota.groupby(keys)["votes_received"]
    .sum()
    .rename("nota_votes")
)

# Obtain official constituency totals from the source columns.
# These are repeated across rows, so take one non-null value per constituency.
source = pd.concat([candidates, nota], ignore_index=True)

def first_non_null(series):
    values = series.dropna()
    return values.iloc[0] if not values.empty else float("nan")

official = (
    source.groupby(keys)
    .agg(
        official_valid_votes=("valid_votes", first_non_null),
        official_total_votes_polled=("total_votes_polled", first_non_null),
        total_electors=("total_electors", first_non_null),
    )
)

audit = (
    official.join(candidate_totals)
    .join(nota_totals)
    .reset_index()
)

audit["candidate_votes_sum"] = audit["candidate_votes_sum"].fillna(0)
audit["nota_votes"] = audit["nota_votes"].fillna(0)

audit["candidate_plus_nota"] = (
    audit["candidate_votes_sum"] + audit["nota_votes"]
)

# Test each measure independently.
audit["candidate_minus_valid_votes"] = (
    audit["candidate_votes_sum"] - audit["official_valid_votes"]
)

audit["candidate_plus_nota_minus_total_polled"] = (
    audit["candidate_plus_nota"] - audit["official_total_votes_polled"]
)

audit["candidate_matches_valid_votes"] = (
    audit["candidate_minus_valid_votes"] == 0
)

audit["candidate_plus_nota_matches_total_polled"] = (
    audit["candidate_plus_nota_minus_total_polled"] == 0
)

output = DATA / "vote_reconciliation_2024.csv"
audit.to_csv(output, index=False)

print("2024 vote reconciliation")
print("Constituencies checked:", len(audit))
print(
    "Candidate votes match official valid votes:",
    int(audit["candidate_matches_valid_votes"].sum())
)
print(
    "Candidate + NOTA match total votes polled:",
    int(audit["candidate_plus_nota_matches_total_polled"].sum())
)

print("\nLargest differences: candidate votes vs valid votes")
print(
    audit.assign(
        abs_diff=audit["candidate_minus_valid_votes"].abs()
    )
    .sort_values("abs_diff", ascending=False)
    .head(10)[
        keys + [
            "candidate_votes_sum",
            "official_valid_votes",
            "candidate_minus_valid_votes",
        ]
    ]
    .to_string(index=False)
)

print("\nLargest differences: candidate + NOTA vs total votes polled")
print(
    audit.assign(
        abs_diff=audit["candidate_plus_nota_minus_total_polled"].abs()
    )
    .sort_values("abs_diff", ascending=False)
    .head(10)[
        keys + [
            "candidate_plus_nota",
            "official_total_votes_polled",
            "candidate_plus_nota_minus_total_polled",
        ]
    ]
    .to_string(index=False)
)

print("\nFull report:", output)
print("Read-only audit; no database changes made.")
