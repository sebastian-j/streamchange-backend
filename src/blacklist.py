import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BLACKLIST_PATH = Path(__file__).resolve().parent.parent / "blacklist.json"

_blacklist: list[dict] = []


def load_blacklist() -> None:
    global _blacklist
    try:
        with open(_BLACKLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _blacklist = data.get("channels", [])
        logger.info("Załadowano blacklistę: %d kanałów.", len(_blacklist))
    except FileNotFoundError:
        logger.warning("Plik blacklist.json nie istnieje lub blacklista pusta.")
        _blacklist = []
    except json.JSONDecodeError as e:
        logger.error("Błąd parsowania blacklist.json: %s", e)
        _blacklist = []


def check_blacklist(channel: str, platform: str) -> Optional[dict]:
    channel_lower = channel.lower().strip()
    platform_lower = platform.lower().strip()

    for entry in _blacklist:
        if (
            entry.get("name", "").lower() == channel_lower
            and entry.get("platform", "").lower() == platform_lower
        ):
            return entry

    return None
