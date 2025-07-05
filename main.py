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

# Folder na wyniki - tylko jeden folder
os.makedirs("output_tables", exist_ok=True)


def extract_page_name(url):
    """Zwraca końcowy fragment URL-a jako nazwę pliku"""
    return url.strip("/").split("/")[-1].lower()


def clean_text(text):
    """Czyści tekst z niepotrzebnych znaków"""
    if not text:
        return ""
    # Usuwa nadmiarowe białe znaki i znaki specjalne
    cleaned = re.sub(r'\s+', ' ', str(text).strip())
    # Usuwa znaki, które mogą powodować problemy w CSV
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return cleaned


def extract_nuclear_rockets_data(soup, page_name):
    """Specjalna funkcja do wyciągania danych ze strony Nuclear_Rockets"""
    stats_data = []
    combat_data = []
    
    # Szukamy wszystkich elementów zawierających tekst
    all_text_elements = soup.find_all(string=True)
    
    # Wzorce do rozpoznawania statystyk - bardziej precyzyjne
    stat_patterns = {
        'Hitpoints': r'hitpoints?\s*[:\-]?\s*(\d+)',
        'Speed': r'speed\s*[:\-]?\s*(\d+)',
        'Attack': r'attack\s*[:\-]?\s*(\d+)', 
        'Range': r'(?:attack\s+)?range\s*[:\-]?\s*(\d+)',
        'View Range': r'view\s*range\s*[:\-]?\s*(\d+)'
    }
    
    # Wzorce do rozpoznawania combat - bardziej precyzyjne
    combat_patterns = {
        'vs. Unarmored': r'vs\.?\s*unarmored\s*[:\-]?\s*(\d+)',
        'vs. Airplane': r'vs\.?\s*airplane\s*[:\-]?\s*(\d+)', 
        'vs. Light Armor': r'vs\.?\s*light\s*armor\s*[:\-]?\s*(\d+)',
        'vs. Heavy Armor': r'vs\.?\s*heavy\s*armor\s*[:\-]?\s*(\d+)',
        'vs. Ship': r'vs\.?\s*ship\s*[:\-]?\s*(\d+)',
        'vs. Submarine': r'vs\.?\s*submarine\s*[:\-]?\s*(\d+)',
        'vs. Buildings': r'vs\.?\s*buildings?\s*[:\-]?\s*(\d+)',
        'vs. Morale': r'vs\.?\s*morale\s*[:\-]?\s*(\d+)'
    }
    
    # Łączymy cały tekst strony
    full_text = ' '.join([clean_text(elem) for elem in all_text_elements if elem and elem.strip()])
    full_text_lower = full_text.lower()
    
    print(f"Analizuję tekst dla {page_name}...")
    
    # Wyciągamy statystyki podstawowe
    for stat_name, pattern in stat_patterns.items():
        matches = re.findall(pattern, full_text_lower, re.IGNORECASE)
        if matches:
            # Bierzemy pierwszą znalezioną wartość
            value = clean_text(matches[0])
            stats_data.append([stat_name, value])
            print(f"Znaleziono {stat_name}: {value}")
    
    # Wyciągamy dane combat
    for combat_name, pattern in combat_patterns.items():
        matches = re.findall(pattern, full_text_lower, re.IGNORECASE)
        if matches:
            # Bierzemy pierwszą znalezioną wartość
            value = clean_text(matches[0])
            combat_data.append([combat_name, value])
            print(f"Znaleziono {combat_name}: {value}")
    
    # Alternatywne podejście - szukamy w strukturze HTML
    if not stats_data and not combat_data:
        print("Próbuję alternatywne podejście...")
        
        # Szukamy divów lub innych kontenerów z danymi
        containers = soup.find_all(['div', 'span', 'td', 'th', 'li'])
        
        for container in containers:
            text = clean_text(container.get_text()).lower()
            
            # Sprawdzamy czy zawiera interesujące nas dane
            if any(keyword in text for keyword in ['hitpoints', 'speed', 'attack', 'range', 'vs']):
                # Próbujemy wyciągnąć liczby z tego kontenera
                numbers = re.findall(r'\d+', text)
                if numbers and len(text) < 100:  # Ignorujemy bardzo długie teksty
                    clean_label = clean_text(text).title()
                    if 'vs' in text:
                        combat_data.append([clean_label, numbers[0]])
                    else:
                        stats_data.append([clean_label, numbers[0]])
    
    # Zapisujemy statystyki do output_tables
    if stats_data:
        filename = f"output_tables/{page_name}_stats.csv"
        try:
            with open(filename, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["Statistic", "Value"])
                for row in stats_data:
                    # Upewniamy się, że każdy element jest stringiem
                    clean_row = [clean_text(str(cell)) for cell in row]
                    writer.writerow(clean_row)
            print(f"✓ Zapisano statystyki: {filename}")
        except Exception as e:
            print(f"✗ Błąd zapisu statystyk: {e}")
    
    # Zapisujemy dane combat do output_tables
    if combat_data:
        filename = f"output_tables/{page_name}_combat.csv"
        try:
            with open(filename, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["Combat Type", "Damage"])
                for row in combat_data:
                    # Upewniamy się, że każdy element jest stringiem
                    clean_row = [clean_text(str(cell)) for cell in row]
                    writer.writerow(clean_row)
            print(f"✓ Zapisano dane combat: {filename}")
        except Exception as e:
            print(f"✗ Błąd zapisu combat: {e}")
    
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
                value = clean_text(value_elem.get_text())
                readable_name = clean_text(data_source.replace('_', ' ').title())
                stats_data.append([readable_name, value])
                print(f"Infobox - {readable_name}: {value}")
    
    if stats_data:
        filename = f"output_tables/{page_name}_infobox.csv"
        try:
            with open(filename, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["Property", "Value"])
                for row in stats_data:
                    # Upewniamy się, że każdy element jest stringiem
                    clean_row = [clean_text(str(cell)) for cell in row]
                    writer.writerow(clean_row)
            print(f"✓ Zapisano dane infobox: {filename}")
            return True
        except Exception as e:
            print(f"✗ Błąd zapisu infobox: {e}")
    
    return False


for url in URLS:
    print(f"\n{'='*50}")
    print(f"Przetwarzanie: {url}")
    print(f"{'='*50}")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Rzuca wyjątek dla kodów błędów HTTP
    except requests.RequestException as e:
        print(f"Błąd pobierania strony: {e}")
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
            row_data = [clean_text(cell.get_text()) for cell in cells]
            if row_data and any(cell.strip() for cell in row_data):  # Sprawdzamy czy wiersz nie jest pusty
                data.append(row_data)

        if len(data) > 1:  # Tylko jeśli tabela ma więcej niż jeden wiersz
            filename = f"output_tables/{page_name}_table_{index + 1}.csv"
            try:
                with open(filename, "w", newline='', encoding="utf-8") as f:
                    writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
                    writer.writerows(data)
                print(f"✓ Zapisano tabelę: {filename}")
                data_extracted = True
            except Exception as e:
                print(f"✗ Błąd zapisu tabeli: {e}")
    
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
    
    # Jeśli nic nie znaleźliśmy, zapisujemy surowy tekst do output_tables
    if not data_extracted:
        print(f"Nie udało się wyciągnąć żadnych danych ze strony {page_name}")
        
        # Zapisujemy fragment HTML do analizy w output_tables
        filename = f"output_tables/{page_name}_debug.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(str(soup.prettify()))
            print(f"Zapisano HTML do debugowania: {filename}")
        except Exception as e:
            print(f"Błąd zapisu HTML: {e}")

print(f"\n{'='*50}")
print("Zakończono przetwarzanie wszystkich stron.")
print(f"{'='*50}")