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


if __name__ == "__main__":
    unittest.main()
