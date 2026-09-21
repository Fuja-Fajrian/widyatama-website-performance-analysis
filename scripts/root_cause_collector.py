import csv
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from statistics import median

import requests
from dotenv import load_dotenv


# ============================================================
# PMB WIDYATAMA
# ROOT CAUSE COLLECTOR
#
# STEP 12B.2
# 3-RUN STABILITY TEST
#
# CURRENT SCOPE:
# - Homepage P001
# - Mobile only
# - 3 PageSpeed / Lighthouse runs
# - CrUX Field Data
# - Lighthouse Lab Data
# - LCP Breakdown
# - LCP Resource Discovery
# - Root Cause Diagnostics
# - Median Summary
# - Dominant LCP Element
# - Dominant Root Cause
# ============================================================


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
LOG_DIR = PROJECT_ROOT / "logs"

DATA_PROCESSED.mkdir(
    parents=True,
    exist_ok=True,
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 2. ENVIRONMENT
# ============================================================

load_dotenv(
    PROJECT_ROOT / ".env"
)

API_KEY = os.getenv(
    "PAGESPEED_API_KEY"
)

if not API_KEY:

    raise RuntimeError(
        "\nPAGESPEED_API_KEY tidak ditemukan.\n"
        "Pastikan .env berada di root project:\n"
        f"{PROJECT_ROOT}\n"
    )


# ============================================================
# 3. API ENDPOINT
# ============================================================

PSI_ENDPOINT = (
    "https://www.googleapis.com/"
    "pagespeedonline/v5/runPagespeed"
)


# ============================================================
# 4. TEST CONFIGURATION
# ============================================================

PAGE_ID = "P001"

TEST_URL = (
    "https://pmb.widyatama.ac.id/"
)

DEVICE = "mobile"

NUMBER_OF_RUNS = 3

WAIT_BETWEEN_RUNS_SECONDS = 8


# ============================================================
# 5. OUTPUT FILES
# ============================================================

RUNS_OUTPUT_CSV = (
    DATA_PROCESSED
    / "root_cause_homepage_3runs.csv"
)

SUMMARY_OUTPUT_CSV = (
    DATA_PROCESSED
    / "root_cause_homepage_summary.csv"
)


# ============================================================
# 6. GENERIC HELPERS
# ============================================================

def safe_get(
    data,
    *keys,
    default=None,
):

    current = data

    for key in keys:

        if not isinstance(
            current,
            dict,
        ):
            return default

        current = current.get(
            key
        )

        if current is None:
            return default

    return current


def as_number(value):

    try:

        if value is None:
            return None

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def round_or_none(
    value,
    digits=2,
):

    value = as_number(
        value
    )

    if value is None:
        return None

    return round(
        value,
        digits,
    )


def yes_no(value):

    if value is True:
        return "Yes"

    if value is False:
        return "No"

    return None


def bytes_to_mb(value):

    value = as_number(
        value
    )

    if value is None:
        return None

    return round(
        value / 1024 / 1024,
        2,
    )


def median_numeric(
    rows,
    field_name,
    digits=2,
):

    values = []

    for row in rows:

        value = as_number(
            row.get(
                field_name
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


def most_common_nonempty(
    values,
):

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
        return None

    counter = Counter(
        clean
    )

    return counter.most_common(
        1
    )[0][0]


# ============================================================
# 7. PAGESPEED REQUEST
# ============================================================

def request_pagespeed(
    url,
    strategy="mobile",
    retries=3,
):

    params = {

        "url": url,

        "strategy": strategy,

        "category": "performance",

        "key": API_KEY,
    }

    for attempt in range(
        1,
        retries + 1,
    ):

        try:

            print(
                f"[INFO] PSI request "
                f"attempt {attempt}/{retries}"
            )

            response = requests.get(

                PSI_ENDPOINT,

                params=params,

                timeout=180,
            )

            if (
                response.status_code
                == 200
            ):

                return response.json()

            print(
                "[WARNING] HTTP",
                response.status_code,
            )

            if response.status_code in {

                429,
                500,
                502,
                503,
                504,
            }:

                time.sleep(
                    5 * attempt
                )

                continue

            try:

                error_message = (
                    response.json()
                )

            except Exception:

                error_message = (
                    response.text
                )

            raise RuntimeError(
                "PageSpeed API error:\n"
                f"{error_message}"
            )

        except requests.RequestException as exc:

            print(
                "[WARNING] Network error:",
                exc,
            )

            if attempt == retries:
                raise

            time.sleep(
                5 * attempt
            )

    raise RuntimeError(
        "PageSpeed API request gagal."
    )


# ============================================================
# 8. AUDIT FINDER
# ============================================================

def find_audit(
    audits,
    id_candidates=None,
    title_contains=None,
):

    id_candidates = (
        id_candidates
        or []
    )

    title_contains = (
        title_contains
        or []
    )

    # --------------------------------------------------------
    # SEARCH BY ID
    # --------------------------------------------------------

    for audit_id in id_candidates:

        audit = audits.get(
            audit_id
        )

        if audit:

            return (
                audit_id,
                audit,
            )

    # --------------------------------------------------------
    # FALLBACK BY TITLE
    # --------------------------------------------------------

    for (
        audit_id,
        audit,
    ) in audits.items():

        title = str(
            audit.get(
                "title",
                "",
            )
        ).lower()

        for phrase in title_contains:

            if (
                phrase.lower()
                in title
            ):

                return (
                    audit_id,
                    audit,
                )

    return (
        None,
        {},
    )


# ============================================================
# 9. BASIC NUMERIC AUDIT
# ============================================================

def extract_numeric_audit(
    audits,
    audit_id,
):

    audit = audits.get(
        audit_id,
        {},
    )

    return round_or_none(
        audit.get(
            "numericValue"
        )
    )


# ============================================================
# 10. RECURSIVE JSON SUM
# ============================================================

def recursively_sum_key(
    obj,
    target_key,
):

    total = 0.0
    found = False

    if isinstance(
        obj,
        dict,
    ):

        for (
            key,
            value,
        ) in obj.items():

            if (
                key
                == target_key
            ):

                number = as_number(
                    value
                )

                if (
                    number
                    is not None
                ):

                    total += number
                    found = True

            (
                subtotal,
                subfound,
            ) = recursively_sum_key(
                value,
                target_key,
            )

            if subfound:

                total += subtotal
                found = True

    elif isinstance(
        obj,
        list,
    ):

        for item in obj:

            (
                subtotal,
                subfound,
            ) = recursively_sum_key(
                item,
                target_key,
            )

            if subfound:

                total += subtotal
                found = True

    return (
        total,
        found,
    )


# ============================================================
# 11. BYTE SAVINGS
# ============================================================

def audit_savings_bytes(
    audit,
):

    if not audit:
        return None

    details = (
        audit.get(
            "details"
        )
        or {}
    )

    direct_candidates = [

        details.get(
            "overallSavingsBytes"
        ),

        safe_get(
            details,
            "debugData",
            "wastedBytes",
        ),
    ]

    for candidate in direct_candidates:

        number = as_number(
            candidate
        )

        if (
            number
            is not None
        ):

            return round(
                number
            )

    (
        total,
        found,
    ) = recursively_sum_key(

        details.get(
            "items",
            [],
        ),

        "wastedBytes",
    )

    if found:

        return round(
            total
        )

    numeric_unit = str(
        audit.get(
            "numericUnit",
            "",
        )
    ).lower()

    if (
        "byte"
        in numeric_unit
    ):

        number = as_number(
            audit.get(
                "numericValue"
            )
        )

        if (
            number
            is not None
        ):

            return round(
                number
            )

    return None


# ============================================================
# 12. TIME SAVINGS
#
# IMPORTANT:
# Tidak menjumlahkan wastedMs antar resource
# karena nilai dapat overlap.
# ============================================================

def audit_savings_ms(
    audit,
):

    if not audit:
        return None

    display_value = str(
        audit.get(
            "displayValue",
            "",
        )
    )

    # --------------------------------------------------------
    # "Est savings of 2,030 ms"
    # --------------------------------------------------------

    match_ms = re.search(

        r"([0-9][0-9,\.\s\u00A0]*)"
        r"\s*ms",

        display_value,

        re.IGNORECASE,
    )

    if match_ms:

        raw = (
            match_ms
            .group(1)
            .replace(
                ",",
                "",
            )
            .replace(
                " ",
                "",
            )
            .replace(
                "\u00A0",
                "",
            )
        )

        try:

            return round(
                float(raw),
                2,
            )

        except ValueError:

            pass

    # --------------------------------------------------------
    # Seconds fallback
    # --------------------------------------------------------

    match_seconds = re.search(

        r"([0-9]+(?:\.[0-9]+)?)"
        r"\s*s",

        display_value,

        re.IGNORECASE,
    )

    if match_seconds:

        try:

            return round(
                float(
                    match_seconds.group(1)
                )
                * 1000,
                2,
            )

        except ValueError:

            pass

    details = (
        audit.get(
            "details"
        )
        or {}
    )

    overall = as_number(
        details.get(
            "overallSavingsMs"
        )
    )

    if (
        overall
        is not None
    ):

        return round(
            overall,
            2,
        )

    metric_savings = (
        audit.get(
            "metricSavings"
        )
        or {}
    )

    candidates = []

    for metric in [

        "LCP",
        "FCP",
        "TBT",
        "INP",
    ]:

        value = as_number(
            metric_savings.get(
                metric
            )
        )

        if (
            value
            is not None
            and value > 0
        ):

            candidates.append(
                value
            )

    if candidates:

        return round(
            max(
                candidates
            ),
            2,
        )

    return None


# ============================================================
# 13. CRUX HELPERS
# ============================================================

def get_metric_percentile(
    metrics,
    metric_name,
):

    return (
        metrics
        .get(
            metric_name,
            {},
        )
        .get(
            "percentile"
        )
    )


def get_metric_category(
    metrics,
    metric_name,
):

    return (
        metrics
        .get(
            metric_name,
            {},
        )
        .get(
            "category"
        )
    )


# ============================================================
# 14. CWV STATUS
# ============================================================

def derive_cwv_status(
    lcp_ms,
    inp_ms,
    cls_value,
):

    if (
        lcp_ms is None
        or inp_ms is None
        or cls_value is None
    ):

        return "Incomplete"

    if (

        lcp_ms <= 2500

        and inp_ms <= 200

        and cls_value <= 0.10
    ):

        return "Passed"

    return "Failed"


# ============================================================
# 15. PARSE FIELD DATA
# ============================================================

def parse_field_data(
    data,
):

    url_exp = (
        data.get(
            "loadingExperience"
        )
        or {}
    )

    origin_exp = (
        data.get(
            "originLoadingExperience"
        )
        or {}
    )

    url_metrics = (
        url_exp.get(
            "metrics"
        )
        or {}
    )

    origin_metrics = (
        origin_exp.get(
            "metrics"
        )
        or {}
    )

    # URL-level preferred
    if url_metrics:

        experience = (
            url_exp
        )

        metrics = (
            url_metrics
        )

        level = "URL"

    # Origin fallback
    elif origin_metrics:

        experience = (
            origin_exp
        )

        metrics = (
            origin_metrics
        )

        level = "Origin"

    else:

        return {

            "Field_Data_Available":
                "No",

            "Field_Data_Level":
                "Not Available",

            "Field_Overall_Category":
                None,

            "CWV_Status":
                "Not Available",

            "Field_LCP_ms":
                None,

            "Field_INP_ms":
                None,

            "Field_CLS":
                None,

            "Field_FCP_ms":
                None,

            "Field_TTFB_ms":
                None,
        }

    lcp = get_metric_percentile(

        metrics,

        "LARGEST_CONTENTFUL_PAINT_MS",
    )

    inp = get_metric_percentile(

        metrics,

        "INTERACTION_TO_NEXT_PAINT",
    )

    cls_raw = get_metric_percentile(

        metrics,

        "CUMULATIVE_LAYOUT_SHIFT_SCORE",
    )

    fcp = get_metric_percentile(

        metrics,

        "FIRST_CONTENTFUL_PAINT_MS",
    )

    ttfb = get_metric_percentile(

        metrics,

        "EXPERIMENTAL_TIME_TO_FIRST_BYTE",
    )

    cls = (

        cls_raw / 100

        if (
            cls_raw
            is not None
        )

        else None
    )

    return {

        "Field_Data_Available":
            "Yes",

        "Field_Data_Level":
            level,

        "Field_Overall_Category":
            experience.get(
                "overall_category"
            ),

        "CWV_Status":
            derive_cwv_status(
                lcp,
                inp,
                cls,
            ),

        "Field_LCP_ms":
            lcp,

        "Field_INP_ms":
            inp,

        "Field_CLS":
            cls,

        "Field_FCP_ms":
            fcp,

        "Field_TTFB_ms":
            ttfb,
    }


# ============================================================
# 16. LCP BREAKDOWN
# ============================================================

def extract_lcp_breakdown(
    audits,
):

    (
        audit_id,
        audit,
    ) = find_audit(

        audits,

        id_candidates=[

            "lcp-breakdown-insight",

            "lcp-phases-insight",
        ],

        title_contains=[

            "lcp breakdown",

            "lcp phases",
        ],
    )

    result = {

        "LCP_Breakdown_Audit_ID":
            audit_id,

        "LCP_TTFB_ms":
            None,

        "LCP_Resource_Load_Delay_ms":
            None,

        "LCP_Resource_Load_Duration_ms":
            None,

        "LCP_Element_Render_Delay_ms":
            None,

        "LCP_Element":
            None,

        "LCP_Selector":
            None,

        "LCP_Node_Label":
            None,
    }

    if not audit:
        return result

    items = safe_get(

        audit,

        "details",

        "items",

        default=[],
    )

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        if (
            item.get(
                "type"
            )
            == "table"
        ):

            for row in item.get(
                "items",
                [],
            ):

                subpart = str(
                    row.get(
                        "subpart",
                        "",
                    )
                ).lower()

                label = str(
                    row.get(
                        "label",
                        "",
                    )
                ).lower()

                duration = (
                    round_or_none(
                        row.get(
                            "duration"
                        )
                    )
                )

                compact = (
                    subpart
                    .replace(
                        " ",
                        "",
                    )
                    +
                    label
                    .replace(
                        " ",
                        "",
                    )
                )

                if (
                    "timetofirstbyte"
                    in compact
                ):

                    result[
                        "LCP_TTFB_ms"
                    ] = duration

                elif (
                    "resourceloaddelay"
                    in compact
                ):

                    result[
                        "LCP_Resource_Load_Delay_ms"
                    ] = duration

                elif (
                    "resourceloadduration"
                    in compact
                ):

                    result[
                        "LCP_Resource_Load_Duration_ms"
                    ] = duration

                elif (
                    "elementrenderdelay"
                    in compact
                ):

                    result[
                        "LCP_Element_Render_Delay_ms"
                    ] = duration

        # ----------------------------------------------------
        # NODE
        # ----------------------------------------------------

        if (
            item.get(
                "type"
            )
            == "node"
        ):

            result[
                "LCP_Element"
            ] = item.get(
                "snippet"
            )

            result[
                "LCP_Selector"
            ] = item.get(
                "selector"
            )

            result[
                "LCP_Node_Label"
            ] = item.get(
                "nodeLabel"
            )

    return result


# ============================================================
# 17. DETERMINE DOMINANT LCP PHASE
# ============================================================

def determine_dominant_lcp_phase(
    row,
):

    phases = {

        "TTFB":
            as_number(
                row.get(
                    "LCP_TTFB_ms"
                )
            ),

        "Resource Load Delay":
            as_number(
                row.get(
                    "LCP_Resource_Load_Delay_ms"
                )
            ),

        "Resource Load Duration":
            as_number(
                row.get(
                    "LCP_Resource_Load_Duration_ms"
                )
            ),

        "Element Render Delay":
            as_number(
                row.get(
                    "LCP_Element_Render_Delay_ms"
                )
            ),
    }

    valid = {

        key: value

        for (
            key,
            value,
        ) in phases.items()

        if (
            value
            is not None
        )
    }

    if not valid:

        return (
            None,
            None,
        )

    dominant_phase = max(

        valid,

        key=valid.get,
    )

    return (

        dominant_phase,

        round(
            valid[
                dominant_phase
            ],
            2,
        ),
    )


# ============================================================
# 18. LCP RESOURCE DISCOVERY
# ============================================================

def extract_lcp_discovery(
    audits,
):

    (
        audit_id,
        audit,
    ) = find_audit(

        audits,

        id_candidates=[

            "lcp-discovery-insight",
        ],

        title_contains=[

            "lcp request discovery",
        ],
    )

    result = {

        "LCP_Discovery_Audit_ID":
            audit_id,

        "LCP_FetchPriority_High":
            None,

        "LCP_Discoverable_Initial_HTML":
            None,

        "LCP_Lazy_Loaded":
            None,

        "LCP_Discovery_Element":
            None,

        "LCP_Resource_URL":
            None,
    }

    if not audit:
        return result

    items = safe_get(

        audit,

        "details",

        "items",

        default=[],
    )

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        # ----------------------------------------------------
        # CHECKLIST
        # ----------------------------------------------------

        if (
            item.get(
                "type"
            )
            == "checklist"
        ):

            checks = (
                item.get(
                    "items",
                    {},
                )
            )

            priority = safe_get(

                checks,

                "priorityHinted",

                "value",
            )

            discoverable = safe_get(

                checks,

                "requestDiscoverable",

                "value",
            )

            eagerly_loaded = safe_get(

                checks,

                "eagerlyLoaded",

                "value",
            )

            result[
                "LCP_FetchPriority_High"
            ] = yes_no(
                priority
            )

            result[
                "LCP_Discoverable_Initial_HTML"
            ] = yes_no(
                discoverable
            )

            if (
                eagerly_loaded
                is not None
            ):

                result[
                    "LCP_Lazy_Loaded"
                ] = yes_no(
                    not eagerly_loaded
                )

        # ----------------------------------------------------
        # NODE
        # ----------------------------------------------------

        if (
            item.get(
                "type"
            )
            == "node"
        ):

            snippet = (
                item.get(
                    "snippet"
                )
                or ""
            )

            result[
                "LCP_Discovery_Element"
            ] = snippet

            src_match = re.search(

                r'''src=["']([^"']+)["']''',

                snippet,

                re.IGNORECASE,
            )

            if src_match:

                result[
                    "LCP_Resource_URL"
                ] = (
                    src_match.group(
                        1
                    )
                )

    return result


# ============================================================
# 19. DIAGNOSTICS
# ============================================================

def parse_diagnostics(
    audits,
):

    result = {}

    # --------------------------------------------------------
    # IMAGE DELIVERY
    # --------------------------------------------------------

    (
        image_id,
        image_audit,
    ) = find_audit(

        audits,

        id_candidates=[

            "image-delivery-insight",

            "modern-image-formats",

            "uses-optimized-images",
        ],

        title_contains=[

            "improve image delivery",
        ],
    )

    result[
        "Image_Audit_ID"
    ] = image_id

    result[
        "Image_Savings_Bytes"
    ] = audit_savings_bytes(
        image_audit
    )

    # --------------------------------------------------------
    # RENDER BLOCKING
    # --------------------------------------------------------

    (
        render_id,
        render_audit,
    ) = find_audit(

        audits,

        id_candidates=[

            "render-blocking-insight",

            "render-blocking-resources",
        ],

        title_contains=[

            "render-blocking",
        ],
    )

    result[
        "Render_Blocking_Audit_ID"
    ] = render_id

    result[
        "Render_Blocking_Savings_ms"
    ] = audit_savings_ms(
        render_audit
    )

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    (
        cache_id,
        cache_audit,
    ) = find_audit(

        audits,

        id_candidates=[

            "cache-insight",

            "use-cache-insight",

            "uses-long-cache-ttl",
        ],

        title_contains=[

            "cache lifetime",

            "efficient cache",
        ],
    )

    result[
        "Cache_Audit_ID"
    ] = cache_id

    result[
        "Cache_Savings_Bytes"
    ] = audit_savings_bytes(
        cache_audit
    )

    # --------------------------------------------------------
    # UNUSED CSS
    # --------------------------------------------------------

    unused_css = audits.get(
        "unused-css-rules",
        {},
    )

    result[
        "Unused_CSS_Bytes"
    ] = audit_savings_bytes(
        unused_css
    )

    # --------------------------------------------------------
    # UNUSED JS
    # --------------------------------------------------------

    unused_js = audits.get(
        "unused-javascript",
        {},
    )

    result[
        "Unused_JS_Bytes"
    ] = audit_savings_bytes(
        unused_js
    )

    # --------------------------------------------------------
    # PAGE WEIGHT
    # --------------------------------------------------------

    total_weight = audits.get(
        "total-byte-weight",
        {},
    )

    result[
        "Total_Page_Weight_Bytes"
    ] = round_or_none(

        total_weight.get(
            "numericValue"
        ),

        0,
    )

    # --------------------------------------------------------
    # MAIN THREAD WORK
    # --------------------------------------------------------

    main_thread = audits.get(
        "mainthread-work-breakdown",
        {},
    )

    result[
        "Main_Thread_Work_ms"
    ] = round_or_none(

        main_thread.get(
            "numericValue"
        )
    )

    # --------------------------------------------------------
    # LONG TASKS
    # --------------------------------------------------------

    long_tasks = audits.get(
        "long-tasks",
        {},
    )

    long_task_items = safe_get(

        long_tasks,

        "details",

        "items",

        default=[],
    )

    result[
        "Long_Task_Count"
    ] = (

        len(
            long_task_items
        )

        if isinstance(
            long_task_items,
            list,
        )

        else None
    )

    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------

    debug = audits.get(
        "diagnostics",
        {},
    )

    debug_items = safe_get(

        debug,

        "details",

        "items",

        default=[],
    )

    if (
        isinstance(
            debug_items,
            list,
        )
        and debug_items
    ):

        debug_item = (
            debug_items[0]
        )

    else:

        debug_item = {}

    result[
        "Request_Count"
    ] = debug_item.get(
        "numRequests"
    )

    result[
        "Script_Count"
    ] = debug_item.get(
        "numScripts"
    )

    result[
        "Stylesheet_Count"
    ] = debug_item.get(
        "numStylesheets"
    )

    result[
        "Font_Count"
    ] = debug_item.get(
        "numFonts"
    )

    result[
        "Tasks_Over_50ms"
    ] = debug_item.get(
        "numTasksOver50ms"
    )

    result[
        "Tasks_Over_100ms"
    ] = debug_item.get(
        "numTasksOver100ms"
    )

    # --------------------------------------------------------
    # LAB SERVER RESPONSE
    # --------------------------------------------------------

    server_response = audits.get(
        "server-response-time",
        {},
    )

    result[
        "Lab_Server_Response_ms"
    ] = round_or_none(

        server_response.get(
            "numericValue"
        )
    )

    return result


# ============================================================
# 20. ROOT CAUSE CLASSIFICATION
# ============================================================

def classify_root_causes(
    row,
):

    issues = []

    ttfb = as_number(
        row.get(
            "LCP_TTFB_ms"
        )
    )

    load_delay = as_number(
        row.get(
            "LCP_Resource_Load_Delay_ms"
        )
    )

    load_duration = as_number(
        row.get(
            "LCP_Resource_Load_Duration_ms"
        )
    )

    render_delay = as_number(
        row.get(
            "LCP_Element_Render_Delay_ms"
        )
    )

    lazy_loaded = row.get(
        "LCP_Lazy_Loaded"
    )

    fetch_priority = row.get(
        "LCP_FetchPriority_High"
    )

    discoverable = row.get(
        "LCP_Discoverable_Initial_HTML"
    )

    image_savings = as_number(
        row.get(
            "Image_Savings_Bytes"
        )
    )

    render_savings = as_number(
        row.get(
            "Render_Blocking_Savings_ms"
        )
    )

    field_ttfb = as_number(
        row.get(
            "Field_TTFB_ms"
        )
    )

    page_weight = as_number(
        row.get(
            "Total_Page_Weight_Bytes"
        )
    )

    (
        dominant_phase,
        dominant_value,
    ) = determine_dominant_lcp_phase(
        row
    )

    # --------------------------------------------------------
    # PRIMARY ROOT CAUSE
    # --------------------------------------------------------

    if (

        dominant_phase
        == "Element Render Delay"

        and render_delay
        is not None

        and render_delay > 1000
    ):

        if (

            render_savings
            is not None

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

        lazy_loaded == "Yes"

        or discoverable == "No"

        or (
            load_delay
            is not None

            and load_delay > 1000
        )
    ):

        issues.append(
            "Late LCP Resource Discovery"
        )

    elif (

        load_duration
        is not None

        and load_duration > 1000
    ):

        issues.append(
            "Slow LCP Resource Download"
        )

    elif (

        ttfb
        is not None

        and ttfb > 1800
    ):

        issues.append(
            "Slow Lab Server Response"
        )

    # --------------------------------------------------------
    # SUPPORTING ISSUES
    # --------------------------------------------------------

    if (

        image_savings
        is not None

        and image_savings
        > 500_000
    ):

        issues.append(
            "Unoptimized Image Delivery"
        )

    if (

        page_weight
        is not None

        and page_weight
        > 5_000_000
    ):

        issues.append(
            "Excessive Page Weight"
        )

    if (

        field_ttfb
        is not None

        and field_ttfb > 1800
    ):

        issues.append(
            "Slow Real-User "
            "Server Response / TTFB"
        )

    if (

        render_savings
        is not None

        and render_savings > 500

        and (
            "High Element Render Delay / "
            "Render-Blocking Pipeline"
            not in issues
        )
    ):

        issues.append(
            "Render-Blocking Resources"
        )

    if (

        fetch_priority == "No"

        and lazy_loaded != "Yes"

        and discoverable != "No"
    ):

        issues.append(
            "Missing LCP Fetch Priority"
        )

    issues = list(
        dict.fromkeys(
            issues
        )
    )

    if not issues:

        return (

            "No Dominant Root Cause Detected",

            None,

            dominant_phase,

            dominant_value,
        )

    return (

        issues[0],

        (
            issues[1]
            if len(issues) > 1
            else None
        ),

        dominant_phase,

        dominant_value,
    )


# ============================================================
# 21. PARSE ONE RUN
# ============================================================

def parse_pagespeed(
    run_number,
    page_id,
    url,
    device,
    data,
):

    lighthouse = (
        data.get(
            "lighthouseResult"
        )
        or {}
    )

    audits = (
        lighthouse.get(
            "audits"
        )
        or {}
    )

    categories = (
        lighthouse.get(
            "categories"
        )
        or {}
    )

    performance_score = safe_get(

        categories,

        "performance",

        "score",
    )

    if (
        performance_score
        is not None
    ):

        performance_score = round(
            performance_score
            * 100
        )

    row = {

        "Run_Number":
            run_number,

        "Page_ID":
            page_id,

        "URL":
            url,

        "Device":
            device,

        "Test_Date":
            lighthouse.get(
                "fetchTime"
            ),

        "Lighthouse_Version":
            lighthouse.get(
                "lighthouseVersion"
            ),

        "Performance":
            performance_score,

        "Lab_FCP_ms":
            extract_numeric_audit(
                audits,
                "first-contentful-paint",
            ),

        "Lab_LCP_ms":
            extract_numeric_audit(
                audits,
                "largest-contentful-paint",
            ),

        "Lab_TBT_ms":
            extract_numeric_audit(
                audits,
                "total-blocking-time",
            ),

        "Lab_CLS":
            extract_numeric_audit(
                audits,
                "cumulative-layout-shift",
            ),

        "Lab_Speed_Index_ms":
            extract_numeric_audit(
                audits,
                "speed-index",
            ),
    }

    # CrUX
    row.update(
        parse_field_data(
            data
        )
    )

    # LCP Breakdown
    row.update(
        extract_lcp_breakdown(
            audits
        )
    )

    # LCP Discovery
    discovery = (
        extract_lcp_discovery(
            audits
        )
    )

    row.update(
        discovery
    )

    if (

        not row.get(
            "LCP_Element"
        )

        and discovery.get(
            "LCP_Discovery_Element"
        )
    ):

        row[
            "LCP_Element"
        ] = discovery[
            "LCP_Discovery_Element"
        ]

    # Diagnostics
    row.update(
        parse_diagnostics(
            audits
        )
    )

    (
        primary,
        secondary,
        dominant_phase,
        dominant_duration,
    ) = classify_root_causes(
        row
    )

    row[
        "Dominant_LCP_Phase"
    ] = dominant_phase

    row[
        "Dominant_LCP_Phase_ms"
    ] = dominant_duration

    row[
        "Primary_Root_Cause"
    ] = primary

    row[
        "Secondary_Root_Cause"
    ] = secondary

    return row


# ============================================================
# 22. SAVE MULTIPLE ROWS
# ============================================================

def write_rows_csv(
    rows,
    output_path,
):

    if not rows:
        return

    with open(

        output_path,

        "w",

        newline="",

        encoding="utf-8-sig",

    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# 23. BUILD 3-RUN SUMMARY
# ============================================================

def build_summary(
    rows,
):

    dominant_lcp_resource = (
        most_common_nonempty(
            [
                row.get(
                    "LCP_Resource_URL"
                )
                for row in rows
            ]
        )
    )

    dominant_lcp_label = (
        most_common_nonempty(
            [
                row.get(
                    "LCP_Node_Label"
                )
                for row in rows
            ]
        )
    )

    dominant_phase = (
        most_common_nonempty(
            [
                row.get(
                    "Dominant_LCP_Phase"
                )
                for row in rows
            ]
        )
    )

    dominant_primary_cause = (
        most_common_nonempty(
            [
                row.get(
                    "Primary_Root_Cause"
                )
                for row in rows
            ]
        )
    )

    dominant_secondary_cause = (
        most_common_nonempty(
            [
                row.get(
                    "Secondary_Root_Cause"
                )
                for row in rows
            ]
        )
    )

    lazy_frequency = sum(

        1

        for row in rows

        if (
            row.get(
                "LCP_Lazy_Loaded"
            )
            == "Yes"
        )
    )

    missing_priority_frequency = sum(

        1

        for row in rows

        if (
            row.get(
                "LCP_FetchPriority_High"
            )
            == "No"
        )
    )

    undiscoverable_frequency = sum(

        1

        for row in rows

        if (
            row.get(
                "LCP_Discoverable_Initial_HTML"
            )
            == "No"
        )
    )

    summary = {

        "Page_ID":
            PAGE_ID,

        "URL":
            TEST_URL,

        "Device":
            DEVICE,

        "Runs_Completed":
            len(rows),

        # ----------------------------------------------------
        # MEDIAN LAB METRICS
        # ----------------------------------------------------

        "Median_Performance":
            median_numeric(
                rows,
                "Performance",
            ),

        "Median_Lab_FCP_ms":
            median_numeric(
                rows,
                "Lab_FCP_ms",
            ),

        "Median_Lab_LCP_ms":
            median_numeric(
                rows,
                "Lab_LCP_ms",
            ),

        "Median_Lab_TBT_ms":
            median_numeric(
                rows,
                "Lab_TBT_ms",
            ),

        "Median_Lab_CLS":
            median_numeric(
                rows,
                "Lab_CLS",
                digits=4,
            ),

        "Median_Speed_Index_ms":
            median_numeric(
                rows,
                "Lab_Speed_Index_ms",
            ),

        # ----------------------------------------------------
        # FIELD DATA
        # ----------------------------------------------------

        "Field_Data_Level":
            most_common_nonempty(
                [
                    row.get(
                        "Field_Data_Level"
                    )
                    for row in rows
                ]
            ),

        "CWV_Status":
            most_common_nonempty(
                [
                    row.get(
                        "CWV_Status"
                    )
                    for row in rows
                ]
            ),

        "Field_LCP_ms":
            median_numeric(
                rows,
                "Field_LCP_ms",
            ),

        "Field_INP_ms":
            median_numeric(
                rows,
                "Field_INP_ms",
            ),

        "Field_CLS":
            median_numeric(
                rows,
                "Field_CLS",
                digits=4,
            ),

        "Field_FCP_ms":
            median_numeric(
                rows,
                "Field_FCP_ms",
            ),

        "Field_TTFB_ms":
            median_numeric(
                rows,
                "Field_TTFB_ms",
            ),

        # ----------------------------------------------------
        # LCP BREAKDOWN MEDIANS
        # ----------------------------------------------------

        "Median_LCP_TTFB_ms":
            median_numeric(
                rows,
                "LCP_TTFB_ms",
            ),

        "Median_LCP_Load_Delay_ms":
            median_numeric(
                rows,
                "LCP_Resource_Load_Delay_ms",
            ),

        "Median_LCP_Load_Duration_ms":
            median_numeric(
                rows,
                "LCP_Resource_Load_Duration_ms",
            ),

        "Median_LCP_Render_Delay_ms":
            median_numeric(
                rows,
                "LCP_Element_Render_Delay_ms",
            ),

        "Dominant_LCP_Phase":
            dominant_phase,

        # ----------------------------------------------------
        # LCP ELEMENT
        # ----------------------------------------------------

        "Dominant_LCP_Resource":
            dominant_lcp_resource,

        "Dominant_LCP_Label":
            dominant_lcp_label,

        "LCP_Lazy_Loaded_Runs":
            lazy_frequency,

        "Missing_FetchPriority_Runs":
            missing_priority_frequency,

        "Not_Discoverable_Runs":
            undiscoverable_frequency,

        # ----------------------------------------------------
        # DIAGNOSTICS MEDIANS
        # ----------------------------------------------------

        "Median_Image_Savings_Bytes":
            median_numeric(
                rows,
                "Image_Savings_Bytes",
                digits=0,
            ),

        "Median_Image_Savings_MB":
            bytes_to_mb(
                median_numeric(
                    rows,
                    "Image_Savings_Bytes",
                    digits=0,
                )
            ),

        "Median_Page_Weight_Bytes":
            median_numeric(
                rows,
                "Total_Page_Weight_Bytes",
                digits=0,
            ),

        "Median_Page_Weight_MB":
            bytes_to_mb(
                median_numeric(
                    rows,
                    "Total_Page_Weight_Bytes",
                    digits=0,
                )
            ),

        "Median_Render_Savings_ms":
            median_numeric(
                rows,
                "Render_Blocking_Savings_ms",
            ),

        "Median_Unused_CSS_Bytes":
            median_numeric(
                rows,
                "Unused_CSS_Bytes",
                digits=0,
            ),

        "Median_Unused_JS_Bytes":
            median_numeric(
                rows,
                "Unused_JS_Bytes",
                digits=0,
            ),

        "Median_Main_Thread_Work_ms":
            median_numeric(
                rows,
                "Main_Thread_Work_ms",
            ),

        "Median_Request_Count":
            median_numeric(
                rows,
                "Request_Count",
                digits=0,
            ),

        "Median_Script_Count":
            median_numeric(
                rows,
                "Script_Count",
                digits=0,
            ),

        "Median_Stylesheet_Count":
            median_numeric(
                rows,
                "Stylesheet_Count",
                digits=0,
            ),

        # ----------------------------------------------------
        # FINAL ROOT CAUSE
        # ----------------------------------------------------

        "Dominant_Primary_Root_Cause":
            dominant_primary_cause,

        "Dominant_Secondary_Root_Cause":
            dominant_secondary_cause,
    }

    return summary


# ============================================================
# 24. SAVE SUMMARY
# ============================================================

def write_summary_csv(
    summary,
    output_path,
):

    with open(

        output_path,

        "w",

        newline="",

        encoding="utf-8-sig",

    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=list(
                summary.keys()
            ),
        )

        writer.writeheader()

        writer.writerow(
            summary
        )


# ============================================================
# 25. MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 74
    )

    print(
        "PMB WIDYATAMA - "
        "ROOT CAUSE COLLECTOR"
    )

    print(
        "STEP 12B.2 - "
        "3-RUN STABILITY TEST"
    )

    print(
        "=" * 74
    )

    print(
        f"Page ID : {PAGE_ID}"
    )

    print(
        f"URL     : {TEST_URL}"
    )

    print(
        f"Device  : {DEVICE}"
    )

    print(
        f"Runs    : {NUMBER_OF_RUNS}"
    )

    print(
        "=" * 74
    )

    all_rows = []

    # ========================================================
    # RUN LOOP
    # ========================================================

    for run_number in range(
        1,
        NUMBER_OF_RUNS + 1,
    ):

        print()
        print(
            "-" * 74
        )

        print(
            f"RUN {run_number} "
            f"OF {NUMBER_OF_RUNS}"
        )

        print(
            "-" * 74
        )

        data = request_pagespeed(

            TEST_URL,

            DEVICE,
        )

        # ----------------------------------------------------
        # SAVE RAW JSON PER RUN
        # ----------------------------------------------------

        raw_json_path = (

            LOG_DIR

            / (
                f"root_cause_homepage_"
                f"run_{run_number}.json"
            )
        )

        with open(

            raw_json_path,

            "w",

            encoding="utf-8",

        ) as file:

            json.dump(

                data,

                file,

                ensure_ascii=False,

                indent=2,
            )

        row = parse_pagespeed(

            run_number,

            PAGE_ID,

            TEST_URL,

            DEVICE,

            data,
        )

        all_rows.append(
            row
        )

        # ----------------------------------------------------
        # DISPLAY RUN RESULT
        # ----------------------------------------------------

        print(
            "Performance       :",
            row.get(
                "Performance"
            ),
        )

        print(
            "Lab LCP           :",
            row.get(
                "Lab_LCP_ms"
            ),
            "ms",
        )

        print(
            "LCP load delay    :",
            row.get(
                "LCP_Resource_Load_Delay_ms"
            ),
            "ms",
        )

        print(
            "LCP render delay  :",
            row.get(
                "LCP_Element_Render_Delay_ms"
            ),
            "ms",
        )

        print(
            "Dominant phase    :",
            row.get(
                "Dominant_LCP_Phase"
            ),
        )

        print(
            "LCP resource      :",
            row.get(
                "LCP_Resource_URL"
            ),
        )

        print(
            "Primary cause     :",
            row.get(
                "Primary_Root_Cause"
            ),
        )

        print(
            "Secondary cause   :",
            row.get(
                "Secondary_Root_Cause"
            ),
        )

        print(
            "Page weight       :",
            bytes_to_mb(
                row.get(
                    "Total_Page_Weight_Bytes"
                )
            ),
            "MB",
        )

        print(
            "Image savings     :",
            bytes_to_mb(
                row.get(
                    "Image_Savings_Bytes"
                )
            ),
            "MB",
        )

        if (
            run_number
            < NUMBER_OF_RUNS
        ):

            print()

            print(
                f"[INFO] Waiting "
                f"{WAIT_BETWEEN_RUNS_SECONDS} "
                f"seconds before next run..."
            )

            time.sleep(
                WAIT_BETWEEN_RUNS_SECONDS
            )

    # ========================================================
    # SAVE RUN-LEVEL DATA
    # ========================================================

    write_rows_csv(

        all_rows,

        RUNS_OUTPUT_CSV,
    )

    # ========================================================
    # BUILD SUMMARY
    # ========================================================

    summary = build_summary(
        all_rows
    )

    write_summary_csv(

        summary,

        SUMMARY_OUTPUT_CSV,
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print(
        "=" * 74
    )

    print(
        "3-RUN STABILITY SUMMARY"
    )

    print(
        "=" * 74
    )

    print()

    print(
        "Median Performance :",
        summary.get(
            "Median_Performance"
        ),
    )

    print(
        "Median Lab LCP     :",
        summary.get(
            "Median_Lab_LCP_ms"
        ),
        "ms",
    )

    print(
        "Median FCP         :",
        summary.get(
            "Median_Lab_FCP_ms"
        ),
        "ms",
    )

    print(
        "Median TBT         :",
        summary.get(
            "Median_Lab_TBT_ms"
        ),
        "ms",
    )

    print(
        "Median Speed Index :",
        summary.get(
            "Median_Speed_Index_ms"
        ),
        "ms",
    )

    print()

    print(
        "Field LCP          :",
        summary.get(
            "Field_LCP_ms"
        ),
        "ms",
    )

    print(
        "Field INP          :",
        summary.get(
            "Field_INP_ms"
        ),
        "ms",
    )

    print(
        "Field TTFB         :",
        summary.get(
            "Field_TTFB_ms"
        ),
        "ms",
    )

    print(
        "CWV Status         :",
        summary.get(
            "CWV_Status"
        ),
    )

    print()

    print(
        "Median Load Delay  :",
        summary.get(
            "Median_LCP_Load_Delay_ms"
        ),
        "ms",
    )

    print(
        "Median Render Delay:",
        summary.get(
            "Median_LCP_Render_Delay_ms"
        ),
        "ms",
    )

    print(
        "Dominant LCP Phase :",
        summary.get(
            "Dominant_LCP_Phase"
        ),
    )

    print()

    print(
        "Dominant LCP Asset :",
        summary.get(
            "Dominant_LCP_Resource"
        ),
    )

    print()

    print(
        "LCP lazy runs      :",
        summary.get(
            "LCP_Lazy_Loaded_Runs"
        ),
        "/",
        NUMBER_OF_RUNS,
    )

    print(
        "Missing priority   :",
        summary.get(
            "Missing_FetchPriority_Runs"
        ),
        "/",
        NUMBER_OF_RUNS,
    )

    print(
        "Not discoverable   :",
        summary.get(
            "Not_Discoverable_Runs"
        ),
        "/",
        NUMBER_OF_RUNS,
    )

    print()

    print(
        "Median Page Weight :",
        summary.get(
            "Median_Page_Weight_MB"
        ),
        "MB",
    )

    print(
        "Median Img Savings :",
        summary.get(
            "Median_Image_Savings_MB"
        ),
        "MB",
    )

    print(
        "Median Render Save :",
        summary.get(
            "Median_Render_Savings_ms"
        ),
        "ms",
    )

    print()

    print(
        "FINAL PRIMARY CAUSE:"
    )

    print(
        summary.get(
            "Dominant_Primary_Root_Cause"
        )
    )

    print()

    print(
        "FINAL SECONDARY CAUSE:"
    )

    print(
        summary.get(
            "Dominant_Secondary_Root_Cause"
        )
    )

    print()

    print(
        "=" * 74
    )

    print(
        "RUN DATA SAVED TO:"
    )

    print(
        RUNS_OUTPUT_CSV
    )

    print()

    print(
        "SUMMARY SAVED TO:"
    )

    print(
        SUMMARY_OUTPUT_CSV
    )

    print(
        "=" * 74
    )

    print()


# ============================================================
# 26. ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()