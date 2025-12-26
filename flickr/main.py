"""
Flickr Album Downloader
========================
Pobiera zdjęcia z albumu Flickr w NAJWYŻSZEJ DOSTĘPNEJ ROZDZIELCZOŚCI.

Program automatycznie wykrywa i pobiera zdjęcia w najlepszej jakości:
- Original (oryginał, jeśli dostępny)
- X-Large 5K, 4K, 3K
- Large 2048, 1600, 1024
- Medium (jako fallback)

Zapisuje:
- Zdjęcia w folderze z nazwami zgodnie z tytułem w albumie
- Plik photo_urls.txt z listą: nazwa_pliku, URL, tytuł, rozdzielczość
- Plik failed_downloads.txt z listą nieudanych pobrań

Każde zdjęcie jest pobierane indywidualnie z jego strony /sizes/, 
aby uzyskać najlepszą możliwą jakość.

Funkcje inteligentnego wznowienia:
✓ Automatycznie pomija już pobrane pliki
✓ Wznawia pobieranie nieudanych plików przy ponownym uruchomieniu
✓ Wykrywa uszkodzone pliki (< 1KB) i pobiera je ponownie
✓ Śledzi postęp w plikach tekstowych
✓ Obsługa rate limit (HTTP 429) - automatyczna pauza 30 minut

Uruchom program ponownie, aby kontynuować przerwane pobieranie!
"""

import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import threading
from queue import Queue
from tqdm import tqdm

class FlickrAlbumDownloader:
    def __init__(self, album_url, download_folder="flickr_photos"):
        self.album_url = album_url.rstrip('/')
        self.download_folder = download_folder
        self.driver = None
        self.photo_urls = set()  # Używamy set aby uniknąć duplikatów
        self.urls_file = os.path.join(download_folder, "photo_urls.txt")
        self.failed_file = os.path.join(download_folder, "failed_downloads.txt")
        self.download_queue = Queue()
        self.download_stats = {"successful": 0, "failed": 0, "skipped": 0, "resumed": 0, "skipped_scan": 0, "from_cache": 0}
        self.download_lock = threading.Lock()
        self.rate_limit_event = threading.Event()  # Sygnał pauzy przy rate limit
        self.rate_limit_event.set()  # Domyślnie włączony (nie pauzowany)
        self.downloaded_files = set()  # Już pobrane pliki
        self.failed_files = set()  # Pliki, które się nie udały
        self.known_urls = {}  # Mapowanie: filename -> (url, title, size)
        self.global_index = 0  # Globalny licznik zdjęć dla kolejki
        self.total_photos = 0  # Całkowita liczba zdjęć w albumie
        self.download_pbar = None  # Progress bar dla pobierania
        
        # Utwórz folder na zdjęcia
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        
        # Wczytaj listę już pobranych plików i znanych URL-i
        self._load_known_urls()
        self._load_downloaded_files()
        self._load_failed_files()
    
    def _load_known_urls(self):
        """Wczytaj znane URL-e z pliku photo_urls.txt"""
        if os.path.exists(self.urls_file):
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        filename = parts[0]
                        url = parts[1]
                        title = parts[2] if len(parts) > 2 else ""
                        size = parts[3] if len(parts) > 3 else "unknown"
                        self.known_urls[filename] = (url, title, size)
                        self.photo_urls.add(url)  # Dodaj do zestawu URL-i
            
            if self.known_urls:
                print(f"📋 Wczytano {len(self.known_urls)} znanych URL-i z pliku")
    
    def _load_downloaded_files(self):
        """Wczytaj listę już pobranych plików z folderu"""
        if os.path.exists(self.download_folder):
            for filename in os.listdir(self.download_folder):
                if filename.lower().endswith('.jpg'):
                    # Sprawdź czy plik nie jest pusty lub zbyt mały (< 1KB = prawdopodobnie błędny)
                    filepath = os.path.join(self.download_folder, filename)
                    if os.path.getsize(filepath) > 1024:
                        self.downloaded_files.add(filename)
        
        if self.downloaded_files:
            print(f"✓ Znaleziono {len(self.downloaded_files)} już pobranych plików")
    
    def _load_failed_files(self):
        """Wczytaj listę plików, które wcześniej się nie udały"""
        if os.path.exists(self.failed_file):
            with open(self.failed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Format: filename\turl\terror
                    parts = line.strip().split('\t')
                    if parts:
                        self.failed_files.add(parts[0])
            
            if self.failed_files:
                print(f"⚠ Znaleziono {len(self.failed_files)} nieudanych pobrań do ponowienia")
    
    def _save_failed_download(self, filename, url, error):
        """Zapisz informację o nieudanym pobraniu"""
        with open(self.failed_file, 'a', encoding='utf-8') as f:
            f.write(f"{filename}\t{url}\t{error}\n")
    
    def _is_already_downloaded(self, filename):
        """Sprawdź czy plik jest już pobrany (i nie jest uszkodzony)"""
        if filename in self.downloaded_files:
            return True
        
        # Sprawdź fizycznie w folderze
        filepath = os.path.join(self.download_folder, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
            self.downloaded_files.add(filename)
            return True
        
        return False
    
    def setup_driver(self):
        """Konfiguracja Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Usuń tę linię jeśli chcesz widzieć przeglądarkę
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
    
    def get_total_photos_count(self):
        """Pobierz całkowitą liczbę zdjęć z albumu ze strony"""
        try:
            # Szukaj elementu z liczbą zdjęć: <span class="stat photo-count">257 photos</span>
            count_element = self.driver.find_element(By.CSS_SELECTOR, ".stat.photo-count")
            text = count_element.text.strip()
            # Wyciągnij liczbę z tekstu "257 photos"
            match = re.search(r'(\d+)', text)
            if match:
                return int(match.group(1))
        except:
            pass
        
        # Fallback - spróbuj innych selektorów
        try:
            page_source = self.driver.page_source
            match = re.search(r'(\d+)\s*photos', page_source, re.IGNORECASE)
            if match:
                return int(match.group(1))
        except:
            pass
        
        return 0
    
    def get_total_pages(self):
        """Wykryj całkowitą liczbę stron w albumie"""
        max_page = 1
        
        try:
            # METODA 1: Szukaj linków paginacji z różnymi selektorami
            selectors = [
                ".pagination-view a[href*='page']",
                "a[href*='/page']",
                ".pagination a[href*='page']",
                "[class*='pagination'] a[href*='page']"
            ]
            
            for selector in selectors:
                pagination_links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for link in pagination_links:
                    href = link.get_attribute('href')
                    # Wyciągnij numer strony z URL
                    match = re.search(r'/page(\d+)', href)
                    if match:
                        page_num = int(match.group(1))
                        max_page = max(max_page, page_num)
                
                if max_page > 1:
                    break
            
            # METODA 2: Szukaj tekstu typu "1 of 3" lub "Strona 1 z 3"
            if max_page == 1:
                try:
                    page_text = self.driver.find_element(By.CSS_SELECTOR, ".pagination-view").text
                    match = re.search(r'(\d+)\s*(?:of|z)\s*(\d+)', page_text, re.IGNORECASE)
                    if match:
                        max_page = int(match.group(2))
                except:
                    pass
            
            # METODA 3: Szukaj całkowitej liczby zdjęć w albumie i oblicz strony
            if max_page == 1:
                try:
                    # Flickr zazwyczaj pokazuje liczbę zdjęć np. "257 photos"
                    count_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='count'], [class*='total'], .album-info")
                    for el in count_elements:
                        text = el.text
                        match = re.search(r'(\d+)\s*(?:photos|zdjęć|elementów|items)', text, re.IGNORECASE)
                        if match:
                            total_photos = int(match.group(1))
                            # Flickr pokazuje ~100 zdjęć na stronę
                            max_page = (total_photos + 99) // 100  # Zaokrąglij w górę
                            print(f"  📊 Wykryto {total_photos} zdjęć w albumie")
                            break
                except:
                    pass
            
            # METODA 4: Sprawdź nagłówek strony lub metadane
            if max_page == 1:
                try:
                    # Szukaj w tytule strony lub innych miejscach
                    page_source = self.driver.page_source
                    matches = re.findall(r'(\d+)\s*(?:photos|items|zdjęć)', page_source, re.IGNORECASE)
                    for m in matches:
                        count = int(m)
                        if count > 100:  # Prawdopodobnie to całkowita liczba
                            max_page = (count + 99) // 100
                            print(f"  📊 Wykryto ~{count} zdjęć (z metadanych)")
                            break
                except:
                    pass
            
            return max_page
            
        except Exception as e:
            print(f"Nie można wykryć liczby stron, zakładam 1 stronę: {e}")
            return 1
    
    def scroll_to_load_all_on_page(self):
        """Przewiń stronę, aby załadować wszystkie zdjęcia na bieżącej stronie"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        photos_loaded = 0
        stagnant_count = 0
        
        while stagnant_count < 3:  # Jeśli 3 razy z rzędu brak zmian, kończymy
            # Przewiń do końca strony
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            # Sprawdź ile zdjęć jest załadowanych
            current_photos = len(self.driver.find_elements(By.CSS_SELECTOR, "img[src*='staticflickr.com']"))
            if current_photos > photos_loaded:
                photos_loaded = current_photos
                stagnant_count = 0
            else:
                stagnant_count += 1
            
            # Sprawdź czy osiągnięto koniec strony
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                stagnant_count += 1
            else:
                stagnant_count = 0
            last_height = new_height
        
        return photos_loaded
    
    def get_highest_resolution_url(self, photo_page_url):
        """
        Otwiera stronę zdjęcia w najwyższej rozdzielczości i zwraca bezpośredni URL
        
        Strategia:
        1. Próbuje otworzyć /sizes/5k/ (najwyższa rozdzielczość X-Large 5K)
        2. Jeśli nie istnieje, Flickr przekieruje na /sizes/o/ lub najwyższą dostępną
        3. Pobiera URL obrazka z img src (zawiera prawidłowy secret dla tego zdjęcia)
        """
        try:
            # Wykryj użytkownika i ID zdjęcia z URL
            match = re.search(r'/photos/([^/]+)/(\d+)', photo_page_url)
            if not match:
                return None, None
            
            username = match.group(1)
            photo_id = match.group(2)
            
            # Lista rozdzielczości do sprawdzenia (od najwyższej do najniższej)
            # Flickr automatycznie przekieruje na najwyższą dostępną jeśli żądana nie istnieje
            size_urls_to_try = [
                f"https://www.flickr.com/photos/{username}/{photo_id}/sizes/5k/",
                f"https://www.flickr.com/photos/{username}/{photo_id}/sizes/4k/",
                f"https://www.flickr.com/photos/{username}/{photo_id}/sizes/o/",
            ]
            
            # Otwórz stronę z rozmiarami w nowej karcie
            self.driver.execute_script(f"window.open('{size_urls_to_try[0]}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            time.sleep(1.5)  # Poczekaj na załadowanie i ewentualne przekierowanie
            
            # Spróbuj znaleźć najwyższą dostępną rozdzielczość
            best_url = None
            best_size_name = None
            
            # PRIORYTET 1: Sprawdź obrazek na stronie (zawiera secret i jest w najwyższej dostępnej rozdzielczości)
            try:
                img = self.driver.find_element(By.CSS_SELECTOR, "#allsizes-photo img")
                best_url = img.get_attribute('src')
                
                # Wykryj rozmiar z URL (np. _5k.jpg, _4k.jpg, _o.jpg)
                size_match = re.search(r'_([a-z0-9]+)\.jpg$', best_url)
                if size_match:
                    best_size_name = size_match.group(1).upper()
                    
                    # Zmapuj kod na czytelną nazwę
                    size_names = {
                        'O': 'Original',
                        '5K': 'X-Large 5K',
                        '4K': 'X-Large 4K', 
                        '3K': 'X-Large 3K',
                        'K': 'Large 2048',
                        'H': 'Large 1600',
                        'L': 'Large 1024',
                        'C': 'Medium 800',
                        'Z': 'Medium 640',
                        'B': 'Large 1024'
                    }
                    best_size_name = size_names.get(best_size_name, best_size_name)
            except:
                pass
            
            # PRIORYTET 2: Jeśli nie ma obrazka, sprawdź link Original w menu Sizes
            if not best_url:
                try:
                    # Link do oryginału: <a href="/photos/.../sizes/o/">Original</a>
                    original_link = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/sizes/o/']")
                    # Przejdź do strony z oryginałem
                    original_url = original_link.get_attribute('href')
                    self.driver.get(original_url)
                    time.sleep(1)
                    
                    img = self.driver.find_element(By.CSS_SELECTOR, "#allsizes-photo img")
                    best_url = img.get_attribute('src')
                    best_size_name = "Original"
                except:
                    pass
            
            # Zamknij kartę i wróć do głównej
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            return best_url, best_size_name
            
        except Exception as e:
            # W razie błędu, zamknij dodatkowe karty i wróć do głównej
            try:
                while len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None, None
    
    def extract_photo_urls_from_page(self):
        """Wyciągnij wszystkie URL-e zdjęć z bieżącej strony wraz z nazwami"""
        # Znajdź wszystkie karty zdjęć
        photo_cards = self.driver.find_elements(By.CSS_SELECTOR, ".photo-card")
        
        # Licznik dodanych na tej stronie
        added_count = 0
        
        for idx, card in enumerate(photo_cards, 1):
            try:
                # Znajdź link z tytułem
                title_link = card.find_element(By.CSS_SELECTOR, "a.photo-link")
                title = title_link.get_attribute('title')
                photo_page_url = title_link.get_attribute('href')
                
                if photo_page_url and title:
                    # Wyodrębnij ID zdjęcia z URL (np. /photos/user/123456789/ -> 123456789)
                    photo_id_match = re.search(r'/photos/[^/]+/(\d+)', photo_page_url)
                    photo_id = photo_id_match.group(1) if photo_id_match else str(idx)
                    
                    # Wyczyść nazwę pliku (usuń niedozwolone znaki)
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    # Dodaj ID zdjęcia do nazwy pliku dla unikalności
                    filename = f"{safe_title}_{photo_id}.jpg"
                    
                    # PRIORYTET 1: Sprawdź czy plik już istnieje
                    if self._is_already_downloaded(filename):
                        with self.download_lock:
                            self.download_stats["skipped_scan"] += 1
                            # Aktualizuj progressbar dla pominiętych
                            if self.download_pbar:
                                self.download_pbar.update(1)
                                self.download_pbar.set_postfix_str(f"⊘ już: {filename[:30]}...")
                        continue
                    
                    # PRIORYTET 2: Sprawdź czy URL jest już znany z pliku
                    if filename in self.known_urls:
                        url, saved_title, size = self.known_urls[filename]
                        
                        with self.download_lock:
                            self.download_stats["from_cache"] += 1
                            self.global_index += 1
                            current_index = self.global_index
                        
                        # NATYCHMIAST dodaj do kolejki pobierania
                        self.download_queue.put((url, filename, current_index, 0))
                        added_count += 1
                        continue
                    
                    # PRIORYTET 3: Pobierz URL ze strony (tylko jeśli nie mamy go w pliku)
                    high_res_url, size_name = self.get_highest_resolution_url(photo_page_url)
                    
                    if high_res_url:
                        # NAPRAW: usuń podwójne https:
                        if high_res_url.startswith('https:https://'):
                            high_res_url = high_res_url.replace('https:https://', 'https://')
                        elif not high_res_url.startswith('https://'):
                            high_res_url = 'https://' + high_res_url.lstrip('/')
                        
                        # Sprawdź czy to nowe zdjęcie (URL)
                        if high_res_url not in self.photo_urls:
                            self.photo_urls.add(high_res_url)
                            
                            # NATYCHMIAST zapisz URL do pliku
                            self._save_single_url(high_res_url, filename, title, size_name or 'unknown')
                            
                            # NATYCHMIAST dodaj do kolejki pobierania
                            with self.download_lock:
                                self.global_index += 1
                                current_index = self.global_index
                            
                            self.download_queue.put((high_res_url, filename, current_index, 0))
                            added_count += 1
                        
            except Exception as e:
                continue
        
        return added_count
    
    def _save_single_url(self, url, filename, title, size):
        """Zapisz pojedynczy URL do pliku natychmiast po znalezieniu"""
        os.makedirs(self.download_folder, exist_ok=True)
        with open(self.urls_file, 'a', encoding='utf-8') as f:
            f.write(f"{filename}\t{url}\t{title}\t{size}\n")
    
    def save_urls_to_file(self, urls):
        """Zapisz URL-e do pliku"""
        # Upewnij się, że folder istnieje
        os.makedirs(self.download_folder, exist_ok=True)
        
        with open(self.urls_file, 'a', encoding='utf-8') as f:
            for item in urls:
                size_info = item.get('size', 'unknown')
                f.write(f"{item['filename']}\t{item['url']}\t{item['title']}\t{size_info}\n")
    
    def _handle_rate_limit(self):
        """Obsługa rate limit - pauza na 30 minut"""
        print("\n🚫 Wykryto rate limit (HTTP 429)")
        print("⏸️  Pauzowanie pobierania na 30 minut...")
        
        # Zatrzymaj wszystkie wątki
        self.rate_limit_event.clear()
        
        # Pauza 30 minut
        import time
        pause_minutes = 60
        for minute in range(pause_minutes, 0, -1):
            print(f"⏰ Pozostało {minute} minut...", end='\r')
            time.sleep(60)
        
        print("▶️  Wznawianie pobierania...")
        
        # Wznow wszystkie wątki
        self.rate_limit_event.set()
    
    def download_worker(self):
        """Wątek pobierający zdjęcia z kolejki"""
        while True:
            item = self.download_queue.get()
            if item is None:  # Sygnał zakończenia
                break
            
            url, filename, index, total = item
            
            # Sprawdź czy plik już istnieje
            if self._is_already_downloaded(filename):
                with self.download_lock:
                    self.download_stats["skipped"] += 1
                    if self.download_pbar:
                        self.download_pbar.update(1)
                        self.download_pbar.set_postfix_str(f"⊘ {filename[:40]}...")
                self.download_queue.task_done()
                continue
            
            # Sprawdź czy to wcześniej nieudane pobranie
            was_failed = filename in self.failed_files
            
            try:
                # Czekaj na wznowienie jeśli jest rate limit
                self.rate_limit_event.wait()
                
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    filepath = os.path.join(self.download_folder, filename)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Sprawdź czy plik nie jest zbyt mały (prawdopodobnie błąd)
                    if os.path.getsize(filepath) < 1024:
                        os.remove(filepath)
                        raise Exception("Pobrany plik jest zbyt mały (< 1KB)")
                    
                    # Dodaj do listy pobranych
                    self.downloaded_files.add(filename)
                    
                    # Usuń z listy nieudanych (jeśli było)
                    if was_failed:
                        self.failed_files.discard(filename)
                    
                    with self.download_lock:
                        self.download_stats["successful"] += 1
                        if was_failed:
                            self.download_stats["resumed"] += 1
                        if self.download_pbar:
                            self.download_pbar.update(1)
                            self.download_pbar.set_postfix_str(f"✓ {filename[:40]}...")
                else:
                    raise Exception(f"HTTP {response.status_code}")
                            
            except Exception as e:
                error_msg = str(e)[:100]
                
                # Specjalna obsługa rate limit (HTTP 429)
                if "HTTP 429" in error_msg:
                    with self.download_lock:
                        if self.download_pbar:
                            self.download_pbar.set_postfix_str(f"🚫 Rate limit! Pauza...")
                        # Wstrzymaj wszystkie wątki na 30 minut
                        self._handle_rate_limit()
                        # Po pauzie dodaj zdjęcie z powrotem do kolejki
                        self.download_queue.put((url, filename, index, total))
                        self.download_queue.task_done()
                        continue
                
                # Zapisz do listy nieudanych
                if filename not in self.failed_files:
                    self._save_failed_download(filename, url, error_msg)
                    self.failed_files.add(filename)
                
                with self.download_lock:
                    self.download_stats["failed"] += 1
                    if self.download_pbar:
                        self.download_pbar.update(1)
                        self.download_pbar.set_postfix_str(f"✗ {filename[:40]}...")
            
            finally:
                self.download_queue.task_done()
    
    def process_all_pages(self):
        """Przejdź przez wszystkie strony albumu i zbierz URL-e zdjęć"""
        print("Wykrywanie liczby stron...")
        
        # Załaduj pierwszą stronę
        self.driver.get(self.album_url)
        
        # Poczekaj na załadowanie
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='staticflickr.com']"))
        )
        
        # Pobierz całkowitą liczbę zdjęć w albumie
        self.total_photos = self.get_total_photos_count()
        if self.total_photos > 0:
            print(f"📊 Wykryto {self.total_photos} zdjęć w albumie")
        
        # Wykryj całkowitą liczbę stron
        total_pages = self.get_total_pages()
        print(f"✓ Wykryto {total_pages} stron")
        
        # Utwórz progressbar dla pobierania
        print()  # Nowa linia przed progressbarem
        self.download_pbar = tqdm(
            total=self.total_photos if self.total_photos > 0 else None,
            desc="📥 Pobieranie",
            unit=" zdjęć",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            position=0,
            leave=True
        )
        
        # Uruchom wątki pobierające (4 wątki równolegle)
        num_workers = 4
        download_threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=self.download_worker, daemon=True)
            t.start()
            download_threads.append(t)
        
        # Przetwórz każdą stronę (bez printów - tylko progressbar)
        for page_num in range(1, total_pages + 1):
            # Przejdź na odpowiednią stronę
            if page_num == 1:
                page_url = self.album_url
            else:
                page_url = f"{self.album_url}/page{page_num}"
            
            self.driver.get(page_url)
            
            # Poczekaj na załadowanie zdjęć
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='staticflickr.com']"))
                )
            except:
                continue
            
            # Przewiń aby załadować wszystkie zdjęcia na tej stronie
            self.scroll_to_load_all_on_page()
            
            # Wyciągnij URL-e z tej strony i NATYCHMIAST dodaj do kolejki pobierania
            self.extract_photo_urls_from_page()
            
            # Krótka pauza między stronami
            time.sleep(0.5)
        
        # Poczekaj na zakończenie wszystkich pobierań
        self.download_queue.join()
        
        # Zamknij progressbar
        if self.download_pbar:
            self.download_pbar.close()
        
        # Zatrzymaj wątki
        for _ in range(num_workers):
            self.download_queue.put(None)
        for t in download_threads:
            t.join()
        
        return list(self.photo_urls)
    
    def download_photo(self, url, filename):
        """Pobierz pojedyncze zdjęcie"""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                filepath = os.path.join(self.download_folder, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                # Spróbuj alternatywnych rozmiarów jeśli _b nie działa
                if '_b.jpg' in url:
                    alt_url = url.replace('_b.jpg', '_c.jpg')  # 800px
                    response = requests.get(alt_url, timeout=30)
                    if response.status_code == 200:
                        filepath = os.path.join(self.download_folder, filename)
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        return True
                
                print(f"  ✗ Błąd {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ Błąd: {str(e)[:50]}")
            return False
    
    def run(self):
        """Główna funkcja uruchamiająca cały proces"""
        try:
            print(f"\n{'='*50}")
            print(f"FLICKR ALBUM DOWNLOADER")
            print(f"{'='*50}")
            print(f"Album: {self.album_url}")
            print(f"Folder: {self.download_folder}\n")
            
            # Pokaż status wznowienia
            if self.downloaded_files:
                print(f"📂 Tryb wznowienia: pominięto {len(self.downloaded_files)} już pobranych plików")
            if self.failed_files:
                print(f"↻ Ponowne pobieranie: {len(self.failed_files)} wcześniej nieudanych plików\n")
            
            self.setup_driver()
            print("✓ Przeglądarka uruchomiona\n")
            
            # Przetwórz wszystkie strony i zbierz URL-e (równocześnie pobierając)
            photo_urls = self.process_all_pages()
            
            if not photo_urls:
                print("✗ Nie znaleziono żadnych zdjęć!")
                return
            
            # Podsumowanie
            print(f"\n{'='*50}")
            print(f"POBIERANIE ZAKOŃCZONE!")
            print(f"{'='*50}")
            
            # Pokaż statystyki skanowania i cache
            if self.download_stats['skipped_scan'] > 0:
                print(f"⊘ Pominięto podczas skanowania: {self.download_stats['skipped_scan']} (już pobrane)")
            if self.download_stats['from_cache'] > 0:
                print(f"📋 URL-e pobrane z cache: {self.download_stats['from_cache']} (plik photo_urls.txt)")
            
            # Pokaż statystyki pobierania
            print(f"✓ Pobrano pomyślnie: {self.download_stats['successful']}")
            if self.download_stats['resumed'] > 0:
                print(f"↻ Wznowiono (wcześniej nieudane): {self.download_stats['resumed']}")
            if self.download_stats['skipped'] > 0:
                print(f"⊘ Pominięto podczas pobierania: {self.download_stats['skipped']}")
            if self.download_stats['failed'] > 0:
                print(f"✗ Błędy: {self.download_stats['failed']}")
                print(f"  Lista nieudanych: {os.path.abspath(self.failed_file)}")
            
            print(f"\n📊 Razem zdjęć w albumie: {len(self.photo_urls) + self.download_stats['skipped_scan']}")
            print(f"📁 Lokalizacja: {os.path.abspath(self.download_folder)}")
            print(f"📄 Plik z URL-ami: {os.path.abspath(self.urls_file)}")
            print(f"{'='*50}")
            
            if self.download_stats['failed'] > 0:
                print(f"\n💡 Uruchom program ponownie, aby spróbować pobrać nieudane pliki.")
            print()
            
        except Exception as e:
            print(f"\n✗ Wystąpił błąd: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()
                print("\n✓ Przeglądarka zamknięta")


if __name__ == "__main__":
    # Wklej tutaj URL albumu Flickr (bez /page1 na końcu)
    ALBUM_URL = "https://www.flickr.com/photos/ikmgdansk/albums/72177720330390070/"
    
    # Możesz zmienić folder docelowy
    DOWNLOAD_FOLDER = "MusicJam"

    downloader = FlickrAlbumDownloader(ALBUM_URL, DOWNLOAD_FOLDER)
    downloader.run()