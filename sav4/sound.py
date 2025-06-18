"""
Sound and TTS utility module for Screen Region Monitor.

Provides functions to play sounds and perform text-to-speech (TTS).
"""

import os
import platform
import threading
from typing import Optional

try:
    import playsound
except ImportError:
    playsound = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

def play_sound(sound_path: str) -> None:
    """
    Play a sound from the given file path.

    Args:
        sound_path: The path to the sound file to play.
    """
    if not sound_path or not os.path.exists(sound_path):
        return
    if playsound:
        try:
            playsound.playsound(sound_path, block=False)
        except Exception:
            pass

def speak_tts(text: str, voice: Optional[str] = None) -> None:
    """
    Speak the given text using TTS in a background thread.

    Args:
        text: The text to speak.
        voice: Optional voice name or id to use.
    """
    if not text or pyttsx3 is None:
        return

    def _speak():
        try:
            engine = pyttsx3.init()
            if voice:
                for v in engine.getProperty('voices'):
                    if voice in v.name or voice == v.id:
                        engine.setProperty('voice', v.id)
                        break
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

    threading.Thread(target=_speak, daemon=True).start()