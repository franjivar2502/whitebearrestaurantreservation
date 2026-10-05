#!/usr/bin/env python3
"""
Restaura una copia hecha con scripts/backup.py.

Uso:
    python3 scripts/restore.py backups/whitebear-20261003-120000.json

Escribe en Supabase si SUPABASE_URL y SUPABASE_KEY están definidas, y si no
en los archivos locales de data/. Hace "upsert" por id: lo que está en el
respaldo se escribe (sobrescribiendo la versión actual de esa misma fila) y
lo que no está en el respaldo no se toca. Nunca borra nada.

Pide confirmación antes de escribir; --si la omite (para usarlo en scripts).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if a != "--si"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)

    with open(args[0], "r", encoding="utf-8") as f:
        backup = json.load(f)

    destination = f"Supabase ({storage.SUPABASE_URL})" if storage.enabled() else "archivos locales de data/"
    counts = ", ".join(f"{name}: {len(rows)}" for name, rows in backup.get("tables", {}).items())
    print(f"Respaldo del {backup.get('exportedAt', '?')} ({counts})")
    print(f"Destino: {destination}")
    if "--si" not in sys.argv:
        if input("¿Restaurar? Escribe 'si' para continuar: ").strip().lower() not in ("si", "sí"):
            print("Cancelado.")
            sys.exit(1)

    restored = storage.import_all(backup)
    print("Restaurado: " + ", ".join(f"{name}: {n}" for name, n in restored.items()))


if __name__ == "__main__":
    main()
