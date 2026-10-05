"""
Arranque común de las pruebas: un servidor real en un puerto libre, con los
datos en una carpeta temporal y sin Supabase, para que las pruebas nunca
toquen datos de verdad.
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import timedelta

# Antes de importar server: sin Supabase, y con contraseñas de prueba.
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""
os.environ["ADMIN_PASSWORD"] = "admin-de-prueba"
os.environ["STAFF_PASSWORD"] = "staff-de-prueba"
for var in ("SMTP_HOST", "TWILIO_ACCOUNT_SID", "RESERVATION_RETENTION_DAYS"):
    os.environ.pop(var, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import notifications  # noqa: E402
import server  # noqa: E402
import storage  # noqa: E402

# Los avisos simulados (dry-run) se imprimen; en las pruebas solo ensucian.
notifications.print = lambda *args, **kwargs: None

STAFF_HEADERS = {
    "X-Staff-Password": "staff-de-prueba",
    "X-Admin-Password": "admin-de-prueba",
}


def point_storage_at(data_dir):
    """Redirige todos los archivos locales a data_dir."""
    storage.SUPABASE_URL = ""
    storage.SUPABASE_KEY = ""
    storage.LOCAL_DATA_FILE = os.path.join(data_dir, "reservations.json")
    storage.LOCAL_PHOTOS_FILE = os.path.join(data_dir, "photos.json")
    storage.LOCAL_TABLE_STATUS_FILE = os.path.join(data_dir, "table_status.json")
    storage.LOCAL_REVIEWS_FILE = os.path.join(data_dir, "reviews.json")
    storage.LOCAL_REVIEW_PHOTOS_DIR = os.path.join(data_dir, "uploads")
    storage.LOCAL_SETTINGS_FILE = os.path.join(data_dir, "settings.json")
    storage._LOCAL_FILES = {
        "reservations": storage.LOCAL_DATA_FILE,
        "table_status": storage.LOCAL_TABLE_STATUS_FILE,
        "reviews": storage.LOCAL_REVIEWS_FILE,
        "photos": storage.LOCAL_PHOTOS_FILE,
    }
    notifications.LOG_FILE = os.path.join(data_dir, "notifications_log.txt")


def next_open_day(days_ahead=3):
    """Una fecha futura (el restaurante abre todos los días)."""
    return (server._today() + timedelta(days=days_ahead)).isoformat()


class ServerTestCase(unittest.TestCase):
    """Levanta un servidor por clase y vacía los datos antes de cada prueba."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = tempfile.mkdtemp(prefix="whitebear-test-")
        point_storage_at(cls.data_dir)
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.data_dir, ignore_errors=True)

    def setUp(self):
        # Los topes por conexión (todas las pruebas salen de 127.0.0.1) se
        # vacían para que una prueba no herede los intentos de otra.
        for limiter in (
            server.LOGIN_FAILURES,
            server.RESERVATION_LIMIT,
            server.REVIEW_LIMIT,
            server.LOOKUP_LIMIT,
        ):
            limiter._events.clear()
        for name in os.listdir(self.data_dir):
            path = os.path.join(self.data_dir, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    def request(self, method, path, body=None, headers=None, raw=None):
        """Devuelve (status, json_o_bytes)."""
        hdrs = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status, payload, ctype = resp.status, resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            status, payload, ctype = exc.code, exc.read(), exc.headers.get("Content-Type", "")
        if "json" in ctype and payload:
            return status, json.loads(payload)
        return status, payload

    def staff(self, method, path, body=None):
        return self.request(method, path, body=body, headers=STAFF_HEADERS)

    def reservation(self, **overrides):
        payload = {
            "name": "Ana Prueba",
            "phone": "518-555-0100",
            "email": "ana@example.com",
            "date": next_open_day(),
            "time": "18:00",
            "partySize": 2,
            "termsConsent": True,
        }
        payload.update(overrides)
        return payload

    def book(self, **overrides):
        return self.request("POST", "/api/reservations", body=self.reservation(**overrides))
