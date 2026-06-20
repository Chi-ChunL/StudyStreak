import importlib
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta


def load_storage_with_stubs(data_dir):
    os.environ["STUDYSTREAK_DATA_DIR"] = data_dir

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
    api_client_stub.upload_subject_topics = lambda token, subject_topics: None
    api_client_stub.upload_subjects = lambda token, subjects: None
    api_client_stub.upload_streak = lambda token, current_streak: None
    api_client_stub.upload_timetable = lambda token, timetable: None
    api_client_stub.upload_todo_items = lambda token, todo_items: None

    sys.modules["studystreak.session"] = session_stub
    sys.modules["studystreak.profile_sync"] = profile_sync_stub
    sys.modules["studystreak.api_client"] = api_client_stub

    sys.modules.pop("studystreak.paths", None)
    sys.modules.pop("studystreak.storage", None)
    return importlib.import_module("studystreak.storage")


class StreakStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(os.environ.pop, "STUDYSTREAK_DATA_DIR", None)
        self.storage = load_storage_with_stubs(self.temp_dir.name)

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

    def make_signed_focus_summary(self, completed_at, secret="test-secret"):
        payload = {
            **self.make_chrome_session(completed_at),
            "source": "chrome_extension",
        }

        return {
            "payload": payload,
            "signature": self.storage.sign_focus_summary(payload, secret),
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

    def test_manual_import_skips_session_already_synced_from_server(self):
        completed_at = datetime.now().astimezone().isoformat()
        data = self.storage.get_default_data()
        data["focus_import_settings"]["secret"] = "test-secret"
        data["sessions"] = [
            {
                "subject": "computer science",
                "minutes": 1,
                "date": self.storage.get_today_text(),
                "source": "chrome_extension",
                "completed_at": completed_at,
                "cloud_focus_session_id": "42",
            }
        ]
        self.storage.save_local_data_without_sync(data)

        with self.assertRaisesRegex(ValueError, "already synced"):
            self.storage.save_focus_quality_session(
                self.make_signed_focus_summary(completed_at)
            )

        saved = self.storage.load_data()
        self.assertEqual(len(saved["sessions"]), 1)
        self.assertEqual(saved["focus_quality_sessions"], [])

    def test_server_focus_session_merges_with_manual_browser_session(self):
        completed_at = datetime.now().astimezone().isoformat()
        data = self.storage.get_default_data()
        data["sessions"] = [
            {
                "subject": "computer science",
                "minutes": 1,
                "date": self.storage.get_today_text(),
                "source": "chrome_extension",
                "completed_at": completed_at,
            }
        ]

        updates = self.storage.merge_cloud_focus_sessions(
            data,
            [
                {
                    "id": 42,
                    "subject": "computer science",
                    "minutes": 1,
                    "completed_at": completed_at,
                    "source": "chrome_extension",
                }
            ],
        )

        self.assertEqual(updates, 1)
        self.assertEqual(len(data["sessions"]), 1)
        self.assertEqual(data["sessions"][0]["cloud_focus_session_id"], "42")

    def test_server_subject_websites_fill_local_subject_settings(self):
        data = self.storage.get_default_data()
        data["subjects"] = ["maths"]
        data["subject_websites"] = {"maths": []}

        updates = self.storage.merge_subject_websites(
            data,
            {
                "maths": ["pearsonactivelearn.com", "quizlet.com"],
                "physics": ["senecalearning.com"],
            },
        )

        self.assertEqual(updates, 2)
        self.assertIn("physics", data["subjects"])
        self.assertEqual(
            data["subject_websites"]["maths"],
            ["https://pearsonactivelearn.com", "https://quizlet.com"],
        )
        self.assertEqual(
            data["subject_websites"]["physics"],
            ["https://senecalearning.com"],
        )

    def test_repair_builds_review_queue_from_session_topics(self):
        data = self.storage.get_default_data()
        data["sessions"] = [
            {
                "subject": "maths",
                "topic": "Integration",
                "minutes": 30,
                "date": "2026-06-10",
                "source": "manual",
                "note": "Substitution questions",
            },
            {
                "subject": "maths",
                "topic": "Integration",
                "minutes": 20,
                "date": "2026-06-12",
                "source": "manual",
            },
            {
                "subject": "physics",
                "minutes": 15,
                "date": "2026-06-12",
                "source": "manual",
            },
        ]

        repaired = self.storage.repair_data(data)

        self.assertEqual(len(repaired["review_items"]), 1)
        review = repaired["review_items"][0]
        self.assertEqual(review["subject"], "maths")
        self.assertEqual(review["topic"], "Integration")
        self.assertEqual(review["review_count"], 2)
        self.assertEqual(review["last_studied"], "2026-06-12")
        self.assertEqual(review["next_due"], "2026-06-15")

    def test_review_queue_moves_due_date_after_new_topic_session(self):
        data = self.storage.get_default_data()
        data["sessions"] = [
            {
                "subject": "maths",
                "topic": "Integration",
                "minutes": 30,
                "date": "2026-06-10",
                "source": "manual",
            },
        ]

        first = self.storage.repair_data(data)["review_items"][0]
        self.assertEqual(first["next_due"], "2026-06-11")

        data["sessions"].append({
            "subject": "maths",
            "topic": "Integration",
            "minutes": 25,
            "date": "2026-06-11",
            "source": "manual",
        })

        second = self.storage.repair_data(data)["review_items"][0]
        self.assertEqual(second["review_count"], 2)
        self.assertEqual(second["next_due"], "2026-06-14")


if __name__ == "__main__":
    unittest.main()
