import logging

from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException

logger = logging.getLogger(__name__)


def get_chatroom_id(slug: str) -> int:
    try:
        r = requests.get(
            f"https://kick.com/api/v2/channels/{slug}", impersonate="chrome", timeout=10
        )
        r.raise_for_status()
    except RequestException as e:
        logger.error("Błąd sieci przy pobieraniu kanału '%s': %s", slug, e)
        raise

    chatroom = r.json().get("chatroom")
    if not chatroom:
        raise ValueError(f"Kanał '{slug}' nie ma chatroomu")

    return chatroom["id"]
