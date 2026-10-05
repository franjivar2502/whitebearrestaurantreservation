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

import hashlib
import hmac
import json
import os
import re
import threading
import time
import unicodedata
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import notifications
import security
import storage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# URL pública del sitio, usada para armar los links de confirmación de
# asistencia que se envían por SMS/correo. En local apunta a localhost; al
# desplegar, define PUBLIC_BASE_URL (p. ej. https://tu-sitio.onrender.com).
PUBLIC_BASE_URL = None

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
    # Última hora para reservar: 15 minutos antes del cierre. Se reserva desde
    # la apertura hasta esa hora; fuera de ese rango el servidor rechaza la
    # reserva (y los formularios ni siquiera ofrecen esas horas).
    "lastSeatingBufferMinutes": 15,
    "maxPartySize": 40,
}

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

VALID_STATUSES = {"pending", "confirmed", "seated", "completed", "cancelled"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_SEATING_PREFERENCES = {"", "inside", "outside"}
# Estados de una reseña: "approved" se ve en el sitio, "pending" espera al
# staff, "hidden" la ocultó el staff (se conserva, no se borra).
VALID_REVIEW_STATUSES = {"approved", "pending", "hidden"}

# Moderación de reseñas de clientes por palabras clave: una reseña que
# contenga una palabra de esta lista (español o inglés) NO se publica sola,
# pero tampoco se descarta: se guarda como "pending" y llega a la cola de
# moderación del panel (/admin-photos.html), donde el staff decide si la
# publica o la oculta. Así el restaurante se entera y puede responder o
# llamar, y no se suprimen críticas en silencio (ver la norma de la FTC en
# DURABILIDAD.md). La calificación en estrellas no influye: una reseña de una
# estrella sin palabras de la lista se publica igual que una de cinco.
# Topes de longitud y de antelación. En un sitio abierto a internet, todo
# campo libre necesita un techo: si no, cualquiera llena la base del cliente.
MAX_NAME_LENGTH = 120
MAX_NOTES_LENGTH = 1000
MAX_REVIEW_LENGTH = 2000
MAX_BOOKING_DAYS_AHEAD = 180
MAX_PHONE_LENGTH = 40
MAX_EMAIL_LENGTH = 254
MAX_PHOTO_BYTES = 8 * 1024 * 1024

# Tamaño máximo del cuerpo de una petición. Sin techo, cualquiera manda un
# "Content-Length: 2000000000" y el servidor intenta leerlo todo en memoria.
MAX_JSON_BODY_BYTES = 64 * 1024
MAX_MULTIPART_BODY_BYTES = MAX_PHOTO_BYTES + 512 * 1024

# Límites por IP. Holgados para una persona real, cortos para un script:
# - Contraseña de staff/admin: 10 fallos cada 15 minutos. Una contraseña de
#   12+ caracteres no se adivina a ese ritmo ni en siglos.
# - Reservaciones: 10 por hora desde la misma conexión (el staff no cuenta).
# - Reseñas: 5 por hora.
# - Consultar/confirmar una reservación por su código: 60 cada 10 minutos,
#   para que nadie barra códigos buscando datos de otros clientes.
LOGIN_FAILURES = security.RateLimiter(10, 15 * 60)
RESERVATION_LIMIT = security.RateLimiter(10, 60 * 60)
REVIEW_LIMIT = security.RateLimiter(5, 60 * 60)
LOOKUP_LIMIT = security.RateLimiter(60, 10 * 60)

# Campos de una reservación que puede ver quien tiene solo el código (el link
# de confirmación de asistencia). Teléfono, correo y notas quedan fuera: el
# código viaja por SMS y correo, y si se reenvía no debe arrastrar esos datos.
PUBLIC_RESERVATION_FIELDS = (
    "id", "name", "date", "time", "partySize", "status", "attendanceConfirmed",
)
PAST_TIME_GRACE_MINUTES = 30

# Versión de las condiciones y la política de privacidad (public/legal.html)
# que acepta el cliente al marcar la casilla. Se guarda con cada reservación
# y reseña como prueba de qué texto aceptó: al cambiar ese texto, cambiar
# también esta fecha.
LEGAL_TERMS_VERSION = "2026-10-05"

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


def _normalize_review_text(text):
    """Minúsculas y sin acentos, para que 'pésimo' y 'pesimo' den lo mismo."""
    lowered = (text or "").lower()
    descompuesto = unicodedata.normalize("NFD", lowered)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


# Las palabras se buscan como palabras completas, no como subcadenas.
#
# Buscar subcadenas parecía más estricto y en realidad rechazaba reseñas
# buenas: "rat" cae dentro de "t-rat-o", así que "excelente trato" -- de las
# frases más comunes en una reseña positiva en español -- quedaba bloqueada.
# Lo mismo "robo" dentro de "robot", "rata" en "barata" o "asco" en "frasco".
_NEGATIVE_REVIEW_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(
        re.escape(_normalize_review_text(kw))
        for kw in sorted(NEGATIVE_REVIEW_KEYWORDS, key=len, reverse=True)
    )
    + r")\b"
)


def _review_text_allowed(text):
    """True si el texto no contiene ninguna palabra clave negativa."""
    return _NEGATIVE_REVIEW_PATTERN.search(_normalize_review_text(text)) is None


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
# El plano es un esquema ordenado sobre una CUADRÍCULA, no un plano a escala.
# Cada salón mide ROOM_UNITS (en "unidades"; 1 unidad = 1% del ancho del
# salón del fondo) y el panel lo dibuja con esa misma proporción, así que un
# cuadrado se ve cuadrado en cualquier pantalla. Reglas que lo mantienen
# armonioso, y que _build_tables comprueba al arrancar:
#   - Todas las mesas tienen el mismo fondo (TABLE_DEPTH). El largo crece con
#     los asientos: cuadrada de 4 = 14, rectangular = 6 + 4 por asiento
#     (4 → 22, 6 → 30, 10 → 46, 12 → 54).
#   - Las filas están a la misma distancia (ROW_PITCH) y las columnas pegadas
#     a los muros comparten el mismo margen (WALL_MARGIN): a la izquierda las
#     mesas se alinean por su borde izquierdo y a la derecha por el derecho.
#   - Ninguna mesa se sale del salón ni se encima con otra.
#
# Cada fila es (id, forma, asientos, número, salón, x, y). x e y son el CENTRO
# de la mesa en unidades. El id no depende de la posición ni del número, así
# que mover o renumerar una mesa aquí no invalida las que el staff dejó
# marcadas como no disponibles.
#
# Inventario: 10 cuadradas de 4, 5 rectangulares de 4, 8 de 6, 1 de 10 y 1 de
# 12 = 25 mesas, 130 asientos (el cliente siempre dijo 130 de palabra).
#
# 2026-10-05: el cliente aclaró que la mesa 21 es de 6 asientos (la 16 ya lo
# era), no de 4. Su id sigue siendo "rect4-4" a propósito: el estado "no
# disponible" se guarda por id, y renombrarlo dejaría la mesa desmarcada.
#
# PENDIENTE DE CONFIRMAR CON EL CLIENTE -- hasta entonces esto es una lectura
# del mapa, no un dato verificado:
#   1. El mapa no trae números. Los asigné en orden de lectura: primero el
#      salón de la entrada, de arriba hacia abajo, y después el del fondo.
#   2. El mapa marca las rectangulares con "R" sin decir cuáles son de 4 y
#      cuáles de 6.
#   3. Cuál de las dos grandes es la de 12 y cuál la de 10: puse la de 12 en
#      la del fondo (la más larga) y la de 10 en la del centro.
ROOM_UNITS = {"left": (125, 156), "right": (100, 156)}  # (ancho, alto)
TABLE_DEPTH = 14
WALL_MARGIN = 8
ROW_PITCH = 21
_ROWS = [15 + ROW_PITCH * i for i in range(7)]  # 15, 36, 57, 78, 99, 120, 141


def _table_length(shape, seats):
    return TABLE_DEPTH if shape == "square" else 6 + 4 * seats


def _left_x(shape, seats):  # columna pegada al muro izquierdo (borde izquierdo alineado)
    return WALL_MARGIN + _table_length(shape, seats) / 2


def _right_x(room, shape, seats):  # columna pegada al muro derecho (borde derecho alineado)
    return ROOM_UNITS[room][0] - WALL_MARGIN - _table_length(shape, seats) / 2


def _center_x(room):
    return ROOM_UNITS[room][0] / 2


TABLE_LAYOUT = [
    # --- Salón de la entrada (barra, entrada, baño) ---
    # Bloque de 4 cuadradas junto a la ventana (2x2) y una columna de mesas
    # contra el muro derecho, con el pasillo de la entrada en medio.
    ("square4-1", "square", 4, 1, "left", _left_x("square", 4), _ROWS[0]),
    ("square4-2", "square", 4, 2, "left", _left_x("square", 4) + 22, _ROWS[0]),
    ("square4-3", "square", 4, 3, "left", _right_x("left", "square", 4), _ROWS[0]),
    ("square4-10", "square", 4, 4, "left", _left_x("square", 4), _ROWS[1]),
    ("square4-11", "square", 4, 5, "left", _left_x("square", 4) + 22, _ROWS[1]),
    ("rect6-1", "rect", 6, 6, "left", _right_x("left", "rect", 6), _ROWS[1]),
    ("rect6-2", "rect", 6, 7, "left", _right_x("left", "rect", 6), _ROWS[2]),
    ("rect6-3", "rect", 6, 8, "left", _right_x("left", "rect", 6), _ROWS[3]),
    ("rect4-8", "rect", 4, 9, "left", _right_x("left", "rect", 4), _ROWS[4]),
    ("rect4-9", "rect", 4, 10, "left", _right_x("left", "rect", 4), _ROWS[5]),
    # --- Salón del fondo: 7 filas, tres columnas (izquierda, centro, derecha) ---
    ("square4-4", "square", 4, 11, "right", _left_x("square", 4), _ROWS[0]),
    ("square4-5", "square", 4, 12, "right", _center_x("right"), _ROWS[0]),
    ("square4-6", "square", 4, 13, "right", _right_x("right", "square", 4), _ROWS[0]),
    ("rect4-1", "rect", 4, 14, "right", _left_x("rect", 4), _ROWS[1]),
    ("square4-7", "square", 4, 15, "right", _center_x("right"), _ROWS[1]),
    ("rect6-6", "rect", 6, 16, "right", _right_x("right", "rect", 6), _ROWS[1]),
    ("rect4-2", "rect", 4, 17, "right", _left_x("rect", 4), _ROWS[2]),
    ("rect4-3", "rect", 4, 19, "right", _right_x("right", "rect", 4), _ROWS[2]),
    ("rect10-1", "rect", 10, 20, "right", _center_x("right"), _ROWS[3]),
    ("rect4-4", "rect", 6, 21, "right", _left_x("rect", 6), _ROWS[4]),  # el id conserva "rect4": ver nota arriba
    ("square4-9", "square", 4, 22, "right", _center_x("right"), _ROWS[4]),
    ("rect6-7", "rect", 6, 23, "right", _right_x("right", "rect", 6), _ROWS[4]),
    ("rect6-8", "rect", 6, 24, "right", _left_x("rect", 6), _ROWS[5]),
    ("rect6-9", "rect", 6, 25, "right", _right_x("right", "rect", 6), _ROWS[5]),
    ("rect12-1", "rect", 12, 26, "right", _center_x("right"), _ROWS[6]),
]

# Orden en que se dibujan los salones en el panel, de izquierda a derecha.
ROOM_ORDER = ["left", "right"]


def _build_tables():
    """Convierte la cuadrícula a lo que dibuja el panel: x, y, w, h en % del
    salón. Falla al arrancar si el plano deja de ser ordenado."""
    tables = []
    boxes = {}
    for table_id, shape, seats, number, room, cx, cy in TABLE_LAYOUT:
        room_w, room_h = ROOM_UNITS[room]
        length = _table_length(shape, seats)
        left, right = cx - length / 2, cx + length / 2
        top, bottom = cy - TABLE_DEPTH / 2, cy + TABLE_DEPTH / 2
        if left < WALL_MARGIN - 1e-6 or right > room_w - WALL_MARGIN + 1e-6 or top < 0 or bottom > room_h:
            raise ValueError(f"La mesa {number} se sale del salón {room}.")
        for other_number, (l2, r2, t2, b2) in boxes.get(room, {}).items():
            if left < r2 and l2 < right and top < b2 and t2 < bottom:
                raise ValueError(f"Las mesas {number} y {other_number} se traslapan en el salón {room}.")
        boxes.setdefault(room, {})[number] = (left, right, top, bottom)
        tables.append(
            {
                "id": table_id,
                "shape": shape,
                "seats": seats,
                "number": number,
                "room": room,
                # Centro y tamaño en % del salón (el panel los usa tal cual).
                "x": round(cx / room_w * 100, 2),
                "y": round(cy / room_h * 100, 2),
                "w": round(length / room_w * 100, 2),
                "h": round(TABLE_DEPTH / room_h * 100, 2),
            }
        )

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

# Contraseña del panel de staff (/tablet.html) y de la API privada de
# reservaciones y mesas, que expone nombres y teléfonos de los clientes.
# Si no se define, se usa ADMIN_PASSWORD; si tampoco hay esa, la API
# privada queda bloqueada por completo (nunca abierta por omisión).
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "") or ADMIN_PASSWORD


def _password_matches(given, expected):
    """Compara contraseñas sin filtrar por tiempo cuántos caracteres acertó.
    Sin contraseña configurada, nada coincide (ni siquiera la vacía)."""
    if not expected or not isinstance(given, str):
        return False
    return hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8"))


# Interruptor global de reservaciones. El staff lo apaga desde el panel
# (/tablet.html) cuando no quiere más reservaciones del público: noche de
# evento privado, cocina saturada, obra en el salón. Apagado, el sitio de
# clientes deja de aceptar reservaciones nuevas, pero el alta rápida del
# panel sigue funcionando -- apagarlo es cerrar la agenda al público, no
# impedir que el encargado apunte la mesa que acaba de entrar por teléfono.
#
# Las reservaciones ya tomadas no se tocan: siguen en la lista del turno.
BOOKING_SETTING_KEY = "bookingEnabled"


def _bookings_open():
    """True si se aceptan reservaciones nuevas del público.

    Por omisión está encendido: una base recién creada (sin la fila del
    ajuste) debe comportarse como siempre, aceptando reservaciones."""
    return storage.get_setting(BOOKING_SETTING_KEY, True) is not False

# Hora del restaurante. El servidor en la nube corre en UTC: sin esto, a
# partir de las 8 de la noche en Lake Placid el servidor ya creía que era
# "mañana" (y rechazaba reservas para esa misma noche como fecha pasada), y
# los recordatorios salían con 4-5 horas de desfase. Todas las fechas y horas
# guardadas son de reloj local del restaurante, así que "ahora" también.
RESTAURANT_TIMEZONE = os.environ.get("RESTAURANT_TIMEZONE", "America/New_York")
try:
    _RESTAURANT_TZ = ZoneInfo(RESTAURANT_TIMEZONE)
except (ZoneInfoNotFoundError, ValueError):
    print(f"[ERROR] Zona horaria {RESTAURANT_TIMEZONE!r} no disponible; se usa la del servidor.")
    _RESTAURANT_TZ = None


def _now():
    """Fecha y hora actuales en el restaurante (sin tzinfo, como las guardadas)."""
    return datetime.now(_RESTAURANT_TZ).replace(tzinfo=None)


def _today():
    return _now().date()


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
    for r in storage.list_reservations(on_date=res_date):
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


def _validate_reservation(payload):
    """
    Devuelve (datos_limpios, errores). Cada error es un dict {"code": ...,
    "params": {...}} en vez de un mensaje ya traducido: el frontend decide
    el idioma (inglés/español/francés) con su propio diccionario (i18n.js),
    usando "code" como llave y "params" para rellenar valores como horarios
    o el máximo de personas.
    """
    errors = []

    if not isinstance(payload, dict):
        return None, [{"code": "GENERIC"}]

    def text(key):
        # Un número o una lista donde se espera texto no debe tumbar el
        # servidor con un AttributeError: se trata como vacío.
        value = payload.get(key)
        return value.strip() if isinstance(value, str) else ""

    name = text("name")
    phone = text("phone")
    email = text("email")
    res_date = text("date")
    res_time = text("time")
    party_size = payload.get("partySize")
    notes = text("notes")
    seating_preference = text("seatingPreference").lower()
    if seating_preference not in VALID_SEATING_PREFERENCES:
        seating_preference = ""
    # Idioma en que se le escriben los mensajes (SMS y correo). Un valor
    # desconocido o ausente no es un error: se usa el idioma por omisión.
    lang = text("lang").lower()
    if lang not in notifications.SUPPORTED_LANGS:
        lang = notifications.DEFAULT_LANG

    # Los topes de longitud no son cosmética: sin ellos cabe un nombre de
    # 5000 caracteres que descuadra la ficha del panel y llena la base.
    if not name or len(name) < 2 or len(name) > MAX_NAME_LENGTH:
        errors.append({"code": "NAME_REQUIRED"})
    if len(notes) > MAX_NOTES_LENGTH:
        errors.append({"code": "NOTES_TOO_LONG"})
    if not phone or len(re.sub(r"\D", "", phone)) < 7 or len(phone) > MAX_PHONE_LENGTH:
        errors.append({"code": "PHONE_INVALID"})
    if email and (len(email) > MAX_EMAIL_LENGTH or not EMAIL_RE.match(email)):
        errors.append({"code": "EMAIL_INVALID"})

    try:
        parsed_date = datetime.strptime(res_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        parsed_date = None
        errors.append({"code": "DATE_INVALID"})

    if parsed_date and parsed_date < _today():
        errors.append({"code": "DATE_PAST"})

    # Tope por arriba: sin él se aceptaban reservas a 400 días vista. Ningún
    # restaurante toma mesa para dentro de un año, y esas filas se quedan
    # ensuciando el panel durante meses.
    if parsed_date and parsed_date > _today() + timedelta(days=MAX_BOOKING_DAYS_AHEAD):
        errors.append({"code": "DATE_TOO_FAR"})

    try:
        parsed_time = datetime.strptime(res_time, "%H:%M").time()
    except (ValueError, TypeError):
        parsed_time = None
        errors.append({"code": "TIME_INVALID"})

    # Una hora de hoy que ya pasó. Con las reservas 24/7 es fácil pedirla sin
    # querer (a las 23:50, "las 00:15" de hoy). Se deja un margen para que el
    # personal pueda apuntar a quien acaba de sentarse.
    if (
        parsed_date
        and parsed_time
        and datetime.combine(parsed_date, parsed_time) < _now() - timedelta(minutes=PAST_TIME_GRACE_MINUTES)
    ):
        errors.append({"code": "TIME_PAST"})

    # Solo se reserva dentro del horario de apertura, hasta 15 minutos antes
    # del cierre (RESTAURANT["lastSeatingBufferMinutes"]): ese día a esa hora.
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
        if isinstance(party_size, bool):
            raise TypeError
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
        "lang": lang,
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


def _static_file(path):
    """Ruta absoluta del archivo de public/ que corresponde a la URL, o None.
    Nunca sale de public/ (ni con ../ ni con un directorio hermano llamado
    "public-algo") y nunca sirve archivos ocultos (.env, .git...)."""
    if path == "/":
        path = "/index.html"
    safe_path = os.path.normpath("/" + path).lstrip("/")
    if any(part.startswith(".") for part in safe_path.split(os.sep)):
        return None
    full_path = os.path.realpath(os.path.join(PUBLIC_DIR, safe_path))
    if not full_path.startswith(os.path.realpath(PUBLIC_DIR) + os.sep):
        return None
    return full_path if os.path.isfile(full_path) else None


# ---------------------------------------------------------------------------
# Caché de los archivos estáticos.
#
# Antes solo el HTML llevaba Cache-Control; los .js y .css no decían nada y un
# navegador (sobre todo Safari en iPhone) podía seguir usando una copia vieja
# con una página nueva. Tras quitar una sección del panel, un tablet.js viejo
# buscaba elementos que ya no existían y se rompía al cargar: el panel quedaba
# sin mesas ni reservaciones hasta que alguien borraba los datos del sitio.
#
# Dos defensas, que se complementan:
#   1. En el HTML, cada js/xxx.js y css/xxx.css lleva ?v=<huella del contenido>.
#      Como el HTML nunca se guarda en caché, un archivo cambiado trae una URL
#      nueva y el navegador lo descarga sí o sí.
#   2. Los .js y .css se sirven con ETag y "no-cache": el navegador pregunta si
#      cambiaron y, si no, el servidor responde 304 sin reenviarlos.
# ---------------------------------------------------------------------------
_ASSET_REF = re.compile(r'((?:src|href)=")(/?(?:js|css)/[A-Za-z0-9_.\-]+\.(?:js|css))(")')
_asset_versions = {}  # ruta -> (fecha de modificación, huella)


def _asset_version(full_path):
    mtime = os.path.getmtime(full_path)
    cached = _asset_versions.get(full_path)
    if cached and cached[0] == mtime:
        return cached[1]
    with open(full_path, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:10]
    _asset_versions[full_path] = (mtime, digest)
    return digest


def _version_asset_links(html):
    def add_version(match):
        asset = _static_file("/" + match.group(2).lstrip("/"))
        if not asset:
            return match.group(0)
        return f"{match.group(1)}{match.group(2)}?v={_asset_version(asset)}{match.group(3)}"

    return _ASSET_REF.sub(add_version, html)


def _static_payload(full_path, if_none_match=""):
    """(estado, encabezados, cuerpo) de un archivo de public/."""
    ext = os.path.splitext(full_path)[1].lower()
    headers = {"Content-Type": CONTENT_TYPES.get(ext, "application/octet-stream")}
    with open(full_path, "rb") as f:
        body = f.read()
    if ext == ".html":
        # Las páginas siempre frescas: tras un arreglo de seguridad nadie
        # debe quedarse con la versión vieja en caché.
        headers["Cache-Control"] = "no-cache"
        body = _version_asset_links(body.decode("utf-8")).encode("utf-8")
    elif ext in (".js", ".css"):
        etag = '"' + hashlib.sha1(body).hexdigest()[:20] + '"'
        headers["Cache-Control"] = "no-cache"
        headers["ETag"] = etag
        if etag in [tag.strip() for tag in if_none_match.split(",")]:
            return 304, headers, b""
    headers["Content-Length"] = str(len(body))
    return 200, headers, body


def _public_reservation(r):
    return {k: r.get(k) for k in PUBLIC_RESERVATION_FIELDS}


class BodyTooLarge(Exception):
    pass


class BadRequest(Exception):
    pass


class Handler(BaseHTTPRequestHandler):
    # Sin versión de Python ni del servidor en la cabecera Server: no le
    # regalamos a un escáner qué vulnerabilidades probar primero.
    server_version = "WhiteBear"
    sys_version = ""

    def version_string(self):
        return self.server_version
    # Una conexión que no manda nada en 30 s se cierra. Sin esto, unas
    # cuantas conexiones abiertas a propósito y mudas (ataque "slowloris")
    # dejan al servidor sin hilos para los clientes de verdad.
    timeout = 30

    def log_message(self, fmt, *args):
        pass  # silencia el log por defecto (ruidoso)

    def end_headers(self):
        # Cabeceras de seguridad en todas las respuestas (HTML, API y 404).
        for name, value in security.SECURITY_HEADERS.items():
            self.send_header(name, value)
        if (self.headers.get("X-Forwarded-Proto") or "").lower() == "https":
            self.send_header(*security.HSTS_HEADER)
        super().end_headers()

    # ---------- helpers ----------
    def _client_ip(self):
        return security.client_ip(self.headers, self.client_address[0])

    def _send_internal_error(self, method, exc):
        # El detalle va al log del servidor (Render -> Logs), nunca al
        # navegador: un mensaje de excepción puede revelar rutas, nombres de
        # tablas o fragmentos de la configuración.
        print(f"[ERROR] {method} {urlparse(self.path).path}: {exc!r}")
        try:
            self._send_json({"errors": [{"code": "GENERIC"}]}, status=500)
        except Exception:  # noqa: BLE001 - la conexión ya puede estar rota
            pass

    def _handle(self, method, fn):
        try:
            if method in ("POST", "PATCH", "DELETE") and not self._same_origin():
                self._send_json({"errors": ["Origen no permitido."]}, status=403)
                return
            fn()
        except BodyTooLarge:
            self.close_connection = True
            self._send_json({"errors": ["La petición es demasiado grande."]}, status=413)
        except BadRequest:
            self.close_connection = True
            self._send_json({"errors": ["Petición inválida."]}, status=400)
        except Exception as exc:  # noqa: BLE001
            self._send_internal_error(method, exc)

    def _same_origin(self):
        """
        Los navegadores mandan Origin en toda petición que modifica datos. Si
        viene de otro sitio (una página ajena que intenta crear reservas o
        reseñas a nombre de quien la visita), se rechaza. Sin Origin (curl,
        apps) se deja pasar: esos clientes no llevan la sesión de nadie.
        """
        origin = self.headers.get("Origin")
        if not origin:
            return True
        origin_host = urlparse(origin).netloc.lower()
        allowed = {
            (self.headers.get("Host") or "").strip().lower(),
            (self.headers.get("X-Forwarded-Host") or "").strip().lower(),
            urlparse(PUBLIC_BASE_URL or "").netloc.lower(),
        }
        allowed.discard("")
        return origin_host in allowed

    def _content_length(self, limit):
        raw = self.headers.get("Content-Length", "0") or "0"
        try:
            length = int(raw)
        except ValueError:
            raise BadRequest()
        if length < 0:
            raise BadRequest()
        if length > limit:
            raise BodyTooLarge()
        return length

    def _too_many(self, params=None):
        self._send_json(
            {"errors": [{"code": "REQUEST_BLOCKED", "params": {"phone": RESTAURANT["phone"], **(params or {})}}]},
            status=429,
        )

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = self._content_length(MAX_JSON_BODY_BYTES)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        # Todas las rutas esperan un objeto; una lista o un número suelto
        # se trata igual que JSON inválido.
        return data if isinstance(data, dict) else None

    def _read_raw_body(self, limit=MAX_MULTIPART_BODY_BYTES):
        length = self._content_length(limit)
        return self.rfile.read(length) if length else b""

    def _check_password(self, given, *expected):
        """
        Compara una contraseña con protección contra fuerza bruta: tras
        demasiados fallos desde la misma IP se responde 429 sin siquiera
        mirar la contraseña, también si esta vez es la correcta (si no, el
        atacante sabría cuándo acertó). Devuelve True, False o None (=429 ya
        enviado). Una cabecera vacía no cuenta como intento: es la tablet
        recién abierta, sin contraseña guardada.
        """
        ip = self._client_ip()
        if LOGIN_FAILURES.blocked(ip):
            self._too_many()
            return None
        if any(_password_matches(given, e) for e in expected):
            return True
        if given:
            LOGIN_FAILURES.hit(ip)
        return False

    def _require_admin(self):
        ok = self._check_password(self.headers.get("X-Admin-Password"), ADMIN_PASSWORD)
        if ok:
            return True
        if ok is False:
            self._send_json({"errors": ["No autorizado."]}, status=401)
        return False

    def _is_staff(self):
        # La contraseña de administración también abre el panel de staff:
        # quien puede tocar las fotos del sitio puede ver las reservaciones.
        return _password_matches(
            self.headers.get("X-Staff-Password"), STAFF_PASSWORD
        ) or _password_matches(self.headers.get("X-Staff-Password"), ADMIN_PASSWORD)

    def _require_staff(self):
        ok = self._check_password(self.headers.get("X-Staff-Password"), STAFF_PASSWORD, ADMIN_PASSWORD)
        if ok:
            return True
        if ok is False:
            self._send_json({"errors": ["No autorizado."]}, status=401)
        return False

    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        full_path = _static_file(path)
        if not full_path:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        status, headers, body = _static_payload(full_path, self.headers.get("If-None-Match", ""))
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        if status == 200:
            self.wfile.write(body)

    # ---------- routing ----------
    def do_GET(self):
        self._handle("GET", self._do_GET)

    def _do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            health, status = _health()
            self._send_json(health, status=status)
            return
        if parsed.path == "/api/restaurant":
            # bookingEnabled viaja aquí (y no en un endpoint privado) porque
            # el formulario público necesita saberlo para avisar que la
            # agenda está cerrada antes de que el cliente llene todo.
            with _lock:
                booking_enabled = _bookings_open()
            # "now" es la hora de pared del restaurante (no la del cliente): el
            # formulario la usa para no ofrecer las horas de hoy que ya pasaron,
            # aunque quien reserva esté en otra zona horaria.
            self._send_json(
                {
                    **RESTAURANT,
                    "bookingEnabled": booking_enabled,
                    "now": _now().isoformat(timespec="minutes"),
                }
            )
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
        if parsed.path == "/api/settings":
            if not self._require_staff():
                return
            with _lock:
                self._send_json({"bookingEnabled": _bookings_open()})
            return
        if parsed.path == "/api/admin/reviews":
            if not self._require_admin():
                return
            with _lock:
                reviews = storage.list_reviews()
            self._send_json(reviews)
            return
        if parsed.path == "/api/tables":
            if not self._require_staff():
                return
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
                    "roomUnits": {r: {"w": w, "h": h} for r, (w, h) in ROOM_UNITS.items()},
                    "totalSeats": TOTAL_SEATS,
                    "availableSeats": available_seats,
                }
            )
            return
        if parsed.path == "/api/reservations":
            if not self._require_staff():
                return
            qs = parse_qs(parsed.query)
            date_filter = qs.get("date", [None])[0]
            with _lock:
                reservations = storage.list_reservations()
            if date_filter:
                reservations = [r for r in reservations if r["date"] == date_filter]
            reservations.sort(key=lambda r: (r["date"], r["time"]))
            self._send_json(reservations)
            return
        m = re.match(r"^/api/reservations/([a-f0-9]{8,32})$", parsed.path)
        if m:
            if not LOOKUP_LIMIT.hit(self._client_ip()):
                self._too_many()
                return
            res_id = m.group(1)
            with _lock:
                reservations = storage.list_reservations()
            found = next((r for r in reservations if r["id"] == res_id), None)
            if found:
                self._send_json(_public_reservation(found))
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return
        self._serve_static(parsed.path)

    def do_POST(self):
        self._handle("POST", self._do_POST)

    def _do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/reviews":
            if REVIEW_LIMIT.blocked(self._client_ip()):
                self._too_many()
                return
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
            if (fields.get("website", {}).get("data") or b"").strip():
                # Campo trampa lleno: es un bot. Se rechaza sin dar pistas.
                self._too_many()
                return

            errors = []
            if (fields.get("reviewConsent", {}).get("data") or b"").strip() != b"on":
                errors.append({"code": "REVIEW_CONSENT_REQUIRED"})
            if not name or len(name) < 2 or len(name) > MAX_NAME_LENGTH:
                errors.append({"code": "NAME_REQUIRED"})
            if not text or len(text) < 5 or len(text) > MAX_REVIEW_LENGTH:
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

            # Ya no se rechaza: si trae una palabra de la lista, queda
            # retenida para que el staff la vea y decida.
            needs_moderation = not _review_text_allowed(text)

            if not REVIEW_LIMIT.hit(self._client_ip()):
                self._too_many()
                return

            photo_url = ""
            photo_field = fields.get("photo")
            if photo_field and photo_field.get("filename") and photo_field.get("data"):
                photo_bytes = photo_field["data"]
                if len(photo_bytes) > MAX_PHOTO_BYTES:
                    self._send_json({"errors": [{"code": "REVIEW_PHOTO_TOO_LARGE"}]}, status=400)
                    return
                # El tipo y la extensión se deducen del contenido, nunca de lo
                # que declara el navegador: así un SVG con script o un HTML
                # renombrado a .jpg no llega a publicarse.
                sniffed = security.sniff_image(photo_bytes)
                if not sniffed:
                    self._send_json({"errors": [{"code": "REVIEW_PHOTO_INVALID"}]}, status=400)
                    return
                ext, photo_content_type = sniffed
                # Las fotos del celular traen en los metadatos (EXIF) el GPS
                # de donde se tomaron, a menudo la casa del cliente. Se quitan
                # antes de publicarlas.
                try:
                    photo_bytes = security.strip_metadata(photo_bytes, ext)
                except ValueError:
                    self._send_json({"errors": [{"code": "REVIEW_PHOTO_INVALID"}]}, status=400)
                    return
                filename = f"{uuid.uuid4().hex}{ext}"
                with _lock:
                    photo_url = storage.upload_review_photo(filename, photo_bytes, photo_content_type)

            review = {
                "id": uuid.uuid4().hex[:8],
                "name": name,
                "text": text,
                "rating": rating,
                "photoUrl": photo_url,
                "status": "pending" if needs_moderation else "approved",
                "createdAt": _now().isoformat(timespec="seconds"),
                "consent": {"version": LEGAL_TERMS_VERSION, "at": _now().isoformat(timespec="seconds")},
            }
            with _lock:
                storage.save_review(review)
            self._send_json(review, status=201)
            return

        if parsed.path == "/api/reservations":
            # El staff (tablet) no tiene tope: un sábado puede cargar decenas
            # de reservaciones por teléfono desde la misma conexión.
            is_staff = self._is_staff()
            ip = self._client_ip()
            if not is_staff and RESERVATION_LIMIT.blocked(ip):
                self._too_many()
                return
            payload = self._read_json_body()
            if payload is None:
                self._send_json({"errors": ["JSON inválido."]}, status=400)
                return
            # El interruptor cierra la agenda al público; el panel de staff
            # (que manda su contraseña en X-Staff-Password) sigue pudiendo
            # apuntar una reserva tomada por teléfono.
            if not is_staff:
                with _lock:
                    accepting = _bookings_open()
                if not accepting:
                    self._send_json({"errors": [{"code": "BOOKING_CLOSED"}]}, status=403)
                    return
            if isinstance(payload.get("website"), str) and payload["website"].strip():
                self._too_many()
                return
            clean, errors = _validate_reservation(payload)
            # Desde el sitio, el cliente tiene que marcar la casilla de las
            # condiciones (que incluye el aviso de SMS). Las reservas que el
            # staff apunta por teléfono no pasan por ese formulario.
            if not is_staff and payload.get("termsConsent") is not True:
                errors = (errors or []) + [{"code": "CONSENT_REQUIRED"}]
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            if is_staff:
                consent = {"source": "staff"}
            else:
                consent = {
                    "source": "web",
                    "version": LEGAL_TERMS_VERSION,
                    "terms": True,
                    "sms": True,
                    "at": _now().isoformat(timespec="seconds"),
                }
            if not is_staff and not RESERVATION_LIMIT.hit(ip):
                self._too_many()
                return
            reservation = {
                # 32 caracteres hex (128 bits): el código va en el link de
                # confirmación y es lo único que lo protege, así que no debe
                # poder adivinarse. Los códigos cortos ya enviados siguen
                # funcionando.
                "id": uuid.uuid4().hex,
                "status": "pending",
                "createdAt": _now().isoformat(timespec="seconds"),
                "reminderSent": False,
                "attendanceReminderSent": False,
                "attendanceConfirmed": None,
                "consent": consent,
                **clean,
            }
            # Comprobar y guardar bajo el mismo candado. Antes eran dos
            # bloques separados: dos clientes reservando a la vez el último
            # hueco pasaban los dos la comprobación y ambos quedaban dentro.
            with _lock:
                available = _available_seats(clean["date"], clean["time"])
                if available >= clean["partySize"]:
                    storage.save_reservation(reservation)
            if available < clean["partySize"]:
                self._send_json({"errors": [{"code": "NO_AVAILABILITY"}]}, status=400)
                return
            threading.Thread(
                target=notifications.notify_confirmation, args=(reservation,), daemon=True
            ).start()
            self._send_json(reservation, status=201)
            return

        m = re.match(r"^/api/reservations/([a-f0-9]{8,32})/confirm-attendance$", parsed.path)
        if m:
            if not LOOKUP_LIMIT.hit(self._client_ip()):
                self._too_many()
                return
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
                self._send_json(_public_reservation(found))
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return

        if parsed.path == "/api/admin/login":
            payload = self._read_json_body()
            password = (payload or {}).get("password", "")
            ok = self._check_password(password, ADMIN_PASSWORD)
            if ok:
                self._send_json({"ok": True})
            elif ok is False:
                self._send_json({"errors": ["Contraseña incorrecta."]}, status=401)
            return

        if parsed.path == "/api/staff/login":
            payload = self._read_json_body()
            password = (payload or {}).get("password", "")
            ok = self._check_password(password, STAFF_PASSWORD, ADMIN_PASSWORD)
            if ok:
                self._send_json({"ok": True})
            elif ok is False:
                self._send_json({"errors": ["Contraseña incorrecta."]}, status=401)
            return

        if parsed.path == "/api/admin/photos":
            if not self._require_admin():
                return
            payload = self._read_json_body() or {}
            url = str(payload.get("url") or "").strip()
            caption = str(payload.get("caption") or "").strip()[:300]
            # La sección «gallery» se quitó del sitio: toda foto nueva es del menú.
            category = (payload.get("category") or "menu").strip()
            if category not in ("gallery", "menu"):
                category = "menu"
            if not url.startswith(("http://", "https://")) or len(url) > 2000 or re.search(r"\s", url):
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
                    "created_at": _now().isoformat(timespec="seconds"),
                }
                storage.add_photo(photo)
            self._send_json(photo, status=201)
            return

        if parsed.path == "/api/admin/photos/reorder":
            if not self._require_admin():
                return
            payload = self._read_json_body() or {}
            order = payload.get("order")
            # Los ids terminan en la URL de la consulta a Supabase: solo hex.
            if (
                not isinstance(order, list)
                or not order
                or not all(isinstance(i, str) and re.fullmatch(r"[a-f0-9]{1,32}", i) for i in order)
            ):
                self._send_json({"errors": ["Falta el nuevo orden."]}, status=400)
                return
            with _lock:
                storage.set_photo_order(order)
            self._send_json({"ok": True})
            return

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        self._handle("PATCH", self._do_PATCH)

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

        if parsed.path == "/api/settings":
            if not self._require_staff():
                return
            payload = self._read_json_body()
            if payload is None or not isinstance(payload.get("bookingEnabled"), bool):
                self._send_json({"errors": ["Falta indicar si se aceptan reservaciones."]}, status=400)
                return
            with _lock:
                storage.set_setting(BOOKING_SETTING_KEY, payload["bookingEnabled"])
            self._send_json({"bookingEnabled": payload["bookingEnabled"]})
            return
        m = re.match(r"^/api/admin/reviews/([a-f0-9]+)$", parsed.path)
        if m:
            if not self._require_admin():
                return
            review_id = m.group(1)
            payload = self._read_json_body() or {}
            new_status = payload.get("status")
            if new_status not in VALID_REVIEW_STATUSES:
                self._send_json({"errors": ["Estado inválido."]}, status=400)
                return
            with _lock:
                found = next((r for r in storage.list_reviews() if r["id"] == review_id), None)
                if found:
                    found["status"] = new_status
                    found["moderatedAt"] = _now().isoformat(timespec="seconds")
                    storage.save_review(found)
            if found:
                self._send_json(found)
            else:
                self._send_json({"errors": ["Reseña no encontrada."]}, status=404)
            return

        m = re.match(r"^/api/tables/([a-z0-9-]+)$", parsed.path)
        if m:
            if not self._require_staff():
                return
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
            if not self._require_staff():
                return
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
        self._handle("DELETE", self._do_DELETE)

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
            if not self._require_staff():
                return
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
            if path == "/healthz":
                # Los monitores de disponibilidad (UptimeRobot) usan HEAD.
                self.send_response(_health()[1])
                self.end_headers()
                return
            if path == "/":
                path = "/index.html"
            full_path = _static_file(path)
            if full_path:
                status, headers, _ = _static_payload(full_path, self.headers.get("If-None-Match", ""))
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
            else:
                self.send_response(404)
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
    now = _now()
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
    now = _now()
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


# Cuántos días se guardan las reservaciones pasadas antes de borrarlas. Por
# omisión 60 (2 meses), lo que promete la política de privacidad
# (public/legal.html): si se cambia uno, cambiar el otro. Definirla vacía
# apaga la limpieza. Ver OPERACION.md.
RESERVATION_RETENTION_DAYS = os.environ.get("RESERVATION_RETENTION_DAYS", "60").strip()


def _purge_old_reservations():
    if not RESERVATION_RETENTION_DAYS:
        return 0
    days = int(RESERVATION_RETENTION_DAYS)
    if days < 30:
        # Protección contra un error de dedo (p. ej. "3" en vez de "365").
        raise ValueError("RESERVATION_RETENTION_DAYS debe ser 30 o más.")
    cutoff = (_today() - timedelta(days=days)).isoformat()
    with _lock:
        removed = storage.purge_reservations_before(cutoff)
    if removed:
        print(f"[INFO] Limpieza: {removed} reservaciones anteriores a {cutoff} borradas.")
    return removed


_started_at = time.time()
_last_loop_ok = None  # última vuelta del hilo de recordatorios sin errores


def _health():
    """Estado para /healthz: 200 si el almacenamiento responde, 503 si no."""
    health = {
        "ok": True,
        "uptimeSeconds": int(time.time() - _started_at),
        "time": _now().isoformat(timespec="seconds"),
        "timezone": RESTAURANT_TIMEZONE if _RESTAURANT_TZ else "servidor",
        "remindersLastRun": (
            datetime.fromtimestamp(_last_loop_ok, _RESTAURANT_TZ).isoformat(timespec="seconds")
            if _last_loop_ok
            else None
        ),
    }
    try:
        health["storage"] = storage.ping()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] healthz: almacenamiento no responde: {exc!r}")
        health["ok"] = False
        health["storage"] = "error"
    return health, 200 if health["ok"] else 503


def _reminder_loop():
    global _last_loop_ok
    last_purge_day = None
    while True:
        time.sleep(60)
        ok = True
        # Cada tarea por separado: que falle una no debe impedir las demás, ni
        # matar el hilo. Pero el error se imprime -- antes se tragaba en
        # silencio y un fallo de Supabase dejaba de mandar recordatorios sin
        # que nadie se enterara.
        for task in (_check_and_send_attendance_confirmations, _check_and_send_reminders):
            try:
                task()
            except Exception as exc:  # noqa: BLE001
                ok = False
                print(f"[ERROR] {task.__name__}: {exc!r}")
        if last_purge_day != _today():
            try:
                _purge_old_reservations()
                last_purge_day = _today()
            except Exception as exc:  # noqa: BLE001
                ok = False
                print(f"[ERROR] limpieza de reservaciones: {exc!r}")
        if ok:
            _last_loop_ok = time.time()


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
    for var, value in (("STAFF_PASSWORD", STAFF_PASSWORD), ("ADMIN_PASSWORD", ADMIN_PASSWORD)):
        if value and len(value) < 12:
            print(f"  AVISO: {var} es corta ({len(value)} caracteres). Usa 12 o más.")
    if not STAFF_PASSWORD:
        print(
            "  AVISO: sin STAFF_PASSWORD ni ADMIN_PASSWORD el panel de tablet queda "
            "bloqueado. Define STAFF_PASSWORD para poder entrar."
        )
    print(f"Presiona Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
