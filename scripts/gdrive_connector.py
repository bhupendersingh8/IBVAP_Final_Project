"""
IBVAP Google Drive Cloud Storage Connector & Model Cache Manager
Allows connecting 5TB Google Drive or local D:/E: drives for large weights & dataset storage.
Ensures C: drive stays lean while enabling high-capacity cloud/local storage.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path

# Recommended storage directories
DEFAULT_LOCAL_CACHE = r"D:\ibvap_models" if os.path.exists(r"D:\ ") else r"C:\Users\dell\Desktop\p2\IBVAP_Final_Project\models"
GDRIVE_STREAM_PATH = r"G:\My Drive\IBVAP_Storage"

class GDriveConnector:
    def __init__(self, cache_dir=None, gdrive_path=None):
        # Auto-detect best storage drive with maximum free space
        if cache_dir is None:
            self.cache_dir = self._detect_best_storage_drive()
        else:
            self.cache_dir = Path(cache_dir)

        self.gdrive_path = Path(gdrive_path or GDRIVE_STREAM_PATH)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _detect_best_storage_drive(self) -> Path:
        """Finds drive with largest free space on Windows (D:, E:, or C:)."""
        candidates = [r"D:\ibvap_storage", r"E:\ibvap_storage", r"C:\Users\dell\Desktop\p2\IBVAP_Final_Project\data_cache"]
        best_path = candidates[-1]
        max_free = 0

        for cand in candidates:
            drive = cand[:3]
            if os.path.exists(drive):
                try:
                    usage = shutil.disk_usage(drive)
                    if usage.free > max_free:
                        max_free = usage.free
                        best_path = cand
                except Exception:
                    continue

        return Path(best_path)

    def get_status(self):
        """Returns drive storage status and Google Drive stream status."""
        drives = {}
        for letter in ["C", "D", "E", "G"]:
            root = f"{letter}:\\"
            if os.path.exists(root):
                try:
                    usage = shutil.disk_usage(root)
                    drives[letter] = {
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                    }
                except Exception:
                    pass

        gdrive_mounted = os.path.exists(r"G:\ ") or os.path.exists(self.gdrive_path)

        return {
            "drives": drives,
            "active_cache_dir": str(self.cache_dir),
            "gdrive_stream_mounted": gdrive_mounted,
            "gdrive_path": str(self.gdrive_path),
        }

    def sync_weights_from_gdrive(self, model_name: str) -> bool:
        """
        Copies model weights on-demand from Google Drive (G:) to local cache.
        Does not pre-download entire 5TB; copies only requested checkpoint.
        """
        source_file = self.gdrive_path / "models" / model_name
        dest_file = self.cache_dir / model_name

        if dest_file.exists():
            print(f"[CACHE HIT] Model already cached locally: {dest_file}")
            return True

        if not source_file.exists():
            print(f"[MISSING] Model not found in Google Drive: {source_file}")
            print("To sync via Google Drive, place the weights in 'G:\\My Drive\\IBVAP_Storage\\models\\'")
            return False

        print(f"[SYNCING] Streaming {model_name} from Google Drive to {dest_file}...")
        shutil.copyfile(source_file, dest_file)
        print(f"[SUCCESS] {model_name} cached ready for inference.")
        return True

def main():
    connector = GDriveConnector()
    status = connector.get_status()

    print("=" * 70)
    print("   IBVAP STORAGE & GOOGLE DRIVE CLOUD CONNECTOR")
    print("=" * 70)
    print(f"Active Local Model Cache: {status['active_cache_dir']}")
    print(f"Google Drive Virtual Mount (G:): {'CONNECTED' if status['gdrive_stream_mounted'] else 'NOT CONNECTED (Follow setup steps)'}\n")
    print("Detected Local Storage Volumes:")
    for letter, d in status["drives"].items():
        print(f"  Drive {letter}: Total = {d['total_gb']:>6} GB | Used = {d['used_gb']:>6} GB | Free = {d['free_gb']:>6} GB")
    print("=" * 70)

if __name__ == "__main__":
    main()
