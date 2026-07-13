KNOWN_BOTS: set[str] = set(
    {
        "nightbot",
        "streamelements",
        "streamlabs",
        "fossabot",
        "botrix",
        "kickbot",
        "@streamelements",
    }
)


def is_known_bot(username: str) -> bool:
    return username.casefold() in KNOWN_BOTS
