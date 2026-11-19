from pathlib import Path
from python_calamine import CalamineWorkbook

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / "data" / "raw" / "2024" / "7-Constituency-(PC)-Wise-Summary.xls"

print("File exists:", path.exists())

workbook = CalamineWorkbook.from_path(str(path))
print("Sheets:", workbook.sheet_names)

sheet = workbook.get_sheet_by_index(0)
rows = sheet.to_python()

print("Dimensions:", sheet.height, "rows x", sheet.width, "columns")
print("\nFirst 12 rows:")
for i, row in enumerate(rows[:12], start=1):
    print(i, row)