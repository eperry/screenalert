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
    Load configuration from the config file.

    Returns:
        Configuration dictionary.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """
    Save configuration to the config file.

    Args:
        config: Configuration dictionary.
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)