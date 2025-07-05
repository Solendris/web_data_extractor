import requests
from bs4 import BeautifulSoup
import csv
import os
import json


with open("source.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    URLS = data.get("urls", [])

headers = {"User-Agent": "Mozilla/5.0"}

# Folder na wyniki
os.makedirs("output_tables", exist_ok=True)


def extract_page_name(url):
    """Zwraca końcowy fragment URL-a jako nazwę pliku"""
    return url.strip("/").split("/")[-1].lower()


for url in URLS:
    print(f"\nPrzetwarzanie: {url}")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Błąd pobierania strony: {response.status_code}")
        continue

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all("table")

    page_name = extract_page_name(url)

    for index, table in enumerate(tables):
        data = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:
                data.append(row_data)

        if not data:
            continue

        filename = f"output_tables/{page_name}_table_{index + 1}.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerows(data)

        print(f"Zapisano: {filename}")
