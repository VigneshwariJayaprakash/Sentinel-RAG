import hashlib
import os
import shutil
import subprocess
import sys
from datetime import datetime

import requests

SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
SDN_PATH = "data/sdn.csv"
BACKUP_DIR = "data/backups"
VECTOR_DB_DIR = "vector_db"


def utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}")


def file_hash(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def ensure_data_dirs() -> None:
    os.makedirs(os.path.dirname(SDN_PATH), exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_existing_sdn() -> None:
    if not os.path.exists(SDN_PATH):
        return
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = os.path.join(BACKUP_DIR, f"sdn_{timestamp}.csv")
    shutil.copy2(SDN_PATH, backup_name)
    log(f"Backed up previous SDN file to {backup_name}")


def make_session() -> requests.Session:
    """
    Build requests session. Set SDN_BYPASS_PROXY=1 to ignore env proxies.
    """
    session = requests.Session()
    if os.getenv("SDN_BYPASS_PROXY", "").strip() in {"1", "true", "TRUE"}:
        session.trust_env = False
        log("Proxy bypass enabled (SDN_BYPASS_PROXY=1)")
    return session


def download_sdn() -> bool:
    """
    Download SDN CSV and return True only when file content changed.
    """
    ensure_data_dirs()
    old_hash = file_hash(SDN_PATH)

    log(f"Downloading SDN list from {SDN_URL}")
    session = make_session()
    try:
        response = session.get(SDN_URL, timeout=90)
        response.raise_for_status()
    except requests.RequestException as exc:
        if os.path.exists(SDN_PATH):
            log(f"Download failed ({exc}). Using existing local SDN file and skipping rebuild.")
            return False
        raise

    backup_existing_sdn()
    with open(SDN_PATH, "wb") as f:
        f.write(response.content)

    new_hash = file_hash(SDN_PATH)
    size_kb = len(response.content) / 1024
    log(f"Downloaded SDN file ({size_kb:.1f} KB)")

    if old_hash is not None and old_hash == new_hash:
        log("SDN file unchanged. Skipping index rebuild.")
        return False

    log("SDN file changed. Rebuild required.")
    return True


def rebuild_indexes() -> None:
    log("Rebuilding indexes")

    if os.path.exists(VECTOR_DB_DIR):
        shutil.rmtree(VECTOR_DB_DIR)
        log(f"Removed old {VECTOR_DB_DIR} directory")

    # Use the current interpreter so cron/venv behavior is consistent.
    subprocess.run([sys.executable, "ingesting.py"], check=True)
    log("Index rebuild completed")


def main() -> None:
    try:
        changed = download_sdn()
        if changed:
            rebuild_indexes()
        log("SDN update job completed successfully")
    except Exception as exc:
        log(f"SDN update job failed: {exc}")
        raise


if __name__ == "__main__":
    main()
