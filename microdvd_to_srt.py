import os
import re

FPS = 23.976

def frame_to_timecode(frame):
    seconds = frame / FPS
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def convert_microdvd_to_srt(txt_path):
    srt_path = txt_path.rsplit('.', 1)[0] + ".srt"
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        # fallback na CP1250 przy polskich znakach
        with open(txt_path, 'r', encoding='cp1250') as f:
            lines = f.readlines()

    srt_lines = []
    counter = 1
    # obsługa formatu {start}{end} lub [start][end]
    pattern = re.compile(r"[\{\[](\d+)[\}\]][\{\[](\d+)[\}\]]\s*(.*)")

    for line in lines:
        match = pattern.match(line)
        if match:
            start_frame = int(match.group(1))
            end_frame = int(match.group(2))
            # zamień '|' na nową linię i usuń wiodące '/' z każdej linii
            raw = match.group(3)
            lines_txt = raw.replace('|', '\n').split('\n')
            text = '\n'.join(part.lstrip('/') for part in lines_txt)

            start_time = frame_to_timecode(start_frame)
            end_time = frame_to_timecode(end_frame)

            # dodajemy dodatkowy pusty wiersz między wpisami
            srt_lines.append(f"{counter}\n{start_time} --> {end_time}\n{text.strip()}\n\n")
            counter += 1

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.writelines(srt_lines)

    print(f"✔️ Skonwertowano: {txt_path} → {srt_path}")

def convert_all_txt_in_folder():
    for filename in os.listdir('.'):
        if filename.lower().endswith('.txt'):
            convert_microdvd_to_srt(filename)

if __name__ == "__main__":
    convert_all_txt_in_folder()
