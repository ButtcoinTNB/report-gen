import ast
import os

BACKEND_DIR = "backend"  # Change this if your folder is named differently

def find_python_files(base_path):
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                yield os.path.join(root, file)

def check_file_for_missing_imports(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError as e:
            print(f"[SYNTAX ERROR] {file_path}: {e}")
            return

    imports = set()
    used_names = set()

    class ImportCollector(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                imports.add(alias.asname or alias.name.split('.')[0])

        def visit_ImportFrom(self, node):
            module = node.module.split('.')[0] if node.module else ''
            for alias in node.names:
                imports.add(alias.asname or alias.name)
            if module:
                imports.add(module)

    class UsageCollector(ast.NodeVisitor):
        def visit_Name(self, node):
            used_names.add(node.id)

    ImportCollector().visit(tree)
    UsageCollector().visit(tree)

    missing = used_names - imports - set(dir(__builtins__))

    if missing:
        print(f"\n[MISSING IMPORTS] {file_path}")
        for name in sorted(missing):
            print(f"  - {name}")

def main():
    print("Checking for missing imports in backend/...\n")
    for py_file in find_python_files(BACKEND_DIR):
        check_file_for_missing_imports(py_file)

if __name__ == "__main__":
    main()