import requests
from bs4 import BeautifulSoup
import csv
import os

URL = "https://call-of-war-by-bytro.fandom.com/wiki/Militia"
headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(URL, headers=headers)
print("Status:", response.status_code)

# Utwórz folder na wyniki
os.makedirs("output_tables", exist_ok=True)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all("table")

    for index, table in enumerate(tables):
        data = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:
                data.append(row_data)

        # Pomijaj puste tabele
        if not data:
            continue

        # Nazwa pliku: militia_table_1.csv, militia_table_2.csv, itd.
        filename = f"output_tables/militia_table_{index + 1}.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerows(data)

        print(f"Zapisano: {filename}")

else:
    print("Nie udało się pobrać strony:", response.status_code)
