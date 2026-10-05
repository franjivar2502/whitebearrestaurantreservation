"""Ajustes del sitio desde el panel: cerrar el sitio público y reservas 24/7."""

import unittest
import uuid

from helpers import ServerTestCase, server

ADMIN = {"X-Admin-Password": "admin-de-prueba"}
STAFF = {"X-Staff-Password": "staff-de-prueba"}


class SiteSettingsTests(ServerTestCase):
    def settings(self):
        status, body = self.request("GET", "/api/site-settings")
        self.assertEqual(status, 200)
        return body

    def test_defaults(self):
        self.assertEqual(self.settings(), {"publicSiteOffline": False, "bookingAlwaysOpen": True})
        self.assertTrue(self.request("GET", "/api/restaurant")[1]["bookingAlwaysOpen"])

    def test_changing_requires_password(self):
        body = {"publicSiteOffline": True}
        self.assertEqual(self.request("PATCH", "/api/site-settings", body=body)[0], 401)
        self.assertEqual(
            self.request("PATCH", "/api/site-settings", body=body, headers={"X-Admin-Password": "mal"})[0], 401
        )
        self.assertFalse(self.settings()["publicSiteOffline"])

    def test_admin_or_staff_password_can_change(self):
        for headers in (ADMIN, STAFF, {"X-Staff-Password": "admin-de-prueba"}):
            status, body = self.request(
                "PATCH", "/api/site-settings", body={"bookingAlwaysOpen": False}, headers=headers
            )
            self.assertEqual(status, 200, headers)
            self.assertFalse(body["bookingAlwaysOpen"])
            self.request("PATCH", "/api/site-settings", body={"bookingAlwaysOpen": True}, headers=headers)

    def test_rejects_unknown_or_non_boolean_values(self):
        for body in ({"publicSiteOffline": "si"}, {"otraCosa": True}, {}):
            self.assertEqual(self.request("PATCH", "/api/site-settings", body=body, headers=ADMIN)[0], 400, body)

    def test_settings_survive_a_restart(self):
        self.request("PATCH", "/api/site-settings", body={"publicSiteOffline": True}, headers=ADMIN)
        server._site_settings_cache.update(value=None, at=0.0)  # como un proceso nuevo
        self.assertTrue(self.settings()["publicSiteOffline"])

    def test_settings_row_is_not_a_table(self):
        self.request("PATCH", "/api/site-settings", body={"publicSiteOffline": True}, headers=ADMIN)
        self.assertEqual(server.storage.list_unavailable_table_ids(), set())
        self.assertEqual(server._available_seats("2030-01-01", "18:00"), server.TOTAL_SEATS)


class OfflineSiteTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        status, _ = self.request("PATCH", "/api/site-settings", body={"publicSiteOffline": True}, headers=ADMIN)
        self.assertEqual(status, 200)

    def test_home_page_shows_maintenance(self):
        for path in ("/", "/index.html"):
            status, body = self.request("GET", path)
            self.assertEqual(status, 503, path)
            self.assertIn(b"(518) 302-5235", body)
        self.assertEqual(self.request("HEAD", "/")[0], 503)

    def test_public_bookings_and_reviews_are_blocked(self):
        status, body = self.book()
        self.assertEqual(status, 503)
        self.assertEqual(body["errors"][0]["code"], "SITE_OFFLINE")

        boundary = uuid.uuid4().hex
        raw = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\nLuis\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="text"\r\n\r\nMuy rico todo\r\n'
            f"--{boundary}--\r\n"
        ).encode()
        status, _ = self.request(
            "POST", "/api/reviews", raw=raw, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        self.assertEqual(status, 503)

    def test_staff_keeps_working(self):
        self.assertEqual(self.request("GET", "/tablet.html")[0], 200)
        self.assertEqual(self.request("GET", "/healthz")[0], 200)
        status, created = self.request("POST", "/api/reservations", body=self.reservation(), headers=ADMIN)
        self.assertEqual(status, 201)
        # El cliente con una reserva ya hecha puede seguir confirmándola.
        self.assertEqual(self.request("GET", "/confirm.html")[0], 200)
        status, _ = self.request(
            "POST", f"/api/reservations/{created['id']}/confirm-attendance", body={"confirmed": True}
        )
        self.assertEqual(status, 200)

    def test_reopening_restores_the_site(self):
        self.request("PATCH", "/api/site-settings", body={"publicSiteOffline": False}, headers=ADMIN)
        self.assertEqual(self.request("GET", "/")[0], 200)
        self.assertEqual(self.book()[0], 201)


if __name__ == "__main__":
    unittest.main()
