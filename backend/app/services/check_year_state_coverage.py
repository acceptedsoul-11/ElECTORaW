
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[3]
path = root / "data" / "processed" / "candidate_import_preview.csv"

df = pd.read_csv(path, dtype=str).fillna("")
df["election_year"] = df["election_year"].str.strip()

for year in ["2014", "2019", "2024"]:
    subset = df[df["election_year"] == year]
    states = sorted(subset["state_name"].str.strip().unique())

    print(f"\n{'=' * 60}")
    print(f"YEAR: {year}")
    print(f"Rows: {len(subset)}")
    print(f"Distinct state names: {len(states)}")
    print("States:")
    print(", ".join(states))

print("\nCoverage check complete. No database changes made.")
