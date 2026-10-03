"""
Defensas del servidor contra abuso desde internet, sin dependencias externas.

Aquí vive lo que no es lógica del restaurante sino protección del sitio:

- Límite de intentos por IP (fuerza bruta contra la contraseña de staff,
  spam de reservaciones y reseñas, barrido de códigos de reservación).
- La IP real del cliente detrás del proxy de Render.
- Reconocer una imagen por su contenido y no por lo que dice el navegador.
- Las cabeceras de seguridad que acompañan a cada respuesta.
"""

import threading
import time
from collections import deque


class RateLimiter:
    """
    Ventana deslizante en memoria: como mucho `limit` eventos por `window`
    segundos para cada llave (normalmente la IP). Vive en memoria a propósito:
    si el servidor se reinicia los contadores vuelven a cero, que es un precio
    aceptable a cambio de no depender de Redis ni de la base.
    """

    # Tope de llaves distintas que se recuerdan. Sin techo, un ataque con
    # miles de IPs falsas llenaría la memoria del plan gratis de Render.
    MAX_KEYS = 20000

    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self._events = {}
        self._lock = threading.Lock()

    def _prune(self, key, now):
        events = self._events.get(key)
        if events is None:
            return None
        while events and events[0] <= now - self.window:
            events.popleft()
        if not events:
            del self._events[key]
            return None
        return events

    def blocked(self, key):
        """True si la llave ya agotó su cupo (sin registrar un evento nuevo)."""
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, now)
            return events is not None and len(events) >= self.limit

    def hit(self, key):
        """Registra un evento. Devuelve True si todavía estaba dentro del cupo."""
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, now)
            if events is None:
                if len(self._events) >= self.MAX_KEYS:
                    self._sweep(now)
                events = self._events.setdefault(key, deque())
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True

    def reset(self, key):
        with self._lock:
            self._events.pop(key, None)

    def _sweep(self, now):
        for key in list(self._events):
            self._prune(key, now)
        # Si aun así está lleno, se suelta lo más viejo antes que crecer sin fin.
        while len(self._events) >= self.MAX_KEYS:
            self._events.pop(next(iter(self._events)))


def client_ip(headers, socket_address):
    """
    IP del visitante. En Render la conexión llega desde su proxy (Cloudflare
    delante), así que la dirección del socket es la del proxy y no sirve para
    distinguir visitantes. Se prefieren las cabeceras que pone Cloudflare, que
    sobrescribe cualquier valor que mande el cliente; X-Forwarded-For queda
    como respaldo. En local no hay proxy y se usa la del socket.
    """
    for name in ("True-Client-IP", "CF-Connecting-IP"):
        value = (headers.get(name) or "").strip()
        if value:
            return value[:64]
    forwarded = (headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    return socket_address


# Firmas de los formatos de imagen que acepta el sitio. Se mira el contenido
# porque el tipo y la extensión los decide quien sube el archivo: un HTML o un
# SVG con script renombrado a foto.jpg pasaría si solo se mirara eso.
def sniff_image(data):
    """Devuelve (extensión, content_type) si los bytes son una imagen aceptada,
    o None si no lo son."""
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None


# Política de contenido: el sitio solo ejecuta sus propios scripts. Las fotos
# de la galería pueden venir de cualquier https (las pega el staff como URL) y
# las reseñas de Supabase Storage; las fuentes vienen de Google Fonts. Los
# atributos style="" en el HTML obligan a permitir estilos en línea, que es un
# riesgo mucho menor que permitir scripts en línea.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: https:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    # Que el navegador no "adivine" un tipo distinto al que mandamos (p. ej.
    # ejecutar como script algo servido como imagen).
    "X-Content-Type-Options": "nosniff",
    # Nadie puede meter el sitio en un iframe (clickjacking sobre el panel).
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

# Solo tiene sentido sobre https; el servidor la agrega cuando el proxy avisa
# que la petición llegó cifrada (X-Forwarded-Proto: https).
HSTS_HEADER = ("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
