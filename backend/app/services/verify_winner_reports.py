
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "processed"

matched = pd.read_csv(
    OUT / "official_winners_matched.csv",
    dtype=str
).fillna("")

unmatched = pd.read_csv(
    OUT / "official_winners_unmatched.csv",
    dtype=str
).fillna("")

ambiguous_path = OUT / "official_winners_ambiguous.csv"
ambiguous = (
    pd.read_csv(ambiguous_path, dtype=str).fillna("")
    if ambiguous_path.exists()
    else pd.DataFrame()
)

print("OFFICIAL WINNER REPORT AUDIT")
print("=" * 55)

for year in (2014, 2019, 2024):
    m = matched[matched["year"] == str(year)]
    u = unmatched[unmatched["year"] == str(year)]
    a = (
        ambiguous[ambiguous["year"] == str(year)]
        if not ambiguous.empty and "year" in ambiguous.columns
        else pd.DataFrame()
    )

    print(
        f"{year}: matched={len(m)}, "
        f"unmatched={len(u)}, ambiguous={len(a)}"
    )

    if "candidate_result_id" in m.columns:
        ids = m["candidate_result_id"].dropna()
        print(
            f"  unique result IDs={ids.nunique()}, "
            f"duplicate IDs={ids.duplicated().sum()}"
        )

print("\n2014 unmatched states:")
if not unmatched.empty:
    u2014 = unmatched[unmatched["year"] == "2014"]
    if "state" in u2014.columns:
        print(u2014["state"].value_counts().to_string())

print("\n2024 unmatched official winners:")
if not unmatched.empty:
    u2024 = unmatched[unmatched["year"] == "2024"]
    if not u2024.empty:
        columns = [
            c for c in ["state", "constituency", "winner", "party"]
            if c in u2024.columns
        ]
        print(u2024[columns].to_string(index=False))

print("\nAudit reports inspected. No database changes made.")
