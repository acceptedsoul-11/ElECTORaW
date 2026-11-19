
from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / "data" / "processed" / "candidate_import_preview.csv"

df = pd.read_csv(path, dtype=str).fillna("")

def norm(value):
    return re.sub(
        r"\s+", " ",
        re.sub(r"[^a-z0-9]+", " ", str(value).lower())
    ).strip()

# Show the actual state and constituency names in the 2014 CSV.
data = df[df["election_year"].str.strip() == "2014"]

print("2014 STATE NAMES:")
for state in sorted(data["state_name"].unique()):
    print(repr(state))

print("\n2014 CONSTITUENCIES FOR CHHATTISGARH:")
for state in data["state_name"].unique():
    if norm(state) == "chhattisgarh":
        for name in sorted(
            data.loc[data["state_name"] == state, "constituency_name"].unique()
        ):
            print(repr(name))

print("\n2014 CONSTITUENCIES FOR ODISHA / ORISSA:")
for state in data["state_name"].unique():
    if norm(state) in ("odisha", "orissa"):
        for name in sorted(
            data.loc[data["state_name"] == state, "constituency_name"].unique()
        ):
            print(repr(name))

print("\nDiagnostic complete. No database changes made.")
