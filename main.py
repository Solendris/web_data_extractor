import requests
from bs4 import BeautifulSoup

URL = "https://call-of-war-by-bytro.fandom.com/wiki/Militia"

headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(URL, headers=headers)
print(response.status_code)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all("table")
    for index, table in enumerate(tables):
        print(f"\n--- Tabela {index + 1} ---\n")
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            cell_text = [cell.get_text(strip=True) for cell in cells]
            print("\t".join(cell_text))
else:
    print("Nie udało się pobrać strony:", response.status_code)
