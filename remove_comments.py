import os
import sys
import re
import tokenize
from io import StringIO

def remove_comments_from_python_code(code):
    code = "\n".join(line.rstrip() for line in code.splitlines() if not re.match(r'^\s*#', line))
    tokens = tokenize.generate_tokens(StringIO(code).readline)
    tokens_without_comments = [tok for tok in tokens if tok.type != tokenize.COMMENT]
    return tokenize.untokenize(tokens_without_comments)

def remove_comments_from_js_like_code(code):
    result = []
    for line in code.splitlines():
        # Unikaj usuwania // które są częścią URL-i (http://, https://, ws://, wss://, smb://, ftp://, itp.)
        line = re.sub(r'(?<!:)//(?!/).*$', '', line)
        result.append(line)

    code = '\n'.join(result)

    def replace_comment(match):
        comment_text = match.group(0)
        lines = comment_text.splitlines()

        if len(lines) <= 2:
            return ' '

        empty_lines_before = 0
        i = 0
        while i < len(lines) and lines[i].strip() == '':
            empty_lines_before += 1
            i += 1

        empty_lines_after = 0
        i = len(lines) - 1
        while i >= 0 and lines[i].strip() == '':
            empty_lines_after += 1
            i -= 1

        if empty_lines_before > 0 and empty_lines_after > 0:
            return '\n'
        return ' '

    code = re.sub(r'/\*[\s\S]*?\*/', replace_comment, code)

    code = re.sub(r'\n{3,}', '\n\n', code)

    return code

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()

    file_ext = os.path.splitext(filepath)[1].lower()

    if file_ext == '.py':
        new_code = remove_comments_from_python_code(code)
    elif file_ext in ['.c', '.cpp', '.h', '.hpp', '.ts', '.tsx']:
        new_code = remove_comments_from_js_like_code(code)
    else:
        print(f"Unsupported file type: {filepath}")
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_code)
    print(f"Processed: {filepath}")

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d.lower() not in [
            'venv', 'env', '.venv', '__pycache__', '.idea',
            'include', 'lib', 'scripts', 'site-packages']]
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in ['.py', '.c', '.cpp', '.h', '.hpp', '.ts', '.tsx']:
                process_file(os.path.join(root, file))

if __name__ == '__main__':
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    process_directory(target_dir)