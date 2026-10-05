"""Almacenamiento y tareas de mantenimiento, sin servidor HTTP."""

import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta
from unittest import mock

from helpers import point_storage_at, server, storage


class LocalStorageTests(unittest.TestCase):
    def setUp(self):
        self.data_dir = tempfile.mkdtemp(prefix="whitebear-storage-")
        point_storage_at(self.data_dir)

    def tearDown(self):
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def test_write_is_atomic_and_leaves_no_temp_files(self):
        storage.save_reservation({"id": "a1", "date": "2030-01-01"})
        storage.save_reservation({"id": "a2", "date": "2030-01-02"})
        storage.save_reservation({"id": "a1", "date": "2030-01-03"})  # upsert
        self.assertEqual(
            sorted((r["id"], r["date"]) for r in storage.list_reservations()),
            [("a1", "2030-01-03"), ("a2", "2030-01-02")],
        )
        self.assertEqual(sorted(os.listdir(self.data_dir)), ["reservations.json"])

    def test_failed_write_keeps_previous_file(self):
        storage.save_reservation({"id": "a1", "date": "2030-01-01"})
        with mock.patch("json.dump", side_effect=OSError("disco lleno")):
            with self.assertRaises(OSError):
                storage.save_reservation({"id": "a2", "date": "2030-01-02"})
        self.assertEqual([r["id"] for r in storage.list_reservations()], ["a1"])
        self.assertEqual(os.listdir(self.data_dir), ["reservations.json"])

    def test_corrupt_file_is_set_aside_not_overwritten(self):
        with open(storage.LOCAL_DATA_FILE, "w") as f:
            f.write('[{"id": "a1", "da')
        with mock.patch("builtins.print"):
            self.assertEqual(storage.list_reservations(), [])
        aside = [n for n in os.listdir(self.data_dir) if ".corrupt-" in n]
        self.assertEqual(len(aside), 1)
        with open(os.path.join(self.data_dir, aside[0])) as f:
            self.assertIn('"a1"', f.read())

    def test_list_reservations_by_date(self):
        storage.save_reservation({"id": "a1", "date": "2030-01-01"})
        storage.save_reservation({"id": "a2", "date": "2030-01-02"})
        self.assertEqual([r["id"] for r in storage.list_reservations(on_date="2030-01-02")], ["a2"])

    def test_purge_reservations_before(self):
        for i, d in enumerate(("2020-01-01", "2029-12-31", "2030-01-01", "2030-06-01")):
            storage.save_reservation({"id": f"r{i}", "date": d})
        self.assertEqual(storage.purge_reservations_before("2030-01-01"), 2)
        self.assertEqual(sorted(r["date"] for r in storage.list_reservations()), ["2030-01-01", "2030-06-01"])

    def test_backup_and_restore_roundtrip(self):
        storage.save_reservation({"id": "r1", "date": "2030-01-01", "name": "Ana"})
        storage.set_table_unavailable("rect6-1", True)
        storage.save_review({"id": "v1", "text": "Muy rico", "status": "approved"})
        storage.add_photo({"id": "p1", "url": "https://x/1.jpg", "caption": "", "sort_order": 0})
        backup = json.loads(json.dumps(storage.export_all()))  # como si pasara por un archivo

        shutil.rmtree(self.data_dir)
        os.makedirs(self.data_dir)
        self.assertEqual(storage.list_reservations(), [])

        counts = storage.import_all(backup)
        self.assertEqual(counts, {"reservations": 1, "table_status": 1, "reviews": 1, "photos": 1})
        self.assertEqual(storage.list_reservations()[0]["name"], "Ana")
        self.assertEqual(storage.list_unavailable_table_ids(), {"rect6-1"})
        self.assertEqual(storage.list_reviews()[0]["id"], "v1")
        self.assertEqual(storage.list_photos()[0]["url"], "https://x/1.jpg")

    def test_restore_rejects_other_files(self):
        with self.assertRaises(ValueError):
            storage.import_all({"tables": {}})


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class SupabaseClientTests(unittest.TestCase):
    """La ruta de Supabase, con la red simulada."""

    def setUp(self):
        self.patches = [
            mock.patch.object(storage, "SUPABASE_URL", "https://demo.supabase.co"),
            mock.patch.object(storage, "SUPABASE_KEY", "clave"),
            mock.patch.object(storage, "_RETRY_DELAYS", (0, 0)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_pagination_reads_past_1000_rows(self):
        rows = [{"data": {"id": str(i), "date": "2030-01-01"}} for i in range(2500)]
        urls = []

        def fake_urlopen(req, timeout):
            urls.append(req.full_url)
            offset = int(req.full_url.split("offset=")[1])
            limit = int(req.full_url.split("limit=")[1].split("&")[0])
            return FakeResponse(json.dumps(rows[offset : offset + limit]).encode())

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            result = storage.list_reservations()
        self.assertEqual(len(result), 2500)
        self.assertEqual(len(urls), 3)

    def test_date_filter_goes_to_supabase(self):
        seen = []

        def fake_urlopen(req, timeout):
            seen.append(req.full_url)
            return FakeResponse(b"[]")

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            storage.list_reservations(on_date="2030-01-02")
        self.assertIn("data-%3E%3Edate=eq.2030-01-02", seen[0])

    def test_transient_errors_are_retried(self):
        calls = []

        def flaky(req, timeout):
            calls.append(1)
            if len(calls) < 3:
                raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, None)
            return FakeResponse(b"[]")

        with mock.patch("urllib.request.urlopen", flaky):
            self.assertEqual(storage.list_reservations(), [])
        self.assertEqual(len(calls), 3)

    def test_client_errors_are_not_retried(self):
        calls = []

        def bad(req, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, None)

        with mock.patch("urllib.request.urlopen", bad):
            with self.assertRaises(urllib.error.HTTPError):
                storage.save_reservation({"id": "x"})
        self.assertEqual(len(calls), 1)

    def test_plain_insert_is_not_retried(self):
        calls = []

        def down(req, timeout):
            calls.append(1)
            raise urllib.error.URLError("sin red")

        with mock.patch("urllib.request.urlopen", down):
            with self.assertRaises(urllib.error.URLError):
                storage.add_photo({"id": "p", "url": "https://x"})
        self.assertEqual(len(calls), 1)

    def test_restore_upserts_in_batches(self):
        sent = []

        def fake_urlopen(req, timeout):
            sent.append((req.full_url, req.get_header("Prefer"), json.loads(req.data)))
            return FakeResponse(b"")

        backup = {
            "format": "whitebear-backup",
            "tables": {
                "reservations": [{"id": str(i), "data": {"id": str(i)}} for i in range(1200)],
                "photos": [{"id": "p1", "url": "u", "category": "menu"}, {"id": "p2", "url": "v"}],
            },
        }
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            counts = storage.import_all(backup)
        self.assertEqual(counts["reservations"], 1200)
        self.assertEqual([len(body) for _, _, body in sent], [500, 500, 200, 2])
        self.assertTrue(all("merge-duplicates" in prefer for _, prefer, _ in sent))
        self.assertIn("photos?columns=category,id,url", sent[-1][0])


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.data_dir = tempfile.mkdtemp(prefix="whitebear-maint-")
        point_storage_at(self.data_dir)
        self.quiet = mock.patch("builtins.print")
        self.quiet.start()

    def tearDown(self):
        self.quiet.stop()
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def test_clock_uses_restaurant_timezone(self):
        from zoneinfo import ZoneInfo

        expected = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
        self.assertLess(abs((server._now() - expected).total_seconds()), 5)

    def test_purge_is_off_by_default(self):
        storage.save_reservation({"id": "old", "date": "2000-01-01"})
        with mock.patch.object(server, "RESERVATION_RETENTION_DAYS", ""):
            self.assertEqual(server._purge_old_reservations(), 0)
        self.assertEqual(len(storage.list_reservations()), 1)

    def test_purge_with_retention(self):
        today = server._today()
        storage.save_reservation({"id": "old", "date": (today - timedelta(days=400)).isoformat()})
        storage.save_reservation({"id": "recent", "date": (today - timedelta(days=10)).isoformat()})
        with mock.patch.object(server, "RESERVATION_RETENTION_DAYS", "365"):
            self.assertEqual(server._purge_old_reservations(), 1)
        self.assertEqual([r["id"] for r in storage.list_reservations()], ["recent"])

    def test_purge_refuses_tiny_retention(self):
        with mock.patch.object(server, "RESERVATION_RETENTION_DAYS", "3"):
            with self.assertRaises(ValueError):
                server._purge_old_reservations()

    def _reservation(self, minutes_from_now, created_days_ago=2):
        now = server._now()
        when = now + timedelta(minutes=minutes_from_now)
        return {
            "id": f"r{minutes_from_now}",
            "status": "pending",
            "date": when.strftime("%Y-%m-%d"),
            "time": when.strftime("%H:%M"),
            "createdAt": (now - timedelta(days=created_days_ago)).isoformat(timespec="seconds"),
            "reminderSent": False,
            "attendanceReminderSent": False,
            "name": "Ana",
            "phone": "5185550100",
            "partySize": 2,
        }

    def test_reminders_are_sent_once_at_the_right_time(self):
        storage.save_reservation(self._reservation(10))  # dentro de 15 min
        storage.save_reservation(self._reservation(120))  # todavía no
        with mock.patch.object(server.notifications, "notify_reminder") as notify:
            server._check_and_send_reminders()
            server._check_and_send_reminders()
        self.assertEqual([c.args[0]["id"] for c in notify.call_args_list], ["r10"])

    def test_attendance_confirmation_24h_before(self):
        storage.save_reservation(self._reservation(23 * 60))
        storage.save_reservation(self._reservation(3 * 24 * 60))
        with mock.patch.object(server.notifications, "notify_attendance_confirmation") as notify:
            server._check_and_send_attendance_confirmations()
            server._check_and_send_attendance_confirmations()
        self.assertEqual([c.args[0]["id"] for c in notify.call_args_list], [f"r{23 * 60}"])


if __name__ == "__main__":
    unittest.main()
