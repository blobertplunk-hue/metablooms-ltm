"""
GitHub API Integration - List and manage GitHub repositories
"""

import json
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import os


class GitHubAPI:
    """Interface with GitHub API to list repos, check status, etc."""

    API_BASE = "https://api.github.com"

    def __init__(self, token: str = None):
        self.token = token
        self.username = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def set_token(self, token: str):
        """Set the GitHub personal access token"""
        self.token = token

    def _make_request(self, endpoint: str, method: str = "GET", data: dict = None) -> Tuple[Optional[dict], Optional[str]]:
        """Make an authenticated request to GitHub API"""
        url = f"{self.API_BASE}{endpoint}"

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MetaBlooms-Sync"
        }

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        try:
            if data:
                data_bytes = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)

            with urllib.request.urlopen(req, timeout=30) as response:
                # Track rate limits
                self.rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                self.rate_limit_reset = response.headers.get('X-RateLimit-Reset')

                return json.loads(response.read().decode('utf-8')), None

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            return None, f"HTTP {e.code}: {error_body}"
        except urllib.error.URLError as e:
            return None, f"URL Error: {e.reason}"
        except Exception as e:
            return None, str(e)

    def get_token_from_gh_cli(self) -> Optional[str]:
        """Try to get token from GitHub CLI if installed"""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                token = result.stdout.strip()
                if token:
                    self.token = token
                    return token
        except:
            pass
        return None

    def get_token_from_git_credential(self) -> Optional[str]:
        """Try to get token from Git credential manager"""
        try:
            result = subprocess.run(
                ["git", "credential", "fill"],
                input="protocol=https\nhost=github.com\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('password='):
                        token = line.split('=', 1)[1]
                        self.token = token
                        return token
        except:
            pass
        return None

    def auto_authenticate(self) -> bool:
        """Try to automatically find GitHub credentials"""
        # Try gh CLI first
        if self.get_token_from_gh_cli():
            return self.verify_token()

        # Try git credential manager
        if self.get_token_from_git_credential():
            return self.verify_token()

        return False

    def verify_token(self) -> bool:
        """Verify the token works and get username"""
        if not self.token:
            return False

        data, error = self._make_request("/user")
        if data:
            self.username = data.get("login")
            return True
        return False

    def get_user_repos(self, include_private: bool = True, include_forks: bool = False) -> Tuple[List[Dict], Optional[str]]:
        """Get all repositories for the authenticated user"""
        if not self.token:
            return [], "No authentication token set"

        all_repos = []
        page = 1

        while True:
            endpoint = f"/user/repos?per_page=100&page={page}&sort=updated"
            if not include_private:
                endpoint += "&visibility=public"

            data, error = self._make_request(endpoint)
            if error:
                return all_repos, error

            if not data:
                break

            for repo in data:
                # Skip forks if not wanted
                if not include_forks and repo.get("fork"):
                    continue

                repo_info = {
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description") or "",
                    "html_url": repo["html_url"],
                    "clone_url": repo["clone_url"],
                    "ssh_url": repo["ssh_url"],
                    "private": repo["private"],
                    "fork": repo.get("fork", False),
                    "default_branch": repo.get("default_branch", "main"),
                    "size_kb": repo.get("size", 0),
                    "size_mb": round(repo.get("size", 0) / 1024, 2),
                    "language": repo.get("language"),
                    "topics": repo.get("topics", []),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "pushed_at": repo.get("pushed_at"),
                    "stargazers_count": repo.get("stargazers_count", 0),
                    "open_issues_count": repo.get("open_issues_count", 0),
                    "has_issues": repo.get("has_issues", False),
                    "has_wiki": repo.get("has_wiki", False),
                    "archived": repo.get("archived", False),
                    "owner": repo["owner"]["login"],
                    "is_metablooms": "metablooms" in repo["name"].lower(),
                }
                all_repos.append(repo_info)

            # Check if there are more pages
            if len(data) < 100:
                break
            page += 1

        return all_repos, None

    def get_repo_branches(self, owner: str, repo: str) -> Tuple[List[Dict], Optional[str]]:
        """Get all branches for a repository"""
        data, error = self._make_request(f"/repos/{owner}/{repo}/branches")
        if error:
            return [], error

        branches = []
        for branch in data:
            branches.append({
                "name": branch["name"],
                "sha": branch["commit"]["sha"][:8],
                "protected": branch.get("protected", False)
            })
        return branches, None

    def get_repo_commits(self, owner: str, repo: str, branch: str = None, limit: int = 10) -> Tuple[List[Dict], Optional[str]]:
        """Get recent commits for a repository"""
        endpoint = f"/repos/{owner}/{repo}/commits?per_page={limit}"
        if branch:
            endpoint += f"&sha={branch}"

        data, error = self._make_request(endpoint)
        if error:
            return [], error

        commits = []
        for commit in data:
            commits.append({
                "sha": commit["sha"][:8],
                "message": commit["commit"]["message"].split('\n')[0][:80],
                "author": commit["commit"]["author"]["name"],
                "date": commit["commit"]["author"]["date"],
                "url": commit["html_url"]
            })
        return commits, None

    def check_repo_exists(self, owner: str, repo: str) -> bool:
        """Check if a repository exists"""
        data, error = self._make_request(f"/repos/{owner}/{repo}")
        return data is not None

    def get_latest_release(self, owner: str, repo: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Get the latest release for a repository"""
        data, error = self._make_request(f"/repos/{owner}/{repo}/releases/latest")
        if error:
            return None, error

        return {
            "tag": data.get("tag_name"),
            "name": data.get("name"),
            "body": data.get("body"),
            "published_at": data.get("published_at"),
            "assets": [
                {
                    "name": a["name"],
                    "size": a["size"],
                    "download_url": a["browser_download_url"]
                }
                for a in data.get("assets", [])
            ]
        }, None

    def compare_commits(self, owner: str, repo: str, base: str, head: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Compare two commits/branches"""
        data, error = self._make_request(f"/repos/{owner}/{repo}/compare/{base}...{head}")
        if error:
            return None, error

        return {
            "ahead_by": data.get("ahead_by", 0),
            "behind_by": data.get("behind_by", 0),
            "status": data.get("status"),  # ahead, behind, identical, diverged
            "total_commits": data.get("total_commits", 0),
            "commits": [
                {
                    "sha": c["sha"][:8],
                    "message": c["commit"]["message"].split('\n')[0][:50]
                }
                for c in data.get("commits", [])[:5]
            ]
        }, None

    def create_repo(self, name: str, description: str = "", private: bool = True) -> Tuple[Optional[Dict], Optional[str]]:
        """Create a new repository"""
        data, error = self._make_request("/user/repos", method="POST", data={
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True
        })

        if error:
            return None, error

        return {
            "name": data["name"],
            "full_name": data["full_name"],
            "clone_url": data["clone_url"],
            "html_url": data["html_url"]
        }, None

    def find_uncloned_repos(self, local_repos: List[Dict]) -> List[Dict]:
        """Find GitHub repos that aren't cloned locally"""
        remote_repos, error = self.get_user_repos()
        if error:
            return []

        # Get set of remote URLs from local repos
        local_remotes = set()
        for repo in local_repos:
            if repo.get("remote_url"):
                # Normalize URL
                url = repo["remote_url"].lower()
                url = url.replace(".git", "").replace("git@github.com:", "https://github.com/")
                local_remotes.add(url)

        # Find remote repos not in local
        uncloned = []
        for repo in remote_repos:
            clone_url = repo["clone_url"].lower().replace(".git", "")
            if clone_url not in local_remotes:
                uncloned.append(repo)

        return uncloned

    def get_rate_limit_info(self) -> Dict:
        """Get current rate limit status"""
        data, error = self._make_request("/rate_limit")
        if data:
            core = data.get("resources", {}).get("core", {})
            return {
                "limit": core.get("limit", 0),
                "remaining": core.get("remaining", 0),
                "reset": datetime.fromtimestamp(core.get("reset", 0)).isoformat()
            }
        return {}


if __name__ == "__main__":
    # Test the GitHub API
    api = GitHubAPI()

    print("Attempting auto-authentication...")
    if api.auto_authenticate():
        print(f"Authenticated as: {api.username}")

        repos, error = api.get_user_repos()
        if error:
            print(f"Error: {error}")
        else:
            print(f"\nFound {len(repos)} repositories:")
            for repo in repos[:10]:
                print(f"  - {repo['full_name']} ({'private' if repo['private'] else 'public'})")
    else:
        print("Could not auto-authenticate. Please set a token manually.")
