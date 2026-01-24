"""
Self-Updater - Update the app from GitHub
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Tuple, Optional, Dict
from datetime import datetime
import zipfile


class Updater:
    """Handle app self-updates from GitHub"""

    # Update source configuration
    GITHUB_REPO = "blobertplunk-hue/metablooms-ltm"
    BRANCH = "claude/github-upload-desktop-app-evDSa"  # Can be changed to main later
    APP_FOLDER = "desktop-app"

    VERSION_FILE = "version.json"

    def __init__(self, app_dir: str = None):
        self.app_dir = app_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.current_version = self._load_current_version()

    def _load_current_version(self) -> Dict:
        """Load current version info"""
        version_path = os.path.join(self.app_dir, self.VERSION_FILE)
        try:
            if os.path.exists(version_path):
                with open(version_path) as f:
                    return json.load(f)
        except:
            pass

        return {
            "version": "0.0.0",
            "build_date": None,
            "commit": None
        }

    def _save_version(self, version_info: Dict):
        """Save version info"""
        version_path = os.path.join(self.app_dir, self.VERSION_FILE)
        with open(version_path, 'w') as f:
            json.dump(version_info, f, indent=2)

    def get_latest_commit(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the latest commit SHA from GitHub"""
        url = f"https://api.github.com/repos/{self.GITHUB_REPO}/commits/{self.BRANCH}"

        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "MetaBlooms-Sync-Updater"
            })

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data["sha"], data["commit"]["message"].split('\n')[0]

        except Exception as e:
            return None, str(e)

    def check_for_updates(self) -> Tuple[bool, str, Optional[str]]:
        """Check if updates are available"""
        latest_sha, message = self.get_latest_commit()

        if not latest_sha:
            return False, f"Could not check for updates: {message}", None

        current_sha = self.current_version.get("commit")

        if current_sha == latest_sha:
            return False, "Already up to date", None

        if current_sha is None:
            return True, "Update available (first sync)", latest_sha

        return True, f"Update available: {message}", latest_sha

    def download_update(self, progress_callback=None) -> Tuple[bool, str]:
        """Download the latest version"""
        url = f"https://github.com/{self.GITHUB_REPO}/archive/refs/heads/{self.BRANCH}.zip"

        try:
            if progress_callback:
                progress_callback("Downloading update...", 0, 100)

            # Download to temp file
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "update.zip")

            # Download with progress
            req = urllib.request.Request(url, headers={"User-Agent": "MetaBlooms-Sync-Updater"})

            with urllib.request.urlopen(req, timeout=60) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                block_size = 8192

                with open(zip_path, 'wb') as f:
                    while True:
                        block = response.read(block_size)
                        if not block:
                            break
                        f.write(block)
                        downloaded += len(block)

                        if progress_callback and total_size:
                            percent = int((downloaded / total_size) * 100)
                            progress_callback(f"Downloading... {downloaded // 1024}KB", percent, 100)

            if progress_callback:
                progress_callback("Download complete", 100, 100)

            return True, zip_path

        except Exception as e:
            return False, str(e)

    def apply_update(self, zip_path: str, progress_callback=None) -> Tuple[bool, str]:
        """Apply the downloaded update"""
        try:
            if progress_callback:
                progress_callback("Extracting update...", 0, 100)

            temp_dir = os.path.dirname(zip_path)
            extract_dir = os.path.join(temp_dir, "extracted")

            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if progress_callback:
                progress_callback("Extracting...", 30, 100)

            # Find the desktop-app folder in extracted content
            extracted_contents = os.listdir(extract_dir)
            if not extracted_contents:
                return False, "Empty archive"

            # GitHub archives have a top-level folder like "repo-branch"
            top_folder = os.path.join(extract_dir, extracted_contents[0])
            source_app_dir = os.path.join(top_folder, self.APP_FOLDER)

            if not os.path.exists(source_app_dir):
                return False, f"Could not find {self.APP_FOLDER} in update"

            if progress_callback:
                progress_callback("Backing up current version...", 40, 100)

            # Backup current version
            backup_dir = os.path.join(temp_dir, "backup")
            if os.path.exists(self.app_dir):
                shutil.copytree(self.app_dir, backup_dir, dirs_exist_ok=True)

            if progress_callback:
                progress_callback("Installing update...", 60, 100)

            # Copy new files (preserve config)
            config_backup = None
            config_path = os.path.join(self.app_dir, "uploader_config.json")
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config_backup = f.read()

            # Copy all files from update
            for item in os.listdir(source_app_dir):
                src = os.path.join(source_app_dir, item)
                dst = os.path.join(self.app_dir, item)

                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            # Restore config
            if config_backup:
                with open(config_path, 'w') as f:
                    f.write(config_backup)

            if progress_callback:
                progress_callback("Finalizing...", 90, 100)

            # Update version info
            latest_sha, _ = self.get_latest_commit()
            self._save_version({
                "version": "1.0.0",
                "build_date": datetime.now().isoformat(),
                "commit": latest_sha,
                "updated_at": datetime.now().isoformat()
            })

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

            if progress_callback:
                progress_callback("Update complete!", 100, 100)

            return True, "Update installed successfully. Please restart the app."

        except Exception as e:
            return False, str(e)

    def update(self, progress_callback=None) -> Tuple[bool, str]:
        """Download and apply update"""
        # Check for updates
        has_update, message, new_sha = self.check_for_updates()
        if not has_update:
            return True, message

        # Download
        success, result = self.download_update(progress_callback)
        if not success:
            return False, f"Download failed: {result}"

        # Apply
        success, message = self.apply_update(result, progress_callback)
        return success, message

    def get_changelog(self, limit: int = 10) -> list:
        """Get recent commits as changelog"""
        url = f"https://api.github.com/repos/{self.GITHUB_REPO}/commits?sha={self.BRANCH}&per_page={limit}"

        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "MetaBlooms-Sync-Updater"
            })

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return [
                    {
                        "sha": c["sha"][:8],
                        "message": c["commit"]["message"].split('\n')[0],
                        "date": c["commit"]["author"]["date"],
                        "author": c["commit"]["author"]["name"]
                    }
                    for c in data
                ]

        except Exception as e:
            return []


def create_one_shot_installer() -> str:
    """Generate PowerShell one-shot install command"""
    return f'''
# MetaBlooms Sync - One-Shot Installer
$repo = "blobertplunk-hue/metablooms-ltm"
$branch = "claude/github-upload-desktop-app-evDSa"
$installDir = "$env:USERPROFILE\\MetaBlooms_Sync"

Write-Host "Installing MetaBlooms Sync..." -ForegroundColor Cyan

# Clone or update
if (Test-Path "$installDir\\.git") {{
    Write-Host "Updating existing installation..."
    git -C $installDir pull origin $branch
}} else {{
    Write-Host "Fresh install..."
    git clone --branch $branch --depth 1 "https://github.com/$repo.git" "$env:TEMP\\mb-temp"
    Move-Item "$env:TEMP\\mb-temp\\desktop-app" $installDir -Force
    Remove-Item "$env:TEMP\\mb-temp" -Recurse -Force
}}

Write-Host "Done! Run: $installDir\\MetaBlooms_Uploader.bat" -ForegroundColor Green
'''


if __name__ == "__main__":
    updater = Updater()

    print("Checking for updates...")
    has_update, message, sha = updater.check_for_updates()
    print(f"Update available: {has_update}")
    print(f"Message: {message}")

    if has_update:
        print("\nRecent changes:")
        for commit in updater.get_changelog(5):
            print(f"  [{commit['sha']}] {commit['message']}")
