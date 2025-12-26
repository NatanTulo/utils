#!/usr/bin/env python3
"""
Dedup Photo URLs - Usuwa powielone wiersze z plików photo_urls.txt

Użycie:
    python dedup_photo_urls.py [folder_z_plikami]

Jeśli nie podano folderu, skrypt przeszuka wszystkie podfoldery w bieżącym katalogu
i znajdzie pliki photo_urls.txt.

Skrypt:
- Zachowuje pierwszą wystąpienie duplikatu
- Tworzy backup oryginalnego pliku (.bak)
- Wyświetla statystyki przed/po deduplikacji
"""

import os
import sys
import glob
from collections import defaultdict


def deduplicate_photo_urls_file(filepath):
    """
    Usuwa duplikaty z pojedynczego pliku photo_urls.txt

    Format pliku: filename\turl\ttitle\tsize
    Deduplikacja po pełnym wierszu (wszystkie pola)
    """
    print(f"Przetwarzanie: {filepath}")

    # Wczytaj wszystkie wiersze
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    original_count = len(lines)
    print(f"  Oryginalnie: {original_count} wierszy")

    # Usuń puste wiersze i białe znaki
    lines = [line.strip() for line in lines if line.strip()]

    # Deduplikacja - zachowaj kolejność pierwszej wystąpienia
    seen = set()
    unique_lines = []

    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    unique_count = len(unique_lines)
    duplicates_removed = original_count - unique_count

    if duplicates_removed == 0:
        print("  ✓ Brak duplikatów do usunięcia")
        return 0

    # Utwórz backup
    backup_path = filepath + '.bak'
    os.rename(filepath, backup_path)
    print(f"  💾 Backup utworzony: {os.path.basename(backup_path)}")

    # Zapisz deduplikowany plik
    with open(filepath, 'w', encoding='utf-8') as f:
        for line in unique_lines:
            f.write(line + '\n')

    print(f"  ✓ Usunięto {duplicates_removed} duplikatów")
    print(f"  ✓ Zapisano {unique_count} unikalnych wierszy")

    return duplicates_removed


def find_photo_urls_files(search_path):
    """
    Znajdzie wszystkie pliki photo_urls.txt w podanych ścieżkach
    """
    files_found = []

    if os.path.isfile(search_path):
        # Podano konkretny plik
        if os.path.basename(search_path) == 'photo_urls.txt':
            files_found.append(search_path)
    elif os.path.isdir(search_path):
        # Przeszukaj katalog rekursywnie
        pattern = os.path.join(search_path, '**', 'photo_urls.txt')
        files_found = glob.glob(pattern, recursive=True)
    else:
        print(f"❌ Ścieżka nie istnieje: {search_path}")
        return []

    return files_found


def main():
    print("=" * 60)
    print("DEDUPLIKATOR PLIKÓW PHOTO_URLS.TXT")
    print("=" * 60)

    # Określ ścieżkę do przeszukania
    if len(sys.argv) > 1:
        search_path = sys.argv[1]
    else:
        search_path = "."  # bieżący katalog

    print(f"Szukanie plików w: {os.path.abspath(search_path)}")
    print()

    # Znajdź pliki
    photo_urls_files = find_photo_urls_files(search_path)

    if not photo_urls_files:
        print("❌ Nie znaleziono żadnych plików photo_urls.txt")
        return

    print(f"📁 Znaleziono {len(photo_urls_files)} plików:")
    for f in photo_urls_files:
        print(f"  • {f}")
    print()

    # Przetwórz każdy plik
    total_duplicates = 0
    processed_files = 0

    for filepath in photo_urls_files:
        try:
            duplicates = deduplicate_photo_urls_file(filepath)
            total_duplicates += duplicates
            processed_files += 1
            print()

        except Exception as e:
            print(f"❌ Błąd podczas przetwarzania {filepath}: {e}")
            print()

    # Podsumowanie
    print("=" * 60)
    print("PODSUMOWANIE")
    print("=" * 60)
    print(f"📁 Przetworzonych plików: {processed_files}")
    print(f"🗑️  Usuniętych duplikatów: {total_duplicates}")

    if total_duplicates > 0:
        print("✅ Deduplikacja zakończona pomyślnie!")
        print("💡 Oryginalne pliki zostały zapisane z rozszerzeniem .bak")
    else:
        print("ℹ️  Wszystkie pliki były już deduplikowane")


if __name__ == "__main__":
    main()