#!/usr/bin/env python3
"""
MetaBlooms GitHub Uploader
A desktop app to easily upload files, deltas, and OS zips to GitHub.
Automatically handles Git LFS for large files.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import shutil
import threading
import json
from datetime import datetime
from pathlib import Path
import hashlib

# Dark mode colors
COLORS = {
    "bg": "#1e1e1e",
    "bg_light": "#2d2d2d",
    "bg_lighter": "#3c3c3c",
    "fg": "#d4d4d4",
    "fg_dim": "#808080",
    "accent": "#569cd6",
    "success": "#4ec9b0",
    "error": "#f14c4c",
    "warning": "#cca700",
    "border": "#404040"
}


class MetaBloomsUploader:
    # Files larger than this (in bytes) will use Git LFS
    LFS_THRESHOLD = 50 * 1024 * 1024  # 50 MB

    def __init__(self, root):
        self.root = root
        self.root.title("MetaBlooms GitHub Uploader")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)
        self.root.configure(bg=COLORS["bg"])

        # Apply dark theme
        self.apply_dark_theme()

        # Repository paths
        self.repo_paths = {
            "ltm": "",
            "os": ""
        }

        self.create_widgets()
        self.load_config()

    def apply_dark_theme(self):
        """Apply dark mode theme to ttk widgets"""
        style = ttk.Style()

        # Use clam theme as base (works better for customization)
        style.theme_use('clam')

        # Configure main styles
        style.configure(".",
            background=COLORS["bg"],
            foreground=COLORS["fg"],
            fieldbackground=COLORS["bg_light"],
            troughcolor=COLORS["bg_light"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["bg_lighter"],
            darkcolor=COLORS["bg"]
        )

        # Frame
        style.configure("TFrame", background=COLORS["bg"])

        # Label
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["fg"])
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=COLORS["accent"])
        style.configure("Heading.TLabel", font=("Segoe UI", 11, "bold"))

        # LabelFrame
        style.configure("TLabelframe", background=COLORS["bg"], foreground=COLORS["fg"])
        style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["accent"])

        # Button
        style.configure("TButton",
            background=COLORS["bg_lighter"],
            foreground=COLORS["fg"],
            padding=(10, 5)
        )
        style.map("TButton",
            background=[("active", COLORS["accent"]), ("pressed", COLORS["bg_light"])],
            foreground=[("active", "#ffffff")]
        )

        # Entry
        style.configure("TEntry",
            fieldbackground=COLORS["bg_light"],
            foreground=COLORS["fg"],
            insertcolor=COLORS["fg"]
        )

        # Radiobutton
        style.configure("TRadiobutton",
            background=COLORS["bg"],
            foreground=COLORS["fg"]
        )
        style.map("TRadiobutton",
            background=[("active", COLORS["bg"])]
        )

        # Checkbutton
        style.configure("TCheckbutton",
            background=COLORS["bg"],
            foreground=COLORS["fg"]
        )
        style.map("TCheckbutton",
            background=[("active", COLORS["bg"])]
        )

        # Notebook (tabs)
        style.configure("TNotebook",
            background=COLORS["bg"],
            bordercolor=COLORS["border"]
        )
        style.configure("TNotebook.Tab",
            background=COLORS["bg_light"],
            foreground=COLORS["fg"],
            padding=(15, 8)
        )
        style.map("TNotebook.Tab",
            background=[("selected", COLORS["bg_lighter"])],
            foreground=[("selected", COLORS["accent"])]
        )

    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(main_frame, text="MetaBlooms GitHub Uploader", style="Title.TLabel")
        title.pack(pady=(0, 10))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook, padding="10")
        self.files_tab = ttk.Frame(self.notebook, padding="10")
        self.deltas_tab = ttk.Frame(self.notebook, padding="10")
        self.os_tab = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.setup_tab, text="  Setup  ")
        self.notebook.add(self.files_tab, text="  Upload Files  ")
        self.notebook.add(self.deltas_tab, text="  Upload Deltas  ")
        self.notebook.add(self.os_tab, text="  Upload OS Zip  ")

        self.create_setup_tab()
        self.create_files_tab()
        self.create_deltas_tab()
        self.create_os_tab()

        # Log output area
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=("Consolas", 9),
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            selectbackground=COLORS["accent"],
            selectforeground="#ffffff",
            relief=tk.FLAT,
            borderwidth=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure log text tags for colored output
        self.log_text.tag_configure("success", foreground=COLORS["success"])
        self.log_text.tag_configure("error", foreground=COLORS["error"])
        self.log_text.tag_configure("warning", foreground=COLORS["warning"])
        self.log_text.tag_configure("info", foreground=COLORS["fg"])

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            main_frame,
            textvariable=self.status_var,
            bg=COLORS["bg_lighter"],
            fg=COLORS["fg"],
            anchor=tk.W,
            padx=10,
            pady=5
        )
        status_bar.pack(fill=tk.X, pady=(5, 0))

    def create_dark_listbox(self, parent, **kwargs):
        """Create a dark-themed listbox"""
        listbox = tk.Listbox(
            parent,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            selectbackground=COLORS["accent"],
            selectforeground="#ffffff",
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            relief=tk.FLAT,
            borderwidth=1,
            **kwargs
        )
        return listbox

    def create_setup_tab(self):
        """Create the setup/configuration tab"""
        # LTM Repository
        ltm_frame = ttk.LabelFrame(self.setup_tab, text="MetaBlooms LTM Repository", padding="10")
        ltm_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(ltm_frame, text="Path:").grid(row=0, column=0, sticky=tk.W)
        self.ltm_path_var = tk.StringVar()
        ltm_entry = ttk.Entry(ltm_frame, textvariable=self.ltm_path_var, width=60)
        ltm_entry.grid(row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(ltm_frame, text="Browse...", command=lambda: self.browse_repo("ltm")).grid(row=0, column=2)

        ltm_frame.columnconfigure(1, weight=1)

        # OS Repository
        os_frame = ttk.LabelFrame(self.setup_tab, text="MetaBlooms OS Repository", padding="10")
        os_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(os_frame, text="Path:").grid(row=0, column=0, sticky=tk.W)
        self.os_path_var = tk.StringVar()
        os_entry = ttk.Entry(os_frame, textvariable=self.os_path_var, width=60)
        os_entry.grid(row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(os_frame, text="Browse...", command=lambda: self.browse_repo("os")).grid(row=0, column=2)

        os_frame.columnconfigure(1, weight=1)

        # Git LFS Setup
        lfs_frame = ttk.LabelFrame(self.setup_tab, text="Git LFS Configuration", padding="10")
        lfs_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(lfs_frame, text="Large files (>50MB) are automatically tracked with Git LFS").pack(anchor=tk.W)
        ttk.Button(lfs_frame, text="Initialize Git LFS in Repositories", command=self.init_git_lfs).pack(pady=5)

        # Save button
        ttk.Button(self.setup_tab, text="Save Configuration", command=self.save_config).pack(pady=10)

    def create_files_tab(self):
        """Create the general files upload tab"""
        # Target repository selection
        repo_frame = ttk.LabelFrame(self.files_tab, text="Target Repository", padding="10")
        repo_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_repo_var = tk.StringVar(value="ltm")
        ttk.Radiobutton(repo_frame, text="LTM (Long-Term Memory)", variable=self.file_repo_var, value="ltm").pack(anchor=tk.W)
        ttk.Radiobutton(repo_frame, text="OS (Operating System)", variable=self.file_repo_var, value="os").pack(anchor=tk.W)

        # File selection
        file_frame = ttk.LabelFrame(self.files_tab, text="Select Files", padding="10")
        file_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Add Files...", command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Add Folder...", command=self.add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear List", command=self.clear_file_list).pack(side=tk.LEFT, padx=2)

        # File list (dark themed)
        self.file_listbox = self.create_dark_listbox(file_frame, height=8, selectmode=tk.EXTENDED)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        # Destination path
        dest_frame = ttk.Frame(file_frame)
        dest_frame.pack(fill=tk.X)
        ttk.Label(dest_frame, text="Destination subfolder (optional):").pack(side=tk.LEFT)
        self.dest_path_var = tk.StringVar()
        ttk.Entry(dest_frame, textvariable=self.dest_path_var, width=40).pack(side=tk.LEFT, padx=5)

        # Commit message
        msg_frame = ttk.LabelFrame(self.files_tab, text="Commit Message", padding="10")
        msg_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_commit_msg = tk.StringVar(value="Add files via MetaBlooms Uploader")
        ttk.Entry(msg_frame, textvariable=self.file_commit_msg, width=70).pack(fill=tk.X)

        # Upload button
        ttk.Button(self.files_tab, text="Upload Files to GitHub", command=self.upload_files).pack(pady=10)

        self.selected_files = []

    def create_deltas_tab(self):
        """Create the deltas upload tab"""
        info_frame = ttk.LabelFrame(self.deltas_tab, text="Delta Upload Info", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="Deltas are stored in: deltas/YYYY-MM/").pack(anchor=tk.W)
        ttk.Label(info_frame, text="They represent incremental changes to the MetaBlooms system.").pack(anchor=tk.W)

        # Delta file selection
        delta_frame = ttk.LabelFrame(self.deltas_tab, text="Select Delta Files", padding="10")
        delta_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(delta_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Add Delta Files...", command=self.add_delta_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_delta_list).pack(side=tk.LEFT, padx=2)

        self.delta_listbox = self.create_dark_listbox(delta_frame, height=8, selectmode=tk.EXTENDED)
        self.delta_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        # Auto-organize option
        self.auto_organize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(delta_frame, text="Auto-organize by date (deltas/YYYY-MM/)",
                       variable=self.auto_organize_var).pack(anchor=tk.W)

        # Commit message
        msg_frame = ttk.LabelFrame(self.deltas_tab, text="Commit Message", padding="10")
        msg_frame.pack(fill=tk.X, pady=(0, 10))

        self.delta_commit_msg = tk.StringVar(value="Add delta files")
        ttk.Entry(msg_frame, textvariable=self.delta_commit_msg, width=70).pack(fill=tk.X)

        # Upload button
        ttk.Button(self.deltas_tab, text="Upload Deltas to GitHub", command=self.upload_deltas).pack(pady=10)

        self.selected_deltas = []

    def create_os_tab(self):
        """Create the OS zip upload tab"""
        info_frame = ttk.LabelFrame(self.os_tab, text="OS Zip Upload Info", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="Upload complete MetaBlooms OS zip files.").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Large files will automatically use Git LFS.").pack(anchor=tk.W)

        # Repository selection for OS zip
        repo_frame = ttk.LabelFrame(self.os_tab, text="Target Repository", padding="10")
        repo_frame.pack(fill=tk.X, pady=(0, 10))

        self.os_repo_var = tk.StringVar(value="ltm")
        ttk.Radiobutton(repo_frame, text="LTM Repository (recommended for canonical zips)",
                       variable=self.os_repo_var, value="ltm").pack(anchor=tk.W)
        ttk.Radiobutton(repo_frame, text="OS Repository",
                       variable=self.os_repo_var, value="os").pack(anchor=tk.W)

        # Zip file selection
        zip_frame = ttk.LabelFrame(self.os_tab, text="Select OS Zip File", padding="10")
        zip_frame.pack(fill=tk.X, pady=(0, 10))

        self.os_zip_var = tk.StringVar()
        entry_frame = ttk.Frame(zip_frame)
        entry_frame.pack(fill=tk.X)
        ttk.Entry(entry_frame, textvariable=self.os_zip_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(entry_frame, text="Browse...", command=self.browse_os_zip).pack(side=tk.LEFT, padx=5)

        # File info display
        self.zip_info_var = tk.StringVar(value="No file selected")
        ttk.Label(zip_frame, textvariable=self.zip_info_var).pack(anchor=tk.W, pady=5)

        # Update latest.json option
        self.update_latest_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(zip_frame, text="Update manifests/latest.json with new snapshot info",
                       variable=self.update_latest_var).pack(anchor=tk.W)

        # Commit message
        msg_frame = ttk.LabelFrame(self.os_tab, text="Commit Message", padding="10")
        msg_frame.pack(fill=tk.X, pady=(0, 10))

        self.os_commit_msg = tk.StringVar(value="Upload MetaBlooms OS canonical zip")
        ttk.Entry(msg_frame, textvariable=self.os_commit_msg, width=70).pack(fill=tk.X)

        # Upload button
        ttk.Button(self.os_tab, text="Upload OS Zip to GitHub", command=self.upload_os_zip).pack(pady=10)

    def log(self, message, level="info"):
        """Add a message to the log with color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"info": "", "success": "[OK] ", "error": "[ERROR] ", "warning": "[WARN] "}
        full_message = f"[{timestamp}] {prefix.get(level, '')}{message}\n"
        self.log_text.insert(tk.END, full_message, level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def normalize_path(self, path):
        """Normalize and validate a file path"""
        if not path:
            return None
        # Strip whitespace and quotes
        path = path.strip().strip('"').strip("'")
        # Convert to Path object and resolve
        try:
            normalized = str(Path(path).resolve())
            return normalized
        except Exception:
            return None

    def run_git_command(self, cmd, cwd=None):
        """Run a git command and return output"""
        try:
            # Normalize the working directory path
            if cwd:
                cwd = self.normalize_path(cwd)
                if not cwd or not os.path.isdir(cwd):
                    self.log(f"Invalid directory: {cwd}", "error")
                    return None, f"Invalid directory: {cwd}"

            # On Windows, use shell=True for git commands
            if os.name == 'nt':
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    shell=True
                )
            else:
                # On Unix, split the command
                import shlex
                result = subprocess.run(
                    shlex.split(cmd),
                    cwd=cwd,
                    capture_output=True,
                    text=True
                )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.log(f"Git error: {error_msg}", "error")
                return None, error_msg
            return result.stdout, None
        except Exception as e:
            self.log(f"Exception running git: {e}", "error")
            return None, str(e)

    def browse_repo(self, repo_type):
        """Browse for repository folder"""
        path = filedialog.askdirectory(title=f"Select MetaBlooms {repo_type.upper()} Repository")
        if path:
            path = self.normalize_path(path)
            # Verify it's a git repo
            git_dir = os.path.join(path, ".git")
            if os.path.exists(git_dir):
                if repo_type == "ltm":
                    self.ltm_path_var.set(path)
                else:
                    self.os_path_var.set(path)
                self.repo_paths[repo_type] = path
                self.log(f"Set {repo_type.upper()} repo path: {path}", "success")
            else:
                messagebox.showerror("Error", "Selected folder is not a Git repository.\nMake sure you select the folder containing .git")

    def init_git_lfs(self):
        """Initialize Git LFS in both repositories"""
        initialized = False
        for repo_type, path in self.repo_paths.items():
            path = self.normalize_path(path)
            if path and os.path.isdir(path):
                self.log(f"Initializing Git LFS in {repo_type.upper()} repo...")

                # Install LFS
                output, err = self.run_git_command("git lfs install", cwd=path)
                if err:
                    continue

                # Track common large file patterns
                patterns = ["*.zip", "*.bin", "*.exe", "*.dll", "*.so", "*.dylib"]
                for pattern in patterns:
                    self.run_git_command(f'git lfs track "{pattern}"', cwd=path)

                # Add .gitattributes
                self.run_git_command("git add .gitattributes", cwd=path)

                self.log(f"Git LFS initialized in {repo_type.upper()} repo", "success")
                initialized = True

        if initialized:
            messagebox.showinfo("Git LFS", "Git LFS has been initialized. Large files will be tracked automatically.")
        else:
            messagebox.showwarning("Git LFS", "No valid repositories configured. Please set repository paths first.")

    def save_config(self):
        """Save configuration to file"""
        ltm_path = self.normalize_path(self.ltm_path_var.get())
        os_path = self.normalize_path(self.os_path_var.get())

        config = {
            "ltm_path": ltm_path or "",
            "os_path": os_path or ""
        }

        # Update internal paths
        self.repo_paths["ltm"] = ltm_path or ""
        self.repo_paths["os"] = os_path or ""

        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploader_config.json")
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            self.log("Configuration saved", "success")
            messagebox.showinfo("Saved", "Configuration saved successfully!")
        except Exception as e:
            self.log(f"Failed to save config: {e}", "error")

    def load_config(self):
        """Load configuration from file"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploader_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = json.load(f)

                ltm_path = self.normalize_path(config.get("ltm_path", ""))
                os_path = self.normalize_path(config.get("os_path", ""))

                self.ltm_path_var.set(ltm_path or "")
                self.os_path_var.set(os_path or "")
                self.repo_paths["ltm"] = ltm_path or ""
                self.repo_paths["os"] = os_path or ""
                self.log("Configuration loaded", "info")
        except Exception as e:
            self.log(f"No config file found, using defaults", "info")

    def add_files(self):
        """Add files to the upload list"""
        files = filedialog.askopenfilenames(title="Select Files to Upload")
        for f in files:
            f = self.normalize_path(f)
            if f and f not in self.selected_files:
                self.selected_files.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))

    def add_folder(self):
        """Add all files from a folder"""
        folder = filedialog.askdirectory(title="Select Folder to Upload")
        if folder:
            folder = self.normalize_path(folder)
            for root, dirs, files in os.walk(folder):
                for f in files:
                    full_path = os.path.join(root, f)
                    if full_path not in self.selected_files:
                        self.selected_files.append(full_path)
                        rel_path = os.path.relpath(full_path, folder)
                        self.file_listbox.insert(tk.END, rel_path)

    def clear_file_list(self):
        """Clear the file list"""
        self.selected_files = []
        self.file_listbox.delete(0, tk.END)

    def add_delta_files(self):
        """Add delta files"""
        files = filedialog.askopenfilenames(
            title="Select Delta Files",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        for f in files:
            f = self.normalize_path(f)
            if f and f not in self.selected_deltas:
                self.selected_deltas.append(f)
                self.delta_listbox.insert(tk.END, os.path.basename(f))

    def clear_delta_list(self):
        """Clear delta list"""
        self.selected_deltas = []
        self.delta_listbox.delete(0, tk.END)

    def browse_os_zip(self):
        """Browse for OS zip file"""
        file = filedialog.askopenfilename(
            title="Select MetaBlooms OS Zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if file:
            file = self.normalize_path(file)
            self.os_zip_var.set(file)
            # Show file info
            try:
                size = os.path.getsize(file)
                size_mb = size / (1024 * 1024)
                lfs_note = " (will use Git LFS)" if size > self.LFS_THRESHOLD else ""
                self.zip_info_var.set(f"Size: {size_mb:.2f} MB{lfs_note}")
            except Exception as e:
                self.zip_info_var.set(f"Error reading file: {e}")

    def calculate_sha256(self, filepath):
        """Calculate SHA256 hash of a file"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def setup_lfs_for_file(self, repo_path, filename):
        """Setup LFS tracking for a specific file if it's large"""
        filepath = os.path.join(repo_path, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > self.LFS_THRESHOLD:
            # Get file extension
            ext = os.path.splitext(filename)[1]
            if ext:
                self.run_git_command(f'git lfs track "*{ext}"', cwd=repo_path)
                self.run_git_command("git add .gitattributes", cwd=repo_path)
                self.log(f"Tracking {ext} files with Git LFS", "info")

    def upload_files(self):
        """Upload selected files to GitHub"""
        repo_type = self.file_repo_var.get()
        repo_path = self.normalize_path(self.repo_paths.get(repo_type))

        if not repo_path or not os.path.isdir(repo_path):
            messagebox.showerror("Error", f"Please set a valid {repo_type.upper()} repository path in Setup tab")
            return

        if not self.selected_files:
            messagebox.showerror("Error", "No files selected")
            return

        def do_upload():
            try:
                self.status_var.set("Uploading files...")
                dest_subdir = self.dest_path_var.get().strip()

                for filepath in self.selected_files:
                    filename = os.path.basename(filepath)
                    if dest_subdir:
                        dest_path = os.path.join(repo_path, dest_subdir, filename)
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    else:
                        dest_path = os.path.join(repo_path, filename)

                    self.log(f"Copying {filename}...")
                    shutil.copy2(filepath, dest_path)

                    # Setup LFS if needed
                    self.setup_lfs_for_file(repo_path, os.path.relpath(dest_path, repo_path))

                # Git add, commit, push
                self.log("Adding files to git...")
                self.run_git_command("git add .", cwd=repo_path)

                commit_msg = self.file_commit_msg.get()
                self.log(f"Committing: {commit_msg}")
                self.run_git_command(f'git commit -m "{commit_msg}"', cwd=repo_path)

                self.log("Pushing to GitHub...")
                output, err = self.run_git_command("git push", cwd=repo_path)

                if err and "error" in err.lower():
                    self.log(f"Push failed: {err}", "error")
                    self.status_var.set("Upload failed")
                else:
                    self.log("Files uploaded successfully!", "success")
                    self.status_var.set("Upload complete!")
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Files uploaded to GitHub!"))

            except Exception as e:
                self.log(f"Upload failed: {e}", "error")
                self.status_var.set("Upload failed")

        threading.Thread(target=do_upload, daemon=True).start()

    def upload_deltas(self):
        """Upload delta files to GitHub"""
        repo_path = self.normalize_path(self.repo_paths.get("ltm"))

        if not repo_path or not os.path.isdir(repo_path):
            messagebox.showerror("Error", "Please set a valid LTM repository path in Setup tab")
            return

        if not self.selected_deltas:
            messagebox.showerror("Error", "No delta files selected")
            return

        def do_upload():
            try:
                self.status_var.set("Uploading deltas...")

                for filepath in self.selected_deltas:
                    filename = os.path.basename(filepath)

                    if self.auto_organize_var.get():
                        # Organize by current month
                        date_folder = datetime.now().strftime("%Y-%m")
                        dest_dir = os.path.join(repo_path, "deltas", date_folder)
                    else:
                        dest_dir = os.path.join(repo_path, "deltas")

                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, filename)

                    self.log(f"Copying delta: {filename}")
                    shutil.copy2(filepath, dest_path)

                # Git add, commit, push
                self.log("Adding deltas to git...")
                self.run_git_command("git add .", cwd=repo_path)

                commit_msg = self.delta_commit_msg.get()
                self.log(f"Committing: {commit_msg}")
                self.run_git_command(f'git commit -m "{commit_msg}"', cwd=repo_path)

                self.log("Pushing to GitHub...")
                output, err = self.run_git_command("git push", cwd=repo_path)

                if err and "error" in err.lower():
                    self.log(f"Push failed: {err}", "error")
                    self.status_var.set("Upload failed")
                else:
                    self.log("Deltas uploaded successfully!", "success")
                    self.status_var.set("Upload complete!")
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Deltas uploaded to GitHub!"))

            except Exception as e:
                self.log(f"Upload failed: {e}", "error")
                self.status_var.set("Upload failed")

        threading.Thread(target=do_upload, daemon=True).start()

    def upload_os_zip(self):
        """Upload OS zip file to GitHub"""
        repo_type = self.os_repo_var.get()
        repo_path = self.normalize_path(self.repo_paths.get(repo_type))
        zip_path = self.normalize_path(self.os_zip_var.get())

        if not repo_path or not os.path.isdir(repo_path):
            messagebox.showerror("Error", f"Please set a valid {repo_type.upper()} repository path in Setup tab")
            return

        if not zip_path or not os.path.isfile(zip_path):
            messagebox.showerror("Error", "Please select a valid OS zip file")
            return

        def do_upload():
            try:
                self.status_var.set("Uploading OS zip...")
                filename = os.path.basename(zip_path)
                dest_path = os.path.join(repo_path, filename)

                # Check if file needs LFS
                file_size = os.path.getsize(zip_path)
                if file_size > self.LFS_THRESHOLD:
                    self.log(f"Large file detected ({file_size / 1024 / 1024:.1f} MB), setting up Git LFS...")
                    self.run_git_command('git lfs track "*.zip"', cwd=repo_path)
                    self.run_git_command("git add .gitattributes", cwd=repo_path)

                self.log(f"Copying {filename}...")
                shutil.copy2(zip_path, dest_path)

                # Calculate SHA256 for manifest update
                if self.update_latest_var.get():
                    self.log("Calculating SHA256 hash...")
                    sha256 = self.calculate_sha256(dest_path)
                    self.log(f"SHA256: {sha256[:16]}...")

                    # Update latest.json
                    latest_path = os.path.join(repo_path, "manifests", "latest.json")
                    if os.path.exists(latest_path):
                        with open(latest_path) as f:
                            latest = json.load(f)
                    else:
                        os.makedirs(os.path.dirname(latest_path), exist_ok=True)
                        latest = {}

                    latest["snapshot"] = {
                        "file": filename,
                        "sha256": sha256,
                        "uploaded": datetime.now().isoformat(),
                        "size_bytes": file_size
                    }

                    with open(latest_path, "w") as f:
                        json.dump(latest, f, indent=2)
                    self.log("Updated manifests/latest.json", "success")

                # Git add, commit, push
                self.log("Adding files to git...")
                self.run_git_command("git add .", cwd=repo_path)

                commit_msg = self.os_commit_msg.get()
                self.log(f"Committing: {commit_msg}")
                self.run_git_command(f'git commit -m "{commit_msg}"', cwd=repo_path)

                self.log("Pushing to GitHub (this may take a while for large files)...")
                output, err = self.run_git_command("git push", cwd=repo_path)

                if err and "error" in err.lower():
                    # Check if it's an LFS issue
                    if "lfs" in err.lower() or "large" in err.lower():
                        self.log("Large file issue detected, attempting LFS migration...", "warning")
                        self.run_git_command(f'git lfs migrate import --include="{filename}"', cwd=repo_path)
                        self.run_git_command("git push --force", cwd=repo_path)
                    else:
                        self.log(f"Push failed: {err}", "error")
                        self.status_var.set("Upload failed")
                        return

                self.log("OS zip uploaded successfully!", "success")
                self.status_var.set("Upload complete!")
                self.root.after(0, lambda: messagebox.showinfo("Success", "OS zip uploaded to GitHub!"))

            except Exception as e:
                self.log(f"Upload failed: {e}", "error")
                self.status_var.set("Upload failed")

        threading.Thread(target=do_upload, daemon=True).start()


def main():
    root = tk.Tk()
    app = MetaBloomsUploader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
