import os
import sys
import matplotlib.pyplot as plt

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

def get_files_with_lines(directory, extension):
    """Zwraca słownik z plikami i ilością linii"""
    files_data = {}
    for file in os.listdir(directory):
        full_path = os.path.join(directory, file)
        if os.path.isfile(full_path) and file.endswith(extension):
            files_data[file] = count_lines_in_file(full_path)
    return files_data

def plot_lines_chart(files_data):
    """Tworzy poziomy wykres słupkowy"""
    if not files_data:
        print("Brak plików do wyświetlenia")
        return
    
    filenames = list(files_data.keys())
    line_counts = list(files_data.values())
    
    plt.figure(figsize=(10, 6))
    plt.barh(filenames, line_counts, color='steelblue')
    plt.xlabel('Liczba linii', fontsize=12)
    plt.ylabel('Nazwa pliku', fontsize=12)
    plt.title('Liczba linii w każdym pliku', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.grid(axis='x', alpha=0.3)
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_lines.py <extension> [directory] [--chart]")
        sys.exit(1)
        
    extension = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else "."
    show_chart = "--chart" in sys.argv
    
    total = count_lines_in_directory(directory, extension)
    print(f"Łączna liczba linii w plikach z rozszerzeniem {extension}: {total}")
    
    if show_chart:
        files_data = get_files_with_lines(directory, extension)
        plot_lines_chart(files_data)
