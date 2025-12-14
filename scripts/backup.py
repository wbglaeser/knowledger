#!/usr/bin/env python3
"""
Daily backup script for Knowledger database.
Creates timestamped backups and syncs to Google Cloud Storage via rclone.
"""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
DB_PATH = Path("knowledger.db")
BACKUP_DIR = Path("backups")
RCLONE_REMOTE = "gcs:knowledger-backup"  # GCS bucket (change bucket name as needed)
KEEP_LOCAL_DAYS = 7  # Keep local backups for this many days

def create_backup():
    """Create a timestamped backup of the database"""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return None
    
    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"knowledger_backup_{timestamp}.db"
    
    # Copy database
    print(f"Creating backup: {backup_file}")
    shutil.copy2(DB_PATH, backup_file)
    
    return backup_file

def sync_to_gcs(backup_file):
    """Sync backup to Google Cloud Storage using rclone"""
    try:
        print(f"Syncing to Google Cloud Storage: {RCLONE_REMOTE}")
        result = subprocess.run(
            ["rclone", "copy", str(backup_file), RCLONE_REMOTE],
            capture_output=True,
            text=True,
            check=True
        )
        print("Successfully synced to Google Cloud Storage")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error syncing to Google Cloud Storage: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: rclone not found. Please install rclone first.")
        print("Install with: brew install rclone")
        return False

def cleanup_old_backups():
    """Remove local backups older than KEEP_LOCAL_DAYS"""
    if not BACKUP_DIR.exists():
        return
    
    cutoff_time = datetime.now().timestamp() - (KEEP_LOCAL_DAYS * 86400)
    
    for backup in BACKUP_DIR.glob("knowledger_backup_*.db"):
        if backup.stat().st_mtime < cutoff_time:
            print(f"Removing old backup: {backup}")
            backup.unlink()

if __name__ == "__main__":
    print(f"Starting backup at {datetime.now()}")
    
    # Create backup
    backup_file = create_backup()
    if not backup_file:
        exit(1)
    
    # Sync to Google Cloud Storage
    sync_to_gcs(backup_file)
    
    # Cleanup old local backups
    cleanup_old_backups()
    
    print(f"Backup complete at {datetime.now()}")
