import csv
from pathlib import Path
from statistics import median


# ============================================================
# PMB WIDYATAMA
# STEP 13.2
# SPRINT 1 EVIDENCE & PILOT PAGE MAP
#
# INPUT:
# 1. root_cause_batch_results_before_repaired.csv
# 2. remediation_backlog_before.csv
#
# OUTPUT:
# 1. sprint1_page_evidence_before.csv
# 2. sprint1_pilot_pages_before.csv
#
# NO Lighthouse rerun
# NO PSI request
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

PAGE_RESULTS_INPUT = (
    PROCESSED_DIR
    / "root_cause_batch_results_before_repaired.csv"
)

BACKLOG_INPUT = (
    PROCESSED_DIR
    / "remediation_backlog_before.csv"
)

EVIDENCE_OUTPUT = (
    PROCESSED_DIR
    / "sprint1_page_evidence_before.csv"
)

PILOT_OUTPUT = (
    PROCESSED_DIR
    / "sprint1_pilot_pages_before.csv"
)


# ============================================================
# 2. SPRINT 1 TEMPLATES
# ============================================================

SPRINT1_TEMPLATES = [
    "Program",
    "Admission",
]


# ============================================================
# 3. GENERIC HELPERS
# ============================================================

def safe_number(value):

    if value is None:
        return None

    text = str(value).strip()

    if text.lower() in (
        "",
        "none",
        "nan",
        "null",
    ):
        return None

    try:
        return float(text)

    except ValueError:
        return None


def safe_int(value):

    number = safe_number(value)

    if number is None:
        return 0

    return int(number)


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
            csv.DictReader(file)
        )


def write_csv(path, rows):

    if not rows:
        return

    fields = []

    for row in rows:

        for key in row.keys():

            if key not in fields:
                fields.append(key)

    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# 4. CONSISTENCY PARSER
#
# "3/3" -> 100
# "2/3" -> 66.67
# ============================================================

def consistency_pct(value):

    if value is None:
        return None

    text = str(value).strip()

    if "/" not in text:
        return safe_number(text)

    try:

        numerator, denominator = (
            text.split("/", 1)
        )

        numerator = float(numerator)
        denominator = float(denominator)

        if denominator == 0:
            return None

        return round(
            numerator
            / denominator
            * 100,
            2,
        )

    except ValueError:
        return None


# ============================================================
# 5. SPRINT ACTION CODES BY TEMPLATE
# ============================================================

def get_action_map(backlog_rows):

    result = {}

    for template in SPRINT1_TEMPLATES:

        template_rows = [

            row

            for row
            in backlog_rows

            if row.get(
                "Final_Page_Type"
            ) == template
        ]

        codes = [

            row.get(
                "Action_Code"
            )

            for row
            in template_rows

            if row.get(
                "Action_Code"
            )
        ]

        result[template] = "; ".join(
            codes
        )

    return result


# ============================================================
# 6. IMPLEMENTATION READINESS
# ============================================================

def implementation_readiness(row):

    template = row.get(
        "Final_Page_Type"
    )

    primary = str(
        row.get(
            "Primary_Root_Cause",
            ""
        )
    )

    phase = str(
        row.get(
            "Dominant_LCP_Phase",
            ""
        )
    )

    lazy_runs = safe_int(
        row.get(
            "LCP_Lazy_Loaded_Runs"
        )
    )

    missing_priority_runs = safe_int(
        row.get(
            "Missing_FetchPriority_Runs"
        )
    )

    not_discoverable_runs = safe_int(
        row.get(
            "Not_Discoverable_Runs"
        )
    )

    render_savings = safe_number(
        row.get(
            "Median_Render_Blocking_Savings_ms"
        )
    )

    # ========================================================
    # PROGRAM
    # ========================================================

    if template == "Program":

        if (
            primary
            != "Late LCP Resource Discovery"
        ):

            return (
                "OUTLIER - Different Program Root Cause"
            )

        strong_signal = (

            lazy_runs >= 2

            or missing_priority_runs >= 2

            or not_discoverable_runs >= 2
        )

        if strong_signal:

            return (
                "READY - LCP Quick-Win Candidate"
            )

        return (
            "REVIEW - LCP Discovery Signal Incomplete"
        )

    # ========================================================
    # ADMISSION
    # ========================================================

    if template == "Admission":

        render_root_cause = (

            "Render-Blocking" in primary

            or
            "Element Render Delay" in primary
        )

        if not render_root_cause:

            return (
                "OUTLIER - Different Admission Root Cause"
            )

        if (
            phase == "Element Render Delay"

            and render_savings is not None

            and render_savings > 500
        ):

            return (
                "READY - Critical Rendering Path Candidate"
            )

        return (
            "REVIEW - Render Pipeline Evidence Incomplete"
        )

    return "NOT SPRINT 1"


# ============================================================
# 7. EVIDENCE STRENGTH
# ============================================================

def evidence_strength(row):

    root_consistency = (
        consistency_pct(
            row.get(
                "Primary_Root_Cause_Consistency"
            )
        )
    )

    phase_consistency = (
        consistency_pct(
            row.get(
                "Dominant_LCP_Phase_Consistency"
            )
        )
    )

    resource_consistency = (
        consistency_pct(
            row.get(
                "LCP_Resource_Consistency"
            )
        )
    )

    values = [

        value

        for value in (
            root_consistency,
            phase_consistency,
            resource_consistency,
        )

        if value is not None
    ]

    if not values:
        return None

    return round(
        sum(values)
        / len(values),
        2,
    )


# ============================================================
# 8. BUILD EVIDENCE TABLE
# ============================================================

def build_evidence(
    page_rows,
    action_map,
):

    output = []

    for row in page_rows:

        template = row.get(
            "Final_Page_Type"
        )

        if template not in SPRINT1_TEMPLATES:
            continue

        lcp_ms = safe_number(
            row.get(
                "Median_Lab_LCP_ms"
            )
        )

        field_lcp = safe_number(
            row.get(
                "Field_LCP_ms"
            )
        )

        evidence = {

            "Sprint":
                "Sprint 1",

            "Template_Order":
                (
                    1
                    if template == "Program"
                    else 2
                ),

            "Page_ID":
                row.get(
                    "Page_ID"
                ),

            "URL":
                row.get(
                    "URL"
                ),

            "Final_Page_Type":
                template,

            "Test_Priority":
                row.get(
                    "Test_Priority"
                ),

            "Business_Weight":
                row.get(
                    "Business_Weight"
                ),

            "Combined_Priority":
                row.get(
                    "Combined_Priority"
                ),

            # --------------------------------------------
            # BASELINE
            # --------------------------------------------

            "Median_Performance":
                row.get(
                    "Median_Performance"
                ),

            "Median_Lab_LCP_ms":
                row.get(
                    "Median_Lab_LCP_ms"
                ),

            "Median_Lab_LCP_sec":
                (
                    round(
                        lcp_ms / 1000,
                        2,
                    )

                    if lcp_ms is not None

                    else None
                ),

            "Median_Lab_TBT_ms":
                row.get(
                    "Median_Lab_TBT_ms"
                ),

            "Median_Page_Weight_MB":
                row.get(
                    "Median_Page_Weight_MB"
                ),

            "Median_Image_Savings_MB":
                row.get(
                    "Median_Image_Savings_MB"
                ),

            "Median_Render_Blocking_Savings_ms":
                row.get(
                    "Median_Render_Blocking_Savings_ms"
                ),

            "Median_Main_Thread_Work_ms":
                row.get(
                    "Median_Main_Thread_Work_ms"
                ),

            # --------------------------------------------
            # FIELD
            # --------------------------------------------

            "Field_LCP_ms":
                row.get(
                    "Field_LCP_ms"
                ),

            "Field_LCP_sec":
                (
                    round(
                        field_lcp / 1000,
                        2,
                    )

                    if field_lcp is not None

                    else None
                ),

            "Field_INP_ms":
                row.get(
                    "Field_INP_ms"
                ),

            "Field_CLS":
                row.get(
                    "Field_CLS"
                ),

            "Field_TTFB_ms":
                row.get(
                    "Field_TTFB_ms"
                ),

            "CWV_Status":
                row.get(
                    "CWV_Status"
                ),

            # --------------------------------------------
            # ROOT CAUSE
            # --------------------------------------------

            "Primary_Root_Cause":
                row.get(
                    "Primary_Root_Cause"
                ),

            "Primary_Root_Cause_Consistency":
                row.get(
                    "Primary_Root_Cause_Consistency"
                ),

            "Secondary_Root_Cause":
                row.get(
                    "Secondary_Root_Cause"
                ),

            "Dominant_LCP_Phase":
                row.get(
                    "Dominant_LCP_Phase"
                ),

            "Dominant_LCP_Phase_Consistency":
                row.get(
                    "Dominant_LCP_Phase_Consistency"
                ),

            # --------------------------------------------
            # LCP RESOURCE
            # --------------------------------------------

            "Dominant_LCP_Resource":
                row.get(
                    "Dominant_LCP_Resource"
                ),

            "LCP_Resource_Consistency":
                row.get(
                    "LCP_Resource_Consistency"
                ),

            "Dominant_LCP_Label":
                row.get(
                    "Dominant_LCP_Label"
                ),

            "LCP_Label_Consistency":
                row.get(
                    "LCP_Label_Consistency"
                ),

            "LCP_Lazy_Loaded_Runs":
                row.get(
                    "LCP_Lazy_Loaded_Runs"
                ),

            "Missing_FetchPriority_Runs":
                row.get(
                    "Missing_FetchPriority_Runs"
                ),

            "Not_Discoverable_Runs":
                row.get(
                    "Not_Discoverable_Runs"
                ),

            # --------------------------------------------
            # LCP PHASE BREAKDOWN
            # --------------------------------------------

            "Median_LCP_TTFB_ms":
                row.get(
                    "Median_LCP_TTFB_ms"
                ),

            "Median_LCP_Load_Delay_ms":
                row.get(
                    "Median_LCP_Load_Delay_ms"
                ),

            "Median_LCP_Load_Duration_ms":
                row.get(
                    "Median_LCP_Load_Duration_ms"
                ),

            "Median_LCP_Render_Delay_ms":
                row.get(
                    "Median_LCP_Render_Delay_ms"
                ),

            # --------------------------------------------
            # IMPLEMENTATION
            # --------------------------------------------

            "Sprint1_Action_Codes":
                action_map.get(
                    template
                ),

            "Implementation_Readiness":
                implementation_readiness(
                    row
                ),

            "Evidence_Strength_Pct":
                evidence_strength(
                    row
                ),
        }

        output.append(
            evidence
        )

    output.sort(
        key=lambda row: (
            row.get(
                "Template_Order",
                99,
            ),

            -(
                safe_number(
                    row.get(
                        "Median_Lab_LCP_ms"
                    )
                )
                or 0
            ),
        )
    )

    return output


# ============================================================
# 9. PILOT PAGE SELECTION
#
# For each template:
#
# 1. Worst Case
# 2. Representative / Median
# 3. Lower-Bound
#
# This avoids validating only the slowest URLs.
# ============================================================

def select_template_pilots(
    rows,
    template,
):

    candidates = [

        row

        for row
        in rows

        if (
            row.get(
                "Final_Page_Type"
            ) == template

            and str(
                row.get(
                    "Implementation_Readiness",
                    ""
                )
            ).startswith(
                "READY"
            )
        )
    ]

    if not candidates:
        return []

    candidates.sort(
        key=lambda row:
            safe_number(
                row.get(
                    "Median_Lab_LCP_ms"
                )
            )
            or 0
    )

    # Lowest LCP candidate
    lower = candidates[0]

    # Highest LCP candidate
    worst = candidates[-1]

    # Closest to median
    lcp_values = [

        safe_number(
            row.get(
                "Median_Lab_LCP_ms"
            )
        )
        or 0

        for row
        in candidates
    ]

    target_median = median(
        lcp_values
    )

    representative = min(

        candidates,

        key=lambda row:
            abs(
                (
                    safe_number(
                        row.get(
                            "Median_Lab_LCP_ms"
                        )
                    )
                    or 0
                )
                - target_median
            )
    )

    selected = [
        (
            "Worst Case",
            worst,
        ),
        (
            "Representative",
            representative,
        ),
        (
            "Lower-Bound",
            lower,
        ),
    ]

    output = []
    used_ids = set()

    for role, row in selected:

        page_id = row.get(
            "Page_ID"
        )

        if page_id in used_ids:
            continue

        used_ids.add(
            page_id
        )

        pilot = dict(
            row
        )

        pilot[
            "Pilot_Role"
        ] = role

        output.append(
            pilot
        )

    return output


# ============================================================
# 10. BUILD PILOT OUTPUT
# ============================================================

def build_pilot_output(
    evidence_rows,
):

    selected = []

    for template in SPRINT1_TEMPLATES:

        template_pilots = (
            select_template_pilots(
                evidence_rows,
                template,
            )
        )

        for sequence, row in enumerate(
            template_pilots,
            start=1,
        ):

            selected.append(
                {
                    "Pilot_ID":
                        (
                            "PROG"
                            if template == "Program"
                            else "ADM"
                        )
                        + f"-{sequence:02d}",

                    "Pilot_Role":
                        row.get(
                            "Pilot_Role"
                        ),

                    "Final_Page_Type":
                        template,

                    "Page_ID":
                        row.get(
                            "Page_ID"
                        ),

                    "URL":
                        row.get(
                            "URL"
                        ),

                    "Median_Performance":
                        row.get(
                            "Median_Performance"
                        ),

                    "Median_Lab_LCP_sec":
                        row.get(
                            "Median_Lab_LCP_sec"
                        ),

                    "Median_Lab_TBT_ms":
                        row.get(
                            "Median_Lab_TBT_ms"
                        ),

                    "Median_Page_Weight_MB":
                        row.get(
                            "Median_Page_Weight_MB"
                        ),

                    "Primary_Root_Cause":
                        row.get(
                            "Primary_Root_Cause"
                        ),

                    "Dominant_LCP_Phase":
                        row.get(
                            "Dominant_LCP_Phase"
                        ),

                    "Dominant_LCP_Resource":
                        row.get(
                            "Dominant_LCP_Resource"
                        ),

                    "Dominant_LCP_Label":
                        row.get(
                            "Dominant_LCP_Label"
                        ),

                    "LCP_Lazy_Loaded_Runs":
                        row.get(
                            "LCP_Lazy_Loaded_Runs"
                        ),

                    "Missing_FetchPriority_Runs":
                        row.get(
                            "Missing_FetchPriority_Runs"
                        ),

                    "Not_Discoverable_Runs":
                        row.get(
                            "Not_Discoverable_Runs"
                        ),

                    "Median_Render_Blocking_Savings_ms":
                        row.get(
                            "Median_Render_Blocking_Savings_ms"
                        ),

                    "Median_Main_Thread_Work_ms":
                        row.get(
                            "Median_Main_Thread_Work_ms"
                        ),

                    "Evidence_Strength_Pct":
                        row.get(
                            "Evidence_Strength_Pct"
                        ),

                    "Sprint1_Action_Codes":
                        row.get(
                            "Sprint1_Action_Codes"
                        ),

                    "Implementation_Readiness":
                        row.get(
                            "Implementation_Readiness"
                        ),

                    # Filled later
                    "Implementation_Status":
                        "Not Started",

                    "After_Test_Status":
                        "Not Tested",
                }
            )

    return selected


# ============================================================
# 11. MAIN
# ============================================================

def main():

    print()
    print("=" * 82)
    print("PMB WIDYATAMA")
    print("STEP 13.2 - SPRINT 1 EVIDENCE & PILOT PAGE MAP")
    print("=" * 82)

    page_rows = read_csv(
        PAGE_RESULTS_INPUT
    )

    backlog_rows = read_csv(
        BACKLOG_INPUT
    )

    print(
        "[INPUT] Page results :",
        len(page_rows),
    )

    print(
        "[INPUT] Backlog rows :",
        len(backlog_rows),
    )

    action_map = get_action_map(
        backlog_rows
    )

    evidence_rows = build_evidence(
        page_rows,
        action_map,
    )

    pilot_rows = build_pilot_output(
        evidence_rows
    )

    write_csv(
        EVIDENCE_OUTPUT,
        evidence_rows,
    )

    write_csv(
        PILOT_OUTPUT,
        pilot_rows,
    )

    print()
    print("=" * 82)
    print("SPRINT 1 EVIDENCE SUMMARY")
    print("=" * 82)

    for template in SPRINT1_TEMPLATES:

        template_rows = [

            row

            for row
            in evidence_rows

            if row.get(
                "Final_Page_Type"
            ) == template
        ]

        ready = sum(

            1

            for row
            in template_rows

            if str(
                row.get(
                    "Implementation_Readiness",
                    ""
                )
            ).startswith(
                "READY"
            )
        )

        review = sum(

            1

            for row
            in template_rows

            if str(
                row.get(
                    "Implementation_Readiness",
                    ""
                )
            ).startswith(
                "REVIEW"
            )
        )

        outlier = sum(

            1

            for row
            in template_rows

            if str(
                row.get(
                    "Implementation_Readiness",
                    ""
                )
            ).startswith(
                "OUTLIER"
            )
        )

        print()
        print(template)
        print("  Pages   :", len(template_rows))
        print("  READY   :", ready)
        print("  REVIEW  :", review)
        print("  OUTLIER :", outlier)

    print()
    print("=" * 82)
    print("SELECTED PILOT PAGES")
    print("=" * 82)

    for row in pilot_rows:

        print()
        print(
            row.get(
                "Pilot_ID"
            ),
            "-",
            row.get(
                "Pilot_Role"
            ),
        )

        print(
            " Template :",
            row.get(
                "Final_Page_Type"
            ),
        )

        print(
            " Page     :",
            row.get(
                "Page_ID"
            ),
        )

        print(
            " LCP      :",
            row.get(
                "Median_Lab_LCP_sec"
            ),
            "sec",
        )

        print(
            " Root     :",
            row.get(
                "Primary_Root_Cause"
            ),
        )

    print()
    print("=" * 82)
    print("STEP 13.2 FINISHED")
    print("=" * 82)

    print()
    print("Evidence:")
    print(EVIDENCE_OUTPUT)

    print()
    print("Pilot pages:")
    print(PILOT_OUTPUT)
    print()


if __name__ == "__main__":
    main()