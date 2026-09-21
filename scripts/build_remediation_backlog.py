import csv
from pathlib import Path


# ============================================================
# PMB WIDYATAMA
# STEP 13.1
# REMEDIATION BACKLOG BUILDER
#
# INPUT:
# template_remediation_priority_before_final.csv
#
# OUTPUT:
# remediation_backlog_before.csv
#
# PURPOSE:
# Convert diagnostic findings into an actionable IT backlog.
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
    / "template_remediation_priority_before_final.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "remediation_backlog_before.csv"
)


# ============================================================
# 2. CSV HELPERS
# ============================================================

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


def write_csv(path, rows):

    if not rows:
        return

    fieldnames = []

    for row in rows:

        for key in row.keys():

            if key not in fieldnames:
                fieldnames.append(key)

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
        writer.writerows(rows)


# ============================================================
# 3. ACTION LIBRARY
#
# Rules are based on root-cause mechanism.
# ============================================================

def build_actions(row):

    template = row.get(
        "Final_Page_Type"
    )

    primary = str(
        row.get(
            "Dominant_Primary_Root_Cause",
            ""
        )
    )

    secondary = str(
        row.get(
            "Dominant_Secondary_Root_Cause",
            ""
        )
    )

    confidence = row.get(
        "Diagnostic_Confidence"
    )

    pattern = row.get(
        "Root_Cause_Pattern"
    )

    actions = []

    # ========================================================
    # A. LATE LCP RESOURCE DISCOVERY
    # ========================================================

    if "Late LCP Resource Discovery" in primary:

        actions.append(
            {
                "Action_Code": "LCP-01",
                "Technical_Action":
                    "Remove inappropriate lazy-loading from the "
                    "actual above-the-fold LCP image.",
                "Technical_Mechanism":
                    "Allows the browser to request the critical "
                    "LCP asset earlier.",
                "Expected_Primary_Metric":
                    "LCP",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Low",
                "Suggested_Owner":
                    "Web Developer",
                "Acceptance_Criteria":
                    "The confirmed above-the-fold LCP image does "
                    "not use loading='lazy'.",
                "Validation_Method":
                    "3-run Lighthouse mobile + LCP Discovery audit",
            }
        )

        actions.append(
            {
                "Action_Code": "LCP-02",
                "Technical_Action":
                    "Apply fetchpriority='high' only to the "
                    "confirmed critical LCP image where appropriate.",
                "Technical_Mechanism":
                    "Raises browser priority for the primary "
                    "above-the-fold image request.",
                "Expected_Primary_Metric":
                    "LCP",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Low",
                "Suggested_Owner":
                    "Web Developer",
                "Acceptance_Criteria":
                    "LCP Discovery audit confirms the critical "
                    "resource is priority hinted.",
                "Validation_Method":
                    "Lighthouse LCP request discovery",
            }
        )

        actions.append(
            {
                "Action_Code": "LCP-03",
                "Technical_Action":
                    "Ensure the critical LCP resource is directly "
                    "discoverable from initial HTML.",
                "Technical_Mechanism":
                    "Avoids waiting for JavaScript, carousel logic, "
                    "or delayed DOM mutation before discovering LCP.",
                "Expected_Primary_Metric":
                    "LCP",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Medium",
                "Suggested_Owner":
                    "Web Developer",
                "Acceptance_Criteria":
                    "LCP resource is discoverable in initial "
                    "document markup.",
                "Validation_Method":
                    "Lighthouse LCP request discovery + HTML review",
            }
        )

    # ========================================================
    # B. RENDER BLOCKING / ELEMENT RENDER DELAY
    # ========================================================

    if (
        "Render-Blocking" in primary
        or "Element Render Delay" in primary
    ):

        actions.append(
            {
                "Action_Code": "CRP-01",
                "Technical_Action":
                    "Identify and defer non-critical JavaScript "
                    "loaded before above-the-fold content.",
                "Technical_Mechanism":
                    "Reduces main-thread contention and critical "
                    "rendering-path delay.",
                "Expected_Primary_Metric":
                    "LCP / TBT",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Medium",
                "Suggested_Owner":
                    "Web Developer",
                "Acceptance_Criteria":
                    "Non-critical scripts no longer block initial "
                    "page rendering and core functionality remains intact.",
                "Validation_Method":
                    "3-run Lighthouse + regression test",
            }
        )

        actions.append(
            {
                "Action_Code": "CRP-02",
                "Technical_Action":
                    "Reduce render-blocking CSS and isolate critical "
                    "above-the-fold styles.",
                "Technical_Mechanism":
                    "Shortens critical rendering path before the "
                    "largest visible element can render.",
                "Expected_Primary_Metric":
                    "FCP / LCP",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Medium",
                "Suggested_Owner":
                    "Front-End Developer",
                "Acceptance_Criteria":
                    "Render-blocking opportunity is materially lower "
                    "without visual regression.",
                "Validation_Method":
                    "Lighthouse Render Blocking audit",
            }
        )

        actions.append(
            {
                "Action_Code": "CRP-03",
                "Technical_Action":
                    "Review unused CSS and JavaScript from shared "
                    "theme, Elementor, plugins, and template assets.",
                "Technical_Mechanism":
                    "Reduces unnecessary transfer, parse, compile, "
                    "and execution work.",
                "Expected_Primary_Metric":
                    "TBT / LCP",
                "Expected_Impact":
                    "Medium-High",
                "Implementation_Effort":
                    "Medium-High",
                "Suggested_Owner":
                    "Web Developer",
                "Acceptance_Criteria":
                    "Unused CSS/JS opportunities decrease while "
                    "all required components continue working.",
                "Validation_Method":
                    "Lighthouse unused CSS/JS audits + regression test",
            }
        )

    # ========================================================
    # C. IMAGE DELIVERY
    # ========================================================

    if "Unoptimized Image Delivery" in secondary:

        actions.append(
            {
                "Action_Code": "IMG-01",
                "Technical_Action":
                    "Resize oversized images to actual rendered "
                    "dimensions and generate responsive variants.",
                "Technical_Mechanism":
                    "Reduces unnecessary image transfer bytes.",
                "Expected_Primary_Metric":
                    "Page Weight / LCP",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Medium",
                "Suggested_Owner":
                    "Web Developer + Content Team",
                "Acceptance_Criteria":
                    "Large images are served near their required "
                    "display dimensions.",
                "Validation_Method":
                    "Lighthouse Image Delivery audit",
            }
        )

        actions.append(
            {
                "Action_Code": "IMG-02",
                "Technical_Action":
                    "Serve compressed modern image formats where "
                    "technically appropriate.",
                "Technical_Mechanism":
                    "Reduces transfer size while maintaining "
                    "acceptable visual quality.",
                "Expected_Primary_Metric":
                    "Page Weight / LCP",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Medium",
                "Suggested_Owner":
                    "Web Developer",
                "Acceptance_Criteria":
                    "Image-delivery savings materially decrease "
                    "without unacceptable visual degradation.",
                "Validation_Method":
                    "Lighthouse + visual QA",
            }
        )

    # ========================================================
    # D. HEAVY MAIN THREAD
    # ========================================================

    if "Heavy Main-Thread Work" in secondary:

        actions.append(
            {
                "Action_Code": "JS-01",
                "Technical_Action":
                    "Profile long-running JavaScript and reduce "
                    "non-essential main-thread execution.",
                "Technical_Mechanism":
                    "Reduces blocking work before content can render "
                    "and become responsive.",
                "Expected_Primary_Metric":
                    "TBT / LCP",
                "Expected_Impact":
                    "High",
                "Implementation_Effort":
                    "Medium-High",
                "Suggested_Owner":
                    "Web Developer",
                "Acceptance_Criteria":
                    "Main-thread work and long tasks decrease without "
                    "functional regression.",
                "Validation_Method":
                    "Lighthouse + Chrome Performance trace",
            }
        )

    # ========================================================
    # E. LOW CONFIDENCE PROTECTION
    # ========================================================

    if confidence == "Low":

        actions.insert(
            0,
            {
                "Action_Code": "VAL-01",
                "Technical_Action":
                    "Validate the root cause on additional pages "
                    "before applying a template-wide remediation.",
                "Technical_Mechanism":
                    "Prevents a single-page finding from being "
                    "incorrectly generalized to an entire template.",
                "Expected_Primary_Metric":
                    "Diagnostic Confidence",
                "Expected_Impact":
                    "Risk Reduction",
                "Implementation_Effort":
                    "Low",
                "Suggested_Owner":
                    "Data Analyst + Web Developer",
                "Acceptance_Criteria":
                    "At least 2–3 additional representative URLs "
                    "support or reject the same root-cause pattern.",
                "Validation_Method":
                    "Targeted Lighthouse diagnostics",
            }
        )

    # ========================================================
    # F. MIXED PATTERN PROTECTION
    # ========================================================

    if pattern == "Mixed Pattern":

        actions.insert(
            0,
            {
                "Action_Code": "VAL-02",
                "Technical_Action":
                    "Split pages into root-cause subgroups before "
                    "performing template-wide changes.",
                "Technical_Mechanism":
                    "Prevents two different performance mechanisms "
                    "from being treated as one shared defect.",
                "Expected_Primary_Metric":
                    "Diagnostic Precision",
                "Expected_Impact":
                    "Risk Reduction",
                "Implementation_Effort":
                    "Low",
                "Suggested_Owner":
                    "Data Analyst",
                "Acceptance_Criteria":
                    "Each page is mapped to its actual root-cause "
                    "family before remediation.",
                "Validation_Method":
                    "Review repaired page-level root-cause dataset",
            }
        )

    return actions


# ============================================================
# 4. SPRINT CLASSIFICATION
# ============================================================

def sprint_assignment(rank):

    try:
        rank = int(rank)

    except (TypeError, ValueError):
        return "Backlog"

    if rank <= 2:
        return "Sprint 1"

    if rank <= 4:
        return "Sprint 2"

    if rank <= 6:
        return "Sprint 3"

    return "Sprint 4 / Monitor"


# ============================================================
# 5. ACTION PRIORITY
# ============================================================

def action_priority(
    remediation_rank,
    action_code,
):

    try:
        rank = int(
            remediation_rank
        )

    except (TypeError, ValueError):
        rank = 99

    # Validation actions are deliberately first when evidence
    # is mixed or low confidence.
    if action_code.startswith(
        "VAL"
    ):
        return "P0 - Validate First"

    if rank <= 2:
        return "P1 - Critical"

    if rank <= 4:
        return "P2 - High"

    if rank <= 6:
        return "P3 - Medium"

    return "P4 - Lower"


# ============================================================
# 6. MAIN
# ============================================================

def main():

    print()
    print("=" * 82)
    print("PMB WIDYATAMA")
    print("STEP 13.1 - REMEDIATION BACKLOG BUILDER")
    print("=" * 82)

    templates = read_csv(
        INPUT_FILE
    )

    print(
        f"[INPUT] Templates : {len(templates)}"
    )

    backlog = []

    backlog_id = 0

    for template_row in templates:

        actions = build_actions(
            template_row
        )

        for action in actions:

            backlog_id += 1

            rank = template_row.get(
                "Remediation_Rank"
            )

            record = {

                "Backlog_ID":
                    f"REM-{backlog_id:03d}",

                "Remediation_Rank":
                    rank,

                "Sprint":
                    sprint_assignment(
                        rank
                    ),

                "Final_Page_Type":
                    template_row.get(
                        "Final_Page_Type"
                    ),

                "Page_Count":
                    template_row.get(
                        "Page_Count"
                    ),

                "Template_Priority_Score":
                    template_row.get(
                        "Template_Priority_Score"
                    ),

                "Template_Priority_Tier":
                    template_row.get(
                        "Priority_Tier"
                    ),

                "Diagnostic_Confidence":
                    template_row.get(
                        "Diagnostic_Confidence"
                    ),

                "Root_Cause_Pattern":
                    template_row.get(
                        "Root_Cause_Pattern"
                    ),

                "Primary_Root_Cause":
                    template_row.get(
                        "Dominant_Primary_Root_Cause"
                    ),

                "Secondary_Root_Cause":
                    template_row.get(
                        "Dominant_Secondary_Root_Cause"
                    ),

                "Baseline_Performance":
                    template_row.get(
                        "Median_Performance"
                    ),

                "Baseline_LCP_sec":
                    template_row.get(
                        "Median_Lab_LCP_sec"
                    ),

                "Baseline_TBT_ms":
                    template_row.get(
                        "Median_Lab_TBT_ms"
                    ),

                "Baseline_Page_Weight_MB":
                    template_row.get(
                        "Median_Page_Weight_MB"
                    ),

                "Action_Code":
                    action[
                        "Action_Code"
                    ],

                "Action_Priority":
                    action_priority(
                        rank,
                        action[
                            "Action_Code"
                        ],
                    ),

                "Technical_Action":
                    action[
                        "Technical_Action"
                    ],

                "Technical_Mechanism":
                    action[
                        "Technical_Mechanism"
                    ],

                "Expected_Primary_Metric":
                    action[
                        "Expected_Primary_Metric"
                    ],

                "Expected_Impact":
                    action[
                        "Expected_Impact"
                    ],

                "Implementation_Effort":
                    action[
                        "Implementation_Effort"
                    ],

                "Suggested_Owner":
                    action[
                        "Suggested_Owner"
                    ],

                "Acceptance_Criteria":
                    action[
                        "Acceptance_Criteria"
                    ],

                "Validation_Method":
                    action[
                        "Validation_Method"
                    ],

                # Filled after IT execution
                "Implementation_Status":
                    "Not Started",

                "Implementation_Notes":
                    "",

                "Actual_Owner":
                    "",

                "Implementation_Date":
                    "",

                "After_Test_Status":
                    "Not Tested",
            }

            backlog.append(
                record
            )

    # ========================================================
    # WRITE OUTPUT
    # ========================================================

    write_csv(
        OUTPUT_FILE,
        backlog
    )

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print()
    print("=" * 82)
    print("REMEDIATION BACKLOG SUMMARY")
    print("=" * 82)

    print(
        "Templates :",
        len(templates)
    )

    print(
        "Actions   :",
        len(backlog)
    )

    print()

    for template in templates:

        name = template.get(
            "Final_Page_Type"
        )

        count = sum(

            1

            for row in backlog

            if row.get(
                "Final_Page_Type"
            ) == name
        )

        print(
            f"{name:<24} : "
            f"{count} actions"
        )

    print()
    print("=" * 82)
    print("STEP 13.1 FINISHED")
    print("=" * 82)

    print()
    print("Output:")
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()