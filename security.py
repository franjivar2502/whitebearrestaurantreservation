"""
Defensas del servidor contra abuso desde internet, sin dependencias externas.

Aquí vive lo que no es lógica del restaurante sino protección del sitio:

- Límite de intentos por IP (fuerza bruta contra la contraseña de staff,
  spam de reservaciones y reseñas, barrido de códigos de reservación).
- La IP real del cliente detrás del proxy de Render.
- Reconocer una imagen por su contenido y no por lo que dice el navegador,
  y quitarle la ubicación GPS antes de publicarla.
- Las cabeceras de seguridad que acompañan a cada respuesta.
"""

import struct
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


# ---------------------------------------------------------------------------
# Metadatos de las fotos de reseñas. Un celular guarda en la foto el GPS de
# donde se tomó; publicada tal cual, cualquiera puede ver dónde vive quien
# dejó la reseña. Se quitan sin librerías externas:
#
# - JPEG: se borran los datos GPS dentro del EXIF (el resto del EXIF se
#   conserva, sobre todo la orientación: sin ella, las fotos verticales del
#   iPhone saldrían de lado) y se quita entero el bloque XMP, que también
#   puede repetir la ubicación.
# - PNG y WebP: se quitan enteros los bloques EXIF y XMP / de texto.
# - GIF no guarda ubicación.
#
# Si el archivo trae una estructura rara, se devuelve sin tocar lo que no se
# entiende pero nunca se deja pasar un bloque de GPS que sí se reconoció.
# ---------------------------------------------------------------------------

_TIFF_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8, 11: 4, 12: 8}
_GPS_IFD_TAG = 0x8825


def strip_metadata(data, ext):
    """Devuelve los bytes de la imagen sin ubicación. ext es el de sniff_image."""
    try:
        if ext == ".jpg":
            return _strip_jpeg(data)
        if ext == ".png":
            return _strip_png(data)
        if ext == ".webp":
            return _strip_webp(data)
    except (struct.error, IndexError, ValueError):
        # Archivo malformado: mejor rechazarlo que publicarlo con el GPS.
        raise ValueError("No se pudo limpiar la foto")
    return data


def _strip_jpeg(data):
    out = bytearray(data[:2])
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            raise ValueError("JPEG malformado")
        marker = data[i + 1]
        if marker == 0xFF:  # relleno entre segmentos
            i += 1
            continue
        if marker == 0xDA or 0xD0 <= marker <= 0xD9:
            # Empieza la imagen en sí: lo demás se copia tal cual.
            out += data[i:]
            return bytes(out)
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        segment = data[i : i + 2 + length]
        if len(segment) < 2 + length:
            raise ValueError("JPEG truncado")
        payload = segment[4:]
        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            out += segment[:4] + b"Exif\x00\x00" + _clear_gps(bytearray(payload[6:]))
        elif marker == 0xE1 or marker == 0xED:
            pass  # XMP (APP1 no EXIF) o IPTC de Photoshop (APP13): fuera
        else:
            out += segment
        i += 2 + length
    out += data[i:]
    return bytes(out)


def _clear_gps(tiff):
    """Vacía el directorio GPS de un bloque TIFF/EXIF, sin mover nada más
    (así las demás posiciones del EXIF siguen siendo válidas)."""
    if tiff[:2] == b"II":
        e = "<"
    elif tiff[:2] == b"MM":
        e = ">"
    else:
        raise ValueError("EXIF sin cabecera TIFF")
    ifd0 = struct.unpack(e + "I", tiff[4:8])[0]
    count = struct.unpack(e + "H", tiff[ifd0 : ifd0 + 2])[0]
    for n in range(count):
        entry = ifd0 + 2 + n * 12
        tag = struct.unpack(e + "H", tiff[entry : entry + 2])[0]
        if tag != _GPS_IFD_TAG:
            continue
        gps = struct.unpack(e + "I", tiff[entry + 8 : entry + 12])[0]
        gps_count = struct.unpack(e + "H", tiff[gps : gps + 2])[0]
        for k in range(gps_count):
            g = gps + 2 + k * 12
            typ, cnt = struct.unpack(e + "HI", tiff[g + 2 : g + 8])
            size = _TIFF_TYPE_SIZES.get(typ, 1) * cnt
            if size > 4:
                off = struct.unpack(e + "I", tiff[g + 8 : g + 12])[0]
                tiff[off : off + size] = bytes(len(tiff[off : off + size]))
            tiff[g : g + 12] = bytes(12)
        tiff[gps : gps + 2] = b"\x00\x00"
    return bytes(tiff)


def _strip_png(data):
    out = bytearray(data[:8])
    i = 8
    while i + 8 <= len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        kind = data[i + 4 : i + 8]
        end = i + 12 + length
        if end > len(data):
            raise ValueError("PNG truncado")
        if kind not in (b"eXIf", b"tEXt", b"iTXt", b"zTXt"):
            out += data[i:end]
        i = end
        if kind == b"IEND":
            break
    return bytes(out)


def _strip_webp(data):
    body = bytearray()
    i = 12
    while i + 8 <= len(data):
        kind = data[i : i + 4]
        length = struct.unpack("<I", data[i + 4 : i + 8])[0]
        end = i + 8 + length + (length & 1)
        if i + 8 + length > len(data):
            raise ValueError("WebP truncado")
        chunk = bytearray(data[i:end])
        if kind == b"VP8X":
            chunk[8] &= ~0x0C & 0xFF  # ya no hay EXIF (0x08) ni XMP (0x04)
        if kind not in (b"EXIF", b"XMP "):
            body += chunk
        i = end
    return b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP" + bytes(body)


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
