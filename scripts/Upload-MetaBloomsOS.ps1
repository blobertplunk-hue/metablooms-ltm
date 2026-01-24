# MetaBlooms OS Upload Script with Git LFS
# Purpose: Upload large MetaBlooms OS ZIP to GitHub using Git LFS

# Configuration
$ZIP_FILE = "C:\Users\User\Downloads\Metablooms_OS_CANONICAL_P0_REHYDRATED_CLEAN_MB-BOOT-20260124T191416Z.zip"
$REPO_DIR = "C:\Users\User\metablooms-os-upload"
$REMOTE_URL = "REPLACE_WITH_YOUR_GITHUB_REPO_URL"  # e.g., https://github.com/username/repo.git

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "=== MetaBlooms OS Upload Script ==="
Write-Info ""

# Step 1: Check if ZIP file exists
Write-Info "Step 1: Checking if ZIP file exists..."
if (-not (Test-Path $ZIP_FILE)) {
    Write-Error "ERROR: ZIP file not found at: $ZIP_FILE"
    exit 1
}
$fileSize = (Get-Item $ZIP_FILE).Length / 1MB
Write-Success "✓ ZIP file found (${fileSize:N2} MB)"
Write-Info ""

# Step 2: Check if Git is installed
Write-Info "Step 2: Checking if Git is installed..."
try {
    $gitVersion = git --version
    Write-Success "✓ Git installed: $gitVersion"
} catch {
    Write-Error "ERROR: Git is not installed. Please install Git for Windows from https://git-scm.com/download/win"
    exit 1
}
Write-Info ""

# Step 3: Check if Git LFS is installed
Write-Info "Step 3: Checking if Git LFS is installed..."
try {
    $lfsVersion = git lfs version
    Write-Success "✓ Git LFS installed: $lfsVersion"
} catch {
    Write-Error "ERROR: Git LFS is not installed."
    Write-Warning "Please install Git LFS:"
    Write-Warning "1. Download from: https://git-lfs.github.com/"
    Write-Warning "2. Run the installer"
    Write-Warning "3. Run: git lfs install"
    exit 1
}
Write-Info ""

# Step 4: Create/navigate to repo directory
Write-Info "Step 4: Setting up repository directory..."
if (-not (Test-Path $REPO_DIR)) {
    New-Item -ItemType Directory -Path $REPO_DIR | Out-Null
    Write-Success "✓ Created directory: $REPO_DIR"
} else {
    Write-Success "✓ Directory exists: $REPO_DIR"
}

Set-Location $REPO_DIR
Write-Info ""

# Step 5: Initialize Git repository
Write-Info "Step 5: Initializing Git repository..."
if (-not (Test-Path ".git")) {
    git init
    Write-Success "✓ Git repository initialized"
} else {
    Write-Success "✓ Git repository already initialized"
}
Write-Info ""

# Step 6: Initialize Git LFS
Write-Info "Step 6: Initializing Git LFS..."
git lfs install
Write-Success "✓ Git LFS initialized"
Write-Info ""

# Step 7: Track ZIP files with LFS
Write-Info "Step 7: Configuring Git LFS to track .zip files..."
git lfs track "*.zip"
Write-Success "✓ Git LFS configured to track *.zip files"

# Add .gitattributes
if (Test-Path ".gitattributes") {
    Write-Success "✓ .gitattributes updated"
} else {
    Write-Success "✓ .gitattributes created"
}
git add .gitattributes
git commit -m "Add Git LFS tracking for ZIP files" 2>$null
Write-Info ""

# Step 8: Copy ZIP file to repo
Write-Info "Step 8: Copying ZIP file to repository..."
$zipFileName = Split-Path $ZIP_FILE -Leaf
$destPath = Join-Path $REPO_DIR $zipFileName

if (Test-Path $destPath) {
    Write-Warning "ZIP file already exists in repo, overwriting..."
    Remove-Item $destPath -Force
}

Copy-Item $ZIP_FILE -Destination $destPath
Write-Success "✓ ZIP file copied to: $destPath"
Write-Info ""

# Step 9: Check remote URL
Write-Info "Step 9: Checking remote configuration..."
if ($REMOTE_URL -eq "REPLACE_WITH_YOUR_GITHUB_REPO_URL") {
    Write-Error "ERROR: Please edit this script and set REMOTE_URL to your GitHub repository URL"
    Write-Warning "Example: https://github.com/username/metablooms-os.git"
    Write-Warning ""
    Write-Warning "After setting the URL, run this script again."
    exit 1
}

# Check if remote exists
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    Write-Success "✓ Remote 'origin' exists: $existingRemote"
    if ($existingRemote -ne $REMOTE_URL) {
        Write-Warning "Remote URL differs from configured URL"
        Write-Warning "Existing: $existingRemote"
        Write-Warning "Configured: $REMOTE_URL"
        $response = Read-Host "Update remote URL? (y/n)"
        if ($response -eq "y") {
            git remote set-url origin $REMOTE_URL
            Write-Success "✓ Remote URL updated"
        }
    }
} else {
    git remote add origin $REMOTE_URL
    Write-Success "✓ Remote 'origin' added: $REMOTE_URL"
}
Write-Info ""

# Step 10: Add and commit ZIP file
Write-Info "Step 10: Adding and committing ZIP file..."
git add $zipFileName

$commitMessage = "Add MetaBlooms OS CANONICAL P0 REHYDRATED CLEAN (20260124T191416Z)

- File: $zipFileName
- Size: ${fileSize:N2} MB
- Stored with Git LFS
- Boot timestamp: 20260124T191416Z
- State: CANONICAL P0 REHYDRATED CLEAN"

git commit -m $commitMessage
Write-Success "✓ ZIP file committed"
Write-Info ""

# Step 11: Push to GitHub
Write-Info "Step 11: Pushing to GitHub..."
Write-Warning "This may take a while depending on file size and internet speed..."
Write-Info ""

git push -u origin main 2>&1 | ForEach-Object {
    Write-Host $_
}

if ($LASTEXITCODE -eq 0) {
    Write-Info ""
    Write-Success "=== SUCCESS ==="
    Write-Success "✓ MetaBlooms OS uploaded to GitHub!"
    Write-Success "✓ Repository: $REMOTE_URL"
    Write-Success "✓ File: $zipFileName (${fileSize:N2} MB)"
    Write-Success "✓ Stored with Git LFS"
} else {
    Write-Info ""
    Write-Error "=== PUSH FAILED ==="
    Write-Warning "Common issues:"
    Write-Warning "1. Authentication required - make sure you're logged into GitHub"
    Write-Warning "2. Repository doesn't exist - create it on GitHub first"
    Write-Warning "3. Branch name mismatch - try: git push -u origin master"
    Write-Warning "4. Network issues - check your internet connection"
    Write-Warning ""
    Write-Warning "You can retry the push with: git push -u origin main"
    exit 1
}
