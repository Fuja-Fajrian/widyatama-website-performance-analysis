import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median


# ============================================================
# PMB WIDYATAMA
# STEP 13.3
# SPRINT 1 PILOT DEEP DIAGNOSTIC
#
# PURPOSE
# - NO new Lighthouse test
# - NO PSI request
# - Re-read existing raw Lighthouse JSON
# - Inspect 6 Sprint-1 pilot pages
# - Identify exact LCP evidence
# - Extract render-blocking requests
# - Extract biggest image opportunities
# - Build implementation-ready evidence
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

LOG_ROOT = (
    PROJECT_ROOT
    / "logs"
    / "root_cause_batch_before"
)

PILOT_INPUT = (
    PROCESSED_DIR
    / "sprint1_pilot_pages_before.csv"
)

DETAIL_OUTPUT = (
    PROCESSED_DIR
    / "sprint1_pilot_deep_diagnostic_before.csv"
)

RESOURCE_OUTPUT = (
    PROCESSED_DIR
    / "sprint1_pilot_resource_evidence_before.csv"
)

IMPLEMENTATION_OUTPUT = (
    PROCESSED_DIR
    / "sprint1_implementation_spec_before.csv"
)


# ============================================================
# 2. GENERIC HELPERS
# ============================================================

def safe_number(value):
    try:
        if value in (None, "", "None", "nan"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_get(data, *keys, default=None):

    current = data

    for key in keys:

        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def read_csv(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Input tidak ditemukan:\n{path}"
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
        for key in row:
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


def mode(values):

    values = [
        value
        for value in values
        if value not in (
            None,
            "",
            "None",
        )
    ]

    if not values:
        return None

    return Counter(
        values
    ).most_common(1)[0][0]


def numeric_median(values):

    values = [
        safe_number(value)
        for value in values
    ]

    values = [
        value
        for value in values
        if value is not None
    ]

    if not values:
        return None

    return round(
        median(values),
        2,
    )


# ============================================================
# 3. VALID LIGHTHOUSE JSON
# ============================================================

def load_valid_runs(page_id):

    page_dir = (
        LOG_ROOT
        / page_id
    )

    if not page_dir.exists():

        raise FileNotFoundError(
            f"Log folder tidak ditemukan:\n{page_dir}"
        )

    output = []

    files = sorted(
        page_dir.glob(
            "lighthouse_attempt_*.json"
        )
    )

    for path in files:

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

        except Exception:
            continue

        if data.get("runtimeError"):
            continue

        score = safe_get(
            data,
            "categories",
            "performance",
            "score",
        )

        if score is None:
            continue

        output.append(
            {
                "path": path,
                "data": data,
            }
        )

    return output[:3]


# ============================================================
# 4. FIND AUDIT
# ============================================================

def find_audit(
    audits,
    ids=None,
    title_terms=None,
):

    ids = ids or []
    title_terms = title_terms or []

    for audit_id in ids:

        if audit_id in audits:

            return (
                audit_id,
                audits[audit_id],
            )

    for audit_id, audit in audits.items():

        title = str(
            audit.get(
                "title",
                "",
            )
        ).lower()

        for term in title_terms:

            if term.lower() in title:

                return (
                    audit_id,
                    audit,
                )

    return None, {}


# ============================================================
# 5. RECURSIVE STRUCTURE WALKER
#
# Here recursion is used for DISCOVERY ONLY,
# not summing savings.
# ============================================================

def walk(obj):

    if isinstance(obj, dict):

        yield obj

        for value in obj.values():
            yield from walk(value)

    elif isinstance(obj, list):

        for item in obj:
            yield from walk(item)


# ============================================================
# 6. LCP DISCOVERY DETAIL
# ============================================================

def extract_lcp_discovery(audits):

    _, audit = find_audit(
        audits,
        ids=[
            "lcp-discovery-insight",
        ],
        title_terms=[
            "lcp request discovery",
        ],
    )

    result = {
        "LCP_Discovery_URL": None,
        "LCP_Discovery_Node_Label": None,
        "LCP_Discovery_Selector": None,
        "LCP_Discovery_Snippet": None,
        "Priority_Hinted": None,
        "Request_Discoverable": None,
        "Eagerly_Loaded": None,
    }

    if not audit:
        return result

    details = audit.get(
        "details"
    ) or {}

    # --------------------------------------------------------
    # Search every structured object because Lighthouse 13
    # can nest the request URL deeper than our old parser.
    # --------------------------------------------------------

    for obj in walk(details):

        if not isinstance(obj, dict):
            continue

        # Direct URL-like fields
        for key in (
            "url",
            "requestUrl",
            "resourceUrl",
        ):

            value = obj.get(key)

            if (
                result[
                    "LCP_Discovery_URL"
                ] is None

                and isinstance(
                    value,
                    str,
                )

                and value.startswith(
                    ("http://", "https://")
                )
            ):

                result[
                    "LCP_Discovery_URL"
                ] = value

        # Node information
        if obj.get("type") == "node":

            if (
                result[
                    "LCP_Discovery_Node_Label"
                ]
                is None
            ):
                result[
                    "LCP_Discovery_Node_Label"
                ] = obj.get(
                    "nodeLabel"
                )

            if (
                result[
                    "LCP_Discovery_Selector"
                ]
                is None
            ):
                result[
                    "LCP_Discovery_Selector"
                ] = obj.get(
                    "selector"
                )

            if (
                result[
                    "LCP_Discovery_Snippet"
                ]
                is None
            ):
                result[
                    "LCP_Discovery_Snippet"
                ] = obj.get(
                    "snippet"
                )

        # Checklist
        if obj.get("type") == "checklist":

            checks = (
                obj.get("items")
                or {}
            )

            result[
                "Priority_Hinted"
            ] = safe_get(
                checks,
                "priorityHinted",
                "value",
            )

            result[
                "Request_Discoverable"
            ] = safe_get(
                checks,
                "requestDiscoverable",
                "value",
            )

            result[
                "Eagerly_Loaded"
            ] = safe_get(
                checks,
                "eagerlyLoaded",
                "value",
            )

    return result


# ============================================================
# 7. LCP BREAKDOWN / NODE
# ============================================================

def extract_lcp_node(audits):

    _, audit = find_audit(
        audits,
        ids=[
            "lcp-breakdown-insight",
            "lcp-phases-insight",
        ],
        title_terms=[
            "lcp breakdown",
            "lcp phases",
        ],
    )

    result = {
        "LCP_Node_Label": None,
        "LCP_Node_Selector": None,
        "LCP_Node_Snippet": None,
    }

    if not audit:
        return result

    for obj in walk(
        audit.get(
            "details",
            {},
        )
    ):

        if (
            isinstance(obj, dict)
            and obj.get("type") == "node"
        ):

            if result[
                "LCP_Node_Label"
            ] is None:

                result[
                    "LCP_Node_Label"
                ] = obj.get(
                    "nodeLabel"
                )

                result[
                    "LCP_Node_Selector"
                ] = obj.get(
                    "selector"
                )

                result[
                    "LCP_Node_Snippet"
                ] = obj.get(
                    "snippet"
                )

    return result


# ============================================================
# 8. RENDER-BLOCKING REQUESTS
# ============================================================

def extract_render_blocking(
    audits,
):

    _, audit = find_audit(
        audits,
        ids=[
            "render-blocking-insight",
        ],
        title_terms=[
            "render-blocking",
        ],
    )

    requests = []

    if not audit:
        return requests

    seen = set()

    for obj in walk(
        audit.get(
            "details",
            {},
        )
    ):

        if not isinstance(obj, dict):
            continue

        url = (
            obj.get("url")
            or obj.get("requestUrl")
        )

        if (
            not isinstance(url, str)
            or not url.startswith(
                ("http://", "https://")
            )
        ):
            continue

        if url in seen:
            continue

        seen.add(url)

        requests.append(
            {
                "url": url,
                "wasted_ms":
                    (
                        obj.get(
                            "wastedMs"
                        )
                        or obj.get(
                            "duration"
                        )
                    ),
            }
        )

    return requests


# ============================================================
# 9. IMAGE DELIVERY ITEMS
# ============================================================

def extract_image_items(
    audits,
):

    _, audit = find_audit(
        audits,
        ids=[
            "image-delivery-insight",
        ],
        title_terms=[
            "improve image delivery",
        ],
    )

    if not audit:
        return []

    details = (
        audit.get("details")
        or {}
    )

    items = (
        details.get("items")
        or []
    )

    output = []

    for item in items:

        if not isinstance(item, dict):
            continue

        url = item.get("url")

        if not url:
            continue

        output.append(
            {
                "url": url,
                "total_bytes":
                    safe_number(
                        item.get(
                            "totalBytes"
                        )
                    ),

                "wasted_bytes":
                    safe_number(
                        item.get(
                            "wastedBytes"
                        )
                    ),
            }
        )

    output.sort(
        key=lambda row:
            row.get(
                "wasted_bytes"
            )
            or 0,
        reverse=True,
    )

    return output


# ============================================================
# 10. UNUSED CSS / JS
# ============================================================

def extract_unused_items(
    audits,
    audit_id,
):

    audit = audits.get(
        audit_id,
        {}
    )

    details = (
        audit.get("details")
        or {}
    )

    items = (
        details.get("items")
        or []
    )

    output = []

    for item in items:

        if not isinstance(item, dict):
            continue

        url = item.get("url")

        wasted = safe_number(
            item.get(
                "wastedBytes"
            )
        )

        if not url:
            continue

        output.append(
            {
                "url": url,
                "wasted_bytes": wasted,
            }
        )

    output.sort(
        key=lambda row:
            row.get(
                "wasted_bytes"
            )
            or 0,
        reverse=True,
    )

    return output


# ============================================================
# 11. BUILD RESOURCE ROWS
# ============================================================

def add_resource_rows(
    rows,
    pilot,
    run_number,
    resource_type,
    resources,
    limit=10,
):

    for rank, item in enumerate(
        resources[:limit],
        start=1,
    ):

        rows.append(
            {
                "Pilot_ID":
                    pilot["Pilot_ID"],

                "Page_ID":
                    pilot["Page_ID"],

                "Final_Page_Type":
                    pilot[
                        "Final_Page_Type"
                    ],

                "Run_Number":
                    run_number,

                "Resource_Type":
                    resource_type,

                "Resource_Rank":
                    rank,

                "Resource_URL":
                    item.get("url"),

                "Wasted_ms":
                    item.get(
                        "wasted_ms"
                    ),

                "Total_Bytes":
                    item.get(
                        "total_bytes"
                    ),

                "Wasted_Bytes":
                    item.get(
                        "wasted_bytes"
                    ),
            }
        )


# ============================================================
# 12. IMPLEMENTATION INTERPRETATION
# ============================================================

def build_implementation_spec(
    pilot,
    detail_rows,
):

    template = pilot[
        "Final_Page_Type"
    ]

    page_id = pilot[
        "Page_ID"
    ]

    urls = [
        row.get(
            "LCP_Discovery_URL"
        )
        for row
        in detail_rows
    ]

    selectors = [
        row.get(
            "LCP_Node_Selector"
        )
        or row.get(
            "LCP_Discovery_Selector"
        )
        for row
        in detail_rows
    ]

    labels = [
        row.get(
            "LCP_Node_Label"
        )
        or row.get(
            "LCP_Discovery_Node_Label"
        )
        for row
        in detail_rows
    ]

    dominant_url = mode(urls)
    dominant_selector = mode(selectors)
    dominant_label = mode(labels)

    if template == "Program":

        priority_false = sum(
            row.get(
                "Priority_Hinted"
            ) is False
            for row in detail_rows
        )

        discovery_false = sum(
            row.get(
                "Request_Discoverable"
            ) is False
            for row in detail_rows
        )

        eager_false = sum(
            row.get(
                "Eagerly_Loaded"
            ) is False
            for row in detail_rows
        )

        # IMPORTANT:
        # Do not recommend removing lazy loading unless
        # evidence confirms it.
        if eager_false >= 2:

            first_action = (
                "Inspect the confirmed LCP element for "
                "inappropriate lazy-loading before changing it."
            )

        elif discovery_false >= 2:

            first_action = (
                "Make the recurring LCP resource/component "
                "discoverable from initial HTML; inspect whether "
                "CSS background, JS injection, carousel logic, "
                "or delayed component rendering hides the request."
            )

        elif priority_false >= 2:

            first_action = (
                "Evaluate fetchpriority='high' on the confirmed "
                "critical LCP resource only."
            )

        else:

            first_action = (
                "Manual LCP request-chain inspection required "
                "before implementation."
            )

        return {
            "Pilot_ID":
                pilot["Pilot_ID"],

            "Page_ID":
                page_id,

            "Final_Page_Type":
                template,

            "Pilot_Role":
                pilot["Pilot_Role"],

            "URL":
                pilot["URL"],

            "Confirmed_LCP_URL":
                dominant_url,

            "Confirmed_LCP_Selector":
                dominant_selector,

            "Confirmed_LCP_Label":
                dominant_label,

            "Primary_Workstream":
                "LCP Resource Discovery",

            "Recommended_First_Action":
                first_action,

            "Do_Not_Do_Yet":
                (
                    "Do not remove lazy-loading globally; "
                    "do not assign fetchpriority='high' "
                    "to every image."
                ),

            "Validation_Target":
                (
                    "Reduce Resource Load Delay and total LCP "
                    "across 3 independent mobile Lighthouse runs."
                ),
        }

    # ========================================================
    # ADMISSION
    # ========================================================

    return {
        "Pilot_ID":
            pilot["Pilot_ID"],

        "Page_ID":
            page_id,

        "Final_Page_Type":
            template,

        "Pilot_Role":
            pilot["Pilot_Role"],

        "URL":
            pilot["URL"],

        "Confirmed_LCP_URL":
            dominant_url,

        "Confirmed_LCP_Selector":
            dominant_selector,

        "Confirmed_LCP_Label":
            dominant_label,

        "Primary_Workstream":
            "Critical Rendering Path",

        "Recommended_First_Action":
            (
                "Review the recurring render-blocking CSS/JS "
                "identified in the resource evidence table. "
                "Prioritize shared template/theme/plugin assets "
                "appearing across all three Admission pilots."
            ),

        "Do_Not_Do_Yet":
            (
                "Do not add defer/async blindly to all scripts; "
                "verify dependency and functional regression first."
            ),

        "Validation_Target":
            (
                "Reduce Element Render Delay, render-blocking "
                "opportunity, LCP and TBT across 3 independent runs."
            ),
    }


# ============================================================
# 13. MAIN
# ============================================================

def main():

    print()
    print("=" * 84)
    print("PMB WIDYATAMA")
    print("STEP 13.3 - SPRINT 1 PILOT DEEP DIAGNOSTIC")
    print("=" * 84)

    pilots = read_csv(
        PILOT_INPUT
    )

    print(
        "[INPUT] Pilot pages :",
        len(pilots),
    )

    detail_output = []
    resource_output = []
    implementation_output = []

    for pilot in pilots:

        page_id = pilot[
            "Page_ID"
        ]

        print()
        print("-" * 84)
        print(
            pilot[
                "Pilot_ID"
            ],
            page_id,
            pilot[
                "Final_Page_Type"
            ],
        )
        print("-" * 84)

        runs = load_valid_runs(
            page_id
        )

        print(
            "Valid raw JSON runs:",
            len(runs),
        )

        page_detail_rows = []

        for run_number, run in enumerate(
            runs,
            start=1,
        ):

            data = run[
                "data"
            ]

            audits = (
                data.get(
                    "audits"
                )
                or {}
            )

            discovery = (
                extract_lcp_discovery(
                    audits
                )
            )

            node = extract_lcp_node(
                audits
            )

            performance = safe_get(
                data,
                "categories",
                "performance",
                "score",
            )

            row = {
                "Pilot_ID":
                    pilot[
                        "Pilot_ID"
                    ],

                "Pilot_Role":
                    pilot[
                        "Pilot_Role"
                    ],

                "Page_ID":
                    page_id,

                "Final_Page_Type":
                    pilot[
                        "Final_Page_Type"
                    ],

                "URL":
                    pilot["URL"],

                "Run_Number":
                    run_number,

                "JSON_File":
                    str(
                        run[
                            "path"
                        ].relative_to(
                            PROJECT_ROOT
                        )
                    ),

                "Fetch_Time":
                    data.get(
                        "fetchTime"
                    ),

                "Performance":
                    (
                        round(
                            performance * 100
                        )
                        if performance
                        is not None
                        else None
                    ),

                "LCP_ms":
                    safe_get(
                        audits,
                        "largest-contentful-paint",
                        "numericValue",
                    ),

                "TBT_ms":
                    safe_get(
                        audits,
                        "total-blocking-time",
                        "numericValue",
                    ),

                **discovery,
                **node,
            }

            page_detail_rows.append(
                row
            )

            detail_output.append(
                row
            )

            # --------------------------------------------
            # Resource evidence
            # --------------------------------------------

            add_resource_rows(
                resource_output,
                pilot,
                run_number,
                "Render Blocking",
                extract_render_blocking(
                    audits
                ),
                15,
            )

            add_resource_rows(
                resource_output,
                pilot,
                run_number,
                "Image Delivery",
                extract_image_items(
                    audits
                ),
                10,
            )

            add_resource_rows(
                resource_output,
                pilot,
                run_number,
                "Unused CSS",
                extract_unused_items(
                    audits,
                    "unused-css-rules",
                ),
                10,
            )

            add_resource_rows(
                resource_output,
                pilot,
                run_number,
                "Unused JavaScript",
                extract_unused_items(
                    audits,
                    "unused-javascript",
                ),
                10,
            )

        implementation_output.append(
            build_implementation_spec(
                pilot,
                page_detail_rows,
            )
        )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        DETAIL_OUTPUT,
        detail_output,
    )

    write_csv(
        RESOURCE_OUTPUT,
        resource_output,
    )

    write_csv(
        IMPLEMENTATION_OUTPUT,
        implementation_output,
    )

    print()
    print("=" * 84)
    print("STEP 13.3 SUMMARY")
    print("=" * 84)

    print(
        "Pilot pages          :",
        len(pilots),
    )

    print(
        "Run detail rows      :",
        len(detail_output),
    )

    print(
        "Resource evidence    :",
        len(resource_output),
    )

    print(
        "Implementation specs :",
        len(implementation_output),
    )

    print()
    print("Outputs:")
    print(DETAIL_OUTPUT)
    print(RESOURCE_OUTPUT)
    print(IMPLEMENTATION_OUTPUT)

    print()
    print("STEP 13.3 STATUS: COMPLETE")
    print()


if __name__ == "__main__":
    main()