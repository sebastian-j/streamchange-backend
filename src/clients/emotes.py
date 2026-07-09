import re

from src.schemas.chat import MessageFragment
from src.config import TWITCH_EMOTE_URL, KICK_EMOTE_URL

_KICK_EMOTE_RE = re.compile(r"\[emote:(\d+):([^\]]+)\]")


def _text_fragment(text: str) -> MessageFragment | None:
    if not text:
        return None
    return MessageFragment(type="text", text=text)

# emoteID:start-end,start-end/emoteID2:start-end
def parse_twitch_emotes(
    content: str, emotes_tag: str | None
) -> list[MessageFragment] | None:
    if not emotes_tag:
        return None

    chars = list(content)
    spans: list[tuple[int, int, str]] = []
    for group in emotes_tag.split("/"):
        if ":" not in group:
            continue
        emote_id, positions = group.split(":", 1)
        for position in positions.split(","):
            if "-" not in position:
                continue
            start_str, end_str = position.split("-", 1)
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                continue
            if 0 <= start <= end < len(chars):
                spans.append((start, end, emote_id))

    if not spans:
        return None

    spans.sort(key=lambda s: s[0])

    fragments: list[MessageFragment] = []
    cursor = 0
    for start, end, emote_id in spans:
        if start < cursor:
            continue
        leading = _text_fragment("".join(chars[cursor:start]))
        if leading:
            fragments.append(leading)
        code = "".join(chars[start : end + 1])
        fragments.append(
            MessageFragment(
                type="emote",
                url=TWITCH_EMOTE_URL.format(id=emote_id),
                code=code,
            )
        )
        cursor = end + 1

    tail = _text_fragment("".join(chars[cursor:]))
    if tail:
        fragments.append(tail)

    return fragments or None

# [emote:157733:catJAM]
def parse_kick_emotes(content: str) -> list[MessageFragment] | None:
    if not content or "[emote:" not in content:
        return None

    fragments: list[MessageFragment] = []
    cursor = 0
    for match in _KICK_EMOTE_RE.finditer(content):
        leading = _text_fragment(content[cursor : match.start()])
        if leading:
            fragments.append(leading)
        emote_id, name = match.group(1), match.group(2)
        fragments.append(
            MessageFragment(
                type="emote",
                url=KICK_EMOTE_URL.format(id=emote_id),
                code=name,
            )
        )
        cursor = match.end()

    tail = _text_fragment(content[cursor:])
    if tail:
        fragments.append(tail)

    return fragments or None


def strip_kick_emote_tokens(content: str) -> str:
    if "[emote:" not in content:
        return content
    return _KICK_EMOTE_RE.sub(lambda m: m.group(2), content)
