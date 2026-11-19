
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed"

unmatched = pd.read_csv(
    DATA / "official_winners_unmatched.csv"
).fillna("")

candidates = pd.read_csv(
    DATA / "candidate_import_preview.csv"
).fillna("")


def norm(value):
    value = str(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


print("INSPECTING UNMATCHED OFFICIAL WINNERS")
print("=" * 90)

for _, winner in unmatched.iterrows():
    year = int(winner["year"])
    state = norm(winner["state"])
    constituency = norm(winner["constituency"])

    rows = candidates[
        (candidates["election_year"].astype(int) == year)
        & (candidates["state_name"].map(norm) == state)
        & (candidates["constituency_name"].map(norm) == constituency)
    ]

    print(
        f"\n{year} | {winner['state']} | {winner['constituency']}"
    )
    print(f"Official winner: {winner['winner']} ({winner['party']})")

    if rows.empty:
        print("RESULT: No matching state/constituency in prepared CSV.")
    else:
        print(
            rows[
                ["candidate_name", "party_name_source", "votes_received"]
            ].to_string(index=False)
        )

print("\nInspection complete. No database changes were made.")
