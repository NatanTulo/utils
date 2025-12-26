# Deduplikator plików photo_urls.txt

Skrypt do usuwania powielonych wierszy z plików `photo_urls.txt` generowanych przez Flickr Album Downloader.

## Użycie

### Podstawowe użycie (przeszukaj wszystkie foldery):
```bash
python dedup_photo_urls.py
```

### Dla konkretnego folderu:
```bash
python dedup_photo_urls.py hackyeah1xMax
```

### Dla konkretnego pliku:
```bash
python dedup_photo_urls.py hackyeah1xMax/photo_urls.txt
```

## Co robi skrypt:

1. **Znajdzie wszystkie pliki `photo_urls.txt`** w podanych folderach
2. **Dla każdego pliku:**
   - Wczyta wszystkie wiersze
   - Usunie duplikaty (zachowuje pierwsze wystąpienie)
   - Utworzy backup oryginalnego pliku (`.bak`)
   - Zapisz deduplikowany plik
3. **Wyświetli statystyki** przed/po deduplikacji

## Przykład działania:

```
============================================================
DEDUPLIKATOR PLIKÓW PHOTO_URLS.TXT
============================================================
Szukanie plików w: C:\PG\Python\flickr

📁 Znaleziono 2 plików:
  • .\hackyeah1xMax\photo_urls.txt
  • .\hackyeah2xMax\photo_urls.txt

Przetwarzanie: .\hackyeah1xMax\photo_urls.txt
  Oryginalnie: 1458 wierszy
  ✓ Brak duplikatów do usunięcia

Przetwarzanie: .\hackyeah2xMax\photo_urls.txt
  Oryginalnie: 2838 wierszy
  💾 Backup utworzony: photo_urls.txt.bak
  ✓ Usunięto 1299 duplikatów
  ✓ Zapisano 1539 unikalnych wierszy

============================================================
PODSUMOWANIE
============================================================
📁 Przetworzonych plików: 2
🗑️  Usuniętych duplikatów: 1299
✅ Deduplikacja zakończona pomyślnie!
💡 Oryginalne pliki zostały zapisane z rozszerzeniem .bak
```

## Bezpieczeństwo:

- **Backup**: Oryginalne pliki są zachowywane z rozszerzeniem `.bak`
- **Zachowanie kolejności**: Pierwsze wystąpienie duplikatu jest zachowywane
- **Zachowanie formatu**: Format TSV (tab-separated) jest zachowywany

## Wymagania:

- Python 3.x
- Dostęp do plików `photo_urls.txt`