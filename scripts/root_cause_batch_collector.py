import csv
import json
import os
import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path
from statistics import median

import requests
from dotenv import load_dotenv


# ============================================================
# PMB WIDYATAMA
# STEP 12C.1
# FINAL BATCH ROOT CAUSE COLLECTOR
#
# CURRENT MODE:
# SMOKE TEST = 1 PAGE
#
# AFTER VALIDATION:
# PAGE_LIMIT = None
# ============================================================


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "root_cause_targets.csv"
)

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

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LOG_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 2. OUTPUT FILES
# ============================================================

RUNS_OUTPUT = (
    PROCESSED_DIR
    / "root_cause_batch_runs_before.csv"
)

RESULTS_OUTPUT = (
    PROCESSED_DIR
    / "root_cause_batch_results_before.csv"
)


# ============================================================
# 3. TEST CONFIGURATION
# ============================================================

DEVICE = "mobile"

VALID_RUNS_REQUIRED = 3

MAX_ATTEMPTS_PER_PAGE = 5

WAIT_BETWEEN_RUNS = 5

LIGHTHOUSE_TIMEOUT_SECONDS = 240


# ------------------------------------------------------------
# IMPORTANT:
# Untuk smoke test pertama hanya 1 halaman.
#
# Setelah hasil PASS, nanti ubah:
#
# PAGE_LIMIT = None
#
# agar seluruh 43 dataset diproses.
# ------------------------------------------------------------

PAGE_LIMIT = None


# ============================================================
# 4. ENVIRONMENT
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
        "Pastikan file .env berada di root project.\n"
    )


# ============================================================
# 5. PAGESPEED API
# ============================================================

PSI_ENDPOINT = (
    "https://www.googleapis.com/"
    "pagespeedonline/v5/runPagespeed"
)


# ============================================================
# 6. GENERIC HELPERS
# ============================================================

def safe_number(value):

    try:

        if value is None:
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

    value = safe_number(
        value
    )

    if value is None:
        return None

    return round(
        value,
        digits,
    )


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


def yes_no(value):

    if value is True:
        return "Yes"

    if value is False:
        return "No"

    return None


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

    value, count = (
        counter.most_common(1)[0]
    )

    return (
        value,
        count,
    )


# ============================================================
# 7. READ INPUT CSV
# AUTO-DETECT , OR ;
# ============================================================

def read_targets():

    if not INPUT_CSV.exists():

        raise FileNotFoundError(
            f"\nInput file tidak ditemukan:\n"
            f"{INPUT_CSV}\n"
        )

    with open(
        INPUT_CSV,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        sample = file.read(
            4096
        )

        file.seek(0)

        try:

            dialect = csv.Sniffer().sniff(

                sample,

                delimiters=",;\t",
            )

            delimiter = (
                dialect.delimiter
            )

        except csv.Error:

            delimiter = ";"

        reader = csv.DictReader(

            file,

            delimiter=delimiter,
        )

        rows = []

        for raw in reader:

            clean = {

                str(key).strip():
                    (
                        value.strip()
                        if isinstance(
                            value,
                            str,
                        )
                        else value
                    )

                for key, value
                in raw.items()

                if key is not None
            }

            rows.append(
                clean
            )

    required_columns = {

        "Page_ID",
        "URL",
        "Final_Page_Type",
        "Test_Priority",
        "Business_Weight",
        "Combined_Priority",
    }

    if not rows:

        raise RuntimeError(
            "root_cause_targets.csv kosong."
        )

    missing = (

        required_columns
        - set(rows[0].keys())
    )

    if missing:

        raise RuntimeError(

            "Kolom CSV tidak lengkap.\n"
            f"Missing: {missing}"
        )

    print(
        f"[INPUT] Delimiter detected : "
        f"{repr(delimiter)}"
    )

    print(
        f"[INPUT] Total targets      : "
        f"{len(rows)}"
    )

    return rows


# ============================================================
# 8. CSV STORAGE HELPERS
# ============================================================

def load_csv_if_exists(path):

    if not path.exists():
        return []

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

        for row in rows:

            writer.writerow(
                {
                    key: row.get(key)
                    for key
                    in fieldnames
                }
            )


# ============================================================
# 9. PSI REQUEST
# ============================================================

def request_psi_field_data(
    url,
    retries=3,
):

    params = {

        "url": url,

        "strategy": DEVICE,

        "category": "performance",

        "key": API_KEY,
    }

    for attempt in range(
        1,
        retries + 1,
    ):

        try:

            print(
                f"    PSI attempt "
                f"{attempt}/{retries}"
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
                "    PSI HTTP:",
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

            raise RuntimeError(
                response.text
            )

        except requests.RequestException as exc:

            print(
                "    PSI network error:",
                exc,
            )

            if attempt == retries:
                raise

            time.sleep(
                5 * attempt
            )

    return {}


# ============================================================
# 10. CRUX FIELD DATA
# ============================================================

def metric_percentile(
    metrics,
    name,
):

    return safe_get(

        metrics,

        name,

        "percentile",
    )


def derive_cwv(
    lcp,
    inp,
    cls,
):

    if (

        lcp is None
        or inp is None
        or cls is None
    ):

        return "Incomplete"

    if (

        lcp <= 2500
        and inp <= 200
        and cls <= 0.10
    ):

        return "Passed"

    return "Failed"


def parse_field_data(data):

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

    if url_metrics:

        level = "URL"

        experience = (
            url_exp
        )

        metrics = (
            url_metrics
        )

    elif origin_metrics:

        level = "Origin"

        experience = (
            origin_exp
        )

        metrics = (
            origin_metrics
        )

    else:

        return {

            "Field_Data_Available":
                "No",

            "Field_Data_Level":
                "Not Available",

            "Field_Category":
                None,

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

            "CWV_Status":
                "Not Available",
        }

    lcp = metric_percentile(

        metrics,

        "LARGEST_CONTENTFUL_PAINT_MS",
    )

    inp = metric_percentile(

        metrics,

        "INTERACTION_TO_NEXT_PAINT",
    )

    cls_raw = metric_percentile(

        metrics,

        "CUMULATIVE_LAYOUT_SHIFT_SCORE",
    )

    fcp = metric_percentile(

        metrics,

        "FIRST_CONTENTFUL_PAINT_MS",
    )

    ttfb = metric_percentile(

        metrics,

        "EXPERIMENTAL_TIME_TO_FIRST_BYTE",
    )

    cls = (

        cls_raw / 100

        if cls_raw is not None

        else None
    )

    return {

        "Field_Data_Available":
            "Yes",

        "Field_Data_Level":
            level,

        "Field_Category":
            experience.get(
                "overall_category"
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

        "CWV_Status":
            derive_cwv(
                lcp,
                inp,
                cls,
            ),
    }


# ============================================================
# 11. LIGHTHOUSE LOCATION
# ============================================================

def find_npx():

    candidates = [

        shutil.which("npx"),

        shutil.which("npx.cmd"),
    ]

    for candidate in candidates:

        if candidate:

            return candidate

    raise RuntimeError(

        "\nnpx tidak ditemukan.\n"
        "Pastikan Node.js/npm sudah tersedia.\n"
    )


NPX_PATH = find_npx()


# ============================================================
# 12. RUN LOCAL LIGHTHOUSE
# ============================================================

def run_lighthouse(
    url,
    output_path,
):

    command = [

        NPX_PATH,

        "lighthouse",

        url,

        "--only-categories=performance",

        "--form-factor=mobile",

        "--chrome-flags=--headless=new",

        "--output=json",

        f"--output-path={output_path}",

        "--quiet",
    ]

    try:

        result = subprocess.run(

            command,

            cwd=PROJECT_ROOT,

            capture_output=True,

            text=True,

            timeout=LIGHTHOUSE_TIMEOUT_SECONDS,
        )

        return {

            "returncode":
                result.returncode,

            "stdout":
                result.stdout,

            "stderr":
                result.stderr,
        }

    except subprocess.TimeoutExpired:

        return {

            "returncode":
                -999,

            "stdout":
                "",

            "stderr":
                "LIGHTHOUSE_TIMEOUT",
        }


# ============================================================
# 13. VALIDATE LIGHTHOUSE JSON
# ============================================================

def validate_lighthouse_json(
    json_path,
):

    if not json_path.exists():

        return (
            False,
            "JSON_NOT_CREATED",
            None,
        )

    try:

        with open(
            json_path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

    except Exception as exc:

        return (

            False,

            f"JSON_READ_ERROR: {exc}",

            None,
        )

    runtime_error = (
        data.get(
            "runtimeError"
        )
    )

    if runtime_error:

        code = runtime_error.get(
            "code",
            "UNKNOWN_RUNTIME_ERROR",
        )

        return (

            False,

            code,

            data,
        )

    performance_score = safe_get(

        data,

        "categories",

        "performance",

        "score",
    )

    if performance_score is None:

        return (

            False,

            "NO_PERFORMANCE_SCORE",

            data,
        )

    audits = (
        data.get(
            "audits"
        )
        or {}
    )

    required_metrics = [

        "first-contentful-paint",

        "largest-contentful-paint",

        "total-blocking-time",

        "cumulative-layout-shift",

        "speed-index",
    ]

    for metric in required_metrics:

        value = safe_get(

            audits,

            metric,

            "numericValue",
        )

        if value is None:

            return (

                False,

                f"MISSING_{metric}",

                data,
            )

    return (
        True,
        "VALID",
        data,
    )


# ============================================================
# 14. FIND AUDIT
# ============================================================

def find_audit(
    audits,
    ids=None,
    title_terms=None,
):

    ids = ids or []

    title_terms = (
        title_terms
        or []
    )

    for audit_id in ids:

        audit = audits.get(
            audit_id
        )

        if audit:

            return (
                audit_id,
                audit,
            )

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

        for term in title_terms:

            if term.lower() in title:

                return (
                    audit_id,
                    audit,
                )

    return (
        None,
        {},
    )


# ============================================================
# 15. RECURSIVE BYTE SUM
# ============================================================

def recursively_sum_key(
    obj,
    target,
):

    total = 0.0
    found = False

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            if key == target:

                number = safe_number(
                    value
                )

                if number is not None:

                    total += number

                    found = True

            subtotal, subfound = (
                recursively_sum_key(
                    value,
                    target,
                )
            )

            if subfound:

                total += subtotal

                found = True

    elif isinstance(
        obj,
        list,
    ):

        for item in obj:

            subtotal, subfound = (
                recursively_sum_key(
                    item,
                    target,
                )
            )

            if subfound:

                total += subtotal

                found = True

    return (
        total,
        found,
    )


# ============================================================
# 16. SAVINGS BYTES
# ============================================================

def audit_savings_bytes(audit):

    if not audit:
        return None

    details = (
        audit.get(
            "details"
        )
        or {}
    )

    direct = safe_number(
        details.get(
            "overallSavingsBytes"
        )
    )

    if direct is not None:

        return round(
            direct
        )

    total, found = (
        recursively_sum_key(

            details.get(
                "items",
                [],
            ),

            "wastedBytes",
        )
    )

    if found:

        return round(
            total
        )

    return None


# ============================================================
# 17. SAVINGS MS
# ============================================================

def audit_savings_ms(audit):

    if not audit:
        return None

    display = str(
        audit.get(
            "displayValue",
            "",
        )
    )

    match = re.search(

        r"([0-9][0-9,.\s]*)\s*ms",

        display,

        re.IGNORECASE,
    )

    if match:

        raw = (
            match.group(1)
            .replace(",", "")
            .replace(" ", "")
        )

        try:

            return round(
                float(raw),
                2,
            )

        except ValueError:
            pass

    match_seconds = re.search(

        r"([0-9]+(?:\.[0-9]+)?)\s*s",

        display,

        re.IGNORECASE,
    )

    if match_seconds:

        return round(

            float(
                match_seconds.group(1)
            )
            * 1000,

            2,
        )

    details = (
        audit.get(
            "details"
        )
        or {}
    )

    overall = safe_number(
        details.get(
            "overallSavingsMs"
        )
    )

    if overall is not None:

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
    ]:

        value = safe_number(
            metric_savings.get(
                metric
            )
        )

        if (
            value is not None
            and value > 0
        ):

            candidates.append(
                value
            )

    if candidates:

        return round(
            max(candidates),
            2,
        )

    return None


# ============================================================
# 18. LCP BREAKDOWN
# ============================================================

def extract_lcp_breakdown(audits):

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

        "LCP_TTFB_ms":
            None,

        "LCP_Load_Delay_ms":
            None,

        "LCP_Load_Duration_ms":
            None,

        "LCP_Render_Delay_ms":
            None,

        "LCP_Element":
            None,

        "LCP_Selector":
            None,

        "LCP_Node_Label":
            None,
    }

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

        if item.get("type") == "table":

            for row in item.get(
                "items",
                [],
            ):

                text = (

                    str(
                        row.get(
                            "subpart",
                            "",
                        )
                    )

                    +

                    str(
                        row.get(
                            "label",
                            "",
                        )
                    )
                )

                compact = (

                    text.lower()
                    .replace(" ", "")
                )

                duration = rounded(
                    row.get(
                        "duration"
                    )
                )

                if "timetofirstbyte" in compact:

                    result[
                        "LCP_TTFB_ms"
                    ] = duration

                elif "resourceloaddelay" in compact:

                    result[
                        "LCP_Load_Delay_ms"
                    ] = duration

                elif "resourceloadduration" in compact:

                    result[
                        "LCP_Load_Duration_ms"
                    ] = duration

                elif "elementrenderdelay" in compact:

                    result[
                        "LCP_Render_Delay_ms"
                    ] = duration

        if item.get("type") == "node":

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
# 19. LCP DISCOVERY
# ============================================================

def extract_lcp_discovery(audits):

    _, audit = find_audit(

        audits,

        ids=[
            "lcp-discovery-insight"
        ],

        title_terms=[
            "lcp request discovery"
        ],
    )

    result = {

        "LCP_Lazy_Loaded":
            None,

        "LCP_FetchPriority_High":
            None,

        "LCP_Discoverable_Initial_HTML":
            None,

        "LCP_Resource_URL":
            None,
    }

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

        if item.get("type") == "checklist":

            checks = (
                item.get(
                    "items"
                )
                or {}
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

            eager = safe_get(

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

            if eager is not None:

                result[
                    "LCP_Lazy_Loaded"
                ] = yes_no(
                    not eager
                )

        if item.get("type") == "node":

            snippet = str(
                item.get(
                    "snippet",
                    "",
                )
            )

            match = re.search(

                r'''src=["']([^"']+)["']''',

                snippet,

                re.IGNORECASE,
            )

            if match:

                result[
                    "LCP_Resource_URL"
                ] = match.group(1)

    return result


# ============================================================
# 20. DOMINANT LCP PHASE
# ============================================================

def dominant_lcp_phase(row):

    phases = {

        "TTFB":
            safe_number(
                row.get(
                    "LCP_TTFB_ms"
                )
            ),

        "Resource Load Delay":
            safe_number(
                row.get(
                    "LCP_Load_Delay_ms"
                )
            ),

        "Resource Load Duration":
            safe_number(
                row.get(
                    "LCP_Load_Duration_ms"
                )
            ),

        "Element Render Delay":
            safe_number(
                row.get(
                    "LCP_Render_Delay_ms"
                )
            ),
    }

    valid = {

        key: value

        for key, value
        in phases.items()

        if value is not None
    }

    if not valid:

        return (
            None,
            None,
        )

    phase = max(

        valid,

        key=valid.get,
    )

    return (

        phase,

        round(
            valid[phase],
            2,
        ),
    )


# ============================================================
# 21. DIAGNOSTICS
# ============================================================

def extract_diagnostics(audits):

    result = {}

    _, image_audit = find_audit(

        audits,

        ids=[
            "image-delivery-insight"
        ],

        title_terms=[
            "improve image delivery"
        ],
    )

    result[
        "Image_Savings_Bytes"
    ] = audit_savings_bytes(
        image_audit
    )

    _, render_audit = find_audit(

        audits,

        ids=[
            "render-blocking-insight"
        ],

        title_terms=[
            "render-blocking"
        ],
    )

    result[
        "Render_Blocking_Savings_ms"
    ] = audit_savings_ms(
        render_audit
    )

    result[
        "Unused_CSS_Bytes"
    ] = audit_savings_bytes(

        audits.get(
            "unused-css-rules",
            {},
        )
    )

    result[
        "Unused_JS_Bytes"
    ] = audit_savings_bytes(

        audits.get(
            "unused-javascript",
            {},
        )
    )

    total_weight = audits.get(
        "total-byte-weight",
        {},
    )

    result[
        "Page_Weight_Bytes"
    ] = rounded(

        total_weight.get(
            "numericValue"
        ),

        0,
    )

    main_thread = audits.get(
        "mainthread-work-breakdown",
        {},
    )

    result[
        "Main_Thread_Work_ms"
    ] = rounded(

        main_thread.get(
            "numericValue"
        )
    )

    long_tasks = safe_get(

        audits.get(
            "long-tasks",
            {},
        ),

        "details",

        "items",

        default=[],
    )

    result[
        "Long_Task_Count"
    ] = (

        len(long_tasks)

        if isinstance(
            long_tasks,
            list,
        )

        else None
    )

    diagnostics = safe_get(

        audits.get(
            "diagnostics",
            {},
        ),

        "details",

        "items",

        default=[],
    )

    debug = (

        diagnostics[0]

        if (
            isinstance(
                diagnostics,
                list,
            )
            and diagnostics
        )

        else {}
    )

    result[
        "Request_Count"
    ] = debug.get(
        "numRequests"
    )

    result[
        "Script_Count"
    ] = debug.get(
        "numScripts"
    )

    result[
        "Stylesheet_Count"
    ] = debug.get(
        "numStylesheets"
    )

    return result


# ============================================================
# 22. ROOT CAUSE CLASSIFICATION
# ============================================================

def classify_root_cause(row):

    phase, _ = dominant_lcp_phase(
        row
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
    # SUPPORTING ISSUES
    # --------------------------------------------------------

    if (

        image_savings is not None
        and image_savings > 500_000
    ):

        issues.append(
            "Unoptimized Image Delivery"
        )

    if (

        page_weight is not None
        and page_weight > 5_000_000
    ):

        issues.append(
            "Excessive Page Weight"
        )

    if (

        main_thread is not None
        and main_thread > 4000
    ):

        issues.append(
            "Heavy Main-Thread Work"
        )

    if (

        render_savings is not None
        and render_savings > 500
    ):

        issues.append(
            "Render-Blocking Resources"
        )

    if priority == "No":

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
# 23. PARSE VALID LIGHTHOUSE RUN
# ============================================================

def parse_lighthouse_run(
    target,
    valid_run_number,
    attempt_number,
    data,
    json_path,
):

    audits = (
        data.get(
            "audits"
        )
        or {}
    )

    performance_score = safe_get(

        data,

        "categories",

        "performance",

        "score",
    )

    row = {

        "Page_ID":
            target["Page_ID"],

        "URL":
            target["URL"],

        "Final_Page_Type":
            target["Final_Page_Type"],

        "Valid_Run_Number":
            valid_run_number,

        "Attempt_Number":
            attempt_number,

        "Run_Status":
            "VALID",

        "Failure_Reason":
            None,

        "Fetch_Time":
            data.get(
                "fetchTime"
            ),

        "Benchmark_Index":
            safe_get(

                data,

                "environment",

                "benchmarkIndex",
            ),

        "Performance":
            round(
                performance_score
                * 100
            ),

        "Lab_FCP_ms":
            rounded(
                safe_get(
                    audits,
                    "first-contentful-paint",
                    "numericValue",
                )
            ),

        "Lab_LCP_ms":
            rounded(
                safe_get(
                    audits,
                    "largest-contentful-paint",
                    "numericValue",
                )
            ),

        "Lab_TBT_ms":
            rounded(
                safe_get(
                    audits,
                    "total-blocking-time",
                    "numericValue",
                )
            ),

        "Lab_CLS":
            rounded(
                safe_get(
                    audits,
                    "cumulative-layout-shift",
                    "numericValue",
                ),
                4,
            ),

        "Lab_Speed_Index_ms":
            rounded(
                safe_get(
                    audits,
                    "speed-index",
                    "numericValue",
                )
            ),

        "JSON_Path":
            str(
                json_path.relative_to(
                    PROJECT_ROOT
                )
            ),
    }

    row.update(
        extract_lcp_breakdown(
            audits
        )
    )

    row.update(
        extract_lcp_discovery(
            audits
        )
    )

    row.update(
        extract_diagnostics(
            audits
        )
    )

    phase, phase_ms = (
        dominant_lcp_phase(
            row
        )
    )

    row[
        "Dominant_LCP_Phase"
    ] = phase

    row[
        "Dominant_LCP_Phase_ms"
    ] = phase_ms

    primary, secondary = (
        classify_root_cause(
            row
        )
    )

    row[
        "Primary_Root_Cause"
    ] = primary

    row[
        "Secondary_Root_Cause"
    ] = secondary

    return row


# ============================================================
# 24. BUILD PAGE SUMMARY
# ============================================================

def build_page_summary(
    target,
    valid_rows,
    field_data,
    attempts,
):

    (
        dominant_phase,
        dominant_phase_count,
    ) = mode_with_count(

        [
            row.get(
                "Dominant_LCP_Phase"
            )
            for row
            in valid_rows
        ]
    )

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

    (
        lcp_resource,
        lcp_resource_count,
    ) = mode_with_count(

        [
            row.get(
                "LCP_Resource_URL"
            )
            for row
            in valid_rows
        ]
    )

    (
        lcp_label,
        lcp_label_count,
    ) = mode_with_count(

        [
            row.get(
                "LCP_Node_Label"
            )
            for row
            in valid_rows
        ]
    )

    fetch_times = {

        row.get(
            "Fetch_Time"
        )

        for row
        in valid_rows

        if row.get(
            "Fetch_Time"
        )
    }

    valid_count = len(
        valid_rows
    )

    qc = (

        "PASS"

        if (

            valid_count
            == VALID_RUNS_REQUIRED

            and len(fetch_times)
            == VALID_RUNS_REQUIRED
        )

        else "FAIL"
    )

    summary = {

        "Page_ID":
            target["Page_ID"],

        "URL":
            target["URL"],

        "Final_Page_Type":
            target["Final_Page_Type"],

        "Test_Priority":
            target["Test_Priority"],

        "Business_Weight":
            target["Business_Weight"],

        "Combined_Priority":
            target["Combined_Priority"],

        "Batch_Status":
            (
                "COMPLETE"

                if valid_count
                == VALID_RUNS_REQUIRED

                else "FAILED"
            ),

        "Independent_Run_QC":
            qc,

        "Attempts_Used":
            attempts,

        "Valid_Runs":
            valid_count,

        # FIELD DATA
        **field_data,

        # LAB MEDIANS
        "Median_Performance":
            numeric_median(
                valid_rows,
                "Performance",
            ),

        "Median_Lab_FCP_ms":
            numeric_median(
                valid_rows,
                "Lab_FCP_ms",
            ),

        "Median_Lab_LCP_ms":
            numeric_median(
                valid_rows,
                "Lab_LCP_ms",
            ),

        "Median_Lab_TBT_ms":
            numeric_median(
                valid_rows,
                "Lab_TBT_ms",
            ),

        "Median_Lab_CLS":
            numeric_median(
                valid_rows,
                "Lab_CLS",
                4,
            ),

        "Median_Speed_Index_ms":
            numeric_median(
                valid_rows,
                "Lab_Speed_Index_ms",
            ),

        # LCP BREAKDOWN
        "Median_LCP_TTFB_ms":
            numeric_median(
                valid_rows,
                "LCP_TTFB_ms",
            ),

        "Median_LCP_Load_Delay_ms":
            numeric_median(
                valid_rows,
                "LCP_Load_Delay_ms",
            ),

        "Median_LCP_Load_Duration_ms":
            numeric_median(
                valid_rows,
                "LCP_Load_Duration_ms",
            ),

        "Median_LCP_Render_Delay_ms":
            numeric_median(
                valid_rows,
                "LCP_Render_Delay_ms",
            ),

        "Dominant_LCP_Phase":
            dominant_phase,

        "Dominant_LCP_Phase_Consistency":
            (
                f"{dominant_phase_count}/"
                f"{valid_count}"
            ),

        "Dominant_LCP_Resource":
            lcp_resource,

        "LCP_Resource_Consistency":
            (
                f"{lcp_resource_count}/"
                f"{valid_count}"
            ),

        "Dominant_LCP_Label":
            lcp_label,

        "LCP_Label_Consistency":
            (
                f"{lcp_label_count}/"
                f"{valid_count}"
            ),

        # DISCOVERY
        "LCP_Lazy_Loaded_Runs":
            sum(

                1

                for row
                in valid_rows

                if row.get(
                    "LCP_Lazy_Loaded"
                )
                == "Yes"
            ),

        "Missing_FetchPriority_Runs":
            sum(

                1

                for row
                in valid_rows

                if row.get(
                    "LCP_FetchPriority_High"
                )
                == "No"
            ),

        "Not_Discoverable_Runs":
            sum(

                1

                for row
                in valid_rows

                if row.get(
                    "LCP_Discoverable_Initial_HTML"
                )
                == "No"
            ),

        # DIAGNOSTICS
        "Median_Page_Weight_Bytes":
            numeric_median(
                valid_rows,
                "Page_Weight_Bytes",
                0,
            ),

        "Median_Page_Weight_MB":
            bytes_to_mb(
                numeric_median(
                    valid_rows,
                    "Page_Weight_Bytes",
                    0,
                )
            ),

        "Median_Image_Savings_Bytes":
            numeric_median(
                valid_rows,
                "Image_Savings_Bytes",
                0,
            ),

        "Median_Image_Savings_MB":
            bytes_to_mb(
                numeric_median(
                    valid_rows,
                    "Image_Savings_Bytes",
                    0,
                )
            ),

        "Median_Render_Blocking_Savings_ms":
            numeric_median(
                valid_rows,
                "Render_Blocking_Savings_ms",
            ),

        "Median_Unused_CSS_Bytes":
            numeric_median(
                valid_rows,
                "Unused_CSS_Bytes",
                0,
            ),

        "Median_Unused_JS_Bytes":
            numeric_median(
                valid_rows,
                "Unused_JS_Bytes",
                0,
            ),

        "Median_Main_Thread_Work_ms":
            numeric_median(
                valid_rows,
                "Main_Thread_Work_ms",
            ),

        "Median_Long_Task_Count":
            numeric_median(
                valid_rows,
                "Long_Task_Count",
                0,
            ),

        "Median_Request_Count":
            numeric_median(
                valid_rows,
                "Request_Count",
                0,
            ),

        "Median_Script_Count":
            numeric_median(
                valid_rows,
                "Script_Count",
                0,
            ),

        "Median_Stylesheet_Count":
            numeric_median(
                valid_rows,
                "Stylesheet_Count",
                0,
            ),

        # ROOT CAUSE
        "Primary_Root_Cause":
            primary,

        "Primary_Root_Cause_Consistency":
            (
                f"{primary_count}/"
                f"{valid_count}"
            ),

        "Secondary_Root_Cause":
            secondary,

        "Secondary_Root_Cause_Consistency":
            (
                f"{secondary_count}/"
                f"{valid_count}"
            ),
    }

    return summary


# ============================================================
# 25. MAIN
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
        "STEP 12C.1 - "
        "FINAL BATCH ROOT CAUSE COLLECTOR"
    )

    print(
        "=" * 78
    )

    targets = read_targets()

    if PAGE_LIMIT is not None:

        targets = targets[
            :PAGE_LIMIT
        ]

        print(
            f"[MODE] SMOKE TEST: "
            f"{len(targets)} page"
        )

    else:

        print(
            f"[MODE] FULL BATCH: "
            f"{len(targets)} pages"
        )

    existing_runs = (
        load_csv_if_exists(
            RUNS_OUTPUT
        )
    )

    existing_results = (
        load_csv_if_exists(
            RESULTS_OUTPUT
        )
    )

    result_by_page = {

        row.get(
            "Page_ID"
        ):
            row

        for row
        in existing_results
    }

    completed_pages = {

        row.get(
            "Page_ID"
        )

        for row
        in existing_results

        if row.get(
            "Batch_Status"
        )
        == "COMPLETE"
    }

    for index, target in enumerate(
        targets,
        start=1,
    ):

        page_id = target[
            "Page_ID"
        ]

        url = target[
            "URL"
        ]

        print()
        print(
            "=" * 78
        )

        print(
            f"[{index}/{len(targets)}] "
            f"{page_id}"
        )

        print(
            url
        )

        print(
            "=" * 78
        )

        if page_id in completed_pages:

            print(
                "[SKIP] Already COMPLETE."
            )

            continue

        page_log_dir = (
            LOG_ROOT / page_id
        )

        page_log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ====================================================
        # FIELD DATA
        # ====================================================

        print()
        print(
            "[FIELD] Fetching PSI / CrUX..."
        )

        try:

            psi_data = (
                request_psi_field_data(
                    url
                )
            )

            psi_json_path = (

                page_log_dir
                / "psi_field.json"
            )

            with open(
                psi_json_path,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    psi_data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            field_data = (
                parse_field_data(
                    psi_data
                )
            )

            print(
                "    Field level :",
                field_data.get(
                    "Field_Data_Level"
                ),
            )

            print(
                "    Field LCP   :",
                field_data.get(
                    "Field_LCP_ms"
                ),
            )

            print(
                "    CWV         :",
                field_data.get(
                    "CWV_Status"
                ),
            )

        except Exception as exc:

            print(
                "[WARNING] PSI field failed:",
                exc,
            )

            field_data = {

                "Field_Data_Available":
                    "Error",

                "Field_Data_Level":
                    None,

                "Field_Category":
                    None,

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

                "CWV_Status":
                    "Unknown",
            }

        # ====================================================
        # LOCAL LIGHTHOUSE
        # ====================================================

        valid_rows = []

        attempts = 0

        while (

            len(valid_rows)
            < VALID_RUNS_REQUIRED

            and attempts
            < MAX_ATTEMPTS_PER_PAGE
        ):

            attempts += 1

            valid_run_number = (
                len(valid_rows) + 1
            )

            print()
            print(
                f"[LAB] Attempt "
                f"{attempts}/"
                f"{MAX_ATTEMPTS_PER_PAGE}"
            )

            print(
                f"      Need valid run "
                f"{valid_run_number}/"
                f"{VALID_RUNS_REQUIRED}"
            )

            json_path = (

                page_log_dir

                / (
                    f"lighthouse_"
                    f"attempt_{attempts}.json"
                )
            )

            execution = run_lighthouse(

                url,

                json_path,
            )

            (
                is_valid,
                validation_reason,
                lighthouse_data,
            ) = validate_lighthouse_json(
                json_path
            )

            if not is_valid:

                print(
                    "      INVALID:",
                    validation_reason,
                )

                failure_row = {

                    "Page_ID":
                        page_id,

                    "URL":
                        url,

                    "Final_Page_Type":
                        target[
                            "Final_Page_Type"
                        ],

                    "Valid_Run_Number":
                        None,

                    "Attempt_Number":
                        attempts,

                    "Run_Status":
                        "INVALID",

                    "Failure_Reason":
                        validation_reason,

                    "JSON_Path":
                        str(
                            json_path.relative_to(
                                PROJECT_ROOT
                            )
                        ),
                }

                existing_runs.append(
                    failure_row
                )

                write_csv(
                    RUNS_OUTPUT,
                    existing_runs,
                )

                time.sleep(
                    WAIT_BETWEEN_RUNS
                )

                continue

            run_row = (
                parse_lighthouse_run(

                    target,

                    valid_run_number,

                    attempts,

                    lighthouse_data,

                    json_path,
                )
            )

            valid_rows.append(
                run_row
            )

            existing_runs.append(
                run_row
            )

            write_csv(
                RUNS_OUTPUT,
                existing_runs,
            )

            print(
                "      VALID"
            )

            print(
                "      Performance :",
                run_row.get(
                    "Performance"
                ),
            )

            print(
                "      LCP         :",
                run_row.get(
                    "Lab_LCP_ms"
                ),
                "ms",
            )

            print(
                "      Phase       :",
                run_row.get(
                    "Dominant_LCP_Phase"
                ),
            )

            print(
                "      Root cause  :",
                run_row.get(
                    "Primary_Root_Cause"
                ),
            )

            if (
                len(valid_rows)
                < VALID_RUNS_REQUIRED
            ):

                time.sleep(
                    WAIT_BETWEEN_RUNS
                )

        # ====================================================
        # SUMMARY
        # ====================================================

        summary = (
            build_page_summary(

                target,

                valid_rows,

                field_data,

                attempts,
            )
        )

        result_by_page[
            page_id
        ] = summary

        results_rows = list(
            result_by_page.values()
        )

        write_csv(
            RESULTS_OUTPUT,
            results_rows,
        )

        print()
        print(
            "-" * 78
        )

        print(
            "PAGE SUMMARY"
        )

        print(
            "-" * 78
        )

        print(
            "Status       :",
            summary.get(
                "Batch_Status"
            ),
        )

        print(
            "Run QC       :",
            summary.get(
                "Independent_Run_QC"
            ),
        )

        print(
            "Valid runs   :",
            summary.get(
                "Valid_Runs"
            ),
        )

        print(
            "Performance  :",
            summary.get(
                "Median_Performance"
            ),
        )

        print(
            "Median LCP   :",
            summary.get(
                "Median_Lab_LCP_ms"
            ),
            "ms",
        )

        print(
            "LCP Phase    :",
            summary.get(
                "Dominant_LCP_Phase"
            ),
        )

        print(
            "Page Weight  :",
            summary.get(
                "Median_Page_Weight_MB"
            ),
            "MB",
        )

        print(
            "Primary      :",
            summary.get(
                "Primary_Root_Cause"
            ),
        )

        print(
            "Secondary    :",
            summary.get(
                "Secondary_Root_Cause"
            ),
        )

    print()
    print(
        "=" * 78
    )

    print(
        "STEP 12C.1 FINISHED"
    )

    print(
        "=" * 78
    )

    print(
        "Run-level output:"
    )

    print(
        RUNS_OUTPUT
    )

    print()

    print(
        "Page summary output:"
    )

    print(
        RESULTS_OUTPUT
    )

    print(
        "=" * 78
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()