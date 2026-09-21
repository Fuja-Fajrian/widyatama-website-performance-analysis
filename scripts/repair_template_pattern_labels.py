import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "template_remediation_priority_before.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "template_remediation_priority_before_final.csv"
)


def safe_number(value):
    try:
        if value in (None, "", "None", "nan"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def corrected_pattern(page_count, consistency_pct):

    pages = safe_number(page_count) or 0
    consistency = safe_number(consistency_pct) or 0

    # Single-page evidence cannot establish systemic behavior
    if pages == 1:
        return "Single-Page Evidence / Systemic Status Unconfirmed"

    # Two pages: repeated pattern, but still limited evidence
    if pages == 2:
        if consistency >= 75:
            return "Consistent Pattern / Limited Sample"
        return "Mixed Pattern / Limited Sample"

    # 3-4 pages
    if pages < 5:
        if consistency >= 75:
            return "Likely Systemic"
        if consistency >= 50:
            return "Mixed Pattern"
        return "Fragmented / Requires Deeper Review"

    # 5+ pages
    if consistency >= 75:
        return "Systemic / Highly Consistent"

    if consistency >= 60:
        return "Likely Systemic"

    if consistency >= 50:
        return "Mixed Pattern"

    return "Fragmented / Requires Deeper Review"


def main():

    print("=" * 78)
    print("PMB WIDYATAMA")
    print("STEP 12D.3 - ROOT CAUSE PATTERN LABEL REPAIR")
    print("=" * 78)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input tidak ditemukan:\n{INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    changes = 0

    for row in rows:

        old_pattern = row.get(
            "Root_Cause_Pattern"
        )

        new_pattern = corrected_pattern(
            row.get("Page_Count"),
            row.get("Dominant_Primary_Pct"),
        )

        row["Root_Cause_Pattern"] = new_pattern

        if old_pattern != new_pattern:
            changes += 1

            print()
            print(row.get("Final_Page_Type"))
            print("  OLD :", old_pattern)
            print("  NEW :", new_pattern)

    if not rows:
        raise RuntimeError("Input CSV kosong.")

    fieldnames = list(
        rows[0].keys()
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)

    print("Rows              :", len(rows))
    print("Labels corrected  :", changes)
    print()
    print("Output:")
    print(OUTPUT_FILE)
    print()
    print("STEP 12D.3 STATUS: PASS")


if __name__ == "__main__":
    main()