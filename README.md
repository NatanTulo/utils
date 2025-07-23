# Utils - Zbiór przydatnych narzędzi

Kolekcja przydatnych skryptów Python do różnych zadań programistycznych i administratorskich.

## Spis treści

- [count_lines.py](#count_linespy) - Licznik linii kodu
- [delvenv.py](#delvenvpy) - Narzędzie do usuwania środowisk wirtualnych
- [microdvd_to_srt.py](#microdvd_to_srtpy) - Konwerter napisów MicroDVD do SRT
- [remove_comments.py](#remove_commentspy) - Usuwanie komentarzy z kodu

---

## count_lines.py

**Opis:** Narzędzie do liczenia linii kodu w plikach o określonym rozszerzeniu.

**Zastosowanie:**
```bash
python count_lines.py <rozszerzenie> [katalog]
```

**Parametry:**
- `<rozszerzenie>` - rozszerzenie plików do przeszukania (np. `.py`, `.js`, `.cpp`)
- `[katalog]` - opcjonalny katalog do przeszukania (domyślnie bieżący katalog)

**Przykłady użycia:**
```bash
# Policz linie w plikach Python w bieżącym katalogu
python count_lines.py .py

# Policz linie w plikach JavaScript w określonym katalogu
python count_lines.py .js C:\Projects\MyApp

# Policz linie w plikach C++ w katalogu src
python count_lines.py .cpp src
```

**Funkcjonalności:**
- Przeszukuje tylko pliki w podanym katalogu (bez podkatalogów)
- Obsługuje kodowanie UTF-8
- Wyświetla łączną liczbę linii

---

## delvenv.py

**Opis:** Zaawansowane narzędzie do znajdowania i usuwania środowisk wirtualnych Python w projektach.

**Zastosowanie:**
```bash
python delvenv.py <ścieżka> [--delete]
```

**Parametry:**
- `<ścieżka>` - katalog główny do przeszukania
- `--delete` - rzeczywiście usuń (bez tego parametru tylko podgląd)

**Przykłady użycia:**
```bash
# Podgląd folderów venv do usunięcia
python delvenv.py C:\Projects

# Rzeczywiste usunięcie zawartości venv
python delvenv.py C:\Projects --delete

# Przeszukanie bieżącego katalogu
python delvenv.py . --delete
```

**Funkcjonalności:**
- Automatyczne wykrywanie środowisk wirtualnych (venv, virtualenv)
- Obsługa zarówno Windows (Scripts) jak i Linux/Mac (bin)
- Usuwa tylko zawartość venv, zachowując inne pliki użytkownika
- Pokazuje rozmiar miejsca do zwolnienia
- Tryb bezpiecznego podglądu przed usunięciem
- Rekurencyjne przeszukiwanie katalogów

**Bezpieczeństwo:**
- Domyślnie działa w trybie podglądu
- Usuwa tylko typowe elementy venv: `Include`, `Lib`, `Scripts`, `bin`, `lib`, `pyvenv.cfg`
- Zachowuje pliki użytkownika w folderach projektów

---

## microdvd_to_srt.py

**Opis:** Konwerter napisów z formatu MicroDVD (.txt) do formatu SubRip (.srt).

**Zastosowanie:**
```bash
python microdvd_to_srt.py
```

**Funkcjonalności:**
- Automatyczne przetwarzanie wszystkich plików .txt w bieżącym katalogu
- Obsługa formatów `{start}{end}tekst` oraz `[start][end]tekst`
- Konwersja klatek na znaczniki czasu (domyślnie 23.976 FPS)
- Obsługa polskich znaków (UTF-8 i CP1250)
- Zamiana separatora `|` na nowe linie w napisach
- Usuwanie prefiksu `/` z linii napisów

**Przykład konwersji:**
```
Wejście (MicroDVD): {100}{200}Pierwsza linia|Druga linia
Wyjście (SRT):      1
                    00:00:04,170 --> 00:00:08,341
                    Pierwsza linia
                    Druga linia
```

**Obsługiwane formaty wejściowe:**
- `{klatka_start}{klatka_koniec}tekst`
- `[klatka_start][klatka_koniec]tekst`

---

## remove_comments.py

**Opis:** Narzędzie do usuwania komentarzy z kodu źródłowego w różnych językach programowania.

**Zastosowanie:**
```bash
python remove_comments.py [katalog]
```

**Parametry:**
- `[katalog]` - katalog do przetworzenia (domyślnie bieżący katalog)

**Przykłady użycia:**
```bash
# Usuń komentarze z plików w bieżącym katalogu
python remove_comments.py

# Usuń komentarze z plików w określonym katalogu
python remove_comments.py C:\Projects\MyApp

# Usuń komentarze z plików w katalogu src
python remove_comments.py src
```

**Obsługiwane języki:**
- **Python** (`.py`) - komentarze `#` i docstringi
- **C/C++** (`.c`, `.cpp`, `.h`, `.hpp`) - komentarze `//` i `/* */`

**Funkcjonalności:**
- Rekurencyjne przetwarzanie katalogów
- Inteligentne pomijanie folderów systemowych (venv, __pycache__, .idea, itp.)
- Zaawansowane przetwarzanie komentarzy blokowych w C/C++
- Zachowanie struktury kodu i odpowiednich odstępów
- Bezpośrednia modyfikacja plików (uważaj na kopie zapasowe!)

**Uwaga:** Skrypt modyfikuje pliki bezpośrednio. Zaleca się tworzenie kopii zapasowych przed użyciem.

---

## Wymagania systemowe

- Python 3.6+
- Standardowe biblioteki Python (os, sys, re, tokenize, pathlib, argparse, shutil)
