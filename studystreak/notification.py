import sys
from pathlib import Path

SOUND_DIR = Path(__file__).resolve().parent / "assets" / "sounds"

SOUND_FILES = {
    "ui": SOUND_DIR / "ui.wav",
    "focus_complete": SOUND_DIR / "focus_complete.wav",
    "streak_protected": SOUND_DIR / "streak_protected.wav",
    "achievement": SOUND_DIR / "achievement.wav",
}


def play_sound(sound_name, wait=False):
    # Play a short app sound; use wait=True when the sound must not be interrupted.
    sound_file = SOUND_FILES.get(sound_name)

    if sound_file is None:
        return
    
    if not sound_file.exists():
        return

    if sys.platform.startswith("win"):
        try:
            import winsound

            flags = winsound.SND_FILENAME

            if not wait:
                flags = flags | winsound.SND_ASYNC

            winsound.PlaySound(None, 0)
            winsound.PlaySound(
                str(sound_file),
                flags,
            )
            
            return
        except RuntimeError:
            pass
    
    print("\a", end="", flush=True)

def show_focus_complete_notification(subject, minutes):
    try:
        from plyer import notification

        notification.notify(
            title="StudyStreak",
            message=f"Focus session complete: {minutes} minutes of {subject}",
            app_name="StudyStreak",
            timeout=5,
        )
    except Exception:
        pass

def show_sync_failed_notification(error_message):
    try:
        from plyer import notification

        notification.notify(
            title="StudyStreak",
            message=f"Cloud sync failed: {error_message}",
            app_name="StudyStreak",
            timeout=5,
        )
    except Exception:
        pass

def show_achievement_notification(name, description):
    try:
        from plyer import notification

        notification.notify(
            title=f"Achievement unlocked: {name}",
            message=description,
            app_name="StudyStreak",
            timeout=5,
        )
    except Exception:
        pass
