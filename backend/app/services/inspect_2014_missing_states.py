
from pathlib import Path
from python_calamine import CalamineWorkbook

root = Path(__file__).resolve().parents[3]
file = (
    root / "data" / "raw" / "2014"
    / "Constituency(PC) wise summary table.xlsx"
)

workbook = CalamineWorkbook.from_path(str(file))
rows = workbook.get_sheet_by_index(0).to_python()

print("WORKBOOK ROWS:", len(rows))
print("\nFIRST 12 ROWS:")
for i, row in enumerate(rows[:12], start=1):
    print(i, repr(row))

print("\nROWS FOR CHHATTISGARH AND ODISHA:")
for i, row in enumerate(rows, start=1):
    text = " | ".join(str(v or "") for v in row)
    if "chhattisgarh" in text.casefold() or "odisha" in text.casefold():
        print(f"Row {i}: {text}")

print("\nInspection only; no files or database records changed.")
