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
import tempfile
import time
import urllib.error
import urllib.parse
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


class ConfigError(ValueError):
    """La configuración de Supabase (SUPABASE_URL / SUPABASE_KEY) es inválida.

    Es subclase de ValueError para no romper a quien ya la capturaba. Los
    mensajes se escriben a propósito SIN el valor de la variable, solo su
    nombre y qué está mal: /healthz los publica para poder diagnosticar un
    fallo sin entrar a los logs, y no deben filtrar ninguna clave."""


def _check_header_safe(name, value):
    # Los encabezados HTTP solo aceptan texto codificable en latin-1, sin
    # espacios ni saltos de línea. Si al copiar/pegar SUPABASE_KEY (o
    # SUPABASE_URL) en el panel de Render se coló un caracter "inteligente"
    # (comilla curva, guion largo, espacio invisible) o un salto de línea,
    # esto lo señala con precisión en vez de un error genérico.
    try:
        value.encode("latin-1")
    except UnicodeEncodeError as exc:
        bad_char = value[exc.start:exc.end]
        raise ConfigError(
            f"La variable de entorno {name} tiene un caracter no válido "
            f"({bad_char!r} en la posición {exc.start}) -- probablemente se "
            f"coló al copiar/pegar el valor. Vuelve a copiarlo y pégalo de "
            f"nuevo en Render (Environment -> {name})."
        ) from exc
    for position, char in enumerate(value):
        if char.isspace() or ord(char) < 32:
            raise ConfigError(
                f"La variable de entorno {name} tiene un espacio o un salto de "
                f"línea en la posición {position} -- probablemente se coló al "
                f"copiar/pegar el valor. Vuelve a copiarlo y pégalo de nuevo en "
                f"Render (Environment -> {name})."
            )


# Errores que vale la pena reintentar: la red falló, Supabase tardó de más o
# respondió 5xx/429 (sobrecarga momentánea). Un 4xx es un error nuestro y
# reintentarlo solo repite el error.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_RETRY_DELAYS = (0.5, 1.5)


def _request(method, path, body=None, extra_headers=None, retry=True):
    """Llama a la API REST de Supabase.

    Con retry=True reintenta dos veces los fallos pasajeros. Solo es seguro en
    operaciones idempotentes (leer, upsert por id, PATCH, DELETE): repetir un
    INSERT simple podría duplicar la fila si el primero sí llegó.
    """
    _check_header_safe("SUPABASE_KEY", SUPABASE_KEY)
    _check_header_safe("SUPABASE_URL", SUPABASE_URL)
    if not SUPABASE_URL.startswith(("https://", "http://")):
        raise ConfigError(
            "SUPABASE_URL debe empezar con https:// (por ejemplo "
            "https://xxxx.supabase.co). Corrígela en Render (Environment -> SUPABASE_URL)."
        )
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    delays = _RETRY_DELAYS if retry else ()
    attempt = 0
    while True:
        req = urllib.request.Request(url, data=data, method=method, headers=_headers(extra_headers))
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRYABLE_STATUS or attempt >= len(delays):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt >= len(delays):
                raise
        time.sleep(delays[attempt])
        attempt += 1


# PostgREST (la API de Supabase) devuelve como máximo 1000 filas por consulta
# salvo que se pida otra página. Sin paginar, a partir de la reservación 1001
# las nuevas dejaban de aparecer en el panel y la disponibilidad dejaba de
# contarlas: sobrecupo silencioso al cabo de unos meses de uso.
PAGE_SIZE = 1000


def _get_all(path):
    rows = []
    sep = "&" if "?" in path else "?"
    while True:
        page = _request("GET", f"{path}{sep}limit={PAGE_SIZE}&offset={len(rows)}") or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows


def _json_field_filter(field, op, value):
    """Filtro de PostgREST sobre un campo dentro de la columna jsonb `data`."""
    key = urllib.parse.quote(f"data->>{field}", safe="")
    return f"{key}={op}.{urllib.parse.quote(str(value), safe='')}"


# ---------------------------------------------------------------------------
# Archivos JSON locales (cuando no hay Supabase)
#
# Se escriben a un archivo temporal y luego se renombra encima del bueno. El
# renombrado es atómico: si el proceso muere a la mitad (reinicio, disco
# lleno, corte de luz), el archivo queda con la versión anterior entera en
# vez de medio escrito -- y un JSON medio escrito se leía como lista vacía,
# es decir, se perdían todas las reservaciones.
# ---------------------------------------------------------------------------


def _read_json_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw) if raw.strip() else []
    except json.JSONDecodeError:
        # No devolver [] en silencio y seguir: la siguiente escritura pisaría
        # el archivo dañado y lo poco recuperable se perdería. Se aparta una
        # copia para poder rescatarla a mano.
        backup = f"{path}.corrupt-{int(time.time())}"
        os.replace(path, backup)
        print(f"[ERROR] {path} no era JSON válido; se apartó en {backup}")
        return []


def _write_json_file(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _read_local():
    return _read_json_file(LOCAL_DATA_FILE)


def _write_local(reservations):
    _write_json_file(LOCAL_DATA_FILE, reservations)


def list_reservations(on_date=None):
    """Devuelve las reservaciones (sin ordenar; el llamador ordena).

    Con on_date ("YYYY-MM-DD") solo las de ese día: es lo que necesita el
    cálculo de disponibilidad, y así no baja el historial completo en cada
    reservación nueva.
    """
    if enabled():
        path = "reservations?select=data&order=created_at.asc"
        if on_date:
            path += "&" + _json_field_filter("date", "eq", on_date)
        return [row["data"] for row in _get_all(path)]
    reservations = _read_local()
    if on_date:
        reservations = [r for r in reservations if r.get("date") == on_date]
    return reservations


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
    return _read_json_file(LOCAL_PHOTOS_FILE)


def _write_local_photos(photos):
    _write_json_file(LOCAL_PHOTOS_FILE, photos)


def list_photos():
    """Devuelve todas las fotos ordenadas por sort_order."""
    if enabled():
        return _get_all("photos?select=*&order=sort_order.asc")
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
            retry=False,  # INSERT sin id fijo en conflicto: reintentar duplicaría
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


def update_photo_category(photo_id, category):
    """Cambia la sección (gallery/menu) de una foto existente."""
    if enabled():
        _request(
            "PATCH",
            f"photos?id=eq.{photo_id}",
            body={"category": category},
            extra_headers={"Prefer": "return=minimal"},
        )
        return
    photos = _read_local_photos()
    for p in photos:
        if p["id"] == photo_id:
            p["category"] = category
    _write_local_photos(photos)


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
    return _read_json_file(LOCAL_TABLE_STATUS_FILE)


def _write_local_table_status(rows):
    _write_json_file(LOCAL_TABLE_STATUS_FILE, rows)


def list_unavailable_table_ids():
    """Devuelve el conjunto de ids de mesa marcadas como no disponibles."""
    if enabled():
        rows = _get_all("table_status?select=data")
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


# ---------------------------------------------------------------------------
# Reseñas de clientes (texto + foto opcional), con moderación por palabras
# clave (ver server.py). Mismo patrón JSONB que reservations/table_status.
#
# Tabla esperada en Supabase (crear una sola vez, ver README):
#
#     create table reviews (
#         id text primary key,
#         data jsonb not null,
#         created_at timestamptz not null default now()
#     );
# ---------------------------------------------------------------------------

LOCAL_REVIEWS_FILE = os.path.join(BASE_DIR, "data", "reviews.json")


def _read_local_reviews():
    return _read_json_file(LOCAL_REVIEWS_FILE)


def _write_local_reviews(reviews):
    _write_json_file(LOCAL_REVIEWS_FILE, reviews)


def list_reviews():
    """Devuelve todas las reseñas (el llamador filtra por status si hace falta)."""
    if enabled():
        rows = _get_all("reviews?select=data&order=created_at.desc")
        return [row["data"] for row in rows]
    reviews = _read_local_reviews()
    return sorted(reviews, key=lambda r: r.get("createdAt", ""), reverse=True)


def save_review(review):
    """Crea o actualiza una reseña (upsert por id)."""
    if enabled():
        _request(
            "POST",
            "reviews",
            body={"id": review["id"], "data": review},
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        return
    reviews = _read_local_reviews()
    for i, r in enumerate(reviews):
        if r["id"] == review["id"]:
            reviews[i] = review
            break
    else:
        reviews.append(review)
    _write_local_reviews(reviews)


# ---------------------------------------------------------------------------
# Fotos que suben los clientes junto a su reseña. A diferencia de las fotos
# de la galería (que el staff agrega pegando una URL ya alojada en algún
# lado), estas llegan como bytes reales desde el celular del cliente y hay
# que alojarlas nosotros mismos -- Supabase Storage cuando está configurado
# (para que sobrevivan un reinicio de Render), o un archivo local dentro de
# public/ para desarrollo sin cuenta de Supabase.
# ---------------------------------------------------------------------------

REVIEW_PHOTOS_BUCKET = "review-photos"
LOCAL_REVIEW_PHOTOS_DIR = os.path.join(BASE_DIR, "public", "uploads", "reviews")


def upload_review_photo(filename, content_bytes, content_type):
    """Sube la foto de una reseña y devuelve la URL pública para guardarla."""
    if enabled():
        url = f"{SUPABASE_URL}/storage/v1/object/{REVIEW_PHOTOS_BUCKET}/{filename}"
        req = urllib.request.Request(
            url,
            data=content_bytes,
            method="POST",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
        return f"{SUPABASE_URL}/storage/v1/object/public/{REVIEW_PHOTOS_BUCKET}/{filename}"

    os.makedirs(LOCAL_REVIEW_PHOTOS_DIR, exist_ok=True)
    with open(os.path.join(LOCAL_REVIEW_PHOTOS_DIR, filename), "wb") as f:
        f.write(content_bytes)
    return f"/uploads/reviews/{filename}"


# ---------------------------------------------------------------------------
# Ajustes globales del restaurante que el staff puede cambiar desde el panel
# (hoy: si se aceptan reservaciones nuevas del público o no). Van en su
# propia tabla, con el mismo patrón JSONB que table_status: una fila por
# ajuste, y si la fila no existe se usa el valor por omisión del llamador
# -- así una base recién creada se comporta como siempre (reservaciones
# abiertas) sin necesidad de insertar nada a mano.
#
# Tabla esperada en Supabase (crear una sola vez, ver README):
#
#     create table settings (
#         id text primary key,
#         data jsonb not null,
#         created_at timestamptz not null default now()
#     );
# ---------------------------------------------------------------------------

LOCAL_SETTINGS_FILE = os.path.join(BASE_DIR, "data", "settings.json")


def _read_local_settings():
    os.makedirs(os.path.dirname(LOCAL_SETTINGS_FILE), exist_ok=True)
    if not os.path.exists(LOCAL_SETTINGS_FILE):
        with open(LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def _write_local_settings(settings):
    with open(LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def get_setting(key, default=None):
    """Devuelve el valor guardado para ese ajuste, o `default` si no hay fila."""
    if enabled():
        try:
            rows = _request("GET", f"settings?select=data&id=eq.{key}") or []
        except (urllib.error.URLError, OSError):
            # Tabla aún sin crear en Supabase (404) o Supabase caído: se usa
            # el valor por omisión en vez de tumbar las reservaciones. Con el
            # interruptor, el valor por omisión es "abierto".
            return default
        if not rows:
            return default
        data = rows[0].get("data") or {}
        return data.get("value", default)
    return _read_local_settings().get(key, default)


def set_setting(key, value):
    """Guarda el valor de un ajuste (upsert por id)."""
    if enabled():
        _request(
            "POST",
            "settings",
            body={"id": key, "data": {"value": value}},
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        return
    settings = _read_local_settings()
    settings[key] = value
    _write_local_settings(settings)


# ---------------------------------------------------------------------------
# Mantenimiento: salud, limpieza y respaldo
# ---------------------------------------------------------------------------


def ping():
    """Comprueba que el almacenamiento responde. Lanza una excepción si no."""
    if enabled():
        _request("GET", "reservations?select=id&limit=1")
        return "supabase"
    os.makedirs(os.path.dirname(LOCAL_DATA_FILE), exist_ok=True)
    if not os.access(os.path.dirname(LOCAL_DATA_FILE), os.W_OK):
        raise OSError("data/ no tiene permiso de escritura")
    return "local"


def purge_reservations_before(cutoff_date):
    """Borra las reservaciones con fecha anterior a cutoff_date ("YYYY-MM-DD").

    Devuelve cuántas se borraron. Solo toca reservaciones: las reseñas y las
    fotos son contenido del sitio, no datos personales que caduquen.
    """
    if enabled():
        rows = _request(
            "DELETE",
            "reservations?" + _json_field_filter("date", "lt", cutoff_date),
            extra_headers={"Prefer": "return=representation"},
        ) or []
        return len(rows)
    reservations = _read_local()
    keep = [r for r in reservations if (r.get("date") or "") >= cutoff_date]
    if len(keep) != len(reservations):
        _write_local(keep)
    return len(reservations) - len(keep)


# Formato del respaldo: las tablas con columna jsonb van como
# {"id", "data", "created_at"}; photos va con sus columnas tal cual. Es el
# mismo formato venga de Supabase o de los archivos locales, así que un
# respaldo de uno se puede restaurar en el otro.
BACKUP_TABLES = ("reservations", "table_status", "reviews", "photos")
_LOCAL_FILES = {
    "reservations": LOCAL_DATA_FILE,
    "table_status": LOCAL_TABLE_STATUS_FILE,
    "reviews": LOCAL_REVIEWS_FILE,
    "photos": LOCAL_PHOTOS_FILE,
}


def export_all():
    """Devuelve un dict con todas las tablas, listo para json.dump."""
    tables = {}
    for name in BACKUP_TABLES:
        if enabled():
            tables[name] = _get_all(f"{name}?select=*&order=created_at.asc")
        elif name == "photos":
            tables[name] = _read_json_file(_LOCAL_FILES[name])
        else:
            tables[name] = [{"id": row["id"], "data": row} for row in _read_json_file(_LOCAL_FILES[name])]
    return {
        "format": "whitebear-backup",
        "version": 1,
        "source": "supabase" if enabled() else "local",
        "exportedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tables": tables,
    }


def import_all(backup):
    """Restaura un respaldo de export_all(). Hace upsert por id: lo que ya
    existe se sobrescribe con la versión del respaldo y lo que no está en el
    respaldo se deja como está (no borra nada). Devuelve filas por tabla."""
    if backup.get("format") != "whitebear-backup":
        raise ValueError("El archivo no parece un respaldo de White Bear.")
    counts = {}
    for name in BACKUP_TABLES:
        rows = backup.get("tables", {}).get(name, [])
        counts[name] = len(rows)
        if not rows:
            continue
        if enabled():
            # PostgREST exige que todas las filas de un envío tengan las mismas
            # columnas; con ?columns= y missing=default, a la que le falte una
            # (p. ej. fotos antiguas sin "category") se le pone su valor por
            # defecto en vez de rechazar el lote entero.
            columns = sorted({key for row in rows for key in row})
            for i in range(0, len(rows), 500):
                _request(
                    "POST",
                    f"{name}?columns={','.join(columns)}",
                    body=rows[i : i + 500],
                    extra_headers={
                        "Prefer": "resolution=merge-duplicates,missing=default,return=minimal"
                    },
                )
            continue
        path = _LOCAL_FILES[name]
        incoming = rows if name == "photos" else [row["data"] for row in rows]
        by_id = {row["id"]: row for row in _read_json_file(path)}
        by_id.update({row["id"]: row for row in incoming})
        _write_json_file(path, list(by_id.values()))
    return counts
