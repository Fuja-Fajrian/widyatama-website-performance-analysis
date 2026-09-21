import os
import requests
import csv
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

API_KEY = os.getenv("PAGESPEED_API_KEY")

if not API_KEY:
    raise Exception("PAGESPEED_API_KEY tidak ditemukan")

csv_path = BASE_DIR / "data" / "raw" / "pagespeed_input_before.csv"

with open(csv_path, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, delimiter=";")
    first_row = next(reader)

url = first_row["URL"]

print("Testing URL:")
print(url)

endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

params = {
    "url": url,
    "strategy": "mobile",
    "key": API_KEY
}

response = requests.get(endpoint, params=params)

print("\nHTTP Status:")
print(response.status_code)

if response.status_code == 200:
    data = response.json()

    score = (
        data["lighthouseResult"]
        ["categories"]
        ["performance"]
        ["score"]
    )

    print("\nSUCCESS")
    print("Performance Score:")
    print(round(score * 100))

else:
    print("\nFAILED")
    print(response.text)