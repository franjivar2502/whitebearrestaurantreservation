"""Mensajes: formato del teléfono para Twilio y envío de SMS."""

import os
import unittest
import unittest.mock
import urllib.parse

import notifications


class PhoneFormatTests(unittest.TestCase):
    def test_us_numbers_become_e164(self):
        for raw in ("(518) 302-5235", "518-302-5235", "518.302.5235", "5183025235", " 518 302 5235 ", "1-518-302-5235", "15183025235"):
            self.assertEqual(notifications.to_e164(raw), "+15183025235", raw)

    def test_international_numbers_are_respected(self):
        self.assertEqual(notifications.to_e164("+52 55 1234 5678"), "+525512345678")
        self.assertEqual(notifications.to_e164("+15183025235"), "+15183025235")

    def test_unusable_numbers_return_none(self):
        for raw in ("", None, "123", "518-302", "abcdefghij", "+12", "123456789012345678"):
            self.assertIsNone(notifications.to_e164(raw), raw)


class SendSmsTests(unittest.TestCase):
    ENV = {"TWILIO_ACCOUNT_SID": "ACtest", "TWILIO_AUTH_TOKEN": "tok", "TWILIO_FROM_NUMBER": "+15005550006"}

    def send(self, number):
        sent = {}

        def fake_urlopen(req, timeout=None):
            sent["to"] = urllib.parse.parse_qs(req.data.decode())["To"][0]
            return unittest.mock.MagicMock(__enter__=lambda s: s, __exit__=lambda *a: False, read=lambda: b"{}")

        with unittest.mock.patch.dict(os.environ, self.ENV), unittest.mock.patch.object(
            notifications.urllib.request, "urlopen", fake_urlopen
        ), unittest.mock.patch.object(notifications, "_log"):
            result = notifications.send_sms(number, "hola")
        return result, sent

    def test_twilio_receives_the_number_in_e164(self):
        result, sent = self.send("(518) 302-5235")
        self.assertEqual(result, (True, "enviado"))
        self.assertEqual(sent["to"], "+15183025235")

    def test_invalid_number_is_not_sent(self):
        result, sent = self.send("12345")
        self.assertFalse(result[0])
        self.assertEqual(sent, {})

    def test_without_credentials_it_stays_in_dry_run(self):
        with unittest.mock.patch.dict(os.environ, {}, clear=True), unittest.mock.patch.object(notifications, "_log"):
            self.assertEqual(notifications.send_sms("(518) 302-5235", "hola"), (False, "dry-run"))


RESERVATION = {
    "id": "a1b2c3d4e5f60718",
    "name": "Ana",
    "date": "2026-10-12",  # un lunes
    "time": "19:00",
    "partySize": 4,
    "phone": "5183025235",
    "email": "ana@example.com",
}


class MessageLanguageTests(unittest.TestCase):
    def res(self, **kw):
        return {**RESERVATION, **kw}

    def test_each_language_writes_its_own_message(self):
        expected = {"en": "we received your reservation", "es": "recibimos tu reserv", "fr": "nous avons bien re"}
        for lang, phrase in expected.items():
            self.assertIn(phrase, notifications.confirmation_message(self.res(lang=lang)), lang)

    def test_missing_or_unknown_language_falls_back_to_english(self):
        for lang in (None, "", "xx", "de", 5):
            reservation = self.res(**({} if lang is None else {"lang": lang}))
            self.assertEqual(notifications.message_language(reservation), "en", lang)
            self.assertIn("we received your reservation", notifications.confirmation_message(reservation))

    def test_sms_stays_in_the_basic_alphabet(self):
        for lang in ("en", "es", "fr"):
            reservation = self.res(lang=lang)
            for build in (
                lambda r, sms: notifications.confirmation_message(r, sms=sms),
                lambda r, sms: notifications.attendance_confirmation_message(r, "https://x.com", sms=sms),
                lambda r, sms: notifications.reminder_message(r, sms=sms),
            ):
                self.assertTrue(build(reservation, True).isascii(), (lang, build(reservation, True)))
            self.assertTrue(notifications.sms_opt_out_note(reservation).isascii(), lang)
        self.assertIn("reservación", notifications.confirmation_message(self.res(lang="es")))
        self.assertIn("réservation", notifications.confirmation_message(self.res(lang="fr")))

    def test_guest_name_is_kept_as_written_even_in_sms(self):
        message = notifications.confirmation_message(self.res(lang="es", name="José {x}"), sms=True)
        self.assertIn("José {x}", message)

    def test_dates_and_times_are_readable_in_each_language(self):
        self.assertEqual(notifications.date_text("en", "2026-10-12"), "Monday, Oct 12")
        self.assertEqual(notifications.date_text("es", "2026-10-12"), "lunes 12 de octubre")
        self.assertEqual(notifications.date_text("fr", "2026-10-12"), "lundi 12 octobre")
        self.assertEqual(notifications.date_text("en", "mañana"), "mañana")  # dato raro: no rompe
        self.assertEqual(notifications.time_text("en", "19:00"), "7:00 PM")
        self.assertEqual(notifications.time_text("en", "00:15"), "12:15 AM")
        self.assertEqual(notifications.time_text("en", "12:00"), "12:00 PM")
        self.assertEqual(notifications.time_text("es", "07:05"), "7:05 a.m.")
        self.assertEqual(notifications.time_text("fr", "19:00"), "19:00")

    def test_party_size_agrees_in_number(self):
        self.assertEqual(notifications.party_text("es", 1), "1 persona")
        self.assertEqual(notifications.party_text("es", 4), "4 personas")
        self.assertEqual(notifications.party_text("fr", 1), "1 personne")
        self.assertEqual(notifications.party_text("fr", 4), "4 personnes")
        self.assertEqual(notifications.party_text("en", 4), "party of 4")

    def test_attendance_link_carries_the_language(self):
        url = "https://x.com/confirm.html?id=a1b2c3d4e5f60718&lang=fr"
        self.assertIn(url, notifications.attendance_confirmation_message(self.res(lang="fr"), "https://x.com"))

    def test_notify_sends_only_sms_in_the_guests_language(self):
        sent = []
        with unittest.mock.patch.object(notifications, "send_sms", lambda to, body: sent.append(("sms", to, body))):
            reservation = self.res(lang="fr", email="a@b.com")
            notifications.notify_confirmation(reservation)
            notifications.notify_reminder(reservation)
            notifications.notify_attendance_confirmation(reservation, "https://x.com")
        sms = sent
        self.assertEqual(len(sms), 3)
        self.assertFalse(hasattr(notifications, "send_email"))
        # La baja (STOP) va solo en el primer SMS, y en el idioma del cliente.
        self.assertIn("Repondez STOP", sms[0][2])
        self.assertNotIn("STOP", sms[1][2])
        self.assertNotIn("STOP", sms[2][2])


if __name__ == "__main__":
    unittest.main()
