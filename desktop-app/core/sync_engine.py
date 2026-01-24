"""
Sync Engine - Automatic file watching and syncing
"""

import os
import time
import threading
import hashlib
from pathlib import Path
from typing import Dict, List, Callable, Optional
from datetime import datetime
from .git_ops import GitOps


class FileWatcher:
    """Watch a directory for file changes"""

    def __init__(self, path: str, callback: Callable, ignore_patterns: List[str] = None):
        self.path = Path(path)
        self.callback = callback
        self.ignore_patterns = ignore_patterns or ['.git', '__pycache__', '.pyc', '.tmp']
        self.running = False
        self.thread = None
        self.file_hashes: Dict[str, str] = {}

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored"""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True
        return False

    def _hash_file(self, path: Path) -> Optional[str]:
        """Get hash of file contents"""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None

    def _scan_directory(self) -> Dict[str, str]:
        """Scan directory and return file hashes"""
        hashes = {}
        try:
            for path in self.path.rglob('*'):
                if path.is_file() and not self._should_ignore(path):
                    rel_path = str(path.relative_to(self.path))
                    file_hash = self._hash_file(path)
                    if file_hash:
                        hashes[rel_path] = file_hash
        except:
            pass
        return hashes

    def _watch_loop(self):
        """Main watch loop"""
        self.file_hashes = self._scan_directory()

        while self.running:
            time.sleep(2)  # Check every 2 seconds

            current_hashes = self._scan_directory()

            # Find changes
            added = set(current_hashes.keys()) - set(self.file_hashes.keys())
            removed = set(self.file_hashes.keys()) - set(current_hashes.keys())
            modified = {
                f for f in current_hashes.keys() & self.file_hashes.keys()
                if current_hashes[f] != self.file_hashes[f]
            }

            if added or removed or modified:
                changes = {
                    "added": list(added),
                    "removed": list(removed),
                    "modified": list(modified),
                    "timestamp": datetime.now().isoformat()
                }
                self.callback(changes)
                self.file_hashes = current_hashes

    def start(self):
        """Start watching"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop watching"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


class SyncEngine:
    """Handle automatic syncing between local and remote"""

    def __init__(self):
        self.git = GitOps()
        self.watchers: Dict[str, FileWatcher] = {}
        self.sync_queue: List[Dict] = []
        self.sync_interval = 300  # 5 minutes default
        self.auto_sync_enabled = False
        self.sync_thread = None
        self.running = False
        self.last_sync: Dict[str, datetime] = {}
        self.callbacks = {
            "on_change": [],
            "on_sync_start": [],
            "on_sync_complete": [],
            "on_error": []
        }

    def add_callback(self, event: str, callback: Callable):
        """Add callback for events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _emit(self, event: str, *args, **kwargs):
        """Emit event to all callbacks"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except:
                pass

    def watch_repo(self, repo_path: str):
        """Start watching a repository for changes"""
        if repo_path in self.watchers:
            return

        def on_change(changes):
            self.sync_queue.append({
                "repo_path": repo_path,
                "changes": changes,
                "timestamp": datetime.now()
            })
            self._emit("on_change", repo_path, changes)

        watcher = FileWatcher(repo_path, on_change)
        watcher.start()
        self.watchers[repo_path] = watcher

    def unwatch_repo(self, repo_path: str):
        """Stop watching a repository"""
        if repo_path in self.watchers:
            self.watchers[repo_path].stop()
            del self.watchers[repo_path]

    def sync_repo(self, repo_path: str, push: bool = True, pull: bool = True,
                  auto_commit: bool = True, commit_message: str = None) -> Dict:
        """Sync a repository with remote"""
        result = {
            "repo_path": repo_path,
            "success": True,
            "actions": [],
            "errors": []
        }

        self._emit("on_sync_start", repo_path)

        try:
            # Get current status
            status = self.git.get_status(repo_path)

            # Pull first (if enabled and no local changes that might conflict)
            if pull and status["clean"]:
                success, msg = self.git.pull(repo_path)
                if success:
                    result["actions"].append(f"Pulled: {msg}")
                else:
                    result["errors"].append(f"Pull failed: {msg}")

            # Auto-commit if there are changes
            if auto_commit and not status["clean"]:
                message = commit_message or f"Auto-sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                success, msg = self.git.commit(repo_path, message)
                if success:
                    result["actions"].append(f"Committed: {msg}")
                else:
                    result["errors"].append(f"Commit failed: {msg}")

            # Push if enabled and we have commits to push
            if push:
                status = self.git.get_status(repo_path)
                if status["ahead"] > 0:
                    success, msg = self.git.push(repo_path)
                    if success:
                        result["actions"].append(f"Pushed {status['ahead']} commits")
                    else:
                        result["errors"].append(f"Push failed: {msg}")

            self.last_sync[repo_path] = datetime.now()
            result["success"] = len(result["errors"]) == 0

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))

        self._emit("on_sync_complete", repo_path, result)
        return result

    def sync_all(self, repos: List[str] = None) -> List[Dict]:
        """Sync all watched repositories or specified list"""
        repos_to_sync = repos or list(self.watchers.keys())
        results = []

        for repo_path in repos_to_sync:
            result = self.sync_repo(repo_path)
            results.append(result)

        return results

    def _auto_sync_loop(self):
        """Background sync loop"""
        while self.running:
            if self.auto_sync_enabled:
                # Process sync queue
                while self.sync_queue:
                    item = self.sync_queue.pop(0)
                    repo_path = item["repo_path"]

                    # Check if we synced recently
                    last = self.last_sync.get(repo_path)
                    if last and (datetime.now() - last).seconds < 60:
                        continue  # Too soon, skip

                    self.sync_repo(repo_path)

                # Periodic sync
                for repo_path in list(self.watchers.keys()):
                    last = self.last_sync.get(repo_path)
                    if not last or (datetime.now() - last).seconds >= self.sync_interval:
                        self.sync_repo(repo_path)

            time.sleep(10)  # Check every 10 seconds

    def start_auto_sync(self, interval: int = 300):
        """Start automatic syncing"""
        self.sync_interval = interval
        self.auto_sync_enabled = True

        if not self.running:
            self.running = True
            self.sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
            self.sync_thread.start()

    def stop_auto_sync(self):
        """Stop automatic syncing"""
        self.auto_sync_enabled = False

    def stop(self):
        """Stop everything"""
        self.running = False
        self.auto_sync_enabled = False

        # Stop all watchers
        for repo_path in list(self.watchers.keys()):
            self.unwatch_repo(repo_path)

        if self.sync_thread:
            self.sync_thread.join(timeout=5)

    def get_sync_status(self, repo_path: str) -> Dict:
        """Get sync status for a repo"""
        status = self.git.get_status(repo_path)
        last = self.last_sync.get(repo_path)

        return {
            "repo_path": repo_path,
            "is_watching": repo_path in self.watchers,
            "last_sync": last.isoformat() if last else None,
            "pending_changes": not status["clean"],
            "ahead": status["ahead"],
            "behind": status["behind"],
            "branch": status["branch"]
        }


if __name__ == "__main__":
    # Test
    engine = SyncEngine()
    print("Sync engine ready")
