
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[3]
folder = root / "data" / "raw" / "2014"

for file in sorted(folder.iterdir()):
    if file.suffix.lower() not in (".xls", ".xlsx"):
        continue

    print(f"\n{'=' * 75}")
    print("FILE:", file.name)

    try:
        book = pd.ExcelFile(file)
        print("Sheets:", book.sheet_names)

        for sheet in book.sheet_names:
            df = pd.read_excel(file, sheet_name=sheet, header=None)
            text = df.astype(str)

            matches = text.apply(
                lambda col: col.str.contains(
                    r"Chhattisgarh|Odisha|Orissa",
                    case=False,
                    regex=True,
                    na=False,
                )
            )

            rows = df[matches.any(axis=1)]

            print(f"\nSheet: {sheet}")
            print("Dimensions:", df.shape)
            print("Rows mentioning target states:", len(rows))

            if not rows.empty:
                print(rows.head(8).to_string(index=False, header=False))

    except Exception as exc:
        print("Could not inspect file:", exc)

print("\nSource inspection complete. No database changes made.")
