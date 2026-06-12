import importlib
import sys
import types
import unittest
from datetime import datetime, timedelta


def load_storage_with_stubs():
    session_stub = types.ModuleType("studystreak.session")
    session_stub.is_logged_in = lambda: False
    session_stub.get_session_data = lambda: {}
    session_stub.save_session_data = lambda data: None
    session_stub.get_session_username = lambda: "test-user"
    session_stub.get_session_password = lambda: "test-password"
    session_stub.get_server_token = lambda: None

    profile_sync_stub = types.ModuleType("studystreak.profile_sync")
    profile_sync_stub.encrypt_profile_data = lambda data, username, password: "{}"

    api_client_stub = types.ModuleType("studystreak.api_client")
    api_client_stub.upload_profile_data = lambda token, encrypted_profile_data: None
    api_client_stub.upload_subject_websites = lambda token, subject_websites: None
    api_client_stub.upload_subjects = lambda token, subjects: None
    api_client_stub.upload_streak = lambda token, current_streak: None
    api_client_stub.upload_timetable = lambda token, timetable: None

    sys.modules["studystreak.session"] = session_stub
    sys.modules["studystreak.profile_sync"] = profile_sync_stub
    sys.modules["studystreak.api_client"] = api_client_stub

    sys.modules.pop("studystreak.storage", None)
    return importlib.import_module("studystreak.storage")


class StreakStorageTests(unittest.TestCase):
    def setUp(self):
        self.storage = load_storage_with_stubs()

    def make_chrome_session(self, completed_at):
        return {
            "subject": "computer science",
            "score": 100,
            "focused_seconds": 87,
            "distracted_seconds": 0,
            "idle_seconds": 0,
            "top_distracted_domain": "none",
            "completed_at": completed_at,
        }

    def test_protect_streak_today_is_idempotent(self):
        data = self.storage.get_default_data()

        self.assertTrue(self.storage.protect_streak_today(data))
        self.assertFalse(self.storage.protect_streak_today(data))
        self.assertEqual(data["streak_days"], [self.storage.get_today_text()])

    def test_repair_backfills_streak_from_non_chrome_sessions_only(self):
        today = self.storage.get_today_text()
        data = {
            "sessions": [
                {
                    "subject": "math",
                    "minutes": 10,
                    "date": today,
                    "source": "manual",
                },
                {
                    "subject": "science",
                    "minutes": 1,
                    "date": "2099-01-01",
                    "source": "manual",
                },
                {
                    "subject": "computer science",
                    "minutes": 1,
                    "date": today,
                    "source": "chrome_extension",
                    "completed_at": datetime.now().astimezone().isoformat(),
                },
            ]
        }

        repaired = self.storage.repair_data(data)

        self.assertEqual(repaired["streak_days"], [today])

    def test_chrome_sync_today_protects_today_once(self):
        data = self.storage.get_default_data()
        completed_at = datetime.now().astimezone().isoformat()

        first_count = self.storage.merge_focus_quality_sessions(
            data,
            [self.make_chrome_session(completed_at)],
        )
        second_count = self.storage.merge_focus_quality_sessions(
            data,
            [self.make_chrome_session(completed_at)],
        )

        self.assertGreater(first_count, 0)
        self.assertEqual(second_count, 0)
        self.assertEqual(data["streak_days"], [self.storage.get_today_text()])

    def test_chrome_sync_yesterday_does_not_protect_today(self):
        data = self.storage.get_default_data()
        completed_at = (datetime.now().astimezone() - timedelta(days=1)).isoformat()

        self.storage.merge_focus_quality_sessions(
            data,
            [self.make_chrome_session(completed_at)],
        )

        self.assertEqual(data["streak_days"], [])
        self.assertEqual(len(data["sessions"]), 1)

    def test_chrome_sync_then_manual_log_still_has_one_protected_day(self):
        data = self.storage.get_default_data()
        completed_at = datetime.now().astimezone().isoformat()

        self.storage.merge_focus_quality_sessions(
            data,
            [self.make_chrome_session(completed_at)],
        )

        manual_session = {
            "subject": "math",
            "minutes": 10,
            "date": self.storage.get_today_text(),
            "source": "manual",
        }
        data["sessions"].append(manual_session)
        self.storage.protect_streak_today(data)

        self.assertEqual(data["streak_days"], [self.storage.get_today_text()])


if __name__ == "__main__":
    unittest.main()
