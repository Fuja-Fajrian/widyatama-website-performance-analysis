import os
import csv
import time
import requests

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


# ==================================================
# LOAD ENVIRONMENT
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

API_KEY = os.getenv("PAGESPEED_API_KEY")


if not API_KEY:
    raise Exception(
        "PAGESPEED_API_KEY tidak ditemukan"
    )


# ==================================================
# FILE PATH
# ==================================================

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "pagespeed_input_before.csv"
)


OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "pagespeed_results_before.csv"
)


LOG_FILE = (
    BASE_DIR
    / "logs"
    / "pagespeed_error.log"
)


# ==================================================
# API CONFIG
# ==================================================

ENDPOINT = (
    "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
)


# ==================================================
# HELPER FUNCTION
# ==================================================

def safe_score(categories, key):

    """
    Mengambil Lighthouse score.
    Jika tidak tersedia -> None
    """

    try:

        score = (
            categories
            .get(key, {})
            .get("score")
        )


        if score is None:
            return None


        return round(score * 100)


    except Exception:

        return None



def safe_metric(audits, key):

    """
    Mengambil numericValue audit.
    Jika tidak tersedia -> None
    """

    try:

        value = (
            audits
            .get(key, {})
            .get("numericValue")
        )


        return value


    except Exception:

        return None



# ==================================================
# READ INPUT CSV
# ==================================================

with open(
    INPUT_FILE,
    encoding="utf-8-sig"
) as f:


    reader = csv.DictReader(
        f,
        delimiter=";"
    )


    jobs = list(reader)


print("="*50)

print(
    f"TOTAL JOBS : {len(jobs)}"
)

print("="*50)



results = []



# ==================================================
# RUN PAGE SPEED TEST
# ==================================================

for index, job in enumerate(
    jobs,
    start=1
):


    test_id = job["Test_ID"]

    url = job["URL"]

    device = job["Device"].lower()



    print(
        f"[{index}/{len(jobs)}] "
        f"{test_id} | {device}"
    )



    params = {

        "url": url,

        "strategy": device,

        "key": API_KEY

    }



    success = False

    error_message = ""



    # retry 3 kali

    for attempt in range(1,4):


        try:


            response = requests.get(

                ENDPOINT,

                params=params,

                timeout=120

            )



            if response.status_code == 200:


                data = response.json()



                lighthouse = (
                    data
                    .get(
                        "lighthouseResult",
                        {}
                    )
                )


                categories = (
                    lighthouse
                    .get(
                        "categories",
                        {}
                    )
                )


                audits = (
                    lighthouse
                    .get(
                        "audits",
                        {}
                    )
                )



                result = {


                    # IDENTITAS

                    "Test_ID":
                        test_id,


                    "Page_ID":
                        job["Page_ID"],


                    "URL":
                        url,


                    "Device":
                        job["Device"],



                    # SEGMENT

                    "Final_Page_Type":
                        job["Final_Page_Type"],


                    "Speed_Test_Segment":
                        job["Speed_Test_Segment"],


                    "Test_Priority":
                        job["Test_Priority"],



                    # LIGHTHOUSE SCORE

                    "Performance":
                        safe_score(
                            categories,
                            "performance"
                        ),


                    "Accessibility":
                        safe_score(
                            categories,
                            "accessibility"
                        ),


                    "Best_Practices":
                        safe_score(
                            categories,
                            "best-practices"
                        ),


                    "SEO":
                        safe_score(
                            categories,
                            "seo"
                        ),



                    # CORE WEB VITALS

                    "FCP":
                        safe_metric(
                            audits,
                            "first-contentful-paint"
                        ),


                    "LCP":
                        safe_metric(
                            audits,
                            "largest-contentful-paint"
                        ),


                    "CLS":
                        safe_metric(
                            audits,
                            "cumulative-layout-shift"
                        ),


                    "Speed_Index":
                        safe_metric(
                            audits,
                            "speed-index"
                        ),


                    "TBT":
                        safe_metric(
                            audits,
                            "total-blocking-time"
                        ),



                    # STATUS

                    "Status":
                        "SUCCESS",



                    "Test_Date":
                        datetime.now()
                        .strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                }



                results.append(result)


                success = True


                break



            else:


                error_message = (
                    f"{test_id} "
                    f"HTTP {response.status_code}"
                )



        except Exception as e:


            error_message = (
                f"{test_id} "
                f"Attempt {attempt}: {e}"
            )



        print(
            f"Retry {attempt}/3..."
        )


        time.sleep(5)



    # =============================================
    # FAILED REQUEST
    # =============================================


    if not success:


        print(
            "FAILED:",
            test_id
        )


        results.append(

            {

                "Test_ID":
                    test_id,

                "Page_ID":
                    job["Page_ID"],

                "URL":
                    url,

                "Device":
                    job["Device"],

                "Status":
                    "FAILED"

            }

        )



        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as log:


            log.write(
                error_message
                + "\n"
            )



    # delay antar request

    time.sleep(3)



# ==================================================
# SAVE RESULT
# ==================================================

if results:


    fieldnames = results[0].keys()



    with open(

        OUTPUT_FILE,

        "w",

        newline="",

        encoding="utf-8-sig"

    ) as f:



        writer = csv.DictWriter(

            f,

            fieldnames=fieldnames,

            delimiter=";"

        )



        writer.writeheader()


        writer.writerows(results)



print("\n")

print("="*50)

print("FINISHED")

print(
    "TOTAL RESULT:",
    len(results)
)

print(
    "OUTPUT:",
    OUTPUT_FILE
)

print("="*50)