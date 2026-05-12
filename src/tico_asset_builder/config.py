from __future__ import annotations

from .models import ConsoleConfig

ARCHIVE_EXTENSIONS = frozenset({".zip", ".7z", ".rar", ".tar", ".gz"})

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"})

IMAGE_FOLDER_NAMES = frozenset(
    {
        "imgs",
        "images",
        "thumbnails",
        "thumbs",
        "media",
        "covers",
        "cover",
        "boxart",
        "box-art",
        "box_art",
    }
)

DISC_PRIMARY_EXTENSIONS = frozenset({".cue", ".chd", ".iso", ".m3u"})

CONSOLES: dict[str, ConsoleConfig] = {
    "gb": ConsoleConfig("gb", frozenset({".gb"})),
    "gbc": ConsoleConfig("gbc", frozenset({".gbc"})),
    "gba": ConsoleConfig("gba", frozenset({".gba"})),
    "nes": ConsoleConfig("nes", frozenset({".nes"})),
    "snes": ConsoleConfig("snes", frozenset({".sfc", ".smc"})),
    "genesis": ConsoleConfig("genesis", frozenset({".gen", ".md", ".smd", ".bin"})),
    "master-system": ConsoleConfig("master-system", frozenset({".sms"})),
    "game-gear": ConsoleConfig("game-gear", frozenset({".gg"})),
    "sega-cd": ConsoleConfig("sega-cd", frozenset({".cue", ".chd", ".iso", ".m3u", ".bin"}), True),
    "saturn": ConsoleConfig("saturn", frozenset({".cue", ".chd", ".iso", ".m3u", ".bin"}), True),
    "dc": ConsoleConfig("dc", frozenset({".cdi", ".gdi", ".chd", ".cue", ".iso", ".m3u", ".bin"}), True),
    "psx": ConsoleConfig("psx", frozenset({".cue", ".chd", ".iso", ".m3u", ".bin", ".pbp"}), True),
    "psp": ConsoleConfig("psp", frozenset({".iso", ".cso", ".pbp"}), True),
    "gc": ConsoleConfig("gc", frozenset({".iso", ".gcm", ".rvz", ".nkit.iso"}), True),
    "wii": ConsoleConfig("wii", frozenset({".iso", ".wbfs", ".rvz", ".nkit.iso"}), True),
}

