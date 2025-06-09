import platform
import os

def play_sound(sound_file):
    if not sound_file:
        return
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            if os.system(f"aplay '{sound_file}' &") != 0:
                os.system(f"afplay '{sound_file}' &")
    except Exception as e:
        print(f"Failed to play sound: {e}")

def speak_tts(message):
    if not message:
        return
    try:
        if platform.system() == "Windows":
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(message)
            engine.runAndWait()
        else:
            if os.system(f"espeak '{message}' &") != 0:
                os.system(f"say '{message}' &")
    except Exception as e:
        print(f"Failed to speak TTS: {e}")