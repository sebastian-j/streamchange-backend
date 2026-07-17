DEFAULT_CHAT_COLORS = [
    "#FF0000",
    "#0000FF",
    "#008000",
    "#B22222",
    "#FF7F50",
    "#9ACD32",
    "#FF4500",
    "#2E8B57",
    "#DAA520",
    "#D2691E",
    "#5F9EA0",
    "#1E90FF",
    "#FF69B4",
    "#8A2BE2",
    "#00FF7F",
]


def get_fallback_color(username: str) -> str:
    if not username:
        return "#FFFFFF"

    char_sum = sum(ord(char) for char in username)

    return DEFAULT_CHAT_COLORS[char_sum % len(DEFAULT_CHAT_COLORS)]
