"""Zip the whole config dir for backup, and unzip to restore."""
import zipfile
from pathlib import Path


def backup_settings(config_dir, dest_zip) -> Path:
    config_dir = Path(config_dir)
    dest = Path(dest_zip)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(config_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(config_dir).as_posix())
    return dest


def restore_settings(src_zip, config_dir) -> None:
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src_zip, "r") as zf:
        zf.extractall(config_dir)
