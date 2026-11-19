
from pathlib import Path
from python_calamine import CalamineWorkbook

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "eci_inspection_report.txt"

SUPPORTED_EXTENSIONS = {".xls", ".xlsx"}


def inspect_workbook(path: Path) -> list[str]:
    lines = [
        "=" * 90,
        f"FILE: {path.relative_to(RAW_DATA_DIR)}",
        "=" * 90,
    ]

    try:
        workbook = CalamineWorkbook.from_path(str(path))
        lines.append(f"Sheets: {workbook.sheet_names}")

        for sheet_name in workbook.sheet_names:
            sheet = workbook.get_sheet_by_name(sheet_name)
            rows = sheet.to_python()

            lines.append(f"\nSHEET: {sheet_name}")
            lines.append(f"Raw rows: {len(rows)}")
            lines.append(
                f"Maximum columns: {max((len(row) for row in rows), default=0)}"
            )

            # Print the first 8 rows to reveal report titles,
            # multi-row headers and the first candidate records.
            lines.append("First 8 rows:")
            for row_number, row in enumerate(rows[:8], start=1):
                lines.append(f"  Row {row_number}: {row!r}")

            nonempty_rows = sum(
                any(value is not None and str(value).strip() for value in row)
                for row in rows
            )
            lines.append(f"Non-empty rows: {nonempty_rows}")

    except Exception as exc:
        lines.append(f"ERROR: {type(exc).__name__}: {exc}")

    return lines


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path
        for path in RAW_DATA_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and not path.name.startswith("~$")
    )

    report = [
        "ELECTORaW — ECI WORKBOOK INSPECTION",
        f"Files discovered: {len(files)}",
        "Original source files were not modified.",
        "",
    ]

    for index, path in enumerate(files, start=1):
        print(f"[{index}/{len(files)}] {path.name}")
        report.extend(inspect_workbook(path))
        report.append("")

    OUTPUT_FILE.write_text("\n".join(report), encoding="utf-8")
    print(f"\nReport saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
