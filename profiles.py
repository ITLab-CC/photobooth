import json
import os
import threading
import uuid
from typing import Dict, List, Optional

# Event profiles are stored as one small file on the mounted state volume.
STATE_DIR = os.getenv("STATE_DIR", "state")
PROFILES_FILE = os.path.join(STATE_DIR, "profiles.json")

_lock = threading.Lock()


def _read() -> List[Dict]:
    try:
        with open(PROFILES_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _write(profiles: List[Dict]) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


def list_profiles() -> List[Dict]:
    with _lock:
        return _read()


def get_profile(profile_id: str) -> Optional[Dict]:
    with _lock:
        return next((p for p in _read() if p["id"] == profile_id), None)


def add_profile(name: str, settings: Dict, active_background_ids: List[str], frame_id: Optional[str]) -> Dict:
    profile = {
        "id": f"Profile-{uuid.uuid4()}",
        "name": name,
        "settings": settings,
        "active_background_ids": active_background_ids,
        "frame_id": frame_id,
    }
    with _lock:
        profiles = _read()
        profiles.append(profile)
        _write(profiles)
    return profile


def delete_profile(profile_id: str) -> bool:
    with _lock:
        profiles = _read()
        remaining = [p for p in profiles if p["id"] != profile_id]
        if len(remaining) == len(profiles):
            return False
        _write(remaining)
        return True
