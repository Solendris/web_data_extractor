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
os.makedirs("output_stats", exist_ok=True)


def extract_page_name(url):
    """Zwraca końcowy fragment URL-a jako nazwę pliku"""
    return url.strip("/").split("/")[-1].lower()


def extract_stats_section(soup, page_name):
    """Wyciąga sekcję ze statystykami jednostki (jak na stronie Nuclear_Rockets)"""
    stats_data = []
    
    # Szukamy sekcji ze statystykami - może być w różnych kontenerach
    possible_containers = [
        soup.find('div', class_='pi-item-spacing'),
        soup.find('div', class_='portable-infobox'),
        soup.find('aside', class_='portable-infobox'),
        soup.find('div', {'data-source': True}),
    ]
    
    # Sprawdzamy każdy możliwy kontener
    for container in possible_containers:
        if not container:
            continue
            
        # Szukamy par klucz-wartość w różnych formatach
        stat_items = container.find_all(['div', 'li', 'tr'])
        
        for item in stat_items:
            # Próbujemy wyciągnąć tekst z elementu
            text = item.get_text(strip=True)
            
            # Sprawdzamy czy zawiera typowe statystyki
            if any(keyword in text.lower() for keyword in ['hitpoints', 'speed', 'attack', 'range', 'vs.', 'combat']):
                # Próbujemy podzielić na klucz i wartość
                if ':' in text:
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        stats_data.append([parts[0].strip(), parts[1].strip()])
                elif text and len(text) > 2:
                    # Jeśli nie ma dwukropka, zapisujemy jako pojedynczą wartość
                    stats_data.append([text, ''])
    
    # Alternatywne podejście - szukamy konkretnych wzorców
    if not stats_data:
        # Szukamy wszystkich elementów zawierających liczby i statystyki
        all_elements = soup.find_all(text=True)
        current_stat = None
        
        for element in all_elements:
            text = element.strip()
            if not text:
                continue
                
            # Sprawdzamy czy to nazwa statystyki
            if any(keyword in text.lower() for keyword in ['hitpoints', 'speed', 'attack', 'range', 'view range']):
                current_stat = text
            # Sprawdzamy czy to wartość (liczba)
            elif current_stat and (text.isdigit() or any(char.isdigit() for char in text)):
                stats_data.append([current_stat, text])
                current_stat = None
    
    # Zapisujemy dane jeśli coś znaleźliśmy
    if stats_data:
        filename = f"output_stats/{page_name}_stats.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["Statistic", "Value"])  # Nagłówek
            writer.writerows(stats_data)
        print(f"Zapisano statystyki: {filename}")
        return True
    
    return False


def extract_combat_section(soup, page_name):
    """Wyciąga sekcję Combat z danymi vs. różne typy jednostek"""
    combat_data = []
    
    # Szukamy sekcji Combat
    combat_section = None
    
    # Różne sposoby znalezienia sekcji Combat
    possible_selectors = [
        soup.find('h3', string=lambda text: text and 'combat' in text.lower()),
        soup.find('h2', string=lambda text: text and 'combat' in text.lower()),
        soup.find('div', string=lambda text: text and 'combat' in text.lower()),
        soup.find(text=lambda text: text and 'combat' in text.lower() if text else False)
    ]
    
    for selector in possible_selectors:
        if selector:
            # Znajdź rodzica lub następny element zawierający dane
            if hasattr(selector, 'find_next_sibling'):
                combat_section = selector.find_next_sibling()
            elif hasattr(selector, 'parent'):
                combat_section = selector.parent
            break
    
    if combat_section:
        # Szukamy wszystkich elementów zawierających "vs."
        vs_elements = combat_section.find_all(text=lambda text: text and 'vs.' in text.lower() if text else False)
        
        for vs_element in vs_elements:
            # Próbujemy znaleźć powiązane wartości
            parent = vs_element.parent if hasattr(vs_element, 'parent') else None
            if parent:
                # Szukamy liczb w tym samym kontenerze lub sąsiednich
                numbers = []
                for sibling in parent.find_all(text=True):
                    if sibling.strip().isdigit():
                        numbers.append(sibling.strip())
                
                if numbers:
                    combat_data.append([vs_element.strip(), ' | '.join(numbers)])
    
    # Alternatywne podejście - szukamy wzorców "vs. X" w całym dokumencie
    if not combat_data:
        all_text = soup.get_text()
        lines = all_text.split('\n')
        
        for i, line in enumerate(lines):
            if 'vs.' in line.lower():
                # Sprawdzamy następne linie w poszukiwaniu liczb
                values = []
                for j in range(1, 4):  # Sprawdzamy 3 następne linie
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        if next_line.isdigit() or any(char.isdigit() for char in next_line):
                            values.append(next_line)
                
                if values:
                    combat_data.append([line.strip(), ' | '.join(values)])
    
    # Zapisujemy dane combat jeśli coś znaleźliśmy
    if combat_data:
        filename = f"output_stats/{page_name}_combat.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["Combat Type", "Values"])  # Nagłówek
            writer.writerows(combat_data)
        print(f"Zapisano dane combat: {filename}")
        return True
    
    return False


for url in URLS:
    print(f"\nPrzetwarzanie: {url}")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Błąd pobierania strony: {response.status_code}")
        continue

    soup = BeautifulSoup(response.text, 'html.parser')
    page_name = extract_page_name(url)
    
    # Próbujemy wyciągnąć standardowe tabele
    tables = soup.find_all("table")
    table_found = False
    
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

        print(f"Zapisano tabelę: {filename}")
        table_found = True
    
    # Jeśli nie znaleźliśmy standardowych tabel, próbujemy wyciągnąć sekcje statystyk
    if not table_found:
        print(f"Nie znaleziono standardowych tabel dla {page_name}, próbuję wyciągnąć sekcje statystyk...")
        
        stats_extracted = extract_stats_section(soup, page_name)
        combat_extracted = extract_combat_section(soup, page_name)
        
        if not stats_extracted and not combat_extracted:
            print(f"Nie udało się wyciągnąć żadnych danych ze strony {page_name}")
            
            # Zapisujemy surowy tekst do analizy
            filename = f"output_stats/{page_name}_raw_text.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(soup.get_text())
            print(f"Zapisano surowy tekst do analizy: {filename}")

print("\nZakończono przetwarzanie wszystkich stron.")