"""
Envío de mensajes de confirmación y recordatorio para White Bear Restaurant.
Sin dependencias externas: usa smtplib (correo) y la API REST de Twilio
por HTTP directo (SMS), ambas de la librería estándar de Python.

Para activar el envío real, configura variables de entorno antes de correr
server.py. Mientras no estén configuradas, los mensajes se guardan en modo
"dry-run" (simulado) en data/notifications_log.txt y en la consola, así el
sitio funciona igual para probar todo el flujo sin tener credenciales.

Correo (SMTP) — ejemplo con Gmail (requiere una "contraseña de aplicación",
no la contraseña normal de la cuenta):
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=turestaurante@gmail.com
    SMTP_PASSWORD=xxxxxxxxxxxxxxxx
    SMTP_FROM=turestaurante@gmail.com   (opcional, usa SMTP_USER si falta)

SMS (Twilio) — requiere una cuenta en twilio.com:
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_FROM_NUMBER=+15005550006
"""

import base64
import os
import re
import smtplib
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "data", "notifications_log.txt")


def email_enabled():
    return bool(os.environ.get("SMTP_HOST"))


def sms_enabled():
    return bool(
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and os.environ.get("TWILIO_FROM_NUMBER")
    )


def _log(channel, to, message, ok, detail):
    status = "ENVIADO" if ok else ("DRY-RUN" if detail == "dry-run" else "ERROR")
    line = (
        f"[{datetime.now().isoformat(timespec='seconds')}] {status} {channel} -> {to}\n"
        f"{message}\n"
    )
    if detail and detail != "dry-run":
        line += f"detalle: {detail}\n"
    line += "-" * 50 + "\n"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def send_email(to_addr, subject, body):
    if not to_addr:
        return False, "sin destinatario"

    if not email_enabled():
        _log("EMAIL", to_addr, f"Asunto: {subject}\n{body}", False, "dry-run")
        return False, "dry-run"

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = os.environ.get("SMTP_FROM") or user or "no-reply@whitebearrestaurant.com"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        _log("EMAIL", to_addr, f"Asunto: {subject}\n{body}", True, "enviado")
        return True, "enviado"
    except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier falla de red/SMTP
        _log("EMAIL", to_addr, f"Asunto: {subject}\n{body}", False, str(exc))
        return False, str(exc)


def to_e164(raw):
    """Convierte lo que escribe el cliente al formato internacional que exige
    Twilio ("+15183025235"), o devuelve None si no se puede.

    Los clientes escriben "(518) 302-5235", "518-302-5235" o "5183025235", y
    Twilio rechaza cualquiera de esos: sin esta conversión ningún SMS saldría.
    Sin prefijo se asume Estados Unidos / Canadá (+1), que es donde está el
    restaurante; un número con "+" y otro país se respeta tal cual."""
    text = (raw or "").strip()
    digits = re.sub(r"\D", "", text)
    if text.startswith("+"):
        return "+" + digits if 8 <= len(digits) <= 15 else None
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return None


def send_sms(to_number, body):
    if not to_number:
        return False, "sin destinatario"

    if not sms_enabled():
        _log("SMS", to_number, body, False, "dry-run")
        return False, "dry-run"

    e164 = to_e164(to_number)
    if not e164:
        _log("SMS", to_number, body, False, "número de teléfono no válido para SMS")
        return False, "número no válido"
    to_number = e164

    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({"To": to_number, "From": from_number, "Body": body}).encode()
    credentials = base64.b64encode(f"{sid}:{token}".encode()).decode()

    req = urllib.request.Request(url, data=data)
    req.add_header("Authorization", f"Basic {credentials}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        _log("SMS", to_number, body, True, "enviado")
        return True, "enviado"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        _log("SMS", to_number, body, False, detail)
        return False, detail
    except Exception as exc:  # noqa: BLE001
        _log("SMS", to_number, body, False, str(exc))
        return False, str(exc)


# ---------------------------------------------------------------------------
# Textos de los mensajes, en el idioma con que el cliente llenó el formulario
# (reservation["lang"]: "en", "es" o "fr"; sin dato, inglés, que es el idioma
# del restaurante y del sitio por omisión).
#
# Los SMS se escriben sin acentos ni signos como ¡ ¿: un solo carácter fuera
# del alfabeto básico de los SMS (GSM-7) obliga a mandarlo en otra codificación
# que cabe en 70 caracteres por mensaje en vez de 160, y se cobra por partes.
# Por eso cada texto está escrito con acentos (para el correo) y para el SMS se
# convierte con _sms_safe() ANTES de insertar el nombre del cliente, que se
# respeta tal como lo escribió.
# ---------------------------------------------------------------------------
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "es", "fr")
RESTAURANT_PHONE = "(518) 302-5235"

MESSAGES = {
    "en": {
        "confirmation": (
            "White Bear Restaurant: Hi {name}, we received your reservation for "
            "{date} at {time} ({party}). Code #{code}. See you soon!"
        ),
        "attendance": (
            "White Bear Restaurant: Hi {name}, please confirm you're coming on "
            "{date} at {time} ({party}): {url} If you can't confirm, please call "
            "{phone}."
        ),
        "reminder": (
            "White Bear Restaurant: Hi {name}, your table for {n} will be ready "
            "in 15 minutes (at {time}). See you soon!"
        ),
        "optout": " Reply STOP to opt out of texts.",
        "subject_confirmation": "Your reservation was received",
        "subject_attendance": "Please confirm your attendance",
        "subject_reminder": "Your table is almost ready",
    },
    "es": {
        "confirmation": (
            "White Bear Restaurant: hola {name}, recibimos tu reservación para el "
            "{date} a las {time} ({party}). Código #{code}. ¡Te esperamos!"
        ),
        "attendance": (
            "White Bear Restaurant: hola {name}, confirma tu asistencia para el "
            "{date} a las {time} ({party}) aquí: {url} Si no puedes confirmar, "
            "por favor llama al {phone}."
        ),
        "reminder": (
            "White Bear Restaurant: hola {name}, tu mesa para {party} estará lista "
            "en 15 minutos (a las {time}). ¡Te esperamos!"
        ),
        "optout": " Responde STOP para no recibir más SMS.",
        "subject_confirmation": "Recibimos tu reservación",
        "subject_attendance": "Confirma tu asistencia",
        "subject_reminder": "Tu mesa está casi lista",
    },
    "fr": {
        "confirmation": (
            "White Bear Restaurant : bonjour {name}, nous avons bien reçu votre "
            "réservation pour le {date} à {time} ({party}). Code #{code}. À bientôt !"
        ),
        "attendance": (
            "White Bear Restaurant : bonjour {name}, merci de confirmer votre venue "
            "le {date} à {time} ({party}) : {url} Si vous ne pouvez pas confirmer, "
            "appelez le {phone}."
        ),
        "reminder": (
            "White Bear Restaurant : bonjour {name}, votre table pour {party} sera "
            "prête dans 15 minutes (à {time}). À bientôt !"
        ),
        "optout": " Répondez STOP pour ne plus recevoir de SMS.",
        "subject_confirmation": "Nous avons reçu votre réservation",
        "subject_attendance": "Merci de confirmer votre venue",
        "subject_reminder": "Votre table est presque prête",
    },
}

_WEEKDAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
}
_MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"],
}


def message_language(reservation):
    lang = str(reservation.get("lang") or "").strip().lower()
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def _sms_safe(text):
    """Quita acentos y los signos ¡ ¿ para que el SMS quede en GSM-7."""
    text = text.replace("¡", "").replace("¿", "")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def date_text(lang, iso):
    """"2026-10-12" -> "Monday, Oct 12" / "lunes 12 de octubre" / "lundi 12 octobre"."""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return str(iso)
    weekday, month = _WEEKDAYS[lang][d.weekday()], _MONTHS[lang][d.month - 1]
    if lang == "es":
        return f"{weekday} {d.day} de {month}"
    if lang == "fr":
        return f"{weekday} {d.day} {month}"
    return f"{weekday}, {month} {d.day}"


def time_text(lang, hhmm):
    """"19:00" -> "7:00 PM" / "7:00 p.m." / "19:00", igual que el sitio."""
    try:
        h, m = (int(x) for x in str(hhmm).split(":"))
    except (TypeError, ValueError):
        return str(hhmm)
    if lang == "fr":
        return f"{h:02d}:{m:02d}"
    period = ("p.m." if h >= 12 else "a.m.") if lang == "es" else ("PM" if h >= 12 else "AM")
    return f"{h % 12 or 12}:{m:02d} {period}"


def party_text(lang, n):
    if lang == "es":
        return f"{n} persona" if n == 1 else f"{n} personas"
    if lang == "fr":
        return f"{n} personne" if n == 1 else f"{n} personnes"
    return f"party of {n}"


def _render(reservation, key, sms, url=""):
    lang = message_language(reservation)
    template = MESSAGES[lang][key]
    if sms:
        template = _sms_safe(template)
    try:
        n = int(reservation.get("partySize") or 0)
    except (TypeError, ValueError):
        n = 0
    return template.format(
        name=reservation.get("name", ""),
        date=date_text(lang, reservation.get("date")),
        time=time_text(lang, reservation.get("time")),
        party=party_text(lang, n),
        n=n,
        code=str(reservation.get("id", ""))[:8],
        url=url,
        phone=RESTAURANT_PHONE,
    )


def confirmation_message(reservation, sms=False):
    return _render(reservation, "confirmation", sms)


def attendance_confirmation_message(reservation, base_url, sms=False):
    # El enlace lleva el idioma para que la página de confirmación se abra en
    # el mismo idioma del mensaje, aunque el teléfono tenga otro guardado.
    url = f"{base_url}/confirm.html?id={reservation['id']}&lang={message_language(reservation)}"
    return _render(reservation, "attendance", sms, url=url)


def reminder_message(reservation, sms=False):
    return _render(reservation, "reminder", sms)


def sms_opt_out_note(reservation):
    """Va solo en el primer SMS de cada reserva (no en el correo): las normas de
    CTIA piden decir ahí cómo darse de baja. Twilio atiende STOP y HELP por su
    cuenta. Las condiciones completas están en public/legal.html#messages."""
    return _sms_safe(MESSAGES[message_language(reservation)]["optout"])


def _subject(reservation, key):
    return MESSAGES[message_language(reservation)][key]


def notify_confirmation(reservation):
    if reservation.get("phone"):
        send_sms(reservation["phone"], confirmation_message(reservation, sms=True) + sms_opt_out_note(reservation))
    if reservation.get("email"):
        send_email(reservation["email"], _subject(reservation, "subject_confirmation"), confirmation_message(reservation))


def notify_reminder(reservation):
    if reservation.get("phone"):
        send_sms(reservation["phone"], reminder_message(reservation, sms=True))
    if reservation.get("email"):
        send_email(reservation["email"], _subject(reservation, "subject_reminder"), reminder_message(reservation))


def notify_attendance_confirmation(reservation, base_url):
    if reservation.get("phone"):
        send_sms(reservation["phone"], attendance_confirmation_message(reservation, base_url, sms=True))
    if reservation.get("email"):
        send_email(
            reservation["email"],
            _subject(reservation, "subject_attendance"),
            attendance_confirmation_message(reservation, base_url),
        )
