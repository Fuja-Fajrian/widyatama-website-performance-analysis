import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR /
    "data" /
    "processed" /
    "pagespeed_results_before.csv"
)

OUTPUT_FILE = (
    BASE_DIR /
    "data" /
    "processed" /
    "pagespeed_results_clean.csv"
)


def clean_metric(value, metric):

    if value == "" or value is None:
        return value

    try:

        x = float(value)

        # metric waktu (ms)
        if metric in [
            "FCP",
            "LCP",
            "Speed_Index",
            "TBT"
        ]:

            # buang error excel scientific
            while x > 1000000:
                x = x / 1000

            return round(x,0)


        # CLS
        elif metric == "CLS":

            while x > 10:
                x = x / 1000

            return round(x,4)


        else:

            return x


    except:

        return value



metrics = [
    "FCP",
    "LCP",
    "CLS",
    "Speed_Index",
    "TBT"
]


with open(
    INPUT_FILE,
    encoding="utf-8-sig"
) as f:

    reader = csv.DictReader(
        f,
        delimiter=";"
    )

    rows = list(reader)



for row in rows:

    for metric in metrics:

        if metric in row:

            row[metric] = clean_metric(
                row[metric],
                metric
            )



with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=rows[0].keys(),
        delimiter=";"
    )

    writer.writeheader()
    writer.writerows(rows)


print("DONE")
print(OUTPUT_FILE)