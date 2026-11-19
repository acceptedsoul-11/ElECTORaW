
from pathlib import Path
from collections import Counter
from python_calamine import CalamineWorkbook

root = Path(__file__).resolve().parents[3]
file = root / "data" / "raw" / "2014" / "Constituency wise detailed result.xlsx"

workbook = CalamineWorkbook.from_path(str(file))
rows = workbook.get_sheet_by_index(0).to_python()

header = [str(v or "").strip().casefold() for v in rows[2]]
state_col = header.index("state name")
pc_col = header.index("pc name")
candidate_col = header.index("candidates name")

counts = Counter()
examples = {}

for row in rows[3:]:
    row += [None] * max(0, len(header) - len(row))

    state = str(row[state_col] or "").strip()
    constituency = str(row[pc_col] or "").strip()
    candidate = str(row[candidate_col] or "").strip()

    if state and constituency and candidate:
        counts[state] += 1
        examples.setdefault(state, constituency)

print("STATE COUNTS IN ORIGINAL 2014 DETAILED RESULTS")
print("=" * 60)

for state, count in sorted(counts.items()):
    print(f"{state}: {count} rows (example constituency: {examples[state]})")

print("\nTotal qualifying rows:", sum(counts.values()))
