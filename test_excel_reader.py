
from python_calamine import CalamineWorkbook
from pathlib import Path

file_path = Path(
    r"data\raw\2024\33-Constituency-Wise-Detailed-Result.xls"
)

print("File exists:", file_path.exists())

workbook = CalamineWorkbook.from_path(str(file_path))

print("Sheets:", workbook.sheet_names)

sheet = workbook.get_sheet_by_index(0)

print(f"Dimensions: {sheet.height} rows x {sheet.width} columns")
print("\nFirst five rows:")

for row in sheet.to_python()[:5]:
    print(row)
