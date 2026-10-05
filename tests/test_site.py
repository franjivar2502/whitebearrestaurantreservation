"""Reseñas, galería de fotos, páginas estáticas y salud del servicio."""

import re
import tempfile
import time
import urllib.request
import urllib.error
import os
import unittest
import uuid
from unittest import mock

from helpers import ServerTestCase, server, storage


def multipart(fields, photo=None):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    if photo:
        filename, content_type, data = photo
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
            + data
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={boundary}"}


class ReviewTests(ServerTestCase):
    def post_review(self, photo=None, **fields):
        data = {
            "name": "Luis",
            "text": "Excelente trato y la comida riquísima",
            "rating": "5",
            "reviewConsent": "on",
        }
        data.update(fields)
        body, headers = multipart(data, photo)
        return self.request("POST", "/api/reviews", raw=body, headers=headers)

    def public_reviews(self):
        status, reviews = self.request("GET", "/api/reviews")
        self.assertEqual(status, 200)
        return reviews

    def test_positive_review_is_published(self):
        status, review = self.post_review()
        self.assertEqual(status, 201)
        self.assertEqual([r["id"] for r in self.public_reviews()], [review["id"]])

    def test_negative_review_is_not_published(self):
        # Hoy se rechaza; con la moderación de reseñas queda retenida. En
        # ambos casos no debe aparecer en el sitio público.
        status, _ = self.post_review(text="Comida terrible, nunca más")
        self.assertIn(status, (201, 202, 400))
        self.assertEqual(self.public_reviews(), [])

    def test_whole_word_matching(self):
        # "trato" contiene "rat" y "barata" contiene "rata": no deben bloquear.
        status, _ = self.post_review(text="Muy buen trato y comida barata")
        self.assertEqual(status, 201)

    def test_review_validation(self):
        self.assertEqual(self.post_review(name="")[0], 400)
        self.assertEqual(self.post_review(text="ok")[0], 400)
        self.assertEqual(self.post_review(rating="9")[0], 400)

    def test_review_photo_upload(self):
        status, review = self.post_review(photo=("plato.png", "image/png", b"\x89PNG\r\n\x1a\n fake"))
        self.assertEqual(status, 201)
        self.assertTrue(review["photoUrl"].endswith(".png"))

    def test_review_photo_must_be_image(self):
        status, _ = self.post_review(photo=("virus.exe", "application/octet-stream", b"MZ"))
        self.assertEqual(status, 400)

    def test_review_requires_consent(self):
        status, body = self.post_review(reviewConsent="")
        self.assertEqual(status, 400)
        self.assertIn({"code": "REVIEW_CONSENT_REQUIRED"}, body["errors"])

    def test_review_photo_gps_is_removed(self):
        jpeg = make_jpeg_with_gps()
        self.assertIn(b"LATITUDE", jpeg)
        status, review = self.post_review(photo=("plato.jpg", "image/jpeg", jpeg))
        self.assertEqual(status, 201)
        name = review["photoUrl"].rsplit("/", 1)[1]
        with open(os.path.join(storage.LOCAL_REVIEW_PHOTOS_DIR, name), "rb") as f:
            saved = f.read()
        self.assertNotIn(b"LATITUDE", saved)
        self.assertNotIn(b"<x:xmpmeta", saved)
        self.assertIn(b"ORIENT", saved)  # la orientación se conserva
        self.assertTrue(saved.endswith(b"\xff\xd9"))

    def test_review_requires_multipart(self):
        status, _ = self.request("POST", "/api/reviews", body={"name": "x"})
        self.assertEqual(status, 400)


def make_jpeg_with_gps():
    """JPEG mínimo con EXIF (orientación + GPS con datos fuera de línea) y XMP."""
    import struct

    e = "<"
    # IFD0 en 8: 2 entradas (Orientation, puntero GPS) + siguiente IFD.
    ifd0 = 8
    gps = ifd0 + 2 + 2 * 12 + 4
    gps_entries = 1
    lat_data = gps + 2 + gps_entries * 12 + 4
    tiff = bytearray(b"II*\x00" + struct.pack(e + "I", ifd0))
    tiff += struct.pack(e + "H", 2)
    tiff += struct.pack(e + "HHI", 0x0112, 3, 1) + struct.pack(e + "HH", 6, 0)
    tiff += struct.pack(e + "HHII", 0x8825, 4, 1, gps)
    tiff += struct.pack(e + "I", 0)
    tiff += struct.pack(e + "H", gps_entries)
    tiff += struct.pack(e + "HHII", 0x0002, 2, 8, lat_data)  # ASCII de 8 bytes
    tiff += struct.pack(e + "I", 0)
    tiff += b"LATITUDE"
    tiff += b"ORIENT"  # marcador para comprobar que el resto sigue ahí
    exif = b"Exif\x00\x00" + bytes(tiff)
    xmp = b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta>GPS</x:xmpmeta>"
    seg = lambda m, p: b"\xff" + bytes([m]) + struct.pack(">H", len(p) + 2) + p  # noqa: E731
    return b"\xff\xd8" + seg(0xE1, exif) + seg(0xE1, xmp) + b"\xff\xda\x00\x02imagen\xff\xd9"


class PhotoAdminTests(ServerTestCase):
    ADMIN = {"X-Admin-Password": "admin-de-prueba"}

    def test_admin_endpoints_require_password(self):
        body = {"url": "https://example.com/a.jpg"}
        self.assertEqual(self.request("POST", "/api/admin/photos", body=body)[0], 401)
        self.assertEqual(
            self.request("POST", "/api/admin/photos", body=body, headers={"X-Admin-Password": "mal"})[0], 401
        )
        self.assertEqual(self.request("POST", "/api/admin/login", body={"password": ""})[0], 401)
        self.assertEqual(self.request("POST", "/api/admin/login", body={"password": "admin-de-prueba"})[0], 200)

    def test_add_reorder_recategorize_delete(self):
        ids = []
        for n in range(3):
            # La primera simula una foto vieja de la «Galería general», que ya
            # no se muestra en el sitio; las demás van sin sección.
            body = {"url": f"https://example.com/{n}.jpg"}
            if n == 0:
                body["category"] = "gallery"
            status, photo = self.request("POST", "/api/admin/photos", body=body, headers=self.ADMIN)
            self.assertEqual(status, 201)
            # Sin sección, una foto nueva es del menú (la única sección visible).
            self.assertEqual(photo["category"], "gallery" if n == 0 else "menu")
            ids.append(photo["id"])

        new_order = list(reversed(ids))
        self.assertEqual(
            self.request("POST", "/api/admin/photos/reorder", body={"order": new_order}, headers=self.ADMIN)[0], 200
        )
        self.assertEqual([p["id"] for p in self.request("GET", "/api/photos")[1]], new_order)

        status, _ = self.request("PATCH", f"/api/admin/photos/{ids[0]}", body={"category": "menu"}, headers=self.ADMIN)
        self.assertEqual(status, 200)
        photos = {p["id"]: p for p in self.request("GET", "/api/photos")[1]}
        self.assertEqual(photos[ids[0]]["category"], "menu")

        self.assertEqual(self.request("DELETE", f"/api/admin/photos/{ids[0]}", headers=self.ADMIN)[0], 200)
        self.assertEqual(len(self.request("GET", "/api/photos")[1]), 2)

    def test_rejects_non_http_urls(self):
        status, _ = self.request(
            "POST", "/api/admin/photos", body={"url": "javascript:alert(1)"}, headers=self.ADMIN
        )
        self.assertEqual(status, 400)


class SiteTests(ServerTestCase):
    def test_public_pages_load(self):
        for path in ("/", "/tablet.html", "/confirm.html", "/admin-photos.html", "/robots.txt"):
            status, _ = self.request("GET", path)
            self.assertEqual(status, 200, path)

    def test_path_traversal_is_blocked(self):
        for path in ("/../server.py", "/..%2fserver.py", "/%2e%2e/storage.py"):
            self.assertEqual(self.request("GET", path)[0], 404, path)

    def test_restaurant_info(self):
        status, info = self.request("GET", "/api/restaurant")
        self.assertEqual(status, 200)
        self.assertEqual(info["name"], "White Bear Restaurant")

    def test_healthz(self):
        status, health = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertTrue(health["ok"])
        self.assertEqual(health["storage"], "local")
        self.assertEqual(self.request("HEAD", "/healthz")[0], 200)

    @mock.patch("builtins.print")
    def test_healthz_reports_storage_failure(self, _print):
        original = server.storage.ping

        def broken():
            raise OSError("disco roto")

        server.storage.ping = broken
        try:
            status, health = self.request("GET", "/healthz")
            self.assertEqual(status, 503)
            self.assertFalse(health["ok"])
            self.assertEqual(self.request("HEAD", "/healthz")[0], 503)
        finally:
            server.storage.ping = original


class StaticCacheTests(ServerTestCase):
    """Un navegador no debe poder mezclar una página nueva con un .js viejo."""

    def fetch(self, method, path, headers=None):
        req = urllib.request.Request(self.base + path, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def test_html_links_to_scripts_and_styles_carry_a_content_version(self):
        for page in ("/", "/tablet.html", "/confirm.html", "/admin-photos.html"):
            status, _, body = self.fetch("GET", page)
            self.assertEqual(status, 200, page)
            html = body.decode("utf-8")
            links = re.findall(r'(?:src|href)="(/?(?:js|css)/[^"]+)"', html)
            self.assertTrue(links, page)
            for link in links:
                self.assertRegex(link, r"^/?(?:js|css)/[\w.\-]+\.(?:js|css)\?v=[0-9a-f]{10}$", (page, link))

    def test_versioned_url_still_serves_the_file(self):
        _, _, html = self.fetch("GET", "/tablet.html")
        link = re.search(r'src="(js/tablet\.js\?v=[0-9a-f]{10})"', html.decode("utf-8")).group(1)
        status, headers, body = self.fetch("GET", "/" + link)
        self.assertEqual(status, 200)
        self.assertIn(b"fetchTables", body)

    def test_version_changes_when_the_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.js")
            with open(path, "w") as f:
                f.write("a")
            first = server._asset_version(path)
            self.assertEqual(first, server._asset_version(path))
            with open(path, "w") as f:
                f.write("b")
            os.utime(path, (time.time() + 5, time.time() + 5))  # aunque la fecha casi coincida
            self.assertNotEqual(first, server._asset_version(path))

    def test_scripts_and_styles_are_revalidated_with_etag(self):
        for path in ("/js/tablet.js", "/css/style.css"):
            status, headers, body = self.fetch("GET", path + "?v=viejo")
            self.assertEqual(status, 200, path)
            self.assertEqual(headers["Cache-Control"], "no-cache")
            etag = headers["ETag"]
            status, headers, body = self.fetch("GET", path, headers={"If-None-Match": etag})
            self.assertEqual((status, body), (304, b""), path)
            self.assertEqual(headers["ETag"], etag)
            # Con otra huella (el archivo cambió) se vuelve a enviar completo.
            status, _, body = self.fetch("GET", path, headers={"If-None-Match": '"otra"'})
            self.assertEqual(status, 200)
            self.assertTrue(body)

    def test_html_is_never_cached_and_head_reports_the_real_length(self):
        status, headers, body = self.fetch("GET", "/tablet.html")
        self.assertEqual(headers["Cache-Control"], "no-cache")
        status, headers, _ = self.fetch("HEAD", "/tablet.html")
        self.assertEqual(int(headers["Content-Length"]), len(body))


if __name__ == "__main__":
    unittest.main()
