"""Local SQLite backup helpers for the offline deployment."""
from datetime import datetime
from pathlib import Path
import shutil


def create_backup(data_dir="data", backup_dir="backups"):
    source = Path(data_dir)
    target = Path(backup_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    created = []
    for name in ("phase1.db", "memory.db", "accounts.json", "rewards.json"):
        path = source / name
        if path.exists():
            destination = target / f"{path.stem}_{stamp}{path.suffix}"
            shutil.copy2(path, destination)
            created.append(str(destination))
    return created