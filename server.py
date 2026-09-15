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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DATA_FILE = os.path.join(BASE_DIR, "data", "reservations.json")

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


def _ensure_data_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _read_reservations():
    _ensure_data_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_reservations(reservations):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reservations, f, indent=2, ensure_ascii=False)


def _validate_preorder(raw_pre_order):
    """Valida y limpia la lista de platillos preordenados para grupos grandes."""
    if not raw_pre_order:
        return [], []
    if not isinstance(raw_pre_order, list):
        return [], ["El preorden del grupo no es válido."]

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
    errors = []

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    email = (payload.get("email") or "").strip()
    res_date = (payload.get("date") or "").strip()
    res_time = (payload.get("time") or "").strip()
    party_size = payload.get("partySize")
    notes = (payload.get("notes") or "").strip()
    pre_order, pre_order_errors = _validate_preorder(payload.get("preOrder"))
    pre_order_notes = (payload.get("preOrderNotes") or "").strip()
    errors.extend(pre_order_errors)

    if not name or len(name) < 2:
        errors.append("El nombre es obligatorio.")
    if not phone or len(re.sub(r"\D", "", phone)) < 7:
        errors.append("Ingresa un teléfono válido.")
    if email and not EMAIL_RE.match(email):
        errors.append("El correo electrónico no es válido.")

    try:
        parsed_date = datetime.strptime(res_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        parsed_date = None
        errors.append("Selecciona una fecha válida.")

    if parsed_date and parsed_date < date.today():
        errors.append("La fecha no puede ser en el pasado.")

    try:
        parsed_time = datetime.strptime(res_time, "%H:%M").time()
    except (ValueError, TypeError):
        parsed_time = None
        errors.append("Selecciona una hora válida.")

    if parsed_date and parsed_time:
        open_t, _close_t, last_t = _hours_for_date(parsed_date)
        if not (open_t <= parsed_time <= last_t):
            errors.append(
                f"Ese día recibimos reservaciones entre las "
                f"{open_t.strftime('%H:%M')} y las {last_t.strftime('%H:%M')}."
            )

    try:
        party_size = int(party_size)
        if not (1 <= party_size <= RESTAURANT["maxPartySize"]):
            errors.append(
                f"El número de personas debe ser entre 1 y {RESTAURANT['maxPartySize']}. "
                f"Para grupos más grandes, llama al {RESTAURANT['phone']}."
            )
    except (TypeError, ValueError):
        errors.append("Ingresa un número de personas válido.")
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
        "preOrder": pre_order,
        "preOrderNotes": pre_order_notes,
    }, []


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
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }
        content_type = content_types.get(ext, "application/octet-stream")

        with open(full_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- routing ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/restaurant":
            self._send_json(RESTAURANT)
            return
        if parsed.path == "/api/reservations":
            qs = parse_qs(parsed.query)
            date_filter = qs.get("date", [None])[0]
            with _lock:
                reservations = _read_reservations()
            if date_filter:
                reservations = [r for r in reservations if r["date"] == date_filter]
            reservations.sort(key=lambda r: (r["date"], r["time"]))
            self._send_json(reservations)
            return
        m = re.match(r"^/api/reservations/([a-f0-9]+)$", parsed.path)
        if m:
            res_id = m.group(1)
            with _lock:
                reservations = _read_reservations()
            found = next((r for r in reservations if r["id"] == res_id), None)
            if found:
                self._send_json(found)
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return
        self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/reservations":
            payload = self._read_json_body()
            if payload is None:
                self._send_json({"errors": ["JSON inválido."]}, status=400)
                return
            clean, errors = _validate_reservation(payload)
            if errors:
                self._send_json({"errors": errors}, status=400)
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
                reservations = _read_reservations()
                reservations.append(reservation)
                _write_reservations(reservations)
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
                reservations = _read_reservations()
                found = None
                for r in reservations:
                    if r["id"] == res_id:
                        r["attendanceConfirmed"] = confirmed
                        if not confirmed and r["status"] not in ("completed", "cancelled"):
                            r["status"] = "cancelled"
                        found = r
                        break
                if found:
                    _write_reservations(reservations)
            if found:
                self._send_json(found)
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        parsed = urlparse(self.path)
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
                reservations = _read_reservations()
                found = None
                for r in reservations:
                    if r["id"] == res_id:
                        r["status"] = new_status
                        found = r
                        break
                if found:
                    _write_reservations(reservations)
            if found:
                self._send_json(found)
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        m = re.match(r"^/api/reservations/([a-f0-9]+)$", parsed.path)
        if m:
            res_id = m.group(1)
            with _lock:
                reservations = _read_reservations()
                remaining = [r for r in reservations if r["id"] != res_id]
                deleted = len(remaining) != len(reservations)
                if deleted:
                    _write_reservations(remaining)
            if deleted:
                self._send_json({"ok": True})
            else:
                self._send_json({"errors": ["Reservación no encontrada."]}, status=404)
            return
        self.send_response(404)
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
        reservations = _read_reservations()
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
                due.append(r)
        if due:
            _write_reservations(reservations)
    for r in due:
        notifications.notify_attendance_confirmation(r, PUBLIC_BASE_URL)


def _check_and_send_reminders():
    now = datetime.now()
    with _lock:
        reservations = _read_reservations()
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
                due.append(r)
        if due:
            _write_reservations(reservations)
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
    _ensure_data_file()
    threading.Thread(target=_reminder_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"White Bear Restaurant - servidor de reservaciones")
    print(f"  Sitio de clientes:  http://localhost:{port}/")
    print(f"  Panel para tablet:  http://localhost:{port}/tablet.html")
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
