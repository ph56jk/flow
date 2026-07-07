from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"
UPLOADS_DIR = DATA_DIR / "uploads"
DOWNLOADS_DIR = DATA_DIR / "downloads"
STATIC_DIR = PACKAGE_ROOT / "static"
EXTENSION_DIR = PROJECT_ROOT / "extension"
# Built WXT artifact (preferred for packaging). Falls back to EXTENSION_DIR
# when absent, e.g. before `wxt build` has ever run.
EXTENSION_WXT_BUILD_DIR = PROJECT_ROOT / "extension-wxt" / ".output" / "chrome-mv3"


def ensure_app_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
