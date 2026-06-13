import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest


class AppPathTests(unittest.TestCase):
    def test_legacy_file_migrates_to_configured_app_data_dir(self):
        old_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as cwd:
            with tempfile.TemporaryDirectory() as data_dir:
                os.environ["STUDYSTREAK_DATA_DIR"] = data_dir
                sys.modules.pop("studystreak.paths", None)
                paths = importlib.import_module("studystreak.paths")

                try:
                    os.chdir(cwd)
                    Path("study_data.json").write_text('{"sessions": []}', encoding="utf-8")
                    target_file = paths.get_app_data_file("study_data.json")

                    paths.migrate_legacy_file("study_data.json", target_file)

                    self.assertTrue(target_file.exists())
                    self.assertEqual(
                        target_file.read_text(encoding="utf-8"),
                        '{"sessions": []}',
                    )
                finally:
                    os.chdir(old_cwd)
                    os.environ.pop("STUDYSTREAK_DATA_DIR", None)


if __name__ == "__main__":
    unittest.main()
