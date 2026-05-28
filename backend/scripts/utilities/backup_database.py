"""
Database Backup Script for Petroflow
Author: Jhon Villegas
Purpose: Automated SQLite database backup with compression
Cost: $0 (uses only standard library)
"""

import os
import shutil
import gzip
from datetime import datetime
from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DatabaseBackup:
    """Handle database backup operations"""
    
    def __init__(self, db_path: str = None, backup_dir: str = None):
        """
        Initialize backup manager
        
        Args:
            db_path: Path to database file (default: petroflow/petroflow.db)
            backup_dir: Path to backup directory (default: petroflow/storage/backups)
        """
        self.root_dir = Path(__file__).parent.parent
        
        # Set database path
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.root_dir / "petroflow.db"
        
        # Set backup directory
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = self.root_dir / "storage" / "backups"
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, compress: bool = True) -> dict:
        """
        Create database backup
        
        Args:
            compress: Whether to compress backup with gzip
        
        Returns:
            Dictionary with backup information
        """
        if not self.db_path.exists():
            return {
                "success": False,
                "error": f"Database file not found: {self.db_path}"
            }
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"petroflow.db.backup_{timestamp}"
        
        if compress:
            backup_name += ".gz"
            backup_path = self.backup_dir / backup_name
            
            # Copy and compress
            try:
                with open(self.db_path, 'rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Compression failed: {str(e)}"
                }
        else:
            backup_path = self.backup_dir / backup_name
            
            # Simple copy
            try:
                shutil.copy2(self.db_path, backup_path)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Copy failed: {str(e)}"
                }
        
        # Get file sizes
        original_size = self.db_path.stat().st_size
        backup_size = backup_path.stat().st_size
        compression_ratio = (1 - backup_size / original_size) * 100 if compress else 0
        
        return {
            "success": True,
            "backup_path": str(backup_path),
            "backup_name": backup_name,
            "timestamp": timestamp,
            "original_size": original_size,
            "backup_size": backup_size,
            "compression_ratio": compression_ratio,
            "compressed": compress
        }
    
    def list_backups(self) -> list:
        """
        List all available backups
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("petroflow.db.backup_*")):
            stat = backup_file.stat()
            
            # Extract timestamp from filename
            filename = backup_file.name
            if ".gz" in filename:
                timestamp_str = filename.replace("petroflow.db.backup_", "").replace(".gz", "")
            else:
                timestamp_str = filename.replace("petroflow.db.backup_", "")
            
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except ValueError:
                timestamp = None
            
            backups.append({
                "filename": filename,
                "path": str(backup_file),
                "size": stat.st_size,
                "created": timestamp.isoformat() if timestamp else "unknown",
                "compressed": ".gz" in filename
            })
        
        return backups
    
    def restore_backup(self, backup_name: str) -> dict:
        """
        Restore database from backup
        
        Args:
            backup_name: Name of backup file to restore
        
        Returns:
            Dictionary with restore information
        """
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {
                "success": False,
                "error": f"Backup file not found: {backup_name}"
            }
        
        # Create backup of current database before restoring
        current_backup = self.create_backup(compress=True)
        if not current_backup["success"]:
            return {
                "success": False,
                "error": "Failed to backup current database before restore"
            }
        
        try:
            if backup_name.endswith(".gz"):
                # Decompress and restore
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Simple copy
                shutil.copy2(backup_path, self.db_path)
            
            return {
                "success": True,
                "restored_from": backup_name,
                "current_backup": current_backup["backup_name"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Restore failed: {str(e)}"
            }
    
    def cleanup_old_backups(self, keep_count: int = 10) -> dict:
        """
        Remove old backups, keeping only the most recent ones
        
        Args:
            keep_count: Number of backups to keep
        
        Returns:
            Dictionary with cleanup information
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            return {
                "success": True,
                "removed": 0,
                "kept": len(backups),
                "message": f"Only {len(backups)} backups exist, no cleanup needed"
            }
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x["created"], reverse=True)
        
        # Remove old backups
        removed = 0
        for backup in backups[keep_count:]:
            try:
                Path(backup["path"]).unlink()
                removed += 1
            except Exception as e:
                print(f"Warning: Could not remove {backup['filename']}: {e}")
        
        return {
            "success": True,
            "removed": removed,
            "kept": keep_count,
            "message": f"Removed {removed} old backups, kept {keep_count} most recent"
        }
    
    def get_backup_stats(self) -> dict:
        """
        Get statistics about backups
        
        Returns:
            Dictionary with backup statistics
        """
        backups = self.list_backups()
        
        if not backups:
            return {
                "total_backups": 0,
                "total_size": 0,
                "oldest_backup": None,
                "newest_backup": None
            }
        
        total_size = sum(b["size"] for b in backups)
        
        # Sort by creation date
        backups.sort(key=lambda x: x["created"])
        
        return {
            "total_backups": len(backups),
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_backup": backups[0]["filename"],
            "oldest_date": backups[0]["created"],
            "newest_backup": backups[-1]["filename"],
            "newest_date": backups[-1]["created"],
            "compressed_count": sum(1 for b in backups if b["compressed"])
        }


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def main():
    """Main backup script"""
    print("=" * 60)
    print("Petroflow Database Backup Utility")
    print("Author: Jhon Villegas")
    print("=" * 60)
    
    backup_manager = DatabaseBackup()
    
    # Check if database exists
    if not backup_manager.db_path.exists():
        print(f"\nError: Database not found at {backup_manager.db_path}")
        print("Please ensure Petroflow is properly installed.")
        return
    
    print(f"\nDatabase: {backup_manager.db_path}")
    print(f"Backup Directory: {backup_manager.backup_dir}")
    
    # Create backup
    print("\nCreating backup...")
    result = backup_manager.create_backup(compress=True)
    
    if result["success"]:
        print(f"✓ Backup created successfully!")
        print(f"  - File: {result['backup_name']}")
        print(f"  - Original size: {format_size(result['original_size'])}")
        print(f"  - Backup size: {format_size(result['backup_size'])}")
        print(f"  - Compression: {result['compression_ratio']:.1f}% reduction")
    else:
        print(f"✗ Backup failed: {result['error']}")
        return
    
    # Show backup statistics
    print("\n" + "=" * 60)
    print("Backup Statistics")
    print("=" * 60)
    
    stats = backup_manager.get_backup_stats()
    print(f"Total backups: {stats['total_backups']}")
    print(f"Total size: {format_size(stats['total_size'])} ({stats['total_size_mb']} MB)")
    print(f"Compressed backups: {stats['compressed_count']}")
    
    if stats['oldest_backup']:
        print(f"\nOldest backup: {stats['oldest_backup']}")
        print(f"  Created: {stats['oldest_date']}")
        print(f"\nNewest backup: {stats['newest_backup']}")
        print(f"  Created: {stats['newest_date']}")
    
    # Cleanup old backups
    print("\n" + "=" * 60)
    print("Cleanup Old Backups")
    print("=" * 60)
    
    cleanup_result = backup_manager.cleanup_old_backups(keep_count=10)
    print(cleanup_result['message'])
    
    # List all backups
    print("\n" + "=" * 60)
    print("Available Backups")
    print("=" * 60)
    
    backups = backup_manager.list_backups()
    for i, backup in enumerate(backups[-5:], 1):  # Show last 5
        print(f"\n{i}. {backup['filename']}")
        print(f"   Size: {format_size(backup['size'])}")
        print(f"   Created: {backup['created']}")
        print(f"   Compressed: {'Yes' if backup['compressed'] else 'No'}")
    
    if len(backups) > 5:
        print(f"\n... and {len(backups) - 5} more backups")
    
    print("\n" + "=" * 60)
    print("Backup Complete!")
    print("=" * 60)
    print("\nTo restore a backup, use:")
    print("  python scripts/backup_database.py --restore <backup_filename>")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Petroflow Database Backup Utility")
    parser.add_argument("--restore", help="Restore from backup file")
    parser.add_argument("--list", action="store_true", help="List all backups")
    parser.add_argument("--stats", action="store_true", help="Show backup statistics")
    parser.add_argument("--cleanup", type=int, metavar="N", help="Keep only N most recent backups")
    
    args = parser.parse_args()
    
    backup_manager = DatabaseBackup()
    
    if args.restore:
        print(f"Restoring from backup: {args.restore}")
        result = backup_manager.restore_backup(args.restore)
        if result["success"]:
            print(f"✓ Database restored successfully!")
            print(f"  - Restored from: {result['restored_from']}")
            print(f"  - Current database backed up as: {result['current_backup']}")
        else:
            print(f"✗ Restore failed: {result['error']}")
    
    elif args.list:
        backups = backup_manager.list_backups()
        print(f"\nFound {len(backups)} backups:")
        for backup in backups:
            print(f"\n- {backup['filename']}")
            print(f"  Size: {format_size(backup['size'])}")
            print(f"  Created: {backup['created']}")
    
    elif args.stats:
        stats = backup_manager.get_backup_stats()
        print("\nBackup Statistics:")
        print(json.dumps(stats, indent=2))
    
    elif args.cleanup:
        result = backup_manager.cleanup_old_backups(keep_count=args.cleanup)
        print(result['message'])
    
    else:
        main()