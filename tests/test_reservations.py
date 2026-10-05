"""Reservaciones: validación, disponibilidad, sobrecupo y cambios de estado."""

import threading
import unittest
from datetime import timedelta

from helpers import STAFF_HEADERS, ServerTestCase, next_open_day, server


class CreateReservationTests(ServerTestCase):
    def test_valid_reservation_is_saved_and_listed(self):
        status, created = self.book()
        self.assertEqual(status, 201)
        self.assertEqual(created["status"], "pending")
        self.assertEqual(created["partySize"], 2)

        status, listed = self.staff("GET", "/api/reservations")
        self.assertEqual(status, 200)
        self.assertEqual([r["id"] for r in listed], [created["id"]])

        status, single = self.request("GET", f"/api/reservations/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(single["name"], "Ana Prueba")

    def test_date_filter(self):
        self.book(date=next_open_day(3))
        self.book(date=next_open_day(4))
        status, listed = self.staff("GET", f"/api/reservations?date={next_open_day(4)}")
        self.assertEqual(status, 200)
        self.assertEqual([r["date"] for r in listed], [next_open_day(4)])

    def assertRejected(self, code, **overrides):
        status, body = self.book(**overrides)
        self.assertEqual(status, 400, body)
        self.assertIn(code, [e["code"] for e in body["errors"]])

    def test_validation_errors(self):
        self.assertRejected("NAME_REQUIRED", name="")
        self.assertRejected("NAME_REQUIRED", name="x" * 500)
        self.assertRejected("PHONE_INVALID", phone="123")
        self.assertRejected("EMAIL_INVALID", email="no-es-correo")
        self.assertRejected("DATE_INVALID", date="mañana")
        self.assertRejected("DATE_PAST", date=(server._today() - timedelta(days=1)).isoformat())
        self.assertRejected(
            "DATE_TOO_FAR",
            date=(server._today() + timedelta(days=server.MAX_BOOKING_DAYS_AHEAD + 1)).isoformat(),
        )
        self.assertRejected("TIME_INVALID", time="7pm")
        self.assertRejected("PARTY_SIZE_OUT_OF_RANGE", partySize=0)
        self.assertRejected("PARTY_SIZE_OUT_OF_RANGE", partySize=server.RESTAURANT["maxPartySize"] + 1)
        self.assertRejected("PARTY_SIZE_INVALID", partySize="muchos")
        self.assertRejected("NOTES_TOO_LONG", notes="x" * (server.MAX_NOTES_LENGTH + 1))

    def test_any_time_is_accepted_24_7(self):
        for t in ("00:00", "03:30", "08:00", "23:45"):
            self.assertEqual(self.book(time=t)[0], 201, t)

    def test_time_already_passed_today_is_rejected(self):
        now = server._now()
        if now.hour < 1:
            self.skipTest("Cerca de medianoche no hay una hora de hoy una hora atrás.")
        past = (now - server.timedelta(minutes=60)).strftime("%H:%M")
        self.assertRejected("TIME_PAST", date=now.date().isoformat(), time=past)
        # Unos minutos atrás sí se admite: alguien que acaba de sentarse.
        recent = (now - server.timedelta(minutes=5)).strftime("%H:%M")
        if recent < now.strftime("%H:%M"):
            self.assertEqual(self.book(date=now.date().isoformat(), time=recent)[0], 201)

    def test_invalid_json_is_rejected(self):
        status, _ = self.request(
            "POST", "/api/reservations", raw=b"{no es json", headers={"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)

    def test_legacy_preorder_fields_are_ignored(self):
        # El pre-pedido para grupos grandes ya no existe. Un navegador con la
        # página vieja en caché puede seguir mandando esos campos: la reserva
        # se acepta y simplemente no se guardan.
        status, created = self.book(
            partySize=20,
            preOrder=[{"itemId": "item-1", "quantity": 5}],
            preOrderNotes="sin gluten",
        )
        self.assertEqual(status, 201)
        self.assertNotIn("preOrder", created)
        self.assertNotIn("preOrderNotes", created)


class ConsentTests(ServerTestCase):
    def test_web_booking_requires_consent(self):
        status, body = self.book(termsConsent=False)
        self.assertEqual(status, 400)
        self.assertIn({"code": "CONSENT_REQUIRED"}, body["errors"])

    def test_consent_is_stored_with_the_reservation(self):
        status, created = self.book()
        self.assertEqual(status, 201)
        self.assertEqual(created["consent"]["source"], "web")
        self.assertEqual(created["consent"]["version"], server.LEGAL_TERMS_VERSION)
        self.assertTrue(created["consent"]["sms"])

    def test_staff_phone_booking_needs_no_checkbox(self):
        body = self.reservation(termsConsent=False)
        status, created = self.request("POST", "/api/reservations", body=body, headers=STAFF_HEADERS)
        self.assertEqual(status, 201)
        self.assertEqual(created["consent"], {"source": "staff"})


class AvailabilityTests(ServerTestCase):
    def test_full_slot_is_rejected(self):
        status, _ = self.book(partySize=server.RESTAURANT["maxPartySize"])
        self.assertEqual(status, 201)
        remaining = server.TOTAL_SEATS - server.RESTAURANT["maxPartySize"]
        while remaining > 0:
            size = min(remaining, server.RESTAURANT["maxPartySize"])
            self.assertEqual(self.book(partySize=size)[0], 201)
            remaining -= size
        status, body = self.book(partySize=1)
        self.assertEqual(status, 400)
        self.assertEqual(body["errors"][0]["code"], "NO_AVAILABILITY")

        # Fuera de la ventana de 90 minutos sí hay sitio.
        self.assertEqual(self.book(partySize=4, time="20:00")[0], 201)
        # Y otro día también.
        self.assertEqual(self.book(partySize=4, date=next_open_day(5))[0], 201)

    def test_concurrent_bookings_never_exceed_capacity(self):
        """Muchas reservas a la vez para el mismo horario: ninguna de más."""
        party = 10
        attempts = server.TOTAL_SEATS // party + 8
        results = []

        # Desde la tablet del staff, que no tiene tope por conexión: el tope
        # anti-spam del público cortaría antes de llegar al aforo.
        def attempt():
            body = self.reservation(partySize=party)
            results.append(self.request("POST", "/api/reservations", body=body, headers=STAFF_HEADERS)[0])

        threads = [threading.Thread(target=attempt) for _ in range(attempts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        accepted = results.count(201)
        self.assertEqual(accepted, server.TOTAL_SEATS // party)
        self.assertLessEqual(accepted * party, server.TOTAL_SEATS)
        self.assertEqual(results.count(400), attempts - accepted)

    def test_unavailable_table_reduces_capacity(self):
        table = max(server.TABLES, key=lambda t: t["seats"])
        status, _ = self.staff("PATCH", f"/api/tables/{table['id']}", {"unavailable": True})
        self.assertEqual(status, 200)
        self.assertEqual(
            server._available_seats(next_open_day(), "18:00"), server.TOTAL_SEATS - table["seats"]
        )
        status, tables = self.staff("GET", "/api/tables")
        self.assertEqual(tables["availableSeats"], server.TOTAL_SEATS - table["seats"])

    def test_cancelled_reservation_frees_seats(self):
        _, created = self.book(partySize=30)
        before = server._available_seats(created["date"], created["time"])
        status, _ = self.request(
            "POST", f"/api/reservations/{created['id']}/confirm-attendance", body={"confirmed": False}
        )
        self.assertEqual(status, 200)
        self.assertEqual(server._available_seats(created["date"], created["time"]), before + 30)


class StatusTests(ServerTestCase):
    def test_staff_can_move_reservation_through_states(self):
        _, created = self.book()
        for new_status in ("confirmed", "seated", "completed"):
            status, updated = self.staff("PATCH", f"/api/reservations/{created['id']}", {"status": new_status})
            self.assertEqual(status, 200)
            self.assertEqual(updated["status"], new_status)

    def test_invalid_status_is_rejected(self):
        _, created = self.book()
        status, _ = self.staff("PATCH", f"/api/reservations/{created['id']}", {"status": "borrado"})
        self.assertEqual(status, 400)

    def test_unknown_reservation_is_404(self):
        self.assertEqual(self.staff("PATCH", "/api/reservations/abc123", {"status": "confirmed"})[0], 404)
        self.assertEqual(self.request("GET", "/api/reservations/abc123")[0], 404)
        self.assertEqual(self.staff("DELETE", "/api/reservations/abc123")[0], 404)

    def test_delete_reservation(self):
        _, created = self.book()
        self.assertEqual(self.staff("DELETE", f"/api/reservations/{created['id']}")[0], 200)
        self.assertEqual(self.request("GET", f"/api/reservations/{created['id']}")[0], 404)

    def test_attendance_confirmation(self):
        _, created = self.book()
        status, updated = self.request(
            "POST", f"/api/reservations/{created['id']}/confirm-attendance", body={"confirmed": True}
        )
        self.assertEqual(status, 200)
        self.assertTrue(updated["attendanceConfirmed"])
        self.assertEqual(updated["status"], "pending")

        status, _ = self.request(
            "POST", f"/api/reservations/{created['id']}/confirm-attendance", body={"confirmed": "sí"}
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
