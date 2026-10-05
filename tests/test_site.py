"""Reseñas, galería de fotos, páginas estáticas y salud del servicio."""

import unittest
import uuid
from unittest import mock

from helpers import ServerTestCase, server


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
        data = {"name": "Luis", "text": "Excelente trato y la comida riquísima", "rating": "5"}
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

    def test_review_requires_multipart(self):
        status, _ = self.request("POST", "/api/reviews", body={"name": "x"})
        self.assertEqual(status, 400)


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
            status, photo = self.request(
                "POST", "/api/admin/photos", body={"url": f"https://example.com/{n}.jpg"}, headers=self.ADMIN
            )
            self.assertEqual(status, 201)
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


if __name__ == "__main__":
    unittest.main()
