"""
Configuration module for Screen Region Monitor.
Handles loading and saving of application settings.
"""

import json
import os
from typing import Any, Dict

CONFIG_FILE = "config.json"

def load_config() -> Dict[str, Any]:
    """
    Load configuration from the config.json file.
    Returns:
        A dictionary containing configuration values.
    """
    if not os.path.exists(CONFIG_FILE):
        # Provide default config if file does not exist
        return {
            "timer_warning_threshold": 10.0,
            "timer_warning_color": "#FFD700",
            "timer_alert_threshold": 1.0,
            "timer_alert_color": "#FF3333",
            "timer_sound": "",
            # Add other default settings as needed
        }
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config: Dict[str, Any]) -> None:
    """
    Save configuration to the config.json file.
    Args:
        config: The configuration dictionary to save.
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)