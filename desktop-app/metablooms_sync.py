#!/usr/bin/env python3
"""
MetaBlooms Sync - Ultimate GitHub Desktop App
Auto-detect repos, sync with GitHub, dark mode, system tray
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import json
import threading
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.repo_scanner import RepoScanner
from core.github_api import GitHubAPI
from core.git_ops import GitOps
from core.sync_engine import SyncEngine
from core.updater import Updater

# Try to import tray support
try:
    from utils.tray import SystemTray, HAS_TRAY
except ImportError:
    HAS_TRAY = False
    SystemTray = None

# ============== DARK THEME ==============
COLORS = {
    "bg": "#1a1a1a",
    "bg_secondary": "#252526",
    "bg_tertiary": "#2d2d2d",
    "bg_hover": "#3c3c3c",
    "fg": "#cccccc",
    "fg_dim": "#808080",
    "accent": "#0078d4",
    "accent_hover": "#1084d8",
    "success": "#4ec9b0",
    "warning": "#cca700",
    "error": "#f14c4c",
    "border": "#3c3c3c"
}


class MetaBloomsSync:
    """Main application class"""

    def __init__(self, root):
        self.root = root
        self.root.title("MetaBlooms Sync")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLORS["bg"])

        # Core components
        self.scanner = RepoScanner()
        self.github = GitHubAPI()
        self.git = GitOps()
        self.sync_engine = SyncEngine()
        self.updater = Updater()

        # State
        self.local_repos = []
        self.remote_repos = []
        self.selected_repo = None
        self.config = self.load_config()

        # System tray
        self.tray = None
        if HAS_TRAY:
            self.setup_tray()

        # Apply theme and create UI
        self.apply_theme()
        self.create_ui()

        # Check for updates on startup
        self.root.after(1000, self.check_updates_async)

        # Auto-authenticate GitHub
        self.root.after(500, self.auto_authenticate)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def apply_theme(self):
        """Apply dark theme"""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure all widgets
        style.configure(".", background=COLORS["bg"], foreground=COLORS["fg"],
                       fieldbackground=COLORS["bg_secondary"], bordercolor=COLORS["border"])

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["fg"])
        style.configure("TLabelframe", background=COLORS["bg"])
        style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["accent"])

        style.configure("TButton", background=COLORS["bg_tertiary"], foreground=COLORS["fg"], padding=(12, 6))
        style.map("TButton", background=[("active", COLORS["accent"])], foreground=[("active", "#ffffff")])

        style.configure("Accent.TButton", background=COLORS["accent"], foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", COLORS["accent_hover"])])

        style.configure("TEntry", fieldbackground=COLORS["bg_secondary"], foreground=COLORS["fg"])
        style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["fg"])
        style.configure("TRadiobutton", background=COLORS["bg"], foreground=COLORS["fg"])

        style.configure("TNotebook", background=COLORS["bg"], bordercolor=COLORS["border"])
        style.configure("TNotebook.Tab", background=COLORS["bg_secondary"], foreground=COLORS["fg"], padding=(16, 8))
        style.map("TNotebook.Tab", background=[("selected", COLORS["bg_tertiary"])],
                 foreground=[("selected", COLORS["accent"])])

        style.configure("Treeview", background=COLORS["bg_secondary"], foreground=COLORS["fg"],
                       fieldbackground=COLORS["bg_secondary"], borderwidth=0)
        style.configure("Treeview.Heading", background=COLORS["bg_tertiary"], foreground=COLORS["fg"])
        style.map("Treeview", background=[("selected", COLORS["accent"])])

    def create_ui(self):
        """Create the main UI"""
        # Main container
        main = ttk.Frame(self.root, padding=0)
        main.pack(fill=tk.BOTH, expand=True)

        # === LEFT SIDEBAR ===
        sidebar = ttk.Frame(main, width=280)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        sidebar.pack_propagate(False)

        self.create_sidebar(sidebar)

        # === MAIN CONTENT ===
        content = ttk.Frame(main)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(1, 0))

        self.create_content(content)

    def create_sidebar(self, parent):
        """Create left sidebar"""
        # Header
        header = tk.Frame(parent, bg=COLORS["bg_secondary"], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="MetaBlooms Sync", font=("Segoe UI", 14, "bold"),
                bg=COLORS["bg_secondary"], fg=COLORS["accent"]).pack(pady=15)

        # Repo list section
        repo_frame = ttk.Frame(parent)
        repo_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tabs for Local / GitHub
        self.repo_tabs = ttk.Notebook(repo_frame)
        self.repo_tabs.pack(fill=tk.BOTH, expand=True)

        # Local repos tab
        local_frame = ttk.Frame(self.repo_tabs)
        self.repo_tabs.add(local_frame, text="  Local  ")

        btn_frame = ttk.Frame(local_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="Scan PC", command=self.scan_local_repos).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Add", command=self.add_local_repo).pack(side=tk.LEFT, padx=2)

        self.local_tree = ttk.Treeview(local_frame, columns=("status",), show="tree headings", height=10)
        self.local_tree.heading("#0", text="Repository")
        self.local_tree.heading("status", text="Status")
        self.local_tree.column("#0", width=150)
        self.local_tree.column("status", width=60)
        self.local_tree.pack(fill=tk.BOTH, expand=True)
        self.local_tree.bind("<<TreeviewSelect>>", self.on_repo_select)

        # GitHub repos tab
        github_frame = ttk.Frame(self.repo_tabs)
        self.repo_tabs.add(github_frame, text="  GitHub  ")

        btn_frame2 = ttk.Frame(github_frame)
        btn_frame2.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame2, text="Refresh", command=self.fetch_github_repos).pack(side=tk.LEFT, padx=2)

        self.github_tree = ttk.Treeview(github_frame, columns=("status",), show="tree headings", height=10)
        self.github_tree.heading("#0", text="Repository")
        self.github_tree.heading("status", text="")
        self.github_tree.column("#0", width=170)
        self.github_tree.column("status", width=40)
        self.github_tree.pack(fill=tk.BOTH, expand=True)
        self.github_tree.bind("<<TreeviewSelect>>", self.on_github_repo_select)

        # Quick actions
        actions = ttk.LabelFrame(parent, text="Quick Actions", padding=8)
        actions.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(actions, text="Sync All", style="Accent.TButton",
                  command=self.sync_all).pack(fill=tk.X, pady=2)
        ttk.Button(actions, text="Check for Updates",
                  command=self.check_updates).pack(fill=tk.X, pady=2)

        # Status
        self.status_label = tk.Label(parent, text="Ready", bg=COLORS["bg_secondary"],
                                     fg=COLORS["fg_dim"], anchor="w", padx=10, pady=8)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def create_content(self, parent):
        """Create main content area"""
        # Top toolbar
        toolbar = tk.Frame(parent, bg=COLORS["bg_secondary"], height=50)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        self.repo_name_label = tk.Label(toolbar, text="Select a repository",
                                        font=("Segoe UI", 12, "bold"),
                                        bg=COLORS["bg_secondary"], fg=COLORS["fg"])
        self.repo_name_label.pack(side=tk.LEFT, padx=15, pady=12)

        # Action buttons
        btn_frame = tk.Frame(toolbar, bg=COLORS["bg_secondary"])
        btn_frame.pack(side=tk.RIGHT, padx=10)

        self.push_btn = ttk.Button(btn_frame, text="Push", command=self.push_repo)
        self.push_btn.pack(side=tk.LEFT, padx=2)
        self.pull_btn = ttk.Button(btn_frame, text="Pull", command=self.pull_repo)
        self.pull_btn.pack(side=tk.LEFT, padx=2)
        self.sync_btn = ttk.Button(btn_frame, text="Sync", style="Accent.TButton", command=self.sync_repo)
        self.sync_btn.pack(side=tk.LEFT, padx=2)

        # Content tabs
        self.content_tabs = ttk.Notebook(parent)
        self.content_tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Changes tab
        changes_frame = ttk.Frame(self.content_tabs)
        self.content_tabs.add(changes_frame, text="  Changes  ")
        self.create_changes_tab(changes_frame)

        # History tab
        history_frame = ttk.Frame(self.content_tabs)
        self.content_tabs.add(history_frame, text="  History  ")
        self.create_history_tab(history_frame)

        # Upload tab
        upload_frame = ttk.Frame(self.content_tabs)
        self.content_tabs.add(upload_frame, text="  Upload Files  ")
        self.create_upload_tab(upload_frame)

        # Settings tab
        settings_frame = ttk.Frame(self.content_tabs)
        self.content_tabs.add(settings_frame, text="  Settings  ")
        self.create_settings_tab(settings_frame)

        # Log output
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, font=("Consolas", 9),
                                                  bg=COLORS["bg_secondary"], fg=COLORS["fg"],
                                                  insertbackground=COLORS["fg"], relief=tk.FLAT)
        self.log_text.pack(fill=tk.X)

        self.log_text.tag_configure("success", foreground=COLORS["success"])
        self.log_text.tag_configure("error", foreground=COLORS["error"])
        self.log_text.tag_configure("warning", foreground=COLORS["warning"])

    def create_changes_tab(self, parent):
        """Create changes/staging tab"""
        # Staged files
        staged_frame = ttk.LabelFrame(parent, text="Staged Changes", padding=5)
        staged_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.staged_list = tk.Listbox(staged_frame, height=5, bg=COLORS["bg_secondary"],
                                      fg=COLORS["fg"], selectbackground=COLORS["accent"])
        self.staged_list.pack(fill=tk.BOTH, expand=True)

        # Unstaged files
        unstaged_frame = ttk.LabelFrame(parent, text="Unstaged Changes", padding=5)
        unstaged_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.unstaged_list = tk.Listbox(unstaged_frame, height=5, bg=COLORS["bg_secondary"],
                                        fg=COLORS["fg"], selectbackground=COLORS["accent"])
        self.unstaged_list.pack(fill=tk.BOTH, expand=True)

        # Commit section
        commit_frame = ttk.LabelFrame(parent, text="Commit", padding=5)
        commit_frame.pack(fill=tk.X)

        self.commit_msg = ttk.Entry(commit_frame, width=60)
        self.commit_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.commit_msg.insert(0, "Update files")

        ttk.Button(commit_frame, text="Commit & Push", style="Accent.TButton",
                  command=self.commit_and_push).pack(side=tk.RIGHT)

    def create_history_tab(self, parent):
        """Create commit history tab"""
        self.history_tree = ttk.Treeview(parent, columns=("message", "author", "date"),
                                         show="headings", height=15)
        self.history_tree.heading("message", text="Message")
        self.history_tree.heading("author", text="Author")
        self.history_tree.heading("date", text="Date")
        self.history_tree.column("message", width=400)
        self.history_tree.column("author", width=120)
        self.history_tree.column("date", width=150)
        self.history_tree.pack(fill=tk.BOTH, expand=True)

    def create_upload_tab(self, parent):
        """Create file upload tab"""
        info = ttk.Label(parent, text="Drag files here or use the buttons below to upload to the selected repository")
        info.pack(pady=10)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Add Files...", command=self.add_files_to_upload).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Add Folder...", command=self.add_folder_to_upload).pack(side=tk.LEFT, padx=5)

        # File list
        self.upload_list = tk.Listbox(parent, height=10, bg=COLORS["bg_secondary"],
                                      fg=COLORS["fg"], selectbackground=COLORS["accent"])
        self.upload_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.files_to_upload = []

        # Upload button
        ttk.Button(parent, text="Upload All Files", style="Accent.TButton",
                  command=self.upload_files).pack(pady=10)

    def create_settings_tab(self, parent):
        """Create settings tab"""
        # GitHub auth
        auth_frame = ttk.LabelFrame(parent, text="GitHub Authentication", padding=10)
        auth_frame.pack(fill=tk.X, pady=5)

        self.auth_status = ttk.Label(auth_frame, text="Not authenticated")
        self.auth_status.pack(anchor="w")

        ttk.Button(auth_frame, text="Authenticate with GitHub CLI", command=self.authenticate_github).pack(pady=5)

        # Auto-sync settings
        sync_frame = ttk.LabelFrame(parent, text="Auto-Sync", padding=10)
        sync_frame.pack(fill=tk.X, pady=5)

        self.auto_sync_var = tk.BooleanVar(value=self.config.get("auto_sync", False))
        ttk.Checkbutton(sync_frame, text="Enable auto-sync (check for changes every 5 minutes)",
                       variable=self.auto_sync_var, command=self.toggle_auto_sync).pack(anchor="w")

        # Scan paths
        paths_frame = ttk.LabelFrame(parent, text="Scan Locations", padding=10)
        paths_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(paths_frame, text="Additional paths to scan for Git repositories:").pack(anchor="w")

        self.scan_paths_list = tk.Listbox(paths_frame, height=5, bg=COLORS["bg_secondary"],
                                          fg=COLORS["fg"], selectbackground=COLORS["accent"])
        self.scan_paths_list.pack(fill=tk.BOTH, expand=True, pady=5)

        for path in self.config.get("extra_scan_paths", []):
            self.scan_paths_list.insert(tk.END, path)

        btn_frame = ttk.Frame(paths_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Add Path", command=self.add_scan_path).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self.remove_scan_path).pack(side=tk.LEFT, padx=2)

        # Save button
        ttk.Button(parent, text="Save Settings", command=self.save_config).pack(pady=10)

    # ============== ACTIONS ==============

    def log(self, message, level="info"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"success": "[OK] ", "error": "[ERROR] ", "warning": "[WARN] ", "info": ""}
        self.log_text.insert(tk.END, f"[{timestamp}] {prefix.get(level, '')}{message}\n", level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def set_status(self, text):
        """Update status bar"""
        self.status_label.config(text=text)
        self.root.update_idletasks()

    def scan_local_repos(self):
        """Scan for local Git repositories"""
        def do_scan():
            self.set_status("Scanning for repositories...")
            self.log("Scanning PC for Git repositories...")

            extra_paths = self.config.get("extra_scan_paths", [])
            repos = self.scanner.scan_all(additional_paths=extra_paths)

            self.local_repos = repos
            self.root.after(0, self.update_local_repo_list)
            self.log(f"Found {len(repos)} repositories", "success")
            self.set_status(f"Found {len(repos)} repositories")

        threading.Thread(target=do_scan, daemon=True).start()

    def update_local_repo_list(self):
        """Update the local repo tree"""
        self.local_tree.delete(*self.local_tree.get_children())

        for repo in self.local_repos:
            status_icon = {"synced": "✓", "ahead": "↑", "behind": "↓", "diverged": "⇅"}.get(
                repo.get("sync_status", "unknown"), "?"
            )
            self.local_tree.insert("", "end", text=repo["name"], values=(status_icon,),
                                   tags=(repo["path"],))

    def add_local_repo(self):
        """Add a local repository manually"""
        path = filedialog.askdirectory(title="Select Git Repository")
        if path:
            info = self.scanner.get_repo_info(Path(path))
            if info:
                self.local_repos.append(info)
                self.update_local_repo_list()
                self.log(f"Added: {info['name']}", "success")
            else:
                messagebox.showerror("Error", "Not a valid Git repository")

    def fetch_github_repos(self):
        """Fetch repositories from GitHub"""
        def do_fetch():
            self.set_status("Fetching GitHub repositories...")
            self.log("Connecting to GitHub...")

            repos, error = self.github.get_user_repos()
            if error:
                self.log(f"GitHub error: {error}", "error")
                self.set_status("GitHub error")
                return

            self.remote_repos = repos
            self.root.after(0, self.update_github_repo_list)
            self.log(f"Found {len(repos)} GitHub repositories", "success")
            self.set_status(f"Found {len(repos)} GitHub repositories")

        threading.Thread(target=do_fetch, daemon=True).start()

    def update_github_repo_list(self):
        """Update the GitHub repo tree"""
        self.github_tree.delete(*self.github_tree.get_children())

        # Check which are cloned locally
        local_remotes = {r.get("remote_url", "").lower() for r in self.local_repos}

        for repo in self.remote_repos:
            clone_url = repo["clone_url"].lower()
            is_cloned = any(clone_url.replace(".git", "") in lr.replace(".git", "") for lr in local_remotes)
            status = "✓" if is_cloned else "↓"
            self.github_tree.insert("", "end", text=repo["name"], values=(status,),
                                   tags=(repo["clone_url"],))

    def on_repo_select(self, event):
        """Handle local repo selection"""
        selection = self.local_tree.selection()
        if selection:
            item = self.local_tree.item(selection[0])
            repo_path = item["tags"][0] if item["tags"] else None

            for repo in self.local_repos:
                if repo["path"] == repo_path:
                    self.selected_repo = repo
                    self.update_repo_details()
                    break

    def on_github_repo_select(self, event):
        """Handle GitHub repo selection"""
        selection = self.github_tree.selection()
        if selection:
            item = self.github_tree.item(selection[0])
            clone_url = item["tags"][0] if item["tags"] else None

            for repo in self.remote_repos:
                if repo["clone_url"] == clone_url:
                    # Check if cloned
                    is_cloned = False
                    for local in self.local_repos:
                        if clone_url.lower().replace(".git", "") in local.get("remote_url", "").lower():
                            self.selected_repo = local
                            is_cloned = True
                            break

                    if not is_cloned:
                        # Offer to clone
                        if messagebox.askyesno("Clone Repository",
                                              f"'{repo['name']}' is not cloned locally.\n\nClone it now?"):
                            self.clone_repo(repo)
                    else:
                        self.update_repo_details()
                    break

    def update_repo_details(self):
        """Update UI with selected repo details"""
        if not self.selected_repo:
            return

        repo = self.selected_repo
        self.repo_name_label.config(text=repo["name"])

        # Get fresh status
        status = self.git.get_status(repo["path"])

        # Update staged/unstaged lists
        self.staged_list.delete(0, tk.END)
        for f in status.get("staged", []):
            self.staged_list.insert(tk.END, f"  {f}")

        self.unstaged_list.delete(0, tk.END)
        for f in status.get("modified", []):
            self.unstaged_list.insert(tk.END, f"M {f}")
        for f in status.get("untracked", []):
            self.unstaged_list.insert(tk.END, f"? {f}")
        for f in status.get("deleted", []):
            self.unstaged_list.insert(tk.END, f"D {f}")

        # Update history
        self.history_tree.delete(*self.history_tree.get_children())
        commits = self.git.get_log(repo["path"], limit=20)
        for c in commits:
            self.history_tree.insert("", "end", values=(c["message"][:60], c["author"], c["date"][:16]))

    def clone_repo(self, repo):
        """Clone a GitHub repository"""
        # Ask for destination
        dest = filedialog.askdirectory(title="Select folder to clone into")
        if not dest:
            return

        clone_path = os.path.join(dest, repo["name"])

        def do_clone():
            self.set_status(f"Cloning {repo['name']}...")
            self.log(f"Cloning {repo['full_name']}...")

            def progress(msg):
                self.log(msg)

            success, message = self.git.clone(repo["clone_url"], clone_path, progress_callback=progress)

            if success:
                self.log(f"Cloned successfully to {clone_path}", "success")
                # Add to local repos
                info = self.scanner.get_repo_info(Path(clone_path))
                if info:
                    self.local_repos.append(info)
                    self.root.after(0, self.update_local_repo_list)
            else:
                self.log(f"Clone failed: {message}", "error")

            self.set_status("Ready")

        threading.Thread(target=do_clone, daemon=True).start()

    def push_repo(self):
        """Push current repo"""
        if not self.selected_repo:
            return

        def do_push():
            self.set_status("Pushing...")
            success, msg = self.git.push(self.selected_repo["path"])
            if success:
                self.log(f"Push successful", "success")
            else:
                self.log(f"Push failed: {msg}", "error")
            self.set_status("Ready")
            self.root.after(0, self.update_repo_details)

        threading.Thread(target=do_push, daemon=True).start()

    def pull_repo(self):
        """Pull current repo"""
        if not self.selected_repo:
            return

        def do_pull():
            self.set_status("Pulling...")
            success, msg = self.git.pull(self.selected_repo["path"])
            if success:
                self.log(f"Pull: {msg}", "success")
            else:
                self.log(f"Pull failed: {msg}", "error")
            self.set_status("Ready")
            self.root.after(0, self.update_repo_details)

        threading.Thread(target=do_pull, daemon=True).start()

    def sync_repo(self):
        """Sync current repo (pull then push)"""
        if not self.selected_repo:
            return

        def do_sync():
            self.set_status("Syncing...")
            result = self.sync_engine.sync_repo(self.selected_repo["path"])

            for action in result.get("actions", []):
                self.log(action, "success")
            for error in result.get("errors", []):
                self.log(error, "error")

            self.set_status("Ready")
            self.root.after(0, self.update_repo_details)

        threading.Thread(target=do_sync, daemon=True).start()

    def sync_all(self):
        """Sync all repos"""
        def do_sync():
            self.set_status("Syncing all repositories...")
            self.log("Starting sync for all repositories...")

            for repo in self.local_repos:
                self.log(f"Syncing {repo['name']}...")
                result = self.sync_engine.sync_repo(repo["path"])

                if result["success"]:
                    self.log(f"  {repo['name']}: Synced", "success")
                else:
                    for e in result.get("errors", []):
                        self.log(f"  {repo['name']}: {e}", "error")

            self.log("Sync complete", "success")
            self.set_status("Ready")
            self.root.after(0, self.update_local_repo_list)

        threading.Thread(target=do_sync, daemon=True).start()

    def commit_and_push(self):
        """Commit and push changes"""
        if not self.selected_repo:
            return

        message = self.commit_msg.get().strip()
        if not message:
            messagebox.showwarning("Warning", "Please enter a commit message")
            return

        def do_commit():
            self.set_status("Committing...")

            # Add all
            success, msg = self.git.commit(self.selected_repo["path"], message, add_all=True)
            if not success and "nothing to commit" not in msg:
                self.log(f"Commit failed: {msg}", "error")
                self.set_status("Ready")
                return

            self.log("Committed changes", "success")

            # Push
            self.set_status("Pushing...")
            success, msg = self.git.push(self.selected_repo["path"])
            if success:
                self.log("Pushed to remote", "success")
            else:
                self.log(f"Push failed: {msg}", "error")

            self.set_status("Ready")
            self.root.after(0, self.update_repo_details)

        threading.Thread(target=do_commit, daemon=True).start()

    def add_files_to_upload(self):
        """Add files to upload list"""
        files = filedialog.askopenfilenames(title="Select files to upload")
        for f in files:
            if f not in self.files_to_upload:
                self.files_to_upload.append(f)
                self.upload_list.insert(tk.END, os.path.basename(f))

    def add_folder_to_upload(self):
        """Add folder contents to upload list"""
        folder = filedialog.askdirectory(title="Select folder to upload")
        if folder:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    full_path = os.path.join(root, f)
                    if full_path not in self.files_to_upload:
                        self.files_to_upload.append(full_path)
                        self.upload_list.insert(tk.END, os.path.relpath(full_path, folder))

    def upload_files(self):
        """Upload files to selected repo"""
        if not self.selected_repo:
            messagebox.showwarning("Warning", "Please select a repository first")
            return

        if not self.files_to_upload:
            messagebox.showwarning("Warning", "No files to upload")
            return

        def do_upload():
            import shutil
            self.set_status("Uploading files...")
            repo_path = self.selected_repo["path"]

            for f in self.files_to_upload:
                dest = os.path.join(repo_path, os.path.basename(f))
                self.log(f"Copying {os.path.basename(f)}...")
                shutil.copy2(f, dest)

            # Commit and push
            success, msg = self.git.commit(repo_path, f"Upload {len(self.files_to_upload)} files")
            if success:
                self.log("Files committed", "success")
                success, msg = self.git.push(repo_path)
                if success:
                    self.log("Files uploaded successfully", "success")
                else:
                    self.log(f"Push failed: {msg}", "error")
            else:
                self.log(f"Commit failed: {msg}", "error")

            self.files_to_upload = []
            self.root.after(0, lambda: self.upload_list.delete(0, tk.END))
            self.set_status("Ready")

        threading.Thread(target=do_upload, daemon=True).start()

    def auto_authenticate(self):
        """Try to auto-authenticate with GitHub"""
        if self.github.auto_authenticate():
            self.auth_status.config(text=f"Authenticated as: {self.github.username}")
            self.log(f"GitHub: Authenticated as {self.github.username}", "success")
            self.fetch_github_repos()
        else:
            self.auth_status.config(text="Not authenticated - click to authenticate")
            self.log("GitHub: Not authenticated", "warning")

    def authenticate_github(self):
        """Authenticate with GitHub"""
        if self.github.auto_authenticate():
            self.auth_status.config(text=f"Authenticated as: {self.github.username}")
            self.log(f"Authenticated as {self.github.username}", "success")
            self.fetch_github_repos()
        else:
            messagebox.showinfo("GitHub Authentication",
                              "Please install GitHub CLI and run 'gh auth login' in terminal")

    def toggle_auto_sync(self):
        """Toggle auto-sync"""
        if self.auto_sync_var.get():
            self.sync_engine.start_auto_sync(300)
            self.log("Auto-sync enabled", "success")
        else:
            self.sync_engine.stop_auto_sync()
            self.log("Auto-sync disabled")

    def add_scan_path(self):
        """Add scan path"""
        path = filedialog.askdirectory(title="Select folder to scan")
        if path:
            self.scan_paths_list.insert(tk.END, path)

    def remove_scan_path(self):
        """Remove scan path"""
        selection = self.scan_paths_list.curselection()
        if selection:
            self.scan_paths_list.delete(selection[0])

    def check_updates(self):
        """Check for updates"""
        def do_check():
            self.set_status("Checking for updates...")
            has_update, message, sha = self.updater.check_for_updates()

            if has_update:
                self.log(f"Update available: {message}", "success")
                if messagebox.askyesno("Update Available", f"{message}\n\nDownload and install now?"):
                    self.install_update()
            else:
                self.log(message)
                messagebox.showinfo("Updates", message)

            self.set_status("Ready")

        threading.Thread(target=do_check, daemon=True).start()

    def check_updates_async(self):
        """Check for updates in background"""
        def do_check():
            has_update, message, sha = self.updater.check_for_updates()
            if has_update:
                self.log(f"Update available: {message}", "warning")

        threading.Thread(target=do_check, daemon=True).start()

    def install_update(self):
        """Install update"""
        def do_update():
            def progress(msg, current, total):
                self.log(f"{msg} ({current}/{total})")
                self.set_status(msg)

            success, message = self.updater.update(progress_callback=progress)

            if success:
                self.log(message, "success")
                messagebox.showinfo("Update Complete", message)
            else:
                self.log(f"Update failed: {message}", "error")
                messagebox.showerror("Update Failed", message)

            self.set_status("Ready")

        threading.Thread(target=do_update, daemon=True).start()

    def load_config(self):
        """Load config"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            with open(config_path) as f:
                return json.load(f)
        except:
            return {}

    def save_config(self):
        """Save config"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")

        # Get scan paths
        paths = [self.scan_paths_list.get(i) for i in range(self.scan_paths_list.size())]

        self.config = {
            "auto_sync": self.auto_sync_var.get(),
            "extra_scan_paths": paths
        }

        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

        self.log("Settings saved", "success")
        messagebox.showinfo("Saved", "Settings saved!")

    def setup_tray(self):
        """Setup system tray"""
        self.tray = SystemTray("MetaBlooms Sync")
        self.tray.on_show_window = self.show_window
        self.tray.on_sync_all = self.sync_all
        self.tray.on_quit = self.quit_app
        self.tray.start()

    def show_window(self):
        """Show main window"""
        self.root.deiconify()
        self.root.lift()

    def on_close(self):
        """Handle window close"""
        if HAS_TRAY and self.tray:
            self.root.withdraw()  # Minimize to tray
        else:
            self.quit_app()

    def quit_app(self):
        """Quit application"""
        self.sync_engine.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MetaBloomsSync(root)
    root.mainloop()


if __name__ == "__main__":
    main()
