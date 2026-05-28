import sys
from pathlib import Path

SOUND_DIR =     Path(__file__).resolve().parent / "assets"  / "sounds"

SOUND_FILES = {
    "ui": SOUND_DIR / "ui.wav",
    "focus_complete": SOUND_DIR / "focus_complete.wav",
    "streak_protected": SOUND_DIR / "streak_protected.wav"
}


def play_sound(sound_name):
    #play a simple completetion sound
    sound_file = SOUND_FILES.get(sound_name)

    if sound_file is None:
        return
    
    if not sound_file.exists():
        return
    


    if sys.platform.startswith("win"):
        try:
            import winsound

            winsound.PlaySound(
                str(sound_file),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
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
