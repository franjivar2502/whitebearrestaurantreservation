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
import smtplib
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


def send_sms(to_number, body):
    if not to_number:
        return False, "sin destinatario"

    if not sms_enabled():
        _log("SMS", to_number, body, False, "dry-run")
        return False, "dry-run"

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


def confirmation_message(reservation):
    return (
        f"White Bear Restaurant: hola {reservation['name']}, tu reservacion para "
        f"el {reservation['date']} a las {reservation['time']} "
        f"({reservation['partySize']} personas) fue recibida. "
        f"Codigo #{reservation['id']}. Te esperamos!"
    )


def reminder_message(reservation):
    return (
        f"White Bear Restaurant: hola {reservation['name']}, tu mesa para "
        f"{reservation['partySize']} personas estara lista en 15 minutos "
        f"(a las {reservation['time']}). Te esperamos!"
    )


def notify_confirmation(reservation):
    message = confirmation_message(reservation)
    if reservation.get("phone"):
        send_sms(reservation["phone"], message)
    if reservation.get("email"):
        send_email(reservation["email"], "Confirmación de tu reservación", message)


def notify_reminder(reservation):
    message = reminder_message(reservation)
    if reservation.get("phone"):
        send_sms(reservation["phone"], message)
    if reservation.get("email"):
        send_email(reservation["email"], "Tu mesa está casi lista", message)
