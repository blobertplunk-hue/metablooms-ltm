# MetaBlooms GitHub Uploader

A desktop application to easily upload files, deltas, and OS zips to GitHub with automatic Git LFS support for large files.

## Features

- **Upload Files**: Upload any files to your MetaBlooms LTM or OS repository
- **Upload Deltas**: Upload delta files with automatic organization by date
- **Upload OS Zips**: Upload MetaBlooms OS canonical zips with automatic LFS handling
- **Git LFS Support**: Automatically handles large files (>50MB) using Git LFS
- **Manifest Updates**: Optionally updates `manifests/latest.json` with snapshot info

## Requirements

### 1. Python 3.8+
Download from: https://python.org

Make sure to check "Add Python to PATH" during installation.

### 2. Git
Download from: https://git-scm.com

### 3. Git LFS
Download from: https://git-lfs.github.com

After installing, run:
```bash
git lfs install
```

## Installation

1. **Clone or download this repository**

2. **No additional Python packages needed** - Uses built-in tkinter

3. **Run the application**:

   **Option A: Double-click** `MetaBlooms_Uploader.bat`

   **Option B: PowerShell** (shows more details):
   ```powershell
   .\MetaBlooms_Uploader.ps1
   ```

   **Option C: Direct Python**:
   ```bash
   python metablooms_uploader.py
   ```

## First-Time Setup

1. Launch the application
2. Go to the **Setup** tab
3. Set your repository paths:
   - **LTM Repository**: Path to your local `metablooms-ltm` clone
   - **OS Repository**: Path to your local `metablooms-os` clone
4. Click **Initialize Git LFS in Repositories**
5. Click **Save Configuration**

## Usage

### Uploading Files

1. Go to **Upload Files** tab
2. Select target repository (LTM or OS)
3. Click **Add Files** or **Add Folder**
4. Optionally set a destination subfolder
5. Enter a commit message
6. Click **Upload Files to GitHub**

### Uploading Deltas

1. Go to **Upload Deltas** tab
2. Click **Add Delta Files**
3. Enable "Auto-organize by date" to put files in `deltas/YYYY-MM/`
4. Enter a commit message
5. Click **Upload Deltas to GitHub**

### Uploading OS Zips

1. Go to **Upload OS Zip** tab
2. Select target repository
3. Click **Browse** and select your OS zip file
4. Enable "Update manifests/latest.json" to track the snapshot
5. Enter a commit message
6. Click **Upload OS Zip to GitHub**

## Troubleshooting

### "Large files detected" error on push
The app should handle this automatically, but if it fails:
```bash
git lfs migrate import --include="filename.zip"
git push --force
```

### "Python not found"
Make sure Python is installed and added to PATH. You may need to restart your terminal.

### "Permission denied" on push
Make sure you have:
1. Push access to the repository
2. Configured Git credentials (`git config --global credential.helper store`)

### Git LFS not working
```bash
git lfs install
git lfs track "*.zip"
git add .gitattributes
```

## Creating a Desktop Shortcut (Windows)

1. Right-click `MetaBlooms_Uploader.bat`
2. Select "Create shortcut"
3. Move the shortcut to your Desktop
4. (Optional) Right-click shortcut > Properties > Change Icon

## File Structure

```
desktop-app/
├── metablooms_uploader.py    # Main application
├── MetaBlooms_Uploader.bat   # Windows batch launcher
├── MetaBlooms_Uploader.ps1   # PowerShell launcher
├── uploader_config.json      # Saved configuration (created on first save)
└── README.md                 # This file
```

## Configuration File

The app saves your settings to `uploader_config.json`:
```json
{
  "ltm_path": "C:\\Users\\User\\repos\\metablooms-ltm",
  "os_path": "C:\\Users\\User\\repos\\metablooms-os"
}
```
