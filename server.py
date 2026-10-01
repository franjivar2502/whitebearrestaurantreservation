#!/usr/bin/env python3
"""
White Bear Restaurant - servidor de reservaciones.
Sin dependencias externas (solo librería estándar de Python).

Uso:
    python3 server.py [puerto]

Sirve el sitio web de reservaciones (public/index.html) y el panel
para tablet (public/tablet.html) desde el mismo servidor, y expone
una API JSON en /api/reservations respaldada por data/reservations.json,
para que cualquier reservación hecha desde una computadora, celular o
la propia tablet se refleje al instante en la tablet del restaurante.
"""

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import notifications
import storage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# URL pública del sitio, usada para armar los links de confirmación de
# asistencia que se envían por SMS/correo. En local apunta a localhost; al
# desplegar, define PUBLIC_BASE_URL (p. ej. https://tu-sitio.onrender.com).
PUBLIC_BASE_URL = None

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

RESTAURANT = {
    "name": "White Bear Restaurant",
    "address": "2793 Wilmington Rd, Lake Placid, NY 12946",
    "phone": "(518) 302-5235",
    "priceRange": "$20-30 por persona",
    "rating": 4.2,
    "reviewCount": 243,
    # Horario por día. lunes a jueves y domingo cierran a las 9pm;
    # viernes y sábado cierran más tarde, a las 9:30pm.
    "hours": {
        "mon": {"open": "11:00", "close": "21:00"},
        "tue": {"open": "11:00", "close": "21:00"},
        "wed": {"open": "11:00", "close": "21:00"},
        "thu": {"open": "11:00", "close": "21:00"},
        "fri": {"open": "11:00", "close": "21:30"},
        "sat": {"open": "11:00", "close": "21:30"},
        "sun": {"open": "11:00", "close": "21:00"},
    },
    # Última hora para reservar: unos minutos antes del cierre, para que
    # los comensales alcancen a disfrutar la mesa antes de que cerremos.
    "lastSeatingBufferMinutes": 30,
    "maxPartySize": 40,
    "highlights": [
        "Crispy Calamari with Marinara Sauce",
        "Tortellini",
        "Chicken Caesar Salad",
        "Eggplant Parmigiana",
    ],
    # Menú reducido para grupos grandes: a partir de "threshold" personas,
    # el formulario muestra estos platillos para que el grupo preordene.
    # EDITAR AQUÍ cuando se defina el menú real: basta con reemplazar los
    # elementos de "items" (id único, nombre, descripción opcional).
    "groupMenu": {
        "threshold": 20,
        "note": (
            "Para grupos de 20 personas o más ofrecemos un menú reducido. "
            "Preordena aquí y tendremos tu pedido listo para revisar cuando llegues."
        ),
        "items": [
            {
                "id": "item-1",
                "name": "Platillo de grupo 1 (pendiente de definir)",
                "description": "",
            },
            {
                "id": "item-2",
                "name": "Platillo de grupo 2 (pendiente de definir)",
                "description": "",
            },
            {
                "id": "item-3",
                "name": "Platillo de grupo 3 (pendiente de definir)",
                "description": "",
            },
        ],
    },
}

VALID_STATUSES = {"pending", "confirmed", "seated", "completed", "cancelled"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_SEATING_PREFERENCES = {"", "inside", "outside"}

# Moderación de reseñas de clientes por palabras clave: cualquier reseña que
# contenga una palabra de esta lista (español o inglés) se rechaza -- nunca
# llega a publicarse, para no afectar la reputación del restaurante con
# comentarios ofensivos, acusaciones graves o spam evidente. Es una barrera
# simple a propósito (sin servicio externo, sin dependencias) -- no
# reemplaza el criterio del staff, pero filtra lo obviamente dañino antes de
# que se publique solo.
NEGATIVE_REVIEW_KEYWORDS = {
    "terrible", "horrible", "pesimo", "pésimo", "asqueroso", "asquerosa",
    "asco", "sucio", "sucia", "grosero", "grosera", "maleducado",
    "maleducada", "estafa", "robo", "rata", "ratas", "cucaracha",
    "cucarachas", "intoxicacion", "intoxicación", "vomito", "vómito",
    "nunca mas", "nunca más", "no vuelvo", "malisimo", "malísimo", "fatal",
    "porqueria", "porquería", "basura", "denuncia", "demanda", "veneno",
    "asqueado", "asqueada", "pelo en la comida", "insecto en la comida",
    "awful", "disgusting", "filthy", "rude", "scam", "rat", "roach",
    "roaches", "cockroach", "vomit", "food poisoning", "never again",
    "worst", "trash", "gross", "nasty", "lawsuit", "poison",
}


def _review_text_allowed(text):
    """True si el texto no contiene ninguna palabra clave negativa."""
    lowered = (text or "").lower()
    return not any(kw in lowered for kw in NEGATIVE_REVIEW_KEYWORDS)


def _parse_multipart(body, boundary):
    """
    Parser mínimo de multipart/form-data (sin dependencias -- el módulo
    `cgi` que antes hacía esto fue eliminado de la librería estándar en
    Python 3.13). Devuelve un dict {nombre_de_campo: {"data": bytes,
    "filename": str|None, "content_type": str|None}}.
    """
    fields = {}
    delimiter = b"--" + boundary.encode("utf-8")
    parts = body.split(delimiter)
    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        content = content.rstrip(b"\r\n")
        headers = {}
        for line in raw_headers.split(b"\r\n"):
            if b":" not in line:
                continue
            key, value = line.split(b":", 1)
            headers[key.strip().lower().decode("ascii", "ignore")] = value.strip().decode("utf-8", "ignore")
        disposition = headers.get("content-disposition", "")
        name_match = re.search(r'name="([^"]*)"', disposition)
        if not name_match:
            continue
        field_name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        filename = filename_match.group(1) if filename_match else None
        fields[field_name] = {
            "data": content,
            "filename": filename,
            "content_type": headers.get("content-type"),
        }
    return fields


# Plano del salón, trazado sobre el mapa que dibujó el cliente: el local son
# dos salones separados por un pasillo. El izquierdo tiene la entrada, la
# barra y el baño; el derecho es el comedor del fondo.
#
# Cada fila es (id, forma, asientos, número, salón, x, y). x e y son el centro
# de la mesa en % del ancho y del alto del salón -- es un esquema para que el
# staff ubique la mesa de un vistazo, no un plano a escala. El id no depende
# de la posición ni del número, así que mover o renumerar una mesa aquí no
# invalida las que el staff dejó marcadas como no disponibles.
#
# Inventario: 11 cuadradas de 4, 7 rectangulares de 4, 6 rectangulares de 6,
# 1 de 12 y 1 de 10 = 26 mesas, 130 asientos. El desglose que dio el cliente
# al principio sumaba 122 con 9 cuadradas, pero de palabra siempre dijo 130;
# al revisar el mapa del salón aparecieron dos cuadradas más en el grupo de
# la entrada (el 2x2 junto a la ventana), que son justo los 8 asientos que
# faltaban. 130 es ahora el tope que el sitio de clientes puede vender.
#
# PENDIENTE DE CONFIRMAR CON EL CLIENTE -- hasta entonces esto es una lectura
# del mapa, no un dato verificado:
#   1. El mapa no trae números. Los asigné en orden de lectura: primero el
#      salón de la entrada, de arriba hacia abajo, y después el del fondo.
#   2. El mapa marca las rectangulares con "R" sin decir cuáles son de 4 y
#      cuáles de 6. Puse las 5 de la pared derecha del salón de la entrada
#      como las de 6 (más una del fondo), y el resto de 4.
#   3. Cuál de las dos grandes es la de 12 y cuál la de 10: puse la de 12 en
#      la del fondo (la más larga) y la de 10 en la del centro.
TABLE_LAYOUT = [
    # --- Salón de la entrada (barra, entrada, baño) ---
    ("square4-1", "square", 4, 1, "left", 8, 7),
    ("square4-2", "square", 4, 2, "left", 26, 9),
    ("square4-3", "square", 4, 3, "left", 69, 7),
    ("square4-10", "square", 4, 4, "left", 9, 18),
    ("square4-11", "square", 4, 5, "left", 27, 20),
    ("rect6-1", "rect", 6, 6, "left", 78, 24),
    ("rect6-2", "rect", 6, 7, "left", 78, 35),
    ("rect6-3", "rect", 6, 8, "left", 78, 46),
    ("rect6-4", "rect", 6, 9, "left", 78, 68),
    ("rect6-5", "rect", 6, 10, "left", 78, 83),
    # --- Salón del fondo ---
    ("square4-4", "square", 4, 11, "right", 14, 7),
    ("square4-5", "square", 4, 12, "right", 49, 7),
    ("square4-6", "square", 4, 13, "right", 79, 7),
    ("rect4-1", "rect", 4, 14, "right", 14, 21),
    ("square4-7", "square", 4, 15, "right", 50, 21),
    ("rect6-6", "rect", 6, 16, "right", 84, 21),
    ("rect4-2", "rect", 4, 17, "right", 14, 33),
    ("square4-8", "square", 4, 18, "right", 50, 33),
    ("rect4-3", "rect", 4, 19, "right", 84, 33),
    ("rect10-1", "rect", 10, 20, "right", 48, 48),
    ("rect4-4", "rect", 4, 21, "right", 16, 63),
    ("square4-9", "square", 4, 22, "right", 52, 69),
    ("rect4-5", "rect", 4, 23, "right", 82, 68),
    ("rect4-6", "rect", 4, 24, "right", 24, 78),
    ("rect4-7", "rect", 4, 25, "right", 81, 81),
    ("rect12-1", "rect", 12, 26, "right", 47, 91),
]

# Orden en que se dibujan los salones en el panel, de izquierda a derecha.
ROOM_ORDER = ["left", "right"]


def _build_tables():
    tables = [
        {
            "id": table_id,
            "shape": shape,
            "seats": seats,
            "number": number,
            "room": room,
            "x": x,
            "y": y,
        }
        for table_id, shape, seats, number, room, x, y in TABLE_LAYOUT
    ]

    # El rótulo que ve el staff es este número: si se repite, dos mesas
    # distintas se ven iguales y alguien saca de servicio la que no era.
    # Lo mismo con el id, que es con lo que se guarda el estado.
    for field in ("number", "id"):
        values = [t[field] for t in tables]
        if len(set(values)) != len(values):
            raise ValueError(f"TABLE_LAYOUT tiene {field} repetidos.")
    return tables


TABLES = _build_tables()
TOTAL_SEATS = sum(t["seats"] for t in TABLES)

# Cuánto tiempo ocupa una mesa una reservación, para saber si dos horarios
# se cruzan. El restaurante puede acomodar un grupo en varias mesas juntas
# (no hace falta una mesa exacta del tamaño del grupo), así que la
# disponibilidad se calcula por total de asientos libres, no por mesa.
RESERVATION_DURATION_MINUTES = 90

# Contraseña para el panel de administración de fotos (/admin-photos.html).
# Sin esto configurado, los endpoints de administración quedan bloqueados.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def _hours_for_date(d):
    """Devuelve (hora_apertura, hora_cierre, última_hora_para_reservar) para la fecha dada."""
    day_hours = RESTAURANT["hours"][DAY_KEYS[d.weekday()]]
    open_t = datetime.strptime(day_hours["open"], "%H:%M").time()
    close_t = datetime.strptime(day_hours["close"], "%H:%M").time()
    last_seating_dt = datetime.combine(d, close_t) - timedelta(
        minutes=RESTAURANT["lastSeatingBufferMinutes"]
    )
    return open_t, close_t, last_seating_dt.time()

_lock = threading.Lock()


def _time_to_minutes(t_str):
    h, m = t_str.split(":")
    return int(h) * 60 + int(m)


def _seats_committed(res_date, res_time, exclude_id=None):
    """
    Suma de personas de reservaciones activas cuyo horario se cruza con
    [res_time, res_time + duración) ese mismo día -- así una reservación a
    las 19:00 no le quita disponibilidad a otra a las 21:30.
    """
    start = _time_to_minutes(res_time)
    end = start + RESERVATION_DURATION_MINUTES
    total = 0
    for r in storage.list_reservations():
        if exclude_id and r.get("id") == exclude_id:
            continue
        if r.get("status") in ("cancelled", "completed") or r.get("date") != res_date:
            continue
        try:
            r_start = _time_to_minutes(r["time"])
        except (KeyError, ValueError, AttributeError):
            continue
        r_end = r_start + RESERVATION_DURATION_MINUTES
        if r_start < end and start < r_end:
            total += int(r.get("partySize", 0))
    return total


def _available_seats(res_date, res_time, exclude_id=None):
    """Asientos libres para ese horario: capacidad total (menos las mesas
    que el staff marcó como no disponibles) menos lo ya comprometido."""
    unavailable_ids = storage.list_unavailable_table_ids()
    capacity = TOTAL_SEATS - sum(t["seats"] for t in TABLES if t["id"] in unavailable_ids)
    committed = _seats_committed(res_date, res_time, exclude_id=exclude_id)
    return capacity - committed


def _validate_preorder(raw_pre_order):
    """Valida y limpia la lista de platillos preordenados para grupos grandes."""
    if not raw_pre_order:
        return [], []
    if not isinstance(raw_pre_order, list):
        return [], [{"code": "PREORDER_INVALID"}]

    menu_by_id = {item["id"]: item for item in RESTAURANT["groupMenu"]["items"]}
    cleaned = []
    for entry in raw_pre_order:
        if not isinstance(entry, dict):
            continue
        item = menu_by_id.get(entry.get("itemId"))
        if not item:
            continue
        try:
            quantity = int(entry.get("quantity"))
        except (TypeError, ValueError):
            quantity = 0
        if quantity <= 0:
            continue
        cleaned.append({"itemId": item["id"], "name": item["name"], "quantity": quantity})

    return cleaned, []


def _validate_reservation(payload):
    """
    Devuelve (datos_limpios, errores). Cada error es un dict {"code": ...,
    "params": {...}} en vez de un mensaje ya traducido: el frontend decide
    el idioma (inglés/español/francés) con su propio diccionario (i18n.js),
    usando "code" como llave y "params" para rellenar valores como horarios
    o el máximo de personas.
    """
    errors = []

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    email = (payload.get("email") or "").strip()
    res_date = (payload.get("date") or "").strip()
    res_time = (payload.get("time") or "").strip()
    party_size = payload.get("partySize")
    notes = (payload.get("notes") or "").strip()
    seating_preference = (payload.get("seatingPreference") or "").strip().lower()
    if seating_preference not in VALID_SEATING_PREFERENCES:
        seating_preference = ""
    pre_order, pre_order_errors = _validate_preorder(payload.get("preOrder"))
    pre_order_notes = (payload.get("preOrderNotes") or "").strip()
    errors.extend(pre_order_errors)

    if not name or len(name) < 2:
        errors.append({"code": "NAME_REQUIRED"})
    if not phone or len(re.sub(r"\D", "", phone)) < 7:
        errors.append({"code": "PHONE_INVALID"})
    if email and not EMAIL_RE.match(email):
        errors.append({"code": "EMAIL_INVALID"})

    try:
        parsed_date = datetime.strptime(res_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        parsed_date = None
        errors.append({"code": "DATE_INVALID"})

    if parsed_date and parsed_date < date.today():
        errors.append({"code": "DATE_PAST"})

    try:
        parsed_time = datetime.strptime(res_time, "%H:%M").time()
    except (ValueError, TypeError):
        parsed_time = None
        errors.append({"code": "TIME_INVALID"})

    if parsed_date and parsed_time:
        open_t, _close_t, last_t = _hours_for_date(parsed_date)
        if not (open_t <= parsed_time <= last_t):
            errors.append(
                {
                    "code": "TIME_OUT_OF_HOURS",
                    "params": {
                        "open": open_t.strftime("%H:%M"),
                        "close": last_t.strftime("%H:%M"),
                    },
                }
            )

    try:
        party_size = int(party_size)
        if not (1 <= party_size <= RESTAURANT["maxPartySize"]):
            errors.append(
                {
                    "code": "PARTY_SIZE_OUT_OF_RANGE",
                    "params": {"max": RESTAURANT["maxPartySize"], "phone": RESTAURANT["phone"]},
                }
            )
    except (TypeError, ValueError):
        errors.append({"code": "PARTY_SIZE_INVALID"})
        party_size = None

    if errors:
        return None, errors

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "date": res_date,
        "time": res_time,
        "partySize": party_size,
        "notes": notes,
        "seatingPreference": seating_preference,
        "preOrder": pre_order,
        "preOrderNotes": pre_order_notes,
    }, []


# Content-Type por extensión, para servir los archivos de public/. Faltaba
# .jpg/.jpeg -- las fotos se servían como application/octet-stream, lo que
# algunos navegadores (en particular Chrome para Android con "modo de ahorro
# de datos") pueden negarse a mostrar como fondo CSS aunque el navegador de
# escritorio no tenga problema.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    # robots.txt y sitemap.xml: sin estos dos, se sirven como
    # application/octet-stream y los buscadores los descartan.
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "WhiteBearReservations/1.0"

    def log_message(self, fmt, *args):
        pass  # silencia el log por defecto (ruidoso)

    # ---------- helpers ----------
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _read_raw_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def _is_admin(self):
        if not ADMIN_PASSWORD:
            return False
        return self.headers.get("X-Admin-Password") == ADMIN_PASSWORD

    def _require_admin(self):
        if self._is_admin():
            return True
        self._send_json({"errors": ["No autorizado."]}, status=401)
        return False

    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        safe_path = os.path.normpath(path).lstrip("/")
        full_path = os.path.join(PUBLIC_DIR, safe_path)
        if not full_path.startswith(PUBLIC_DIR) or not os.path.isfile(full_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        ext = os.path.splitext(full_path)[1].lower()
        content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

        with open(full_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- routing ----------
    def do_GET(self):
        try:
            self._do_GET()
        except Exception as exc:  # noqa: BLE001 - queremos ver el error, no un 502 genérico
            print(f"[ERROR] GET {self.path}: {exc!r}")
            self._send_json({"errors": [f"Error interno: {exc}"]}, status=500)

    def _do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/restaurant":
            self._send_json(RESTAURANT)
            return
        if parsed.path == "/api/photos":
            with _lock:
                photos = storage.list_photos()
            self._send_json(photos)
            return
        if parsed.path == "/api/reviews":
            with _lock:
                reviews = storage.list_reviews()
            approved = [r for r in reviews if r.get("status") == "approved"]
            self._send_json(approved)
            return
        if parsed.path == "/api/tables":
            with _lock:
                unavailable_ids = storage.list_unavailable_table_ids()
            tables = [{**t, "unavailable": t["id"] in unavailable_ids} for t in TABLES]
            available_seats = TOTAL_SEATS - sum(
                t["seats"] for t in TABLES if t["id"] in unavailable_ids
            )
            self._send_json(
                {
                    "tables": tables,
                    "rooms": ROOM_ORDER,
                    "totalSeats": TOTAL_SEATS,
                    "availableSeats": available_seats,
                }
            )
            return
        if parsed.path == "/api/reservations":
            qs = parse_qs(parsed.query)
            date_filter = qs.get("date", [None])[0]
            with _lock:
                reservations = storage.list_reservations()
            if date_filter:
                reservations = [r for r in reservations if r["date"] == date_filter]
            reservations.sort(key=lambda r: (r["date"], r["time"]))
            self._send_json(reservations)
            return
        m = re.match(r"^/api/reservations/([a-f0-9]+)$", parsed.path)
        if m:
            res_id = m.group(1)
            with _lock:
                reservations = storage.list_reservations()
            found = next((r for r in reservations if r["id"] == res_id), None)
            if found:
                self._send_json(found)
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return
        self._serve_static(parsed.path)

    def do_POST(self):
        try:
            self._do_POST()
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] POST {self.path}: {exc!r}")
            self._send_json({"errors": [f"Error interno: {exc}"]}, status=500)

    def _do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/reviews":
            content_type_header = self.headers.get("Content-Type", "")
            boundary_match = re.search(r'boundary="?([^";]+)"?', content_type_header)
            if "multipart/form-data" not in content_type_header or not boundary_match:
                self._send_json({"errors": [{"code": "REVIEW_INVALID"}]}, status=400)
                return
            body = self._read_raw_body()
            fields = _parse_multipart(body, boundary_match.group(1))

            name = (fields.get("name", {}).get("data") or b"").decode("utf-8", "ignore").strip()
            text = (fields.get("text", {}).get("data") or b"").decode("utf-8", "ignore").strip()
            rating_raw = (fields.get("rating", {}).get("data") or b"").decode("utf-8", "ignore").strip()

            errors = []
            if not name or len(name) < 2:
                errors.append({"code": "NAME_REQUIRED"})
            if not text or len(text) < 5:
                errors.append({"code": "REVIEW_TEXT_REQUIRED"})
            rating = None
            if rating_raw:
                try:
                    rating = int(rating_raw)
                    if not (1 <= rating <= 5):
                        raise ValueError
                except ValueError:
                    errors.append({"code": "REVIEW_RATING_INVALID"})
            if errors:
                self._send_json({"errors": errors}, status=400)
                return

            if not _review_text_allowed(text):
                self._send_json({"errors": [{"code": "REVIEW_REJECTED"}]}, status=400)
                return

            photo_url = ""
            photo_field = fields.get("photo")
            if photo_field and photo_field.get("filename"):
                photo_bytes = photo_field["data"]
                photo_content_type = photo_field.get("content_type") or "application/octet-stream"
                if not photo_content_type.startswith("image/"):
                    self._send_json({"errors": [{"code": "REVIEW_PHOTO_INVALID"}]}, status=400)
                    return
                if len(photo_bytes) > 8 * 1024 * 1024:
                    self._send_json({"errors": [{"code": "REVIEW_PHOTO_TOO_LARGE"}]}, status=400)
                    return
                ext = os.path.splitext(photo_field["filename"])[1].lower() or ".jpg"
                if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    ext = ".jpg"
                filename = f"{uuid.uuid4().hex[:12]}{ext}"
                with _lock:
                    photo_url = storage.upload_review_photo(filename, photo_bytes, photo_content_type)

            review = {
                "id": uuid.uuid4().hex[:8],
                "name": name,
                "text": text,
                "rating": rating,
                "photoUrl": photo_url,
                "status": "approved",
                "createdAt": datetime.now().isoformat(timespec="seconds"),
            }
            with _lock:
                storage.save_review(review)
            self._send_json(review, status=201)
            return

        if parsed.path == "/api/reservations":
            payload = self._read_json_body()
            if payload is None:
                self._send_json({"errors": ["JSON inválido."]}, status=400)
                return
            clean, errors = _validate_reservation(payload)
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            with _lock:
                available = _available_seats(clean["date"], clean["time"])
            if available < clean["partySize"]:
                self._send_json({"errors": [{"code": "NO_AVAILABILITY"}]}, status=400)
                return
            reservation = {
                "id": uuid.uuid4().hex[:8],
                "status": "pending",
                "createdAt": datetime.now().isoformat(timespec="seconds"),
                "reminderSent": False,
                "attendanceReminderSent": False,
                "attendanceConfirmed": None,
                **clean,
            }
            with _lock:
                storage.save_reservation(reservation)
            threading.Thread(
                target=notifications.notify_confirmation, args=(reservation,), daemon=True
            ).start()
            self._send_json(reservation, status=201)
            return

        m = re.match(r"^/api/reservations/([a-f0-9]+)/confirm-attendance$", parsed.path)
        if m:
            res_id = m.group(1)
            payload = self._read_json_body()
            if payload is None or not isinstance(payload.get("confirmed"), bool):
                self._send_json({"errors": ["Falta indicar si confirma o no."]}, status=400)
                return
            confirmed = payload["confirmed"]
            with _lock:
                reservations = storage.list_reservations()
                found = None
                for r in reservations:
                    if r["id"] == res_id:
                        r["attendanceConfirmed"] = confirmed
                        if not confirmed and r["status"] not in ("completed", "cancelled"):
                            r["status"] = "cancelled"
                        found = r
                        break
                if found:
                    storage.save_reservation(found)
            if found:
                self._send_json(found)
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return

        if parsed.path == "/api/admin/login":
            payload = self._read_json_body()
            password = (payload or {}).get("password", "")
            if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
                self._send_json({"ok": True})
            else:
                self._send_json({"errors": ["Contraseña incorrecta."]}, status=401)
            return

        if parsed.path == "/api/admin/photos":
            if not self._require_admin():
                return
            payload = self._read_json_body() or {}
            url = (payload.get("url") or "").strip()
            caption = (payload.get("caption") or "").strip()
            category = (payload.get("category") or "gallery").strip()
            if category not in ("gallery", "menu"):
                category = "gallery"
            if not url.startswith(("http://", "https://")):
                self._send_json({"errors": ["La URL de la imagen no es válida."]}, status=400)
                return
            with _lock:
                existing = storage.list_photos()
                photo = {
                    "id": uuid.uuid4().hex[:8],
                    "url": url,
                    "caption": caption,
                    "category": category,
                    "sort_order": len(existing),
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
                storage.add_photo(photo)
            self._send_json(photo, status=201)
            return

        if parsed.path == "/api/admin/photos/reorder":
            if not self._require_admin():
                return
            payload = self._read_json_body() or {}
            order = payload.get("order")
            if not isinstance(order, list) or not order:
                self._send_json({"errors": ["Falta el nuevo orden."]}, status=400)
                return
            with _lock:
                storage.set_photo_order(order)
            self._send_json({"ok": True})
            return

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        try:
            self._do_PATCH()
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] PATCH {self.path}: {exc!r}")
            self._send_json({"errors": [f"Error interno: {exc}"]}, status=500)

    def _do_PATCH(self):
        parsed = urlparse(self.path)
        m = re.match(r"^/api/admin/photos/([a-f0-9]+)$", parsed.path)
        if m:
            if not self._require_admin():
                return
            photo_id = m.group(1)
            payload = self._read_json_body() or {}
            category = payload.get("category")
            if category not in ("gallery", "menu"):
                self._send_json({"errors": ["Sección inválida."]}, status=400)
                return
            with _lock:
                storage.update_photo_category(photo_id, category)
            self._send_json({"id": photo_id, "category": category})
            return

        m = re.match(r"^/api/tables/([a-z0-9-]+)$", parsed.path)
        if m:
            table_id = m.group(1)
            if not any(t["id"] == table_id for t in TABLES):
                self._send_json({"errors": ["Mesa no encontrada."]}, status=404)
                return
            payload = self._read_json_body()
            if payload is None or not isinstance(payload.get("unavailable"), bool):
                self._send_json({"errors": ["Falta indicar la disponibilidad."]}, status=400)
                return
            with _lock:
                storage.set_table_unavailable(table_id, payload["unavailable"])
            self._send_json({"id": table_id, "unavailable": payload["unavailable"]})
            return

        m = re.match(r"^/api/reservations/([a-f0-9]+)$", parsed.path)
        if m:
            res_id = m.group(1)
            payload = self._read_json_body()
            if payload is None:
                self._send_json({"errors": ["JSON inválido."]}, status=400)
                return
            new_status = payload.get("status")
            if new_status not in VALID_STATUSES:
                self._send_json({"errors": ["Estado inválido."]}, status=400)
                return
            with _lock:
                reservations = storage.list_reservations()
                found = None
                for r in reservations:
                    if r["id"] == res_id:
                        r["status"] = new_status
                        found = r
                        break
                if found:
                    storage.save_reservation(found)
            if found:
                self._send_json(found)
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        try:
            self._do_DELETE()
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] DELETE {self.path}: {exc!r}")
            self._send_json({"errors": [f"Error interno: {exc}"]}, status=500)

    def _do_DELETE(self):
        parsed = urlparse(self.path)
        m = re.match(r"^/api/admin/photos/([a-f0-9]+)$", parsed.path)
        if m:
            if not self._require_admin():
                return
            deleted = False
            with _lock:
                deleted = storage.delete_photo(m.group(1))
            if deleted:
                self._send_json({"ok": True})
            else:
                self._send_json({"errors": ["Foto no encontrada."]}, status=404)
            return

        m = re.match(r"^/api/reservations/([a-f0-9]+)$", parsed.path)
        if m:
            res_id = m.group(1)
            with _lock:
                deleted = storage.delete_reservation(res_id)
            if deleted:
                self._send_json({"ok": True})
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return
        self.send_response(404)
        self.end_headers()

    def do_HEAD(self):
        # BaseHTTPRequestHandler responde 501 a HEAD si no se define este
        # método. Algunas apps (vistas previas de enlaces al compartir por
        # WhatsApp/redes, ciertos proxies) sí lo usan -- sin esto, ese 501
        # puede hacer que el link se vea "roto" antes de que la persona
        # llegue a abrirlo en su navegador.
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/":
                path = "/index.html"
            safe_path = os.path.normpath(path).lstrip("/")
            full_path = os.path.join(PUBLIC_DIR, safe_path)
            if full_path.startswith(PUBLIC_DIR) and os.path.isfile(full_path):
                ext = os.path.splitext(full_path)[1].lower()
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
                self.send_header("Content-Length", str(os.path.getsize(full_path)))
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] HEAD {self.path}: {exc!r}")
            self.send_response(500)
            self.end_headers()


REMINDER_MINUTES_BEFORE = 15
ADVANCE_ATTENDANCE_MINUTES_BEFORE = 24 * 60  # 24 horas antes, para reservaciones hechas con días de anticipación
SAME_DAY_ATTENDANCE_MINUTES_BEFORE = 30  # 30 minutos antes, para reservaciones del mismo día


def _check_and_send_attendance_confirmations():
    """
    Pide confirmar asistencia: 24h antes si la reservación se hizo con días
    de anticipación (la fecha de la reserva es posterior al día en que se
    creó), o 30 minutos antes si se reservó el mismo día para el mismo día.
    Si la persona no responde, el mensaje le indica que debe llamar al
    restaurante; el estado de la reserva no cambia hasta que responda.
    """
    now = datetime.now()
    with _lock:
        reservations = storage.list_reservations()
        due = []
        for r in reservations:
            if r.get("status") == "cancelled" or r.get("attendanceReminderSent"):
                continue
            try:
                res_dt = datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H:%M")
                created_date = datetime.fromisoformat(r["createdAt"]).date()
            except (ValueError, KeyError):
                continue

            same_day_booking = res_dt.date() == created_date
            threshold = (
                SAME_DAY_ATTENDANCE_MINUTES_BEFORE
                if same_day_booking
                else ADVANCE_ATTENDANCE_MINUTES_BEFORE
            )
            minutes_until = (res_dt - now).total_seconds() / 60
            if 0 <= minutes_until <= threshold:
                r["attendanceReminderSent"] = True
                storage.save_reservation(r)
                due.append(r)
    for r in due:
        notifications.notify_attendance_confirmation(r, PUBLIC_BASE_URL)


def _check_and_send_reminders():
    now = datetime.now()
    with _lock:
        reservations = storage.list_reservations()
        due = []
        for r in reservations:
            if r.get("status") == "cancelled" or r.get("reminderSent"):
                continue
            try:
                res_dt = datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H:%M")
            except (ValueError, KeyError):
                continue
            minutes_until = (res_dt - now).total_seconds() / 60
            if 0 <= minutes_until <= REMINDER_MINUTES_BEFORE:
                r["reminderSent"] = True
                storage.save_reservation(r)
                due.append(r)
    for r in due:
        notifications.notify_reminder(r)


def _reminder_loop():
    while True:
        time.sleep(60)
        try:
            _check_and_send_attendance_confirmations()
        except Exception:  # noqa: BLE001 - el hilo de fondo no debe morir por un error puntual
            pass
        try:
            _check_and_send_reminders()
        except Exception:  # noqa: BLE001
            pass


def main():
    import sys

    global PUBLIC_BASE_URL

    # Los proveedores de hosting (Render, Railway, etc.) asignan el puerto
    # mediante la variable de entorno PORT; en local se puede pasar como
    # argumento o usar el valor por defecto 8000.
    if os.environ.get("PORT"):
        port = int(os.environ["PORT"])
    elif len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", f"http://localhost:{port}")
    threading.Thread(target=_reminder_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"White Bear Restaurant - servidor de reservaciones")
    print(f"  Sitio de clientes:  http://localhost:{port}/")
    print(f"  Panel para tablet:  http://localhost:{port}/tablet.html")
    print(
        f"  Almacenamiento: {'Supabase (persistente)' if storage.enabled() else 'archivo local data/reservations.json (NO persistente en hosting gratis)'}"
    )
    print(
        f"  Notificaciones: correo {'ACTIVO' if notifications.email_enabled() else 'modo prueba (dry-run)'}, "
        f"SMS {'ACTIVO' if notifications.sms_enabled() else 'modo prueba (dry-run)'}"
    )
    print(f"Presiona Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
