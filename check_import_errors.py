import os
import ast

# Common names to ignore (often defined dynamically or contextually)
IGNORED_NAMES = {
    'self', 'cls', 'e', 'exc', 'args', 'kwargs',
    '__class__', '__name__', '__file__', '__init__',
    'request', 'Response', 'Depends', 'HTTPException',
    'db', 'session', 'logger', 'settings', 'app'
}

def find_python_files(folder):
    python_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files

def find_undefined_names(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError as e:
            print(f"[SYNTAX ERROR] {file_path}: {e}")
            return []

    defined_names = set()
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined_names.add(node.name)
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            elif isinstance(node.ctx, (ast.Store, ast.Param)):
                defined_names.add(node.id)

    builtins = set(dir(__builtins__))
    undefined = used_names - defined_names - builtins - IGNORED_NAMES

    return sorted(undefined)

def main():
    backend_folder = "./backend"
    print(f"Scanning folder: {backend_folder}")
    files = find_python_files(backend_folder)

    for file in files:
        undefined = find_undefined_names(file)
        if undefined:
            print(f"\n[UNDEFINED NAMES] in {file}:")
            for name in undefined:
                print(f"  - {name}")

if __name__ == "__main__":
    main()