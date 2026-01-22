# MetaBlooms Browser Agent (MBA) - Bug Fix Report

**Date:** 2026-01-22
**Script Version:** 0.1.8+fullreemit5
**Bug Fixed:** Memory leak in export functions

## Bug Summary

**Type:** Memory Leak
**Severity:** Medium-High
**Location:** `exportArtifacts()` and `exportLedger()` functions
**Impact:** Memory accumulates on repeated exports, degrading browser performance over time

## Root Cause

Both export functions call `URL.createObjectURL()` to create blob URLs for downloads but never call `URL.revokeObjectURL()` to free the allocated memory. In long-running browser sessions with multiple exports, this causes memory to accumulate indefinitely.

## Code Changes

### Location 1: `exportArtifacts()` function

**Before (lines ~383-393):**
```javascript
async function exportArtifacts() {
  if ((await getPhase()) !== PHASES.VERIFY) throw new Error("EXPORT_REQUIRES_VERIFY");
  await setPhase(PHASES.EXPORT);

  const ledger = await kvGet(STORAGE.LEDGER, null);
  const turns = await kvGet(STORAGE.TURNS, []);
  const payload = { ledger, turns, mba_version: MBA_VERSION };

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  GM_download({ url, name: safeFilename(`mba_export_${ledger.run_id}.json`), saveAs: true });
  await ledgerAppend({ t: nowIso(), phase: PHASES.EXPORT, type: "EXPORT_COMPLETE" });
}
```

**After (with fix):**
```javascript
async function exportArtifacts() {
  if ((await getPhase()) !== PHASES.VERIFY) throw new Error("EXPORT_REQUIRES_VERIFY");
  await setPhase(PHASES.EXPORT);

  const ledger = await kvGet(STORAGE.LEDGER, null);
  const turns = await kvGet(STORAGE.TURNS, []);
  const payload = { ledger, turns, mba_version: MBA_VERSION };

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  GM_download({ url, name: safeFilename(`mba_export_${ledger.run_id}.json`), saveAs: true });

  // FIX: Revoke URL after download starts to prevent memory leak
  setTimeout(() => URL.revokeObjectURL(url), 1000);

  await ledgerAppend({ t: nowIso(), phase: PHASES.EXPORT, type: "EXPORT_COMPLETE" });
}
```

### Location 2: `exportLedger()` function

**Before (lines ~397-403):**
```javascript
async function exportLedger() {
  const ledger = await kvGet(STORAGE.LEDGER, null);
  if (!ledger) throw new Error("LEDGER_MISSING");
  const blob = new Blob([JSON.stringify(ledger, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  GM_download({ url, name: safeFilename(`mba_ledger_${ledger.run_id}.json`), saveAs: true });
  return { ok: true };
}
```

**After (with fix):**
```javascript
async function exportLedger() {
  const ledger = await kvGet(STORAGE.LEDGER, null);
  if (!ledger) throw new Error("LEDGER_MISSING");
  const blob = new Blob([JSON.stringify(ledger, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  GM_download({ url, name: safeFilename(`mba_ledger_${ledger.run_id}.json`), saveAs: true });

  // FIX: Revoke URL after download starts to prevent memory leak
  setTimeout(() => URL.revokeObjectURL(url), 1000);

  return { ok: true };
}
```

## Technical Explanation

### How `URL.createObjectURL()` Works
- Creates a DOMString containing a URL representing the blob object
- The browser allocates memory to maintain the blob-to-URL mapping
- Memory persists until explicitly revoked or page unloads

### Why This is a Problem
- Each export creates a new blob URL
- Memory is never freed during the session
- In a long-running userscript, repeated exports cause memory bloat
- Can degrade browser performance or cause crashes

### The Fix
- Call `URL.revokeObjectURL(url)` after a 1-second delay
- 1000ms is sufficient for `GM_download()` to initiate the download
- Frees memory immediately after download starts
- Safe for all normal use cases

## Additional Bugs Found (Not Fixed in This Commit)

### 1. Stable Text Detection Logic
**Location:** `waitForNonEmptyAssistantText()` around line ~187
**Issue:** Comment says "stable_twice" but `sameCount >= 1` only requires one match after initial
**Recommendation:** Change to `sameCount >= 2` for true "twice" requirement, or update comment

### 2. Missing Error Handling
**Location:** `GM_download()` calls
**Issue:** No error handling if download fails
**Recommendation:** Add try-catch or error callbacks

### 3. Race Condition on Bootstrap
**Location:** Bootstrap `executeTick()` call around line ~460
**Issue:** No guarantee DOM is ready when auto-executing
**Recommendation:** Add DOMContentLoaded check or readyState verification

### 4. Hard-coded Magic Numbers
**Location:** Throughout (200 iterations, 900ms delays, etc.)
**Issue:** Not configurable
**Recommendation:** Move to configuration constants

## Testing Recommendations

1. **Memory Leak Test:**
   - Run 10+ consecutive exports
   - Monitor browser memory usage
   - Verify memory is freed after each export

2. **Download Verification:**
   - Ensure files still download correctly
   - Test on slow connections (1s timeout sufficient?)

3. **Regression Test:**
   - Verify all existing functionality still works
   - Run through REVEAL → PLAN → EXECUTE → VERIFY → EXPORT flow

## Version Recommendation

Increment version to: **0.1.9** (bug fix release)

Update version constant:
```javascript
const MBA_VERSION = "0.1.9";
```

And userscript header:
```javascript
// @version      0.1.9
```
