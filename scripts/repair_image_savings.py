import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


# ============================================================
# PMB WIDYATAMA
# STEP 12C.3
# IMAGE SAVINGS REPAIR
#
# PURPOSE:
# - NO Lighthouse rerun
# - Re-read existing Lighthouse JSON
# - Repair Image_Savings_Bytes
# - Avoid recursive double counting
# - Recalculate root cause fields
# - Produce repaired datasets
# ============================================================


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

RUNS_INPUT = (
    PROCESSED_DIR
    / "root_cause_batch_runs_before.csv"
)

RESULTS_INPUT = (
    PROCESSED_DIR
    / "root_cause_batch_results_before.csv"
)


# ============================================================
# 2. NEW OUTPUT FILES
#
# ORIGINAL FILES WILL NOT BE OVERWRITTEN
# ============================================================

RUNS_OUTPUT = (
    PROCESSED_DIR
    / "root_cause_batch_runs_before_repaired.csv"
)

RESULTS_OUTPUT = (
    PROCESSED_DIR
    / "root_cause_batch_results_before_repaired.csv"
)

QC_OUTPUT = (
    PROCESSED_DIR
    / "root_cause_image_repair_qc.csv"
)


# ============================================================
# 3. GENERIC HELPERS
# ============================================================

def safe_number(value):

    try:

        if value in (
            None,
            "",
            "None",
        ):
            return None

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def rounded(
    value,
    digits=2,
):

    number = safe_number(
        value
    )

    if number is None:
        return None

    return round(
        number,
        digits,
    )


def bytes_to_mb(value):

    value = safe_number(
        value
    )

    if value is None:
        return None

    return round(
        value / 1024 / 1024,
        2,
    )


def numeric_median(
    rows,
    field,
    digits=2,
):

    values = []

    for row in rows:

        value = safe_number(
            row.get(
                field
            )
        )

        if value is not None:

            values.append(
                value
            )

    if not values:
        return None

    return round(
        median(values),
        digits,
    )


def mode_with_count(values):

    clean = [

        value

        for value in values

        if value not in (
            None,
            "",
            "None",
        )
    ]

    if not clean:

        return (
            None,
            0,
        )

    counter = Counter(
        clean
    )

    return counter.most_common(
        1
    )[0]


# ============================================================
# 4. CSV HELPERS
# ============================================================

def read_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"\nFile tidak ditemukan:\n{path}\n"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        return list(
            csv.DictReader(
                file
            )
        )


def write_csv(
    path,
    rows,
):

    if not rows:
        return

    fieldnames = []

    for row in rows:

        for key in row.keys():

            if key not in fieldnames:

                fieldnames.append(
                    key
                )

    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:

            writer.writerow(
                {
                    key:
                        row.get(key)

                    for key
                    in fieldnames
                }
            )


# ============================================================
# 5. RESOLVE JSON PATH
# ============================================================

def resolve_json_path(
    path_string,
):

    if not path_string:

        return None

    raw = Path(
        path_string
    )

    if raw.is_absolute():

        return raw

    return (
        PROJECT_ROOT
        / raw
    )


# ============================================================
# 6. PARSE LIGHTHOUSE DISPLAY VALUE
#
# Example:
# Est savings of 33,772 KiB
# ============================================================

def parse_display_savings_bytes(
    display_value,
):

    if not display_value:

        return None

    text = str(
        display_value
    )

    # --------------------------------------------------------
    # KiB
    # --------------------------------------------------------

    match = re.search(

        r"([0-9][0-9,.\s]*)"
        r"\s*KiB",

        text,

        re.IGNORECASE,
    )

    if match:

        raw = (
            match.group(1)
            .replace(
                ",",
                "",
            )
            .replace(
                " ",
                "",
            )
        )

        try:

            return round(
                float(raw)
                * 1024
            )

        except ValueError:

            pass

    # --------------------------------------------------------
    # MiB
    # --------------------------------------------------------

    match = re.search(

        r"([0-9][0-9,.\s]*)"
        r"\s*MiB",

        text,

        re.IGNORECASE,
    )

    if match:

        raw = (
            match.group(1)
            .replace(
                ",",
                "",
            )
            .replace(
                " ",
                "",
            )
        )

        try:

            return round(
                float(raw)
                * 1024
                * 1024
            )

        except ValueError:

            pass

    # --------------------------------------------------------
    # KB
    # --------------------------------------------------------

    match = re.search(

        r"([0-9][0-9,.\s]*)"
        r"\s*KB",

        text,

        re.IGNORECASE,
    )

    if match:

        raw = (
            match.group(1)
            .replace(
                ",",
                "",
            )
            .replace(
                " ",
                "",
            )
        )

        try:

            return round(
                float(raw)
                * 1000
            )

        except ValueError:

            pass

    # --------------------------------------------------------
    # MB
    # --------------------------------------------------------

    match = re.search(

        r"([0-9][0-9,.\s]*)"
        r"\s*MB",

        text,

        re.IGNORECASE,
    )

    if match:

        raw = (
            match.group(1)
            .replace(
                ",",
                "",
            )
            .replace(
                " ",
                "",
            )
        )

        try:

            return round(
                float(raw)
                * 1_000_000
            )

        except ValueError:

            pass

    return None


# ============================================================
# 7. CORRECT IMAGE SAVINGS EXTRACTION
#
# IMPORTANT:
# DO NOT recursively sum subItems.
#
# Priority:
# 1. official overallSavingsBytes
# 2. top-level item wastedBytes
# 3. audit displayValue fallback
#
# If top-level sum is materially inconsistent with Lighthouse's
# displayValue, use displayValue as safer audit-level figure.
# ============================================================

def extract_correct_image_savings(
    lighthouse_data,
):

    audits = (
        lighthouse_data.get(
            "audits"
        )
        or {}
    )

    # Also supports PSI-shaped JSON if required
    if not audits:

        audits = (
            lighthouse_data
            .get(
                "lighthouseResult",
                {},
            )
            .get(
                "audits",
                {},
            )
            or {}
        )

    audit = (
        audits.get(
            "image-delivery-insight"
        )
        or {}
    )

    if not audit:

        return {

            "bytes":
                None,

            "source":
                "AUDIT_NOT_AVAILABLE",

            "display_bytes":
                None,

            "top_level_bytes":
                None,

            "item_count":
                0,
        }

    details = (
        audit.get(
            "details"
        )
        or {}
    )

    # --------------------------------------------------------
    # OPTION 1
    # Lighthouse direct overall savings
    # --------------------------------------------------------

    direct = safe_number(
        details.get(
            "overallSavingsBytes"
        )
    )

    if direct is None:

        direct = safe_number(
            audit.get(
                "overallSavingsBytes"
            )
        )

    if direct is not None:

        return {

            "bytes":
                round(
                    direct
                ),

            "source":
                "OVERALL_SAVINGS_BYTES",

            "display_bytes":
                parse_display_savings_bytes(
                    audit.get(
                        "displayValue"
                    )
                ),

            "top_level_bytes":
                None,

            "item_count":
                len(
                    details.get(
                        "items",
                        [],
                    )
                    or []
                ),
        }

    # --------------------------------------------------------
    # OPTION 2
    # Sum ONLY top-level image item wastedBytes
    #
    # Never descend into subItems.
    # --------------------------------------------------------

    items = (
        details.get(
            "items"
        )
        or []
    )

    top_level_values = []

    for item in items:

        if not isinstance(
            item,
            dict,
        ):

            continue

        wasted = safe_number(
            item.get(
                "wastedBytes"
            )
        )

        if wasted is not None:

            top_level_values.append(
                wasted
            )

    top_level_sum = (

        round(
            sum(
                top_level_values
            )
        )

        if top_level_values

        else None
    )

    # --------------------------------------------------------
    # OPTION 3
    # Lighthouse display value
    # --------------------------------------------------------

    display_bytes = (
        parse_display_savings_bytes(
            audit.get(
                "displayValue"
            )
        )
    )

    # --------------------------------------------------------
    # CROSS-CHECK
    # --------------------------------------------------------

    if (
        top_level_sum
        is not None

        and display_bytes
        is not None

        and display_bytes > 0
    ):

        difference_ratio = abs(

            top_level_sum
            - display_bytes

        ) / display_bytes

        # Within 5%:
        # use more precise top-level values.
        if difference_ratio <= 0.05:

            return {

                "bytes":
                    top_level_sum,

                "source":
                    "TOP_LEVEL_WASTED_BYTES",

                "display_bytes":
                    display_bytes,

                "top_level_bytes":
                    top_level_sum,

                "item_count":
                    len(items),
            }

        # Strong disagreement:
        # Lighthouse's audit-level display figure is safer.
        return {

            "bytes":
                display_bytes,

            "source":
                "DISPLAY_VALUE_FALLBACK",

            "display_bytes":
                display_bytes,

            "top_level_bytes":
                top_level_sum,

            "item_count":
                len(items),
        }

    if top_level_sum is not None:

        return {

            "bytes":
                top_level_sum,

            "source":
                "TOP_LEVEL_WASTED_BYTES",

            "display_bytes":
                display_bytes,

            "top_level_bytes":
                top_level_sum,

            "item_count":
                len(items),
        }

    if display_bytes is not None:

        return {

            "bytes":
                display_bytes,

            "source":
                "DISPLAY_VALUE_FALLBACK",

            "display_bytes":
                display_bytes,

            "top_level_bytes":
                None,

            "item_count":
                len(items),
        }

    return {

        "bytes":
            None,

        "source":
            "NO_SAVINGS_VALUE",

        "display_bytes":
            None,

        "top_level_bytes":
            None,

        "item_count":
            len(items),
    }


# ============================================================
# 8. ROOT CAUSE RECLASSIFICATION
#
# Same logic used by batch collector.
# ============================================================

def classify_root_cause(
    row,
):

    phase = row.get(
        "Dominant_LCP_Phase"
    )

    lazy = row.get(
        "LCP_Lazy_Loaded"
    )

    discoverable = row.get(
        "LCP_Discoverable_Initial_HTML"
    )

    priority = row.get(
        "LCP_FetchPriority_High"
    )

    load_delay = safe_number(
        row.get(
            "LCP_Load_Delay_ms"
        )
    )

    load_duration = safe_number(
        row.get(
            "LCP_Load_Duration_ms"
        )
    )

    render_delay = safe_number(
        row.get(
            "LCP_Render_Delay_ms"
        )
    )

    render_savings = safe_number(
        row.get(
            "Render_Blocking_Savings_ms"
        )
    )

    image_savings = safe_number(
        row.get(
            "Image_Savings_Bytes"
        )
    )

    page_weight = safe_number(
        row.get(
            "Page_Weight_Bytes"
        )
    )

    main_thread = safe_number(
        row.get(
            "Main_Thread_Work_ms"
        )
    )

    issues = []

    # --------------------------------------------------------
    # PRIMARY
    # --------------------------------------------------------

    if (

        phase
        == "Resource Load Delay"

        and (

            lazy == "Yes"

            or discoverable == "No"

            or (
                load_delay is not None
                and load_delay > 1000
            )
        )
    ):

        issues.append(
            "Late LCP Resource Discovery"
        )

    elif (

        phase
        == "Element Render Delay"

        and render_delay is not None

        and render_delay > 1000
    ):

        if (

            render_savings is not None

            and render_savings > 500
        ):

            issues.append(

                "High Element Render Delay / "
                "Render-Blocking Pipeline"
            )

        else:

            issues.append(
                "High Element Render Delay"
            )

    elif (

        phase
        == "Resource Load Duration"

        and load_duration is not None

        and load_duration > 1000
    ):

        issues.append(
            "Slow LCP Resource Download"
        )

    elif (

        lazy == "Yes"

        or discoverable == "No"
    ):

        issues.append(
            "Late LCP Resource Discovery"
        )

    # --------------------------------------------------------
    # SUPPORTING ISSUE:
    # IMAGE DELIVERY
    # --------------------------------------------------------

    if (

        image_savings is not None

        and image_savings > 500_000
    ):

        issues.append(
            "Unoptimized Image Delivery"
        )

    # --------------------------------------------------------
    # PAGE WEIGHT
    # --------------------------------------------------------

    if (

        page_weight is not None

        and page_weight > 5_000_000
    ):

        issues.append(
            "Excessive Page Weight"
        )

    # --------------------------------------------------------
    # MAIN THREAD
    # --------------------------------------------------------

    if (

        main_thread is not None

        and main_thread > 4000
    ):

        issues.append(
            "Heavy Main-Thread Work"
        )

    # --------------------------------------------------------
    # RENDER BLOCKING
    # --------------------------------------------------------

    if (

        render_savings is not None

        and render_savings > 500
    ):

        issues.append(
            "Render-Blocking Resources"
        )

    # --------------------------------------------------------
    # FETCH PRIORITY
    # --------------------------------------------------------

    if priority == "No":

        issues.append(
            "Missing LCP Fetch Priority"
        )

    # Deduplicate while preserving order
    issues = list(
        dict.fromkeys(
            issues
        )
    )

    if not issues:

        return (

            "No Dominant Root Cause Detected",

            None,
        )

    return (

        issues[0],

        (
            issues[1]

            if len(issues) > 1

            else None
        ),
    )


# ============================================================
# 9. MAIN REPAIR PROCESS
# ============================================================

def main():

    print()
    print(
        "=" * 78
    )

    print(
        "PMB WIDYATAMA"
    )

    print(
        "STEP 12C.3 - "
        "IMAGE SAVINGS REPAIR"
    )

    print(
        "=" * 78
    )

    runs = read_csv(
        RUNS_INPUT
    )

    results = read_csv(
        RESULTS_INPUT
    )

    print(
        f"[INPUT] Run rows    : "
        f"{len(runs)}"
    )

    print(
        f"[INPUT] Page rows   : "
        f"{len(results)}"
    )

    repaired_runs = []

    qc_rows = []

    repaired_count = 0

    json_missing_count = 0

    run_qc_pass = 0

    run_qc_fail = 0

    # ========================================================
    # REPAIR RUN LEVEL
    # ========================================================

    for index, row in enumerate(
        runs,
        start=1,
    ):

        row = dict(
            row
        )

        # Preserve invalid rows if any
        if row.get(
            "Run_Status"
        ) != "VALID":

            repaired_runs.append(
                row
            )

            continue

        json_path = resolve_json_path(

            row.get(
                "JSON_Path"
            )
        )

        old_image_savings = safe_number(

            row.get(
                "Image_Savings_Bytes"
            )
        )

        page_weight = safe_number(

            row.get(
                "Page_Weight_Bytes"
            )
        )

        if (
            json_path is None

            or not json_path.exists()
        ):

            json_missing_count += 1

            row[
                "Image_Savings_Repair_Status"
            ] = "JSON_NOT_FOUND"

            repaired_runs.append(
                row
            )

            qc_rows.append(
                {
                    "Page_ID":
                        row.get(
                            "Page_ID"
                        ),

                    "Valid_Run_Number":
                        row.get(
                            "Valid_Run_Number"
                        ),

                    "JSON_Path":
                        row.get(
                            "JSON_Path"
                        ),

                    "Old_Image_Savings_Bytes":
                        old_image_savings,

                    "New_Image_Savings_Bytes":
                        None,

                    "Page_Weight_Bytes":
                        page_weight,

                    "Repair_Source":
                        "JSON_NOT_FOUND",

                    "QC":
                        "FAIL",
                }
            )

            continue

        try:

            with open(
                json_path,
                "r",
                encoding="utf-8",
            ) as file:

                lighthouse_data = (
                    json.load(
                        file
                    )
                )

        except Exception as exc:

            json_missing_count += 1

            row[
                "Image_Savings_Repair_Status"
            ] = (
                "JSON_READ_ERROR"
            )

            repaired_runs.append(
                row
            )

            qc_rows.append(
                {
                    "Page_ID":
                        row.get(
                            "Page_ID"
                        ),

                    "Valid_Run_Number":
                        row.get(
                            "Valid_Run_Number"
                        ),

                    "JSON_Path":
                        row.get(
                            "JSON_Path"
                        ),

                    "Old_Image_Savings_Bytes":
                        old_image_savings,

                    "New_Image_Savings_Bytes":
                        None,

                    "Page_Weight_Bytes":
                        page_weight,

                    "Repair_Source":
                        (
                            f"JSON_READ_ERROR: "
                            f"{exc}"
                        ),

                    "QC":
                        "FAIL",
                }
            )

            continue

        repair = (
            extract_correct_image_savings(
                lighthouse_data
            )
        )

        new_image_savings = (
            repair[
                "bytes"
            ]
        )

        row[
            "Image_Savings_Bytes"
        ] = new_image_savings

        row[
            "Image_Savings_MB"
        ] = bytes_to_mb(
            new_image_savings
        )

        row[
            "Image_Savings_Repair_Source"
        ] = repair[
            "source"
        ]

        row[
            "Image_Savings_Display_Bytes"
        ] = repair[
            "display_bytes"
        ]

        row[
            "Image_Savings_Top_Level_Bytes"
        ] = repair[
            "top_level_bytes"
        ]

        row[
            "Image_Delivery_Item_Count"
        ] = repair[
            "item_count"
        ]

        # ----------------------------------------------------
        # RUN QC
        #
        # Image savings should not materially exceed
        # total network page weight.
        #
        # 5% tolerance protects against rounding differences.
        # ----------------------------------------------------

        if (

            new_image_savings is None

            or page_weight is None
        ):

            qc = "REVIEW"

        elif (

            new_image_savings

            <= page_weight * 1.05
        ):

            qc = "PASS"

        else:

            qc = "FAIL"

        row[
            "Image_Savings_QC"
        ] = qc

        # ----------------------------------------------------
        # RE-CALCULATE ROOT CAUSE
        # ----------------------------------------------------

        (
            primary,
            secondary,
        ) = classify_root_cause(
            row
        )

        row[
            "Primary_Root_Cause"
        ] = primary

        row[
            "Secondary_Root_Cause"
        ] = secondary

        repaired_runs.append(
            row
        )

        repaired_count += 1

        if qc == "PASS":

            run_qc_pass += 1

        elif qc == "FAIL":

            run_qc_fail += 1

        qc_rows.append(
            {
                "Page_ID":
                    row.get(
                        "Page_ID"
                    ),

                "URL":
                    row.get(
                        "URL"
                    ),

                "Valid_Run_Number":
                    row.get(
                        "Valid_Run_Number"
                    ),

                "JSON_Path":
                    row.get(
                        "JSON_Path"
                    ),

                "Old_Image_Savings_Bytes":
                    old_image_savings,

                "Old_Image_Savings_MB":
                    bytes_to_mb(
                        old_image_savings
                    ),

                "New_Image_Savings_Bytes":
                    new_image_savings,

                "New_Image_Savings_MB":
                    bytes_to_mb(
                        new_image_savings
                    ),

                "Page_Weight_Bytes":
                    page_weight,

                "Page_Weight_MB":
                    bytes_to_mb(
                        page_weight
                    ),

                "Display_Savings_Bytes":
                    repair[
                        "display_bytes"
                    ],

                "Top_Level_Savings_Bytes":
                    repair[
                        "top_level_bytes"
                    ],

                "Repair_Source":
                    repair[
                        "source"
                    ],

                "Image_Item_Count":
                    repair[
                        "item_count"
                    ],

                "QC":
                    qc,
            }
        )

    # ========================================================
    # GROUP VALID RUNS BY PAGE
    # ========================================================

    valid_runs_by_page = defaultdict(
        list
    )

    for row in repaired_runs:

        if (
            row.get(
                "Run_Status"
            )
            == "VALID"
        ):

            valid_runs_by_page[
                row.get(
                    "Page_ID"
                )
            ].append(
                row
            )

    # ========================================================
    # REPAIR PAGE-LEVEL SUMMARY
    # ========================================================

    repaired_results = []

    page_qc_pass = 0

    page_qc_fail = 0

    for result in results:

        result = dict(
            result
        )

        page_id = result.get(
            "Page_ID"
        )

        valid_rows = (
            valid_runs_by_page.get(
                page_id,
                [],
            )
        )

        if not valid_rows:

            result[
                "Image_Savings_Repair_Status"
            ] = "NO_VALID_RUNS"

            repaired_results.append(
                result
            )

            continue

        median_image_bytes = (
            numeric_median(

                valid_rows,

                "Image_Savings_Bytes",

                0,
            )
        )

        median_page_weight = (
            numeric_median(

                valid_rows,

                "Page_Weight_Bytes",

                0,
            )
        )

        result[
            "Median_Image_Savings_Bytes"
        ] = median_image_bytes

        result[
            "Median_Image_Savings_MB"
        ] = bytes_to_mb(
            median_image_bytes
        )

        # ----------------------------------------------------
        # ROOT CAUSE MODE
        # ----------------------------------------------------

        (
            primary,
            primary_count,
        ) = mode_with_count(

            [
                row.get(
                    "Primary_Root_Cause"
                )

                for row
                in valid_rows
            ]
        )

        (
            secondary,
            secondary_count,
        ) = mode_with_count(

            [
                row.get(
                    "Secondary_Root_Cause"
                )

                for row
                in valid_rows
            ]
        )

        valid_count = len(
            valid_rows
        )

        result[
            "Primary_Root_Cause"
        ] = primary

        result[
            "Primary_Root_Cause_Consistency"
        ] = (

            f"{primary_count}/"
            f"{valid_count}"
        )

        result[
            "Secondary_Root_Cause"
        ] = secondary

        result[
            "Secondary_Root_Cause_Consistency"
        ] = (

            f"{secondary_count}/"
            f"{valid_count}"
        )

        # ----------------------------------------------------
        # PAGE QC
        # ----------------------------------------------------

        if (

            median_image_bytes is None

            or median_page_weight is None
        ):

            page_qc = "REVIEW"

        elif (

            median_image_bytes

            <= median_page_weight * 1.05
        ):

            page_qc = "PASS"

            page_qc_pass += 1

        else:

            page_qc = "FAIL"

            page_qc_fail += 1

        result[
            "Image_Savings_QC"
        ] = page_qc

        result[
            "Image_Savings_Repair_Status"
        ] = "REPAIRED"

        repaired_results.append(
            result
        )

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    write_csv(
        RUNS_OUTPUT,
        repaired_runs,
    )

    write_csv(
        RESULTS_OUTPUT,
        repaired_results,
    )

    write_csv(
        QC_OUTPUT,
        qc_rows,
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print(
        "=" * 78
    )

    print(
        "IMAGE SAVINGS REPAIR SUMMARY"
    )

    print(
        "=" * 78
    )

    print(
        "Run rows processed       :",
        len(runs),
    )

    print(
        "Valid runs repaired      :",
        repaired_count,
    )

    print(
        "JSON missing/read errors :",
        json_missing_count,
    )

    print(
        "Run-level QC PASS        :",
        run_qc_pass,
    )

    print(
        "Run-level QC FAIL        :",
        run_qc_fail,
    )

    print()

    print(
        "Page rows                :",
        len(results),
    )

    print(
        "Page-level QC PASS       :",
        page_qc_pass,
    )

    print(
        "Page-level QC FAIL       :",
        page_qc_fail,
    )

    print()

    print(
        "Repaired runs:"
    )

    print(
        RUNS_OUTPUT
    )

    print()

    print(
        "Repaired page results:"
    )

    print(
        RESULTS_OUTPUT
    )

    print()

    print(
        "QC report:"
    )

    print(
        QC_OUTPUT
    )

    print(
        "=" * 78
    )

    # ========================================================
    # QUALITY GATE
    # ========================================================

    if (

        json_missing_count == 0

        and run_qc_fail == 0

        and page_qc_fail == 0
    ):

        print()
        print(
            "STEP 12C.3 STATUS: PASS"
        )

        print(
            "Dataset siap untuk "
            "Template-Level Analysis."
        )

    else:

        print()
        print(
            "STEP 12C.3 STATUS: REVIEW REQUIRED"
        )

        print(
            "Periksa "
            "root_cause_image_repair_qc.csv"
        )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()