import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


# ============================================================
# PMB WIDYATAMA
# STEP 12D.1
# TEMPLATE-LEVEL ROOT CAUSE ANALYSIS
#
# INPUT:
# root_cause_batch_results_before_repaired.csv
#
# OUTPUT:
# 1. root_cause_template_summary_before.csv
# 2. root_cause_template_rootcause_matrix_before.csv
# ============================================================


# ============================================================
# 1. PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

INPUT_FILE = (
    PROCESSED_DIR
    / "root_cause_batch_results_before_repaired.csv"
)

SUMMARY_OUTPUT = (
    PROCESSED_DIR
    / "root_cause_template_summary_before.csv"
)

MATRIX_OUTPUT = (
    PROCESSED_DIR
    / "root_cause_template_rootcause_matrix_before.csv"
)


# ============================================================
# 2. HELPERS
# ============================================================

def safe_number(value):

    if value is None:
        return None

    value = str(value).strip()

    if value.lower() in (
        "",
        "none",
        "nan",
        "null",
    ):
        return None

    try:
        return float(value)

    except ValueError:
        return None


def safe_median(
    rows,
    field,
    digits=2,
):

    values = []

    for row in rows:

        value = safe_number(
            row.get(field)
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


def safe_average(
    rows,
    field,
    digits=2,
):

    values = []

    for row in rows:

        value = safe_number(
            row.get(field)
        )

        if value is not None:
            values.append(
                value
            )

    if not values:
        return None

    return round(
        sum(values) / len(values),
        digits,
    )


def percent(
    numerator,
    denominator,
):

    if not denominator:
        return 0

    return round(
        (numerator / denominator)
        * 100,
        1,
    )


def mode_with_count(values):

    clean = [

        value

        for value in values

        if value not in (
            None,
            "",
            "None",
            "nan",
        )
    ]

    if not clean:
        return (
            None,
            0,
        )

    return Counter(
        clean
    ).most_common(1)[0]


def read_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"\nInput file tidak ditemukan:\n{path}\n"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        return list(
            csv.DictReader(file)
        )


def write_csv(
    path,
    rows,
):

    if not rows:
        return

    columns = []

    for row in rows:

        for key in row.keys():

            if key not in columns:
                columns.append(
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
            fieldnames=columns,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# 3. TEMPLATE PERFORMANCE CLASSIFICATION
# ============================================================

def classify_template_health(
    median_performance,
    median_lcp,
):

    performance = safe_number(
        median_performance
    )

    lcp = safe_number(
        median_lcp
    )

    if (
        performance is None
        or lcp is None
    ):
        return "Review"

    # Very poor template-level condition
    if (
        performance < 40
        and lcp > 10000
    ):
        return "Critical"

    if (
        performance < 50
        or lcp > 6000
    ):
        return "High Risk"

    if (
        performance < 90
        or lcp > 2500
    ):
        return "Needs Improvement"

    return "Healthy"


# ============================================================
# 4. TEMPLATE REMEDIATION DIRECTION
# ============================================================

def remediation_direction(
    primary_root_cause,
):

    mapping = {

        (
            "High Element Render Delay / "
            "Render-Blocking Pipeline"
        ):
            (
                "Optimize critical rendering path; "
                "defer/non-critical CSS & JS; "
                "reduce template-level render blocking."
            ),

        "High Element Render Delay":
            (
                "Reduce render delay, main-thread work, "
                "and above-the-fold rendering complexity."
            ),

        "Late LCP Resource Discovery":
            (
                "Prioritize LCP asset; remove lazy-loading "
                "from above-the-fold LCP image; apply "
                "fetchpriority=high where appropriate."
            ),

        "Slow LCP Resource Download":
            (
                "Compress/resize LCP assets and improve "
                "resource delivery/cache/CDN strategy."
            ),
    }

    return mapping.get(
        primary_root_cause,
        "Requires page/template-level technical review.",
    )


# ============================================================
# 5. MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("PMB WIDYATAMA")
    print("STEP 12D.1 - TEMPLATE-LEVEL ROOT CAUSE ANALYSIS")
    print("=" * 80)

    rows = read_csv(
        INPUT_FILE
    )

    print(
        f"[INPUT] Page-level rows : {len(rows)}"
    )

    # ========================================================
    # GROUP BY TEMPLATE
    # ========================================================

    groups = defaultdict(
        list
    )

    for row in rows:

        template = (
            row.get(
                "Final_Page_Type"
            )
            or "Unknown"
        )

        groups[
            template
        ].append(
            row
        )

    print(
        f"[INPUT] Templates       : {len(groups)}"
    )

    summary_rows = []

    all_primary_causes = set()

    # ========================================================
    # TEMPLATE SUMMARY
    # ========================================================

    for template, template_rows in groups.items():

        page_count = len(
            template_rows
        )

        primary_values = [

            row.get(
                "Primary_Root_Cause"
            )

            for row
            in template_rows
        ]

        secondary_values = [

            row.get(
                "Secondary_Root_Cause"
            )

            for row
            in template_rows
        ]

        for value in primary_values:

            if value:
                all_primary_causes.add(
                    value
                )

        (
            dominant_primary,
            dominant_primary_count,
        ) = mode_with_count(
            primary_values
        )

        (
            dominant_secondary,
            dominant_secondary_count,
        ) = mode_with_count(
            secondary_values
        )

        render_delay_count = sum(

            1

            for row
            in template_rows

            if row.get(
                "Primary_Root_Cause"
            )
            in (
                "High Element Render Delay / "
                "Render-Blocking Pipeline",

                "High Element Render Delay",
            )
        )

        late_discovery_count = sum(

            1

            for row
            in template_rows

            if row.get(
                "Primary_Root_Cause"
            )
            == "Late LCP Resource Discovery"
        )

        slow_download_count = sum(

            1

            for row
            in template_rows

            if row.get(
                "Primary_Root_Cause"
            )
            == "Slow LCP Resource Download"
        )

        cwv_failed = sum(

            1

            for row
            in template_rows

            if str(
                row.get(
                    "CWV_Status",
                    ""
                )
            ).lower()
            == "failed"
        )

        cwv_passed = sum(

            1

            for row
            in template_rows

            if str(
                row.get(
                    "CWV_Status",
                    ""
                )
            ).lower()
            == "passed"
        )

        field_available = sum(

            1

            for row
            in template_rows

            if str(
                row.get(
                    "Field_Data_Available",
                    ""
                )
            ).lower()
            == "yes"
        )

        critical_pages = sum(

            1

            for row
            in template_rows

            if (
                "critical"
                in str(
                    row.get(
                        "Test_Priority",
                        ""
                    )
                ).lower()
            )
        )

        median_performance = safe_median(
            template_rows,
            "Median_Performance",
        )

        median_lcp = safe_median(
            template_rows,
            "Median_Lab_LCP_ms",
        )

        median_fcp = safe_median(
            template_rows,
            "Median_Lab_FCP_ms",
        )

        median_tbt = safe_median(
            template_rows,
            "Median_Lab_TBT_ms",
        )

        median_speed_index = safe_median(
            template_rows,
            "Median_Speed_Index_ms",
        )

        median_page_weight = safe_median(
            template_rows,
            "Median_Page_Weight_MB",
        )

        median_image_savings = safe_median(
            template_rows,
            "Median_Image_Savings_MB",
        )

        median_render_savings = safe_median(
            template_rows,
            "Median_Render_Blocking_Savings_ms",
        )

        median_main_thread = safe_median(
            template_rows,
            "Median_Main_Thread_Work_ms",
        )

        median_business_weight = safe_median(
            template_rows,
            "Business_Weight",
        )

        median_combined_priority = safe_median(
            template_rows,
            "Combined_Priority",
        )

        health = classify_template_health(
            median_performance,
            median_lcp,
        )

        summary_rows.append(
            {
                "Final_Page_Type":
                    template,

                "Page_Count":
                    page_count,

                "Critical_Page_Count":
                    critical_pages,

                "Median_Business_Weight":
                    median_business_weight,

                "Median_Combined_Priority":
                    median_combined_priority,

                # --------------------------------------------
                # PERFORMANCE
                # --------------------------------------------

                "Median_Performance":
                    median_performance,

                "Median_Lab_FCP_ms":
                    median_fcp,

                "Median_Lab_LCP_ms":
                    median_lcp,

                "Median_Lab_LCP_sec":
                    (
                        round(
                            median_lcp / 1000,
                            2,
                        )
                        if median_lcp is not None
                        else None
                    ),

                "Median_Lab_TBT_ms":
                    median_tbt,

                "Median_Speed_Index_ms":
                    median_speed_index,

                # --------------------------------------------
                # TECHNICAL DIAGNOSTICS
                # --------------------------------------------

                "Median_Page_Weight_MB":
                    median_page_weight,

                "Median_Image_Savings_MB":
                    median_image_savings,

                "Median_Render_Blocking_Savings_ms":
                    median_render_savings,

                "Median_Main_Thread_Work_ms":
                    median_main_thread,

                # --------------------------------------------
                # CRUX
                # --------------------------------------------

                "Field_Data_Available_Count":
                    field_available,

                "CWV_Failed_Count":
                    cwv_failed,

                "CWV_Failed_Pct":
                    percent(
                        cwv_failed,
                        page_count,
                    ),

                "CWV_Passed_Count":
                    cwv_passed,

                "CWV_Passed_Pct":
                    percent(
                        cwv_passed,
                        page_count,
                    ),

                # --------------------------------------------
                # ROOT CAUSES
                # --------------------------------------------

                "Dominant_Primary_Root_Cause":
                    dominant_primary,

                "Dominant_Primary_Count":
                    dominant_primary_count,

                "Dominant_Primary_Pct":
                    percent(
                        dominant_primary_count,
                        page_count,
                    ),

                "Render_Delay_Count":
                    render_delay_count,

                "Render_Delay_Pct":
                    percent(
                        render_delay_count,
                        page_count,
                    ),

                "Late_LCP_Discovery_Count":
                    late_discovery_count,

                "Late_LCP_Discovery_Pct":
                    percent(
                        late_discovery_count,
                        page_count,
                    ),

                "Slow_LCP_Download_Count":
                    slow_download_count,

                "Slow_LCP_Download_Pct":
                    percent(
                        slow_download_count,
                        page_count,
                    ),

                "Dominant_Secondary_Root_Cause":
                    dominant_secondary,

                "Dominant_Secondary_Count":
                    dominant_secondary_count,

                "Dominant_Secondary_Pct":
                    percent(
                        dominant_secondary_count,
                        page_count,
                    ),

                # --------------------------------------------
                # INTERPRETATION
                # --------------------------------------------

                "Template_Health":
                    health,

                "Recommended_Remediation_Direction":
                    remediation_direction(
                        dominant_primary
                    ),
            }
        )

    # Sort:
    # templates with highest page coverage first
    summary_rows.sort(
        key=lambda x: (
            -int(
                x.get(
                    "Page_Count",
                    0,
                )
            ),
            str(
                x.get(
                    "Final_Page_Type",
                    ""
                )
            ),
        )
    )

    # ========================================================
    # ROOT CAUSE MATRIX
    # ========================================================

    root_causes = sorted(
        all_primary_causes
    )

    matrix_rows = []

    for template, template_rows in groups.items():

        counter = Counter(

            row.get(
                "Primary_Root_Cause"
            )

            for row
            in template_rows

            if row.get(
                "Primary_Root_Cause"
            )
        )

        matrix_row = {

            "Final_Page_Type":
                template,

            "Page_Count":
                len(
                    template_rows
                ),
        }

        for cause in root_causes:

            matrix_row[
                cause
            ] = counter.get(
                cause,
                0,
            )

        matrix_rows.append(
            matrix_row
        )

    matrix_rows.sort(
        key=lambda x:
            -int(
                x.get(
                    "Page_Count",
                    0,
                )
            )
    )

    # ========================================================
    # WRITE OUTPUT
    # ========================================================

    write_csv(
        SUMMARY_OUTPUT,
        summary_rows,
    )

    write_csv(
        MATRIX_OUTPUT,
        matrix_rows,
    )

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("TEMPLATE-LEVEL SUMMARY")
    print("=" * 80)

    for row in summary_rows:

        print()
        print(
            row[
                "Final_Page_Type"
            ]
        )

        print(
            "  Pages          :",
            row[
                "Page_Count"
            ],
        )

        print(
            "  Performance    :",
            row[
                "Median_Performance"
            ],
        )

        print(
            "  Median LCP     :",
            row[
                "Median_Lab_LCP_sec"
            ],
            "sec",
        )

        print(
            "  CWV Failed     :",
            (
                f'{row["CWV_Failed_Count"]}/'
                f'{row["Page_Count"]}'
            ),
        )

        print(
            "  Primary        :",
            row[
                "Dominant_Primary_Root_Cause"
            ],
        )

        print(
            "  Consistency    :",
            (
                f'{row["Dominant_Primary_Pct"]}%'
            ),
        )

        print(
            "  Template Health:",
            row[
                "Template_Health"
            ],
        )

    print()
    print("=" * 80)
    print("STEP 12D.1 FINISHED")
    print("=" * 80)

    print()
    print(
        "Template summary:"
    )

    print(
        SUMMARY_OUTPUT
    )

    print()

    print(
        "Root cause matrix:"
    )

    print(
        MATRIX_OUTPUT
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()