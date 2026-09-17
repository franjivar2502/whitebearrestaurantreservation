"""
Persistencia de reservaciones para White Bear Restaurant.

Usa Supabase (Postgres, vía su API REST autogenerada) cuando las variables
de entorno SUPABASE_URL y SUPABASE_KEY están configuradas -- así los datos
sobreviven reinicios del servidor. Esto es necesario en el plan gratis de
Render: el disco local no es persistente, así que si solo usáramos el
archivo data/reservations.json, cada vez que el servicio se duerme y
despierta se pierden todas las reservaciones.

Si esas variables no están configuradas (por ejemplo en desarrollo local),
usa el archivo local data/reservations.json como antes. No hace falta
ninguna librería nueva: se usa urllib de la librería estándar, igual que
en notifications.py.

Tabla esperada en Supabase (crear una sola vez, ver README):

    create table reservations (
        id text primary key,
        data jsonb not null,
        created_at timestamptz not null default now()
    );
"""

import json
import os
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_FILE = os.path.join(BASE_DIR, "data", "reservations.json")

def _normalize_supabase_url(raw):
    url = raw.strip().rstrip("/")
    # Tolerar que alguien pegue la URL completa del endpoint REST
    # (.../rest/v1) en vez de solo la URL base del proyecto -- este
    # módulo ya agrega /rest/v1/... él solo en cada request.
    for suffix in ("/rest/v1", "/rest"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


SUPABASE_URL = _normalize_supabase_url(os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()


def enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _headers(extra=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _check_header_safe(name, value):
    # Los encabezados HTTP solo aceptan texto codificable en latin-1. Si al
    # copiar/pegar SUPABASE_KEY (o SUPABASE_URL) en el panel de Render se
    # coló un caracter "inteligente" (comilla curva, guion largo, espacio
    # invisible), esto lo señala con precisión en vez de un error genérico.
    try:
        value.encode("latin-1")
    except UnicodeEncodeError as exc:
        bad_char = value[exc.start:exc.end]
        raise ValueError(
            f"La variable de entorno {name} tiene un caracter no válido "
            f"({bad_char!r} en la posición {exc.start}) -- probablemente se "
            f"coló al copiar/pegar el valor. Vuelve a copiarlo y pégalo de "
            f"nuevo en Render (Environment -> {name})."
        ) from exc


def _request(method, path, body=None, extra_headers=None):
    _check_header_safe("SUPABASE_KEY", SUPABASE_KEY)
    _check_header_safe("SUPABASE_URL", SUPABASE_URL)
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=_headers(extra_headers))
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def _ensure_local_file():
    os.makedirs(os.path.dirname(LOCAL_DATA_FILE), exist_ok=True)
    if not os.path.exists(LOCAL_DATA_FILE):
        with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _read_local():
    _ensure_local_file()
    with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_local(reservations):
    with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reservations, f, indent=2, ensure_ascii=False)


def list_reservations():
    """Devuelve todas las reservaciones (sin ordenar; el llamador ordena)."""
    if enabled():
        rows = _request("GET", "reservations?select=data&order=created_at.asc") or []
        return [row["data"] for row in rows]
    return _read_local()


def save_reservation(reservation):
    """Crea o actualiza una reservación (upsert por id)."""
    if enabled():
        _request(
            "POST",
            "reservations",
            body={"id": reservation["id"], "data": reservation},
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        return
    reservations = _read_local()
    for i, r in enumerate(reservations):
        if r["id"] == reservation["id"]:
            reservations[i] = reservation
            break
    else:
        reservations.append(reservation)
    _write_local(reservations)


def delete_reservation(res_id):
    """Elimina una reservación. Devuelve True si existía."""
    if enabled():
        try:
            _request("DELETE", f"reservations?id=eq.{res_id}")
            return True
        except urllib.error.HTTPError:
            return False
    reservations = _read_local()
    remaining = [r for r in reservations if r["id"] != res_id]
    deleted = len(remaining) != len(reservations)
    if deleted:
        _write_local(remaining)
    return deleted


# ---------------------------------------------------------------------------
# Fotos de la galería (sitio de clientes)
#
# Tabla esperada en Supabase (crear una sola vez, ver README):
#
#     create table photos (
#         id text primary key,
#         url text not null,
#         caption text not null default '',
#         sort_order integer not null default 0,
#         created_at timestamptz not null default now()
#     );
# ---------------------------------------------------------------------------

LOCAL_PHOTOS_FILE = os.path.join(BASE_DIR, "data", "photos.json")


def _read_local_photos():
    os.makedirs(os.path.dirname(LOCAL_PHOTOS_FILE), exist_ok=True)
    if not os.path.exists(LOCAL_PHOTOS_FILE):
        with open(LOCAL_PHOTOS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    with open(LOCAL_PHOTOS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_local_photos(photos):
    with open(LOCAL_PHOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(photos, f, indent=2, ensure_ascii=False)


def list_photos():
    """Devuelve todas las fotos ordenadas por sort_order."""
    if enabled():
        return _request("GET", "photos?select=*&order=sort_order.asc") or []
    photos = _read_local_photos()
    return sorted(photos, key=lambda p: p.get("sort_order", 0))


def add_photo(photo):
    """Inserta una foto nueva (dict con id, url, caption, sort_order)."""
    if enabled():
        _request(
            "POST",
            "photos",
            body=photo,
            extra_headers={"Prefer": "return=minimal"},
        )
        return
    photos = _read_local_photos()
    photos.append(photo)
    _write_local_photos(photos)


def delete_photo(photo_id):
    if enabled():
        try:
            _request("DELETE", f"photos?id=eq.{photo_id}")
            return True
        except urllib.error.HTTPError:
            return False
    photos = _read_local_photos()
    remaining = [p for p in photos if p["id"] != photo_id]
    deleted = len(remaining) != len(photos)
    if deleted:
        _write_local_photos(remaining)
    return deleted


def set_photo_order(ordered_ids):
    """Reasigna sort_order según el orden de la lista de ids dada."""
    if enabled():
        for index, photo_id in enumerate(ordered_ids):
            _request(
                "PATCH",
                f"photos?id=eq.{photo_id}",
                body={"sort_order": index},
                extra_headers={"Prefer": "return=minimal"},
            )
        return
    photos = _read_local_photos()
    order_map = {photo_id: index for index, photo_id in enumerate(ordered_ids)}
    for p in photos:
        if p["id"] in order_map:
            p["sort_order"] = order_map[p["id"]]
    _write_local_photos(photos)


# ---------------------------------------------------------------------------
# Estado de mesas (panel de staff): qué mesas están marcadas como no
# disponibles ahora mismo (fuera de servicio, evento privado, etc.). Solo se
# guarda una fila por mesa marcada como no disponible -- una mesa sin fila
# se considera disponible por defecto.
#
# Tabla esperada en Supabase (crear una sola vez, ver README):
#
#     create table table_status (
#         id text primary key,
#         data jsonb not null,
#         created_at timestamptz not null default now()
#     );
# ---------------------------------------------------------------------------

LOCAL_TABLE_STATUS_FILE = os.path.join(BASE_DIR, "data", "table_status.json")


def _read_local_table_status():
    os.makedirs(os.path.dirname(LOCAL_TABLE_STATUS_FILE), exist_ok=True)
    if not os.path.exists(LOCAL_TABLE_STATUS_FILE):
        with open(LOCAL_TABLE_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    with open(LOCAL_TABLE_STATUS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_local_table_status(rows):
    with open(LOCAL_TABLE_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


def list_unavailable_table_ids():
    """Devuelve el conjunto de ids de mesa marcadas como no disponibles."""
    if enabled():
        rows = _request("GET", "table_status?select=data") or []
        return {row["data"]["id"] for row in rows if row.get("data", {}).get("unavailable")}
    rows = _read_local_table_status()
    return {row["id"] for row in rows if row.get("unavailable")}


def set_table_unavailable(table_id, unavailable):
    """Marca (o desmarca) una mesa como no disponible (upsert por id)."""
    if enabled():
        _request(
            "POST",
            "table_status",
            body={"id": table_id, "data": {"id": table_id, "unavailable": unavailable}},
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        return
    rows = _read_local_table_status()
    for row in rows:
        if row["id"] == table_id:
            row["unavailable"] = unavailable
            break
    else:
        rows.append({"id": table_id, "unavailable": unavailable})
    _write_local_table_status(rows)
