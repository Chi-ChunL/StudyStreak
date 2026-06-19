from pathlib import Path
import shutil


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "chrome_extension"
OUTPUT_DIR = REPO_ROOT / "dist" / "firefox_extension"

SHARED_FILES = [
    "background.js",
    "focus_overlay.js",
    "icon128.png",
    "popup.css",
    "popup.html",
    "popup.js",
    "strict_focus_blocked.html",
    "strict_focus_blocked.js",
]


def main() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True)

    for filename in SHARED_FILES:
        shutil.copy2(SOURCE_DIR / filename, OUTPUT_DIR / filename)

    shutil.copy2(SOURCE_DIR / "manifest.firefox.json", OUTPUT_DIR / "manifest.json")

    print(f"Firefox extension built at: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
