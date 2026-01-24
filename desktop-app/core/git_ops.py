"""
Git Operations - Core Git functionality
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime


class GitOps:
    """Handle all Git operations"""

    def __init__(self):
        self.last_error = None

    def run_git(self, args: List[str], cwd: str = None, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run a git command and return success, stdout, stderr"""
        try:
            cmd = ["git"] + args
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def clone(self, url: str, dest_path: str, branch: str = None,
              depth: int = None, progress_callback=None) -> Tuple[bool, str]:
        """Clone a repository"""
        args = ["clone"]

        if branch:
            args.extend(["--branch", branch])
        if depth:
            args.extend(["--depth", str(depth)])

        args.extend(["--progress", url, dest_path])

        # For progress, we need to handle stderr streaming
        try:
            process = subprocess.Popen(
                ["git"] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Read stderr for progress
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                if line and progress_callback:
                    progress_callback(line.strip())

            stdout, stderr = process.communicate()
            success = process.returncode == 0

            if success:
                return True, f"Cloned to {dest_path}"
            else:
                return False, stderr

        except Exception as e:
            return False, str(e)

    def pull(self, repo_path: str, remote: str = "origin", branch: str = None) -> Tuple[bool, str]:
        """Pull changes from remote"""
        args = ["pull", remote]
        if branch:
            args.append(branch)

        success, stdout, stderr = self.run_git(args, cwd=repo_path)

        if success:
            if "Already up to date" in stdout:
                return True, "Already up to date"
            return True, stdout
        else:
            return False, stderr or stdout

    def push(self, repo_path: str, remote: str = "origin", branch: str = None,
             force: bool = False, set_upstream: bool = False) -> Tuple[bool, str]:
        """Push changes to remote"""
        args = ["push"]

        if set_upstream:
            args.append("-u")
        if force:
            args.append("--force")

        args.append(remote)
        if branch:
            args.append(branch)

        success, stdout, stderr = self.run_git(args, cwd=repo_path, timeout=600)

        if success:
            return True, "Push successful"
        else:
            return False, stderr or stdout

    def fetch(self, repo_path: str, remote: str = "origin", prune: bool = True) -> Tuple[bool, str]:
        """Fetch changes from remote"""
        args = ["fetch", remote]
        if prune:
            args.append("--prune")

        success, stdout, stderr = self.run_git(args, cwd=repo_path)
        return success, stderr or stdout

    def commit(self, repo_path: str, message: str, add_all: bool = True) -> Tuple[bool, str]:
        """Create a commit"""
        if add_all:
            success, _, stderr = self.run_git(["add", "-A"], cwd=repo_path)
            if not success:
                return False, f"Failed to add files: {stderr}"

        success, stdout, stderr = self.run_git(["commit", "-m", message], cwd=repo_path)

        if success:
            return True, "Commit created"
        elif "nothing to commit" in (stdout + stderr):
            return True, "Nothing to commit"
        else:
            return False, stderr or stdout

    def get_status(self, repo_path: str) -> Dict:
        """Get repository status"""
        status = {
            "clean": True,
            "staged": [],
            "modified": [],
            "untracked": [],
            "deleted": [],
            "ahead": 0,
            "behind": 0,
            "branch": "unknown",
            "remote_branch": None
        }

        # Get branch info
        success, stdout, _ = self.run_git(["branch", "--show-current"], cwd=repo_path)
        if success:
            status["branch"] = stdout.strip()

        # Get status
        success, stdout, _ = self.run_git(["status", "--porcelain", "-b"], cwd=repo_path)
        if success:
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.startswith("##"):
                    # Parse branch info
                    if "[ahead" in line:
                        import re
                        match = re.search(r'\[ahead (\d+)', line)
                        if match:
                            status["ahead"] = int(match.group(1))
                    if "behind" in line:
                        import re
                        match = re.search(r'behind (\d+)', line)
                        if match:
                            status["behind"] = int(match.group(1))
                elif line:
                    code = line[:2]
                    filename = line[3:]

                    if code[0] in 'MADRCU':
                        status["staged"].append(filename)
                    if code[1] == 'M':
                        status["modified"].append(filename)
                    elif code[1] == 'D':
                        status["deleted"].append(filename)
                    elif code == '??':
                        status["untracked"].append(filename)

            status["clean"] = not (status["staged"] or status["modified"] or
                                   status["untracked"] or status["deleted"])

        return status

    def get_branches(self, repo_path: str, remote: bool = False) -> List[Dict]:
        """Get list of branches"""
        args = ["branch", "-v"]
        if remote:
            args.append("-r")

        success, stdout, _ = self.run_git(args, cwd=repo_path)
        branches = []

        if success:
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                is_current = line.startswith('*')
                line = line.lstrip('* ')
                parts = line.split()
                if len(parts) >= 2:
                    branches.append({
                        "name": parts[0],
                        "sha": parts[1][:8],
                        "current": is_current
                    })

        return branches

    def checkout(self, repo_path: str, branch: str, create: bool = False) -> Tuple[bool, str]:
        """Checkout a branch"""
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(branch)

        success, stdout, stderr = self.run_git(args, cwd=repo_path)
        return success, stderr or stdout

    def get_log(self, repo_path: str, limit: int = 20) -> List[Dict]:
        """Get commit log"""
        success, stdout, _ = self.run_git(
            ["log", f"-{limit}", "--format=%H|%h|%s|%an|%ai"],
            cwd=repo_path
        )

        commits = []
        if success:
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        "hash": parts[0],
                        "short_hash": parts[1],
                        "message": parts[2],
                        "author": parts[3],
                        "date": parts[4]
                    })

        return commits

    def get_diff(self, repo_path: str, staged: bool = False, file: str = None) -> str:
        """Get diff"""
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file:
            args.append(file)

        success, stdout, _ = self.run_git(args, cwd=repo_path)
        return stdout if success else ""

    def stash(self, repo_path: str, message: str = None) -> Tuple[bool, str]:
        """Stash changes"""
        args = ["stash", "push"]
        if message:
            args.extend(["-m", message])

        success, stdout, stderr = self.run_git(args, cwd=repo_path)
        return success, stderr or stdout

    def stash_pop(self, repo_path: str) -> Tuple[bool, str]:
        """Pop stash"""
        success, stdout, stderr = self.run_git(["stash", "pop"], cwd=repo_path)
        return success, stderr or stdout

    def init_lfs(self, repo_path: str) -> Tuple[bool, str]:
        """Initialize Git LFS"""
        success, stdout, stderr = self.run_git(["lfs", "install"], cwd=repo_path)
        return success, stderr or stdout

    def lfs_track(self, repo_path: str, pattern: str) -> Tuple[bool, str]:
        """Track files with LFS"""
        success, stdout, stderr = self.run_git(["lfs", "track", pattern], cwd=repo_path)
        return success, stderr or stdout

    def lfs_migrate(self, repo_path: str, include_patterns: List[str]) -> Tuple[bool, str]:
        """Migrate files to LFS"""
        patterns = ",".join(include_patterns)
        success, stdout, stderr = self.run_git(
            ["lfs", "migrate", "import", f"--include={patterns}"],
            cwd=repo_path,
            timeout=1800  # 30 min timeout for large migrations
        )
        return success, stderr or stdout

    def reset_hard(self, repo_path: str, ref: str = "HEAD") -> Tuple[bool, str]:
        """Hard reset to ref"""
        success, stdout, stderr = self.run_git(["reset", "--hard", ref], cwd=repo_path)
        return success, stderr or stdout

    def clean(self, repo_path: str, directories: bool = True) -> Tuple[bool, str]:
        """Clean untracked files"""
        args = ["clean", "-f"]
        if directories:
            args.append("-d")

        success, stdout, stderr = self.run_git(args, cwd=repo_path)
        return success, stderr or stdout

    def remote_url(self, repo_path: str, remote: str = "origin") -> Optional[str]:
        """Get remote URL"""
        success, stdout, _ = self.run_git(["remote", "get-url", remote], cwd=repo_path)
        return stdout.strip() if success else None

    def set_remote_url(self, repo_path: str, url: str, remote: str = "origin") -> Tuple[bool, str]:
        """Set remote URL"""
        success, stdout, stderr = self.run_git(["remote", "set-url", remote, url], cwd=repo_path)
        return success, stderr or stdout


if __name__ == "__main__":
    # Test
    git = GitOps()
    print("Testing GitOps...")
