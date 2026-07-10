KNOWN_BOTS: set[str] = set(
    {
        "nightbot",
        "streamelements",
        "streamlabs",
        "streamlabsios",
        "moobot",
        "wizebot",
        "fossabot",
        "botisimo",
        "coebot",
        "deepbot",
        "phantombot",
        "ankhbot",
        "vivbot",
        "revlobot",
        "scorpbot",
        "stay_hydrated_bot",
        "commanderroot",
        "soundtrackbot",
        "sery_bot",
        "buttsbot",
        "restreambot",
        "own3d",
        "streamstickers",
        "kofistreambot",
        "botrixoficial",
        "botrix",
        "streamholics",
        "logviewer",
        "playwithviewersbot",
        "creatisbot",
        "pretzelrocks",
        "songlistbot",
        "tangiabot",
        "supibot",
    }
)


def is_known_bot(username: str) -> bool:
    return username.lower() in KNOWN_BOTS
