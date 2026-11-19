
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"

candidate_frames = []
nota_frames = []
summary_rows = []

for year in (2014, 2019, 2024):
    path = PROCESSED / f"candidate_results_{year}.csv"
    df = pd.read_csv(path)

    # Normalize the NOTA flag without altering the source CSV.
    nota_flag = (
        df["is_nota"]
        .fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    # Also recognize NOTA by its source labels.
    for col in ["candidate_name", "party_name_source", "party_symbol"]:
        if col in df.columns:
            label = (
                df[col].fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )
            nota_flag |= label.isin(["NOTA", "NONE OF THE ABOVE"])

    candidates = df.loc[~nota_flag].copy()
    nota = df.loc[nota_flag].copy()

    candidate_frames.append(candidates)
    nota_frames.append(nota)

    summary_rows.append({
        "year": year,
        "source_rows": len(df),
        "candidate_rows": len(candidates),
        "nota_rows": len(nota),
        "candidate_votes": candidates["votes_received"].sum(),
        "nota_votes": nota["votes_received"].sum(),
        "source_files": "; ".join(
            sorted(df["source_file"].dropna().unique())
        ),
    })

candidate_output = PROCESSED / "candidate_import_preview.csv"
nota_output = PROCESSED / "nota_import_preview.csv"
summary_output = PROCESSED / "import_preview_summary.csv"

pd.concat(candidate_frames, ignore_index=True).to_csv(
    candidate_output, index=False
)

pd.concat(nota_frames, ignore_index=True).to_csv(
    nota_output, index=False
)

pd.DataFrame(summary_rows).to_csv(
    summary_output, index=False
)

print("IMPORT PREVIEW CREATED — nothing inserted into MySQL.")
print("\nYear-wise summary:")
print(pd.DataFrame(summary_rows).to_string(index=False))

print("\nCandidate preview:", candidate_output)
print("NOTA preview:", nota_output)
print("Summary:", summary_output)
