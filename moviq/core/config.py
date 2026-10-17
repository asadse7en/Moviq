import logging
from pathlib import Path

API_BASE = "https://api.themoviedb.org/3"
USER_DATA_DIR = Path.home() / ".moviq"
CONFIG_FILE = USER_DATA_DIR / "config.json"
LEGACY_CONFIG_FILE = USER_DATA_DIR / "legacy_config.json"
SHOW_OVERRIDES_FILE = USER_DATA_DIR / "moviq_show_overrides.json"
TMDB_CACHE_FILE = USER_DATA_DIR / "tmdb_cache.sqlite3"
ERROR_LOG_FILE = USER_DATA_DIR / "error.log"
log = logging.getLogger(__name__)

LEGACY_CACHE_FILES = (
    Path.home() / "moviq_cache.sqlite3",
    Path.home() / "moviq_cache.sqlite3-wal",
    Path.home() / "moviq_cache.sqlite3-shm",
    Path.home() / "moviq_cache.sqlite3-journal",
    Path.home() / "moviq_cache.json",
    Path.home() / "tmdb_cache.json",
)


def migrate_user_data(home=None) -> None:
    """Move existing Moviq data files from the home directory."""
    home = Path(home) if home is not None else Path.home()
    user_data_dir = home / ".moviq"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    migrations = (
        (home / ".moviq.json", user_data_dir / "config.json"),
        (home / ".tmdb_renamer.json", user_data_dir / "legacy_config.json"),
        (
            home / "moviq_show_overrides.json",
            user_data_dir / "moviq_show_overrides.json",
        ),
    )
    for source, destination in migrations:
        if not source.is_file():
            continue
        if destination.exists():
            log.warning(
                "Keeping both Moviq data files because the destination "
                "already exists: %s and %s",
                source,
                destination,
            )
            continue
        source.replace(destination)


def remove_legacy_cache_files() -> None:
    for path in LEGACY_CACHE_FILES:
        try:
            path.unlink()
        except OSError:
            pass


VIDEO_EXT = {
    ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v", ".mpg", ".mpeg",
    ".flv", ".webm", ".ts", ".m2ts", ".divx",
}
SIDECAR_EXT = {".srt", ".sub", ".idx", ".ass", ".ssa", ".vtt", ".nfo"}
IMAGE_EXT = {
    ".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".gif", ".tif",
    ".tiff", ".svg", ".jfif", ".heic", ".heif", ".ico", ".jxl",
}
SKIP_DIRS = {
    "sample", "samples", "extras", "featurettes", "trailers", "subs",
    "subtitles", "behind the scenes", "@eadir",
}
