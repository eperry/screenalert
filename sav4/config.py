import json
import os

CONFIG_FILE = "screenalert_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                new_regions = []
                for r in config.get("regions", []):
                    if isinstance(r, dict):
                        for k in ["sound_file", "sound_enabled", "tts_enabled", "tts_message"]:
                            r.pop(k, None)
                        new_regions.append(r)
                    else:
                        new_regions.append({"rect": r})
                config["regions"] = new_regions
                if "highlight_time" not in config:
                    config["highlight_time"] = 5
                if "green_text" not in config:
                    config["green_text"] = "Green"
                if "green_color" not in config:
                    config["green_color"] = "#080"
                if "paused_text" not in config:
                    config["paused_text"] = "Paused"
                if "paused_color" not in config:
                    config["paused_color"] = "#08f"
                if "alert_text" not in config:
                    config["alert_text"] = "Alert"
                if "alert_color" not in config:
                    config["alert_color"] = "#a00"
                return config
        except Exception as e:
            print(f"Config load failed: {e}, using defaults.")
    return {
        "regions": [],
        "interval": 1000,
        "highlight_time": 5,
        "default_sound": "",
        "default_tts": "Alert {name}",
        "alert_threshold": 0.99,
        "green_text": "Green",
        "green_color": "#080",
        "paused_text": "Paused",
        "paused_color": "#08f",
        "alert_text": "Alert",
        "alert_color": "#a00"
    }

def save_config(
    regions, interval, highlight_time, default_sound="", default_tts="", alert_threshold=0.99,
    green_text="Green", green_color="#080",
    paused_text="Paused", paused_color="#08f",
    alert_text="Alert", alert_color="#a00"
):
    serializable_regions = []
    for r in regions:
        r_copy = dict(r)
        r_copy.pop("_diff_img", None)
        serializable_regions.append(r_copy)
    config = {
        "regions": serializable_regions,
        "interval": interval,
        "highlight_time": highlight_time,
        "default_sound": default_sound,
        "default_tts": default_tts,
        "alert_threshold": alert_threshold,
        "green_text": green_text,
        "green_color": green_color,
        "paused_text": paused_text,
        "paused_color": paused_color,
        "alert_text": alert_text,
        "alert_color": alert_color
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)