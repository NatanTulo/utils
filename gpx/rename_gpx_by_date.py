import os
import sys
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from pathlib import Path

def extract_date_from_gpx(file_path):
    """Wyciąga datę z pierwszego punktu trackingowego w pliku GPX"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Namespace dla GPX
        namespace = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        
        # Znajdź pierwszy trkpt z time
        trkpt = root.find('.//gpx:trkpt/gpx:time', namespace)
        
        if trkpt is not None:
            time_str = trkpt.text
            # Format: 2025-07-30T12:18:56Z
            date_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return date_obj.date()
        
        return None
        
    except Exception as e:
        print(f"Błąd przy parsowaniu {file_path}: {e}")
        return None

def get_next_number(directory):
    """Znajduje następny numer w sekwencji plików"""
    max_num = 0
    pattern = re.compile(r'^(\d+)\.\s')
    
    for filename in os.listdir(directory):
        if filename.endswith('.gpx'):
            match = pattern.match(filename)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
    
    return max_num + 1

def format_date_polish(date_obj):
    """Formatuje datę po polsku"""
    months = {
        1: 'stycznia', 2: 'lutego', 3: 'marca', 4: 'kwietnia',
        5: 'maja', 6: 'czerwca', 7: 'lipca', 8: 'sierpnia',
        9: 'września', 10: 'października', 11: 'listopada', 12: 'grudnia'
    }
    
    day = date_obj.day
    month = months[date_obj.month]
    year = date_obj.year
    
    return f"{day} {month} {year}"

def rename_gpx_files(directory='.', dry_run=True):
    """Zmienia nazwy plików GPX na podstawie dat z trackingów"""
    directory = Path(directory)
    
    print(f"Przeszukuję katalog: {directory}")
    print(f"Tryb: {'DRY RUN (tylko podgląd)' if dry_run else 'ZMIANA NAZW'}")
    print("-" * 60)
    
    # Znajdź pliki GPX bez właściwego nazewnictwa
    files_to_rename = []
    
    for file_path in directory.glob('*.gpx'):
        filename = file_path.name
        
        # Sprawdź czy plik ma już właściwe nazewnictwo (zaczyna się od numeru i daty)
        if re.match(r'^\d+\.\s+\d+\s+\w+\s+\d{4}(\s\(\d+\))?\.gpx$', filename):
            print(f"✓ Plik już ma właściwą nazwę: {filename}")
            continue
        
        # Wyciągnij datę z pliku
        date_obj = extract_date_from_gpx(file_path)
        
        if date_obj:
            files_to_rename.append((file_path, date_obj))
            print(f"📅 {filename} → data: {format_date_polish(date_obj)}")
        else:
            print(f"❌ Nie udało się wyciągnąć daty z: {filename}")
    
    if not files_to_rename:
        print("\nBrak plików do zmiany nazwy.")
        return
    
    # Sortuj pliki według daty i nazwy (dla stabilności)
    files_to_rename.sort(key=lambda x: (x[1], x[0].name))
    
    print(f"\nZnaleziono {len(files_to_rename)} plików do zmiany nazwy")
    print("-" * 60)
    
    # Pobierz następny numer w sekwencji
    next_num = get_next_number(directory)
    
    # Grupuj pliki według daty
    date_groups = {}
    for file_path, date_obj in files_to_rename:
        if date_obj not in date_groups:
            date_groups[date_obj] = []
        date_groups[date_obj].append(file_path)
    
    # Przetwarzaj pliki z numeracją dla duplikatów dat
    current_num = next_num
    for date_obj in sorted(date_groups.keys()):
        files_for_date = date_groups[date_obj]
        date_str = format_date_polish(date_obj)
        
        for i, file_path in enumerate(files_for_date):
            # Dodaj numerację dla duplikatów (zaczynając od (2) dla drugiego pliku)
            if i == 0:
                new_name = f"{current_num}. {date_str}.gpx"
            else:
                new_name = f"{current_num}. {date_str} ({i + 1}).gpx"
            
            new_path = directory / new_name
            
            print(f"{current_num:3d}. {file_path.name}")
            print(f"     → {new_name}")
            
            if not dry_run:
                try:
                    if new_path.exists():
                        print(f"     ⚠️  UWAGA: Plik {new_name} już istnieje!")
                        continue
                    
                    file_path.rename(new_path)
                    print(f"     ✅ ZMIENIONO")
                    
                except Exception as e:
                    print(f"     ❌ BŁĄD: {e}")
            else:
                print(f"     → DO ZMIANY")
            
            print()
            current_num += 1
    
    if dry_run:
        print(f"Aby rzeczywiście zmienić nazwy, uruchom z parametrem --rename")
        print(f"Następny numer w sekwencji: {next_num}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Zmienia nazwy plików GPX na podstawie dat z trackingów")
    parser.add_argument("directory", nargs='?', default='.', 
                       help="Katalog z plikami GPX (domyślnie bieżący)")
    parser.add_argument("--rename", action="store_true", 
                       help="Rzeczywiście zmień nazwy (domyślnie tylko podgląd)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Błąd: Katalog {args.directory} nie istnieje!")
        return
    
    if not args.rename:
        print("UWAGA: Tryb podglądu. Dodaj --rename aby rzeczywiście zmienić nazwy.")
        print()
    
    rename_gpx_files(args.directory, dry_run=not args.rename)

if __name__ == "__main__":
    main()