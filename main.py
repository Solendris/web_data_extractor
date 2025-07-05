import requests
from bs4 import BeautifulSoup
import csv
import os
import json
import re


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


def extract_nuclear_rockets_data(soup, page_name):
    """Specjalna funkcja do wyciągania danych ze strony Nuclear_Rockets"""
    stats_data = []
    combat_data = []
    
    # Szukamy wszystkich elementów zawierających tekst
    all_elements = soup.find_all(text=True)
    
    # Wzorce do rozpoznawania statystyk
    stat_patterns = {
        'hitpoints': r'hitpoints?\s*(\d+)',
        'speed': r'speed\s*(\d+)',
        'attack': r'attack\s*(\d+)',
        'range': r'range\s*(\d+)',
        'view_range': r'view\s*range\s*(\d+)'
    }
    
    # Wzorce do rozpoznawania combat
    combat_patterns = {
        'vs_unarmored': r'vs\.?\s*unarmored\s*(\d+)',
        'vs_airplane': r'vs\.?\s*airplane\s*(\d+)', 
        'vs_light_armor': r'vs\.?\s*light\s*armor\s*(\d+)',
        'vs_heavy_armor': r'vs\.?\s*heavy\s*armor\s*(\d+)',
        'vs_ship': r'vs\.?\s*ship\s*(\d+)',
        'vs_submarine': r'vs\.?\s*submarine\s*(\d+)',
        'vs_buildings': r'vs\.?\s*buildings?\s*(\d+)',
        'vs_morale': r'vs\.?\s*morale\s*(\d+)'
    }
    
    # Łączymy cały tekst strony
    full_text = ' '.join([elem.strip() for elem in all_elements if elem.strip()])
    full_text = full_text.lower()
    
    print(f"Analizuję tekst dla {page_name}...")
    
    # Wyciągamy statystyki podstawowe
    for stat_name, pattern in stat_patterns.items():
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            # Bierzemy pierwszą znalezioną wartość
            value = matches[0]
            readable_name = stat_name.replace('_', ' ').title()
            stats_data.append([readable_name, value])
            print(f"Znaleziono {readable_name}: {value}")
    
    # Wyciągamy dane combat
    for combat_name, pattern in combat_patterns.items():
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            # Bierzemy pierwszą znalezioną wartość
            value = matches[0]
            readable_name = combat_name.replace('_', ' ').replace('vs ', 'vs. ').title()
            combat_data.append([readable_name, value])
            print(f"Znaleziono {readable_name}: {value}")
    
    # Alternatywne podejście - szukamy w strukturze HTML
    if not stats_data and not combat_data:
        print("Próbuję alternatywne podejście...")
        
        # Szukamy divów lub innych kontenerów z danymi
        containers = soup.find_all(['div', 'span', 'td', 'th', 'li'])
        
        for container in containers:
            text = container.get_text(strip=True).lower()
            
            # Sprawdzamy czy zawiera interesujące nas dane
            if any(keyword in text for keyword in ['hitpoints', 'speed', 'attack', 'range', 'vs']):
                # Próbujemy wyciągnąć liczby z tego kontenera
                numbers = re.findall(r'\d+', text)
                if numbers:
                    if 'vs' in text:
                        combat_data.append([text.title(), numbers[0]])
                    else:
                        stats_data.append([text.title(), numbers[0]])
    
    # Zapisujemy statystyki
    if stats_data:
        filename = f"output_stats/{page_name}_stats.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["Statistic", "Value"])
            writer.writerows(stats_data)
        print(f"Zapisano statystyki: {filename}")
    
    # Zapisujemy dane combat
    if combat_data:
        filename = f"output_stats/{page_name}_combat.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["Combat Type", "Damage"])
            writer.writerows(combat_data)
        print(f"Zapisano dane combat: {filename}")
    
    return len(stats_data) > 0 or len(combat_data) > 0


def extract_infobox_data(soup, page_name):
    """Wyciąga dane z infobox (portable-infobox)"""
    stats_data = []
    
    # Szukamy infobox
    infobox = soup.find('aside', class_='portable-infobox') or soup.find('div', class_='portable-infobox')
    
    if infobox:
        print(f"Znaleziono infobox dla {page_name}")
        
        # Szukamy wszystkich par data-source/wartość
        data_items = infobox.find_all('div', {'data-source': True})
        
        for item in data_items:
            data_source = item.get('data-source', '')
            
            # Szukamy wartości w tym elemencie
            value_elem = item.find('div', class_='pi-data-value')
            if value_elem:
                value = value_elem.get_text(strip=True)
                stats_data.append([data_source.replace('_', ' ').title(), value])
                print(f"Infobox - {data_source}: {value}")
    
    if stats_data:
        filename = f"output_stats/{page_name}_infobox.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["Property", "Value"])
            writer.writerows(stats_data)
        print(f"Zapisano dane infobox: {filename}")
        return True
    
    return False


for url in URLS:
    print(f"\n{'='*50}")
    print(f"Przetwarzanie: {url}")
    print(f"{'='*50}")
    
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Błąd pobierania strony: {response.status_code}")
        continue

    soup = BeautifulSoup(response.text, 'html.parser')
    page_name = extract_page_name(url)
    
    data_extracted = False
    
    # Próbujemy wyciągnąć standardowe tabele
    tables = soup.find_all("table")
    
    for index, table in enumerate(tables):
        data = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data and any(cell.strip() for cell in row_data):  # Sprawdzamy czy wiersz nie jest pusty
                data.append(row_data)

        if len(data) > 1:  # Tylko jeśli tabela ma więcej niż jeden wiersz
            filename = f"output_tables/{page_name}_table_{index + 1}.csv"
            with open(filename, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerows(data)

            print(f"Zapisano tabelę: {filename}")
            data_extracted = True
    
    # Jeśli to strona Nuclear_Rockets, używamy specjalnej funkcji
    if 'nuclear_rockets' in page_name.lower():
        print("Wykryto stronę Nuclear_Rockets - używam specjalnej funkcji...")
        nuclear_data_extracted = extract_nuclear_rockets_data(soup, page_name)
        if nuclear_data_extracted:
            data_extracted = True
    
    # Próbujemy wyciągnąć dane z infobox
    infobox_extracted = extract_infobox_data(soup, page_name)
    if infobox_extracted:
        data_extracted = True
    
    # Jeśli nic nie znaleźliśmy, zapisujemy surowy tekst
    if not data_extracted:
        print(f"Nie udało się wyciągnąć żadnych danych ze strony {page_name}")
        
        # Zapisujemy fragment HTML do analizy
        filename = f"output_stats/{page_name}_debug.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(str(soup.prettify()))
        print(f"Zapisano HTML do debugowania: {filename}")

print(f"\n{'='*50}")
print("Zakończono przetwarzanie wszystkich stron.")
print(f"{'='*50}")