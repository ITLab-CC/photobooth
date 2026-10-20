import json
import os
import threading
from typing import NamedTuple

# The counter lives in a small file on a mounted volume, so it survives restarts and needs no database rights.
STATE_DIR = os.getenv("STATE_DIR", "state")
PRINT_FILE = os.path.join(STATE_DIR, "print.json")

DEFAULT_CAPACITY = 400  # prints on one roll of paper and foil; the admin sets the real number
_lock = threading.Lock()


class MediaStatus(NamedTuple):
    count: int  # prints since the roll was changed
    capacity: int

    @property
    def remaining(self) -> int:
        return max(0, self.capacity - self.count)

    @property
    def low(self) -> bool:
        """Warn when only a tenth, but at least ten prints, are left."""
        return self.remaining <= max(10, self.capacity // 10)


def _read() -> MediaStatus:
    try:
        with open(PRINT_FILE) as f:
            data = json.load(f)
        return MediaStatus(int(data["count"]), int(data["capacity"]))
    except (OSError, ValueError, KeyError):
        return MediaStatus(0, DEFAULT_CAPACITY)


def _write(status: MediaStatus) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(PRINT_FILE, "w") as f:
        json.dump({"count": status.count, "capacity": status.capacity}, f)


def status() -> MediaStatus:
    with _lock:
        return _read()


def add_prints(amount: int) -> MediaStatus:
    with _lock:
        current = _read()
        updated = MediaStatus(current.count + amount, current.capacity)
        _write(updated)
        return updated


def set_capacity(capacity: int) -> MediaStatus:
    with _lock:
        updated = MediaStatus(_read().count, capacity)
        _write(updated)
        return updated


def reset() -> MediaStatus:
    """A new roll is in: start counting from zero."""
    with _lock:
        updated = MediaStatus(0, _read().capacity)
        _write(updated)
        return updated
