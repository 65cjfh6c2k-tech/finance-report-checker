import json
import sys
from pathlib import Path

from finance_checker import analyze_workbook, save_report_outputs


def validate_input(arguments):
    if len(arguments) != 2:
        raise ValueError("Usage: python analyzer.py path/to/workbook.xlsx")

    workbook_path = Path(arguments[1])
    if workbook_path.suffix.lower() != ".xlsx":
        raise ValueError("Input file must have the .xlsx extension.")

    if not workbook_path.exists():
        raise FileNotFoundError(f"File not found: {workbook_path}")

    if not workbook_path.is_file():
        raise ValueError(f"Path is not a file: {workbook_path}")

    return workbook_path


def main():
    try:
        workbook_path = validate_input(sys.argv)
        report = analyze_workbook(str(workbook_path))
    except FileNotFoundError as error:
        print(json.dumps({"error": str(error)}, indent=2), file=sys.stderr)
        return 1
    except ValueError as error:
        print(json.dumps({"error": str(error)}, indent=2), file=sys.stderr)
        return 1
    except Exception as error:
        print(
            json.dumps({"error": f"Could not read workbook: {error}"}, indent=2),
            file=sys.stderr,
        )
        return 1

    save_report_outputs(workbook_path, report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
