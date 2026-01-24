# MetaBlooms OS Upload Script

## Purpose
PowerShell script to upload large MetaBlooms OS ZIP files to GitHub using Git LFS.

## Prerequisites

1. **Git for Windows** - [Download](https://git-scm.com/download/win)
2. **Git LFS** - [Download](https://git-lfs.github.com/)
3. **GitHub Account** with repository created

## Installation Steps

### 1. Install Git LFS
```powershell
# Download installer from https://git-lfs.github.com/
# Run installer, then:
git lfs install
```

### 2. Create GitHub Repository
- Go to https://github.com/new
- Create a new repository (e.g., `metablooms-os`)
- Do NOT initialize with README (empty repo)
- Copy the repository URL (e.g., `https://github.com/username/metablooms-os.git`)

## Usage

### Step 1: Edit the Script
Open `Upload-MetaBloomsOS.ps1` and update this line:
```powershell
$REMOTE_URL = "REPLACE_WITH_YOUR_GITHUB_REPO_URL"
```

Change to your actual GitHub repository URL:
```powershell
$REMOTE_URL = "https://github.com/yourusername/metablooms-os.git"
```

### Step 2: Run the Script
```powershell
# Open PowerShell as Administrator
cd C:\path\to\metablooms-ltm\scripts

# Allow script execution (if needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the script
.\Upload-MetaBloomsOS.ps1
```

## What the Script Does

1. ✓ Checks if ZIP file exists
2. ✓ Verifies Git and Git LFS are installed
3. ✓ Creates repository directory (`C:\Users\User\metablooms-os-upload`)
4. ✓ Initializes Git and Git LFS
5. ✓ Configures LFS to track `*.zip` files
6. ✓ Copies ZIP file to repository
7. ✓ Adds remote GitHub repository
8. ✓ Commits ZIP file with descriptive message
9. ✓ Pushes to GitHub using Git LFS

## File Being Uploaded

**File**: `Metablooms_OS_CANONICAL_P0_REHYDRATED_CLEAN_MB-BOOT-20260124T191416Z.zip`
**Location**: `C:\Users\User\Downloads\`
**State**: CANONICAL P0 REHYDRATED CLEAN
**Boot Timestamp**: 2026-01-24 19:14:16 UTC

## Troubleshooting

### "Git is not installed"
- Install Git for Windows: https://git-scm.com/download/win
- Restart PowerShell after installation

### "Git LFS is not installed"
- Install Git LFS: https://git-lfs.github.com/
- Run: `git lfs install`
- Restart PowerShell after installation

### "Authentication failed"
```powershell
# Use GitHub Personal Access Token
# 1. Go to GitHub Settings > Developer settings > Personal access tokens
# 2. Generate new token with 'repo' scope
# 3. Use token as password when prompted
```

### "Push failed - branch name mismatch"
```powershell
# Try pushing to 'master' instead of 'main'
cd C:\Users\User\metablooms-os-upload
git push -u origin master
```

### "File too large even with LFS"
```powershell
# Verify LFS is tracking the file
cd C:\Users\User\metablooms-os-upload
git lfs ls-files

# Should show your ZIP file with LFS indicator
```

## Output Location

**Local Repository**: `C:\Users\User\metablooms-os-upload\`
**GitHub Repository**: Your configured remote URL
**Git LFS Storage**: GitHub LFS (separate from regular git storage)

## Verification

After successful upload:
1. Go to your GitHub repository URL
2. You should see the ZIP file listed
3. File will show LFS badge: `Stored with Git LFS`
4. File size will be displayed correctly

## Customization

To upload a different file, edit these lines in `Upload-MetaBloomsOS.ps1`:
```powershell
$ZIP_FILE = "C:\Users\User\Downloads\YOUR_FILE.zip"
$REPO_DIR = "C:\Users\User\YOUR_REPO_DIRECTORY"
$REMOTE_URL = "https://github.com/username/YOUR_REPO.git"
```

## Security Notes

- Script does NOT store credentials
- GitHub authentication will prompt when needed
- Use Personal Access Tokens instead of passwords
- Token should have 'repo' scope for private repos

## Script Features

- ✓ Comprehensive error checking
- ✓ Colored output (Success=Green, Info=Cyan, Warning=Yellow, Error=Red)
- ✓ File size calculation and display
- ✓ Automatic LFS configuration
- ✓ Detailed commit message with metadata
- ✓ Progress feedback during upload
- ✓ Troubleshooting hints on failure
