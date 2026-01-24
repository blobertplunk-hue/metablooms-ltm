"""
Repository Scanner - Auto-detect Git repositories on local machine
"""

import os
import subprocess
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from datetime import datetime


class RepoScanner:
    """Scans local filesystem for Git repositories"""

    # Common locations to search for repos
    DEFAULT_SEARCH_PATHS = [
        Path.home() / "Documents",
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Projects",
        Path.home() / "repos",
        Path.home() / "git",
        Path.home() / "GitHub",
        Path.home() / "code",
        Path.home() / "dev",
        Path.home() / "src",
    ]

    # Folders to skip (speeds up scanning)
    SKIP_FOLDERS = {
        'node_modules', '.git', '__pycache__', 'venv', '.venv',
        'env', '.env', 'vendor', 'packages', '.cache', 'cache',
        'dist', 'build', 'target', 'bin', 'obj', '.idea', '.vscode',
        'AppData', 'Application Data', 'Program Files', 'Program Files (x86)',
        'Windows', 'ProgramData', '$Recycle.Bin', 'System Volume Information'
    }

    def __init__(self):
        self.found_repos: List[Dict] = []
        self.scan_in_progress = False
        self.scan_progress = 0
        self.scan_total = 0

    def get_repo_info(self, repo_path: Path) -> Optional[Dict]:
        """Get detailed information about a Git repository"""
        try:
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return None

            info = {
                "path": str(repo_path),
                "name": repo_path.name,
                "git_dir": str(git_dir),
                "discovered_at": datetime.now().isoformat(),
            }

            # Get current branch
            try:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                info["current_branch"] = result.stdout.strip() or "HEAD detached"
            except:
                info["current_branch"] = "unknown"

            # Get remote URL
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                remote_url = result.stdout.strip()
                info["remote_url"] = remote_url

                # Parse GitHub info from URL
                if "github.com" in remote_url:
                    info["is_github"] = True
                    # Extract owner/repo from URL
                    if remote_url.startswith("https://"):
                        parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")
                    elif remote_url.startswith("git@"):
                        parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
                    else:
                        parts = []

                    if len(parts) >= 2:
                        info["github_owner"] = parts[0]
                        info["github_repo"] = parts[1]
                else:
                    info["is_github"] = False
            except:
                info["remote_url"] = None
                info["is_github"] = False

            # Get last commit info
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%H|%s|%ai"],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout.strip():
                    parts = result.stdout.strip().split("|")
                    if len(parts) >= 3:
                        info["last_commit_hash"] = parts[0][:8]
                        info["last_commit_message"] = parts[1][:50]
                        info["last_commit_date"] = parts[2]
            except:
                pass

            # Check sync status (ahead/behind)
            try:
                result = subprocess.run(
                    ["git", "status", "-sb"],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                status = result.stdout.strip()
                info["has_uncommitted"] = bool(result.stdout.count('\n') > 0)

                if "[ahead" in status:
                    info["sync_status"] = "ahead"
                elif "[behind" in status:
                    info["sync_status"] = "behind"
                elif "[ahead" in status and "behind" in status:
                    info["sync_status"] = "diverged"
                else:
                    info["sync_status"] = "synced"
            except:
                info["sync_status"] = "unknown"
                info["has_uncommitted"] = False

            # Check if LFS is enabled
            try:
                lfs_path = repo_path / ".gitattributes"
                info["has_lfs"] = lfs_path.exists() and "filter=lfs" in lfs_path.read_text()
            except:
                info["has_lfs"] = False

            # Get repo size (approximate)
            try:
                total_size = sum(
                    f.stat().st_size for f in repo_path.rglob('*') if f.is_file()
                )
                info["size_bytes"] = total_size
                info["size_mb"] = round(total_size / (1024 * 1024), 2)
            except:
                info["size_bytes"] = 0
                info["size_mb"] = 0

            return info

        except Exception as e:
            return None

    def scan_directory(self, path: Path, max_depth: int = 5, current_depth: int = 0) -> List[Path]:
        """Recursively scan a directory for Git repositories"""
        repos = []

        if current_depth > max_depth:
            return repos

        try:
            # Check if this directory is a git repo
            git_dir = path / ".git"
            if git_dir.exists() and git_dir.is_dir():
                repos.append(path)
                # Don't scan inside git repos (submodules handled separately)
                return repos

            # Scan subdirectories
            for item in path.iterdir():
                if item.is_dir() and item.name not in self.SKIP_FOLDERS:
                    try:
                        repos.extend(self.scan_directory(item, max_depth, current_depth + 1))
                    except PermissionError:
                        pass

        except PermissionError:
            pass
        except Exception:
            pass

        return repos

    def scan_all(self, additional_paths: List[str] = None, callback=None) -> List[Dict]:
        """Scan all default locations plus any additional paths"""
        self.scan_in_progress = True
        self.found_repos = []

        # Build search paths
        search_paths = []
        for p in self.DEFAULT_SEARCH_PATHS:
            if p.exists():
                search_paths.append(p)

        if additional_paths:
            for p in additional_paths:
                path = Path(p)
                if path.exists():
                    search_paths.append(path)

        self.scan_total = len(search_paths)
        self.scan_progress = 0

        all_repo_paths = []

        # Scan each path
        for i, search_path in enumerate(search_paths):
            self.scan_progress = i + 1
            if callback:
                callback(f"Scanning {search_path}...", self.scan_progress, self.scan_total)

            repo_paths = self.scan_directory(search_path)
            all_repo_paths.extend(repo_paths)

        # Remove duplicates
        unique_paths = list(set(all_repo_paths))

        # Get info for each repo (parallel for speed)
        if callback:
            callback(f"Getting info for {len(unique_paths)} repositories...", 0, len(unique_paths))

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.get_repo_info, p): p for p in unique_paths}

            for i, future in enumerate(as_completed(futures)):
                info = future.result()
                if info:
                    self.found_repos.append(info)
                if callback:
                    callback(f"Processing repos...", i + 1, len(unique_paths))

        # Sort by last activity
        self.found_repos.sort(key=lambda x: x.get("last_commit_date", ""), reverse=True)

        self.scan_in_progress = False
        return self.found_repos

    def quick_scan(self, paths: List[str]) -> List[Dict]:
        """Quick scan of specific paths only"""
        repos = []
        for path_str in paths:
            path = Path(path_str)
            if path.exists():
                info = self.get_repo_info(path)
                if info:
                    repos.append(info)
        return repos

    def find_github_repos(self) -> List[Dict]:
        """Filter found repos to only GitHub repos"""
        return [r for r in self.found_repos if r.get("is_github")]

    def find_metablooms_repos(self) -> List[Dict]:
        """Filter found repos to MetaBlooms-related repos"""
        return [r for r in self.found_repos if "metablooms" in r.get("name", "").lower()]

    def save_cache(self, cache_path: str):
        """Save found repos to cache file"""
        with open(cache_path, 'w') as f:
            json.dump({
                "scanned_at": datetime.now().isoformat(),
                "repos": self.found_repos
            }, f, indent=2)

    def load_cache(self, cache_path: str) -> bool:
        """Load repos from cache file"""
        try:
            with open(cache_path) as f:
                data = json.load(f)
                self.found_repos = data.get("repos", [])
                return True
        except:
            return False


if __name__ == "__main__":
    # Test the scanner
    scanner = RepoScanner()

    def progress_callback(msg, current, total):
        print(f"[{current}/{total}] {msg}")

    repos = scanner.scan_all(callback=progress_callback)

    print(f"\nFound {len(repos)} repositories:")
    for repo in repos[:10]:  # Show first 10
        print(f"  - {repo['name']} ({repo['path']})")
        print(f"    Branch: {repo['current_branch']}, Status: {repo['sync_status']}")
