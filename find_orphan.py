import os
from pathlib import Path

# Configurazione
PROJECT_DIR = Path("backend")
EXCLUDED_DIRS = {
    "__pycache__",
    ".venv",
    "env",
    "temp_venv",
    ".git",
    "site-packages",
}
IGNORED_PREFIXES = [
    "backend/tests",
    "backend/scripts",
    "backend/temp_venv",
    "backend/temp_env",
    "backend/__pycache__",
]

def is_excluded(path):
    return any(part in EXCLUDED_DIRS for part in Path(path).parts)

def is_ignored(path):
    return any(path.startswith(prefix) for prefix in IGNORED_PREFIXES)

# 1. Trova tutti i file .py nel progetto (escludendo cartelle inutili)
all_py_files = []
for root, dirs, files in os.walk(PROJECT_DIR):
    # Modifica dirs in-place per saltare le cartelle escluse
    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
    for file in files:
        if file.endswith(".py"):
            full_path = os.path.join(root, file)
            rel_path = str(Path(full_path).as_posix())
            all_py_files.append(rel_path)

# 2. Costruisci una mappa di tutti gli import usati
imported_modules = set()
for file_path in all_py_files:
    if is_ignored(file_path):
        continue
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            for line in f:
                line = line.strip()
                if line.startswith("import ") or line.startswith("from "):
                    parts = line.replace("import", "").replace("from", "").split()
                    if parts:
                        module = parts[0].split(".")[0]
                        imported_modules.add(module)
        except Exception:
            pass

# 3. Trova file orfani (non importati da nessuno)
orphans = []
for file_path in all_py_files:
    if is_ignored(file_path):
        continue
    module_name = Path(file_path).stem
    if module_name not in imported_modules:
        orphans.append(file_path)

# 4. Stampa risultato
if orphans:
    print("\n📂 Possibili file Python **orfani** (mai importati da altri):\n")
    for orphan in sorted(orphans):
        print(f" - {orphan}")
else:
    print("✅ Nessun file orfano trovato!")