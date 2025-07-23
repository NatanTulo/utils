import os
import sys

def count_lines_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)

def count_lines_in_directory(directory, extension):
    total_lines = 0
    # Przetwarzaj tylko pliki w katalogu bez podkatalogów
    for file in os.listdir(directory):
        full_path = os.path.join(directory, file)
        if os.path.isfile(full_path) and file.endswith(extension):
            total_lines += count_lines_in_file(full_path)
    return total_lines

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_lines.py <extension> [directory]")
        sys.exit(1)
        
    extension = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else "."
    total = count_lines_in_directory(directory, extension)
    print(f"Łączna liczba linii w plikach z rozszerzeniem {extension}: {total}")
