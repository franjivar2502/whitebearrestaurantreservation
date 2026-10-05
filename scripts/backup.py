#!/usr/bin/env python3
"""
Copia de seguridad de todos los datos (reservaciones, reseñas, fotos de la
galería y estado de mesas) a un archivo JSON.

Uso:
    python3 scripts/backup.py                 # crea backups/whitebear-<fecha>.json
    python3 scripts/backup.py mi-copia.json   # o en el archivo que digas

Lee de Supabase si SUPABASE_URL y SUPABASE_KEY están definidas, y si no de
los archivos locales de data/. El archivo resultante contiene nombres y
teléfonos de clientes: guárdalo en un sitio privado, nunca en el repositorio
(la carpeta backups/ está en .gitignore por eso).

Las fotos que suben los clientes con sus reseñas no van dentro: viven en
Supabase Storage y el respaldo guarda su URL. Ver OPERACION.md.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage  # noqa: E402


def main():
    if len(sys.argv) > 1:
        out_path = sys.argv[1]
    else:
        out_dir = os.path.join(os.path.dirname(storage.LOCAL_DATA_FILE), "..", "backups")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.normpath(
            os.path.join(out_dir, time.strftime("whitebear-%Y%m%d-%H%M%S.json"))
        )

    backup = storage.export_all()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=1, ensure_ascii=False)

    counts = ", ".join(f"{name}: {len(rows)}" for name, rows in backup["tables"].items())
    print(f"Respaldo de {backup['source']} guardado en {out_path}")
    print(f"  {counts}")


if __name__ == "__main__":
    main()
