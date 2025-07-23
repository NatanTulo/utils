import os
import shutil
import argparse
from pathlib import Path

def is_venv_folder(folder_path):
    """Sprawdza czy folder jest środowiskiem wirtualnym Python"""
    folder = Path(folder_path)
    
    # Sprawdź plik pyvenv.cfg (standardowy marker venv)
    if (folder / "pyvenv.cfg").exists():
        return True
    
    # Sprawdź strukturę Windows venv
    windows_markers = [
        folder / "Scripts" / "activate.bat",
        folder / "Scripts" / "python.exe",
        folder / "Scripts" / "pip.exe"
    ]
    
    # Sprawdź strukturę Linux/Mac venv
    linux_markers = [
        folder / "bin" / "activate",
        folder / "bin" / "python",
        folder / "bin" / "pip"
    ]
    
    # Jeśli istnieje jakikolwiek marker, to prawdopodobnie venv
    return any(marker.exists() for marker in windows_markers + linux_markers)

def get_folder_size(folder_path):
    """Oblicza rozmiar folderu w bajtach"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, FileNotFoundError):
        pass
    return total_size

def format_size(size_bytes):
    """Formatuje rozmiar w czytelnej formie"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def remove_venv_contents(venv_folder, dry_run=True):
    """Usuwa tylko zawartość venv, zachowując inne pliki użytkownika"""
    folder = Path(venv_folder)
    
    # Elementy venv do usunięcia na Windows
    windows_venv_items = ['Include', 'Lib', 'Scripts', 'pyvenv.cfg']
    
    # Elementy venv do usunięcia na Linux/Mac
    linux_venv_items = ['bin', 'lib', 'include', 'share', 'pyvenv.cfg']
    
    # Wszystkie możliwe elementy venv
    venv_items = set(windows_venv_items + linux_venv_items)
    
    removed_size = 0
    items_removed = []
    
    for item_name in venv_items:
        item_path = folder / item_name
        if item_path.exists():
            try:
                if item_path.is_file():
                    size = item_path.stat().st_size
                    if not dry_run:
                        item_path.unlink()
                    removed_size += size
                    items_removed.append(f"  - plik: {item_name}")
                elif item_path.is_dir():
                    size = get_folder_size(item_path)
                    if not dry_run:
                        shutil.rmtree(item_path)
                    removed_size += size
                    items_removed.append(f"  - folder: {item_name}")
            except Exception as e:
                print(f"  ✗ BŁĄD przy usuwaniu {item_name}: {e}")
    
    return removed_size, items_removed

def find_and_remove_venvs(root_path, dry_run=True):
    """Znajduje i usuwa zawartość folderów venv"""
    root = Path(root_path)
    total_size_freed = 0
    venvs_found = []
    
    print(f"Przeszukuję katalog: {root}")
    print(f"Tryb: {'DRY RUN (tylko podgląd)' if dry_run else 'USUWANIE ZAWARTOŚCI VENV'}")
    print("-" * 50)
    
    for folder_path in root.rglob("*"):
        if folder_path.is_dir() and is_venv_folder(folder_path):
            venvs_found.append(folder_path)
            
            print(f"Znaleziono venv: {folder_path}")
            
            # Usuń tylko zawartość venv, nie cały folder
            size_freed, items_removed = remove_venv_contents(folder_path, dry_run)
            total_size_freed += size_freed
            
            print(f"  Rozmiar do zwolnienia: {format_size(size_freed)}")
            
            if items_removed:
                if dry_run:
                    print("  Elementy do usunięcia:")
                else:
                    print("  Usunięte elementy:")
                for item in items_removed:
                    print(item)
            else:
                print("  Brak elementów venv do usunięcia")
            
            if not dry_run and items_removed:
                print(f"  ✓ ZAWARTOŚĆ VENV USUNIĘTA")
            elif dry_run and items_removed:
                print(f"  → ZAWARTOŚĆ VENV DO USUNIĘCIA")
            print()
    
    print("-" * 50)
    print(f"Znaleziono {len(venvs_found)} folderów venv")
    print(f"Całkowity rozmiar do zwolnienia: {format_size(total_size_freed)}")
    
    if dry_run and venvs_found:
        print("\nAby rzeczywiście usunąć zawartość venv, uruchom z parametrem --delete")
        print("UWAGA: Usuwana będzie tylko zawartość venv (Include, Lib, Scripts, bin, lib itp.)")
        print("Inne pliki w folderach pozostaną nietknięte!")
    elif not dry_run:
        print("Operacja zakończona!")

def main():
    parser = argparse.ArgumentParser(description="Usuwa foldery venv z projektów Python")
    parser.add_argument("path", help="Ścieżka do katalogu głównego")
    parser.add_argument("--delete", action="store_true", 
                       help="Rzeczywiście usuń (domyślnie tylko podgląd)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Błąd: Ścieżka {args.path} nie istnieje!")
        return
    
    if not args.delete:
        print("UWAGA: Tryb podglądu. Dodaj --delete aby rzeczywiście usunąć.")
        print()
    
    find_and_remove_venvs(args.path, dry_run=not args.delete)

if __name__ == "__main__":
    main()
