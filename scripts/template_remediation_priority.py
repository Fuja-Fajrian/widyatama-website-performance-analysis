import csv
from pathlib import Path


# ============================================================
# PMB WIDYATAMA
# STEP 12D.2
# TEMPLATE REMEDIATION PRIORITY RANKING
#
# INPUT:
# root_cause_template_summary_before.csv
#
# OUTPUT:
# template_remediation_priority_before.csv
#
# PURPOSE:
# Convert template-level diagnostics into an actionable
# remediation priority ranking for IT + Marketing.
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
    / "root_cause_template_summary_before.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "template_remediation_priority_before.csv"
)


# ============================================================
# 2. SCORING WEIGHTS
#
# Total = 100%
# ============================================================

WEIGHT_BUSINESS = 0.30
WEIGHT_COVERAGE = 0.20
WEIGHT_PERFORMANCE = 0.20
WEIGHT_LCP = 0.20
WEIGHT_CWV = 0.10


# ============================================================
# 3. SCORING CONSTANTS
# ============================================================

MAX_BUSINESS_WEIGHT = 5.0

# Lighthouse Performance:
# lower score = higher remediation severity.
PERFORMANCE_BEST_REFERENCE = 100.0

# LCP:
# <= 2.5 sec = good
# >= 20 sec = treated as maximum severity
LCP_GOOD_MS = 2500.0
LCP_MAX_SEVERITY_MS = 20000.0


# ============================================================
# 4. GENERIC HELPERS
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


def clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def read_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"\nInput file tidak ditemukan:\n"
            f"{path}\n"
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

        writer.writerows(
            rows
        )


# ============================================================
# 5. BUSINESS IMPORTANCE SCORE
#
# Business Weight 5 = 100
# Business Weight 4 = 80
# etc.
# ============================================================

def business_score(
    business_weight,
):

    value = safe_number(
        business_weight
    )

    if value is None:
        return 0.0

    score = (
        value
        / MAX_BUSINESS_WEIGHT
        * 100
    )

    return round(
        clamp(score),
        2,
    )


# ============================================================
# 6. PAGE COVERAGE SCORE
#
# Template with largest number of pages = 100.
#
# Example:
# Program = 16 pages
# Admission = 10 pages
#
# Program will receive maximum coverage score.
# ============================================================

def coverage_score(
    page_count,
    maximum_page_count,
):

    pages = safe_number(
        page_count
    )

    maximum = safe_number(
        maximum_page_count
    )

    if (
        pages is None
        or maximum is None
        or maximum <= 0
    ):
        return 0.0

    score = (
        pages
        / maximum
        * 100
    )

    return round(
        clamp(score),
        2,
    )


# ============================================================
# 7. PERFORMANCE SEVERITY SCORE
#
# Performance = 100 → severity 0
# Performance = 50  → severity 50
# Performance = 34  → severity 66
#
# Lower Lighthouse Performance = higher remediation urgency.
# ============================================================

def performance_severity_score(
    performance,
):

    value = safe_number(
        performance
    )

    if value is None:
        return 0.0

    score = (
        PERFORMANCE_BEST_REFERENCE
        - value
    )

    return round(
        clamp(score),
        2,
    )


# ============================================================
# 8. LCP SEVERITY SCORE
#
# <= 2.5 sec → 0
# >= 20 sec  → 100
#
# Values between these points are linearly normalized.
# ============================================================

def lcp_severity_score(
    lcp_ms,
):

    value = safe_number(
        lcp_ms
    )

    if value is None:
        return 0.0

    if value <= LCP_GOOD_MS:
        return 0.0

    if value >= LCP_MAX_SEVERITY_MS:
        return 100.0

    score = (

        (
            value
            - LCP_GOOD_MS
        )

        /

        (
            LCP_MAX_SEVERITY_MS
            - LCP_GOOD_MS
        )

        * 100
    )

    return round(
        clamp(score),
        2,
    )


# ============================================================
# 9. FIELD CWV FAILURE SCORE
#
# Uses percentage directly.
#
# 100% failed = severity score 100
# 50% failed  = severity score 50
# ============================================================

def cwv_failure_score(
    failed_pct,
):

    value = safe_number(
        failed_pct
    )

    if value is None:
        return 0.0

    return round(
        clamp(value),
        2,
    )


# ============================================================
# 10. TOTAL PRIORITY SCORE
# ============================================================

def calculate_priority_score(
    business,
    coverage,
    performance,
    lcp,
    cwv,
):

    score = (

        business
        * WEIGHT_BUSINESS

        +

        coverage
        * WEIGHT_COVERAGE

        +

        performance
        * WEIGHT_PERFORMANCE

        +

        lcp
        * WEIGHT_LCP

        +

        cwv
        * WEIGHT_CWV
    )

    return round(
        score,
        2,
    )


# ============================================================
# 11. PRIORITY TIER
# ============================================================

def priority_tier(
    score,
):

    if score >= 80:

        return (
            "P1 - Critical"
        )

    if score >= 65:

        return (
            "P2 - High"
        )

    if score >= 50:

        return (
            "P3 - Medium"
        )

    return (
        "P4 - Lower"
    )


# ============================================================
# 12. DIAGNOSTIC CONFIDENCE
#
# Root cause consistency alone is NOT enough.
#
# Example:
# 1/1 Registration page = 100% consistency,
# but only one page was sampled.
#
# Therefore sample coverage matters.
# ============================================================

def diagnostic_confidence(
    page_count,
    consistency_pct,
):

    pages = safe_number(
        page_count
    )

    consistency = safe_number(
        consistency_pct
    )

    if pages is None:
        pages = 0

    if consistency is None:
        consistency = 0

    # Strong evidence:
    # multiple pages + strong consistency.
    if (
        pages >= 5
        and consistency >= 70
    ):

        return "High"

    # Still credible systemic evidence.
    if (
        pages >= 3
        and consistency >= 60
    ):

        return "Medium-High"

    # Mixed root cause or smaller sample.
    if (
        pages >= 2
        and consistency >= 50
    ):

        return "Medium"

    # Single page or weak consistency.
    return "Low"


# ============================================================
# 13. ROOT CAUSE PATTERN
# ============================================================

def root_cause_pattern(
    primary,
    consistency_pct,
):

    consistency = safe_number(
        consistency_pct
    )

    if consistency is None:
        consistency = 0

    if consistency >= 75:

        return "Systemic / Highly Consistent"

    if consistency >= 60:

        return "Likely Systemic"

    if consistency >= 50:

        return "Mixed Pattern"

    return "Fragmented / Requires Deeper Review"


# ============================================================
# 14. REMEDIATION WORKSTREAM
# ============================================================

def remediation_workstream(
    primary_root_cause,
):

    cause = str(
        primary_root_cause
        or ""
    ).lower()

    if "late lcp resource discovery" in cause:

        return (
            "LCP Asset Priority & "
            "Above-the-Fold Image Delivery"
        )

    if (
        "render-blocking"
        in cause
        or
        "element render delay"
        in cause
    ):

        return (
            "Critical Rendering Path & "
            "CSS/JS Optimization"
        )

    if "slow lcp resource download" in cause:

        return (
            "Image Compression, CDN & "
            "Resource Delivery"
        )

    return (
        "Template-Level Technical Review"
    )


# ============================================================
# 15. RECOMMENDED FIRST ACTION
# ============================================================

def recommended_first_action(
    primary_root_cause,
):

    cause = str(
        primary_root_cause
        or ""
    ).lower()

    if "late lcp resource discovery" in cause:

        return (
            "Identify recurring LCP image/component; "
            "remove inappropriate lazy-loading from "
            "above-the-fold LCP assets; verify initial HTML "
            "discovery; evaluate fetchpriority='high'."
        )

    if (
        "render-blocking"
        in cause
        or
        "element render delay"
        in cause
    ):

        return (
            "Audit shared CSS/JS and above-the-fold rendering; "
            "defer non-critical JavaScript; reduce unused CSS; "
            "prioritize critical rendering resources."
        )

    if "slow lcp resource download" in cause:

        return (
            "Optimize LCP file size, dimensions and format; "
            "review cache/CDN delivery and request duration."
        )

    return (
        "Perform targeted manual template inspection "
        "before remediation."
    )


# ============================================================
# 16. FIX ORDER LABEL
# ============================================================

def fix_order_label(rank):

    if rank == 1:
        return "Fix First"

    if rank == 2:
        return "Fix Second"

    if rank <= 4:
        return "High-Priority Sprint"

    if rank <= 6:
        return "Secondary Sprint"

    return "Later / Monitor"


# ============================================================
# 17. MAIN
# ============================================================

def main():

    print()
    print("=" * 82)
    print("PMB WIDYATAMA")
    print("STEP 12D.2 - TEMPLATE REMEDIATION PRIORITY RANKING")
    print("=" * 82)

    rows = read_csv(
        INPUT_FILE
    )

    print(
        f"[INPUT] Templates : {len(rows)}"
    )

    if not rows:

        raise RuntimeError(
            "Input template summary kosong."
        )

    # ========================================================
    # MAX TEMPLATE COVERAGE
    # ========================================================

    page_counts = [

        safe_number(
            row.get(
                "Page_Count"
            )
        )

        for row
        in rows
    ]

    page_counts = [

        value

        for value
        in page_counts

        if value is not None
    ]

    maximum_page_count = max(
        page_counts
    )

    print(
        "[MODEL] Maximum template page coverage :",
        maximum_page_count,
    )

    scored_rows = []

    # ========================================================
    # CALCULATE SCORES
    # ========================================================

    for row in rows:

        business = business_score(
            row.get(
                "Median_Business_Weight"
            )
        )

        coverage = coverage_score(
            row.get(
                "Page_Count"
            ),
            maximum_page_count,
        )

        performance = performance_severity_score(
            row.get(
                "Median_Performance"
            )
        )

        lcp = lcp_severity_score(
            row.get(
                "Median_Lab_LCP_ms"
            )
        )

        cwv = cwv_failure_score(
            row.get(
                "CWV_Failed_Pct"
            )
        )

        priority_score = calculate_priority_score(
            business,
            coverage,
            performance,
            lcp,
            cwv,
        )

        consistency = safe_number(
            row.get(
                "Dominant_Primary_Pct"
            )
        )

        pages = safe_number(
            row.get(
                "Page_Count"
            )
        )

        output = dict(
            row
        )

        # ----------------------------------------------------
        # COMPONENT SCORES
        # ----------------------------------------------------

        output[
            "Business_Importance_Score"
        ] = business

        output[
            "Page_Coverage_Score"
        ] = coverage

        output[
            "Performance_Severity_Score"
        ] = performance

        output[
            "LCP_Severity_Score"
        ] = lcp

        output[
            "CWV_Failure_Score"
        ] = cwv

        # ----------------------------------------------------
        # WEIGHTED CONTRIBUTIONS
        # ----------------------------------------------------

        output[
            "Weighted_Business"
        ] = round(
            business
            * WEIGHT_BUSINESS,
            2,
        )

        output[
            "Weighted_Coverage"
        ] = round(
            coverage
            * WEIGHT_COVERAGE,
            2,
        )

        output[
            "Weighted_Performance"
        ] = round(
            performance
            * WEIGHT_PERFORMANCE,
            2,
        )

        output[
            "Weighted_LCP"
        ] = round(
            lcp
            * WEIGHT_LCP,
            2,
        )

        output[
            "Weighted_CWV"
        ] = round(
            cwv
            * WEIGHT_CWV,
            2,
        )

        # ----------------------------------------------------
        # FINAL SCORE
        # ----------------------------------------------------

        output[
            "Template_Priority_Score"
        ] = priority_score

        output[
            "Priority_Tier"
        ] = priority_tier(
            priority_score
        )

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        output[
            "Diagnostic_Confidence"
        ] = diagnostic_confidence(
            pages,
            consistency,
        )

        output[
            "Root_Cause_Pattern"
        ] = root_cause_pattern(
            row.get(
                "Dominant_Primary_Root_Cause"
            ),
            consistency,
        )

        # ----------------------------------------------------
        # REMEDIATION
        # ----------------------------------------------------

        output[
            "Remediation_Workstream"
        ] = remediation_workstream(
            row.get(
                "Dominant_Primary_Root_Cause"
            )
        )

        output[
            "Recommended_First_Action"
        ] = recommended_first_action(
            row.get(
                "Dominant_Primary_Root_Cause"
            )
        )

        scored_rows.append(
            output
        )

    # ========================================================
    # SORT DESCENDING BY PRIORITY
    # ========================================================

    scored_rows.sort(
        key=lambda row:
            (
                -safe_number(
                    row.get(
                        "Template_Priority_Score"
                    )
                ),

                -safe_number(
                    row.get(
                        "Page_Count"
                    )
                ),
            )
    )

    # ========================================================
    # ADD RANK
    # ========================================================

    final_rows = []

    for rank, row in enumerate(
        scored_rows,
        start=1,
    ):

        ordered = {

            "Remediation_Rank":
                rank,

            "Recommended_Fix_Order":
                fix_order_label(
                    rank
                ),
        }

        ordered.update(
            row
        )

        final_rows.append(
            ordered
        )

    # ========================================================
    # WRITE OUTPUT
    # ========================================================

    write_csv(
        OUTPUT_FILE,
        final_rows,
    )

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print()
    print("=" * 82)
    print("TEMPLATE REMEDIATION PRIORITY")
    print("=" * 82)

    for row in final_rows:

        print()

        print(
            f'#{row["Remediation_Rank"]} '
            f'{row["Final_Page_Type"]}'
        )

        print(
            "  Score       :",
            row[
                "Template_Priority_Score"
            ],
        )

        print(
            "  Tier        :",
            row[
                "Priority_Tier"
            ],
        )

        print(
            "  Pages       :",
            row[
                "Page_Count"
            ],
        )

        print(
            "  Performance :",
            row[
                "Median_Performance"
            ],
        )

        print(
            "  Median LCP  :",
            row[
                "Median_Lab_LCP_sec"
            ],
            "sec",
        )

        print(
            "  Root Cause  :",
            row[
                "Dominant_Primary_Root_Cause"
            ],
        )

        print(
            "  Confidence  :",
            row[
                "Diagnostic_Confidence"
            ],
        )

        print(
            "  Fix Order   :",
            row[
                "Recommended_Fix_Order"
            ],
        )

    print()
    print("=" * 82)
    print("STEP 12D.2 FINISHED")
    print("=" * 82)

    print()
    print(
        "Output:"
    )

    print(
        OUTPUT_FILE
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()