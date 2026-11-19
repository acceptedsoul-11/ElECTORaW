
from pathlib import Path
from python_calamine import CalamineWorkbook
import re

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / "data" / "raw" / "2014" / "Constituency wise detailed result.xlsx"

workbook = CalamineWorkbook.from_path(str(path))
sheet = workbook.get_sheet_by_index(0)
rows = sheet.to_python()


def norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


print("WORKBOOK DIMENSIONS:", len(rows), "rows")
print("\nFIRST 15 ROWS:")
for i, row in enumerate(rows[:15], start=1):
    print(i, repr(row))


print("\nHEADER DETECTION:")
for i, row in enumerate(rows):
    cells = [norm(x) for x in row]
    has_state = any(x in ("state name", "state") for x in cells)
    has_pc = any(x in ("pc name", "constituency") for x in cells)
    has_candidate = any(
        "candidate name" in x or "candidates name" in x
        for x in cells
    )

    if has_state and has_pc and has_candidate:
        print("Detected header row:", i + 1)
        print("Headers:", repr(row))

        headers = [norm(x) for x in row]

        for row_number, data in enumerate(rows[i + 1:], start=i + 2):
            padded = data + [None] * max(0, len(headers) - len(data))
            record = dict(zip(headers, padded[:len(headers)]))

            state = norm(record.get("state name") or record.get("state"))
            constituency = norm(
                record.get("pc name") or record.get("constituency")
            )
            candidate = norm(
                record.get("candidate name")
                or record.get("candidates name")
            )

            if state in ("chhattisgarh", "odisha", "orissa"):
                print(
                    f"Source row {row_number}:",
                    repr(state),
                    repr(constituency),
                    repr(candidate),
                )

        break
else:
    print("No header row found using the current detection rules.")

print("\nDiagnostic only. No files or database records changed.")
