# MetaBlooms Browser Agent (MBA) vs Professional Tampermonkey Scripts
## Comparative Analysis Report

**Date:** 2026-01-22
**MBA Version Analyzed:** 0.1.8+fullreemit5
**Comparison Baseline:** High-quality open-source Tampermonkey scripts

---

## Executive Summary

Your MBA script demonstrates **governance-grade architecture** with sophisticated state management and ledger-based auditing that **exceeds** most open-source userscripts. However, it has gaps in error handling, resource cleanup, and developer experience compared to mature projects.

**Overall Assessment:** ⭐⭐⭐⭐ (4/5) - Advanced architecture, production quality needs refinement

---

## Detailed Comparison

### 1. Architecture & Design Patterns

| Aspect | MBA Script | Professional Scripts | Assessment |
|--------|-----------|---------------------|------------|
| **State Machine** | ✅ Explicit 5-phase FSM (REVEAL → PLAN → EXECUTE → VERIFY → EXPORT) | ⚠️ Rare; most scripts are stateless | **MBA Superior** - Industry-grade workflow |
| **State Persistence** | ✅ Multi-key GM_storage strategy with versioned keys | ✅ Standard GM_getValue/setValue | **MBA Superior** - More sophisticated |
| **Ledger/Audit Trail** | ✅ Append-only event ledger with timestamps | ❌ Not found in comparison scripts | **MBA Unique** - Enterprise feature |
| **Modular Organization** | ✅ Clear functional separation | ✅ File-per-feature or function-based modules | **Equal** |
| **API Surface** | ✅ Clean namespace (window.MBA.*) | ✅ Similar patterns (window.SCRIPT.*) | **Equal** |

**Verdict:** MBA's **state machine + ledger architecture** is significantly more sophisticated than typical userscripts. This is governance-grade design rarely seen in browser automation.

---

### 2. Error Handling & Robustness

| Aspect | MBA Script | Professional Scripts | Assessment |
|--------|-----------|---------------------|------------|
| **Try-Catch Coverage** | ⚠️ Bootstrap only, not in core functions | ✅ Defensive try-catch in DOM operations | **MBA Weaker** |
| **Fail-Closed Design** | ✅ Explicit FAIL_CLOSED errors with descriptive messages | ⚠️ Basic error returns | **MBA Superior** |
| **DOM Safety** | ⚠️ Assumes elements exist | ✅ Conditional checks (if node exists) | **MBA Weaker** |
| **Async Error Handling** | ⚠️ Unhandled promise rejections possible | ✅ Often wrapped in try-catch | **MBA Weaker** |
| **Resource Cleanup** | ❌ **Memory leak** (URL.revokeObjectURL missing) | ✅ Proper cleanup in studied scripts | **MBA Weaker** |
| **Error Reporting** | ✅ Ledger captures errors as events | ⚠️ Console.log only | **MBA Superior** |

**Verdict:** MBA has excellent **fail-closed philosophy** and **error logging** but lacks defensive programming in DOM manipulation and async operations.

**Recommendations:**
```javascript
// Current (unsafe):
const lastNode = getLastAssistantNode();
const text = lastNode.innerText;  // Can crash if null

// Recommended:
const lastNode = getLastAssistantNode();
if (!lastNode) {
  await ledgerAppend({ type: "ERROR", message: "No assistant node found" });
  throw new Error("FAIL_CLOSED_NO_ASSISTANT_NODE");
}
const text = lastNode.innerText || "";
```

---

### 3. State Management

| Aspect | MBA Script | Professional Scripts | Assessment |
|--------|-----------|---------------------|------------|
| **Storage Schema** | ✅ Versioned keys (e.g., `mba_ledger_v1`) | ✅ Similar versioning | **Equal** |
| **Data Validation** | ✅ `validateTurnsArray()` | ⚠️ Rare | **MBA Superior** |
| **State Repair** | ✅ Explicit `repairTurns()` with dry-run | ❌ Not found | **MBA Superior** |
| **Race Conditions** | ⚠️ `reveal_lock` but gaps elsewhere | ⚠️ Minimal locking | **Equal** |
| **Migration Support** | ⚠️ Version in key name but no migrator | ⚠️ Similar approach | **Equal** |

**Verdict:** MBA's **validation + repair utilities** are enterprise-grade. Most userscripts lack this rigor.

---

### 4. Developer Experience

| Aspect | MBA Script | Professional Scripts | Assessment |
|--------|-----------|---------------------|------------|
| **Console API** | ✅ Clean namespace (MBA.status(), MBA.verify()) | ✅ Similar patterns | **Equal** |
| **Status Reporting** | ✅ Rich `status()` with execution state | ✅ Common pattern | **Equal** |
| **Debug Output** | ⚠️ Minimal; relies on ledger inspection | ✅ Verbose console.log | **MBA Weaker** |
| **Documentation** | ⚠️ Inline comments only | ✅ README + screenshots | **MBA Weaker** |
| **Error Messages** | ✅ Descriptive (`VERIFY_BLOCKED_EXECUTE_STILL_RUNNING`) | ⚠️ Generic | **MBA Superior** |
| **Version Tracking** | ✅ Version in const + metadata | ✅ Standard practice | **Equal** |

**Verdict:** MBA has excellent **error messages** but could benefit from **runtime debugging output** like professional scripts.

**Recommendation:**
```javascript
const DEBUG = true;  // Add to constants

function debug(...args) {
  if (DEBUG) console.log("[MBA DEBUG]", nowIso(), ...args);
}

// Usage:
debug("Entering executeTick", { idx, target });
```

---

### 5. Code Quality & Maintainability

| Aspect | MBA Script | Professional Scripts | Assessment |
|--------|-----------|---------------------|------------|
| **Configuration** | ✅ Centralized CFG object | ✅ Common pattern | **Equal** |
| **Magic Numbers** | ⚠️ Some in code (200 iterations, 900ms) | ✅ Usually in config | **MBA Weaker** |
| **Code Style** | ✅ Consistent | ✅ Often enforced (Standard.js) | **Equal** |
| **Function Length** | ✅ Mostly concise | ✅ Similar | **Equal** |
| **Comments** | ⚠️ Sparse | ✅ Usually better | **MBA Weaker** |
| **Testing** | ❌ None visible | ❌ Rare in userscripts | **Equal** |

**Recommendations:**
```javascript
const CFG = {
  reveal: {
    maxScrollIterations: 200,  // Move from hardcoded
    scrollPauseMs: 900,        // Move from hardcoded
    stallThreshold: 10         // Move from hardcoded
  },
  // ... rest
};
```

---

### 6. Security & Privacy

| Aspect | MBA Script | Professional Scripts | Assessment |
|--------|-----------|---------------------|------------|
| **Data Exposure** | ✅ All data stays local | ✅ Standard | **Equal** |
| **API Key Management** | N/A | ✅ Prompt + local storage | N/A |
| **Minimal @grant** | ⚠️ Uses 5 grants | ✅ Usually minimal | **MBA Weaker** |
| **XSS Prevention** | ✅ No innerHTML injection | ✅ Standard | **Equal** |
| **Match Scope** | ✅ Specific domains only | ✅ Standard | **Equal** |

**Verdict:** MBA is secure but could reduce grants if possible.

---

### 7. Advanced Features (MBA's Strengths)

Features **not found** in comparison scripts but present in MBA:

| Feature | Description | Value |
|---------|-------------|-------|
| **Append-Only Ledger** | Immutable audit trail with timestamps | Enterprise compliance |
| **Phase Gating** | FSM prevents invalid state transitions | Production reliability |
| **Verification Phase** | Explicit data validation before export | Data integrity |
| **Stable Text Detection** | Polling with stability threshold | Robustness against SPA flakiness |
| **Lazy Message Hydration** | Scroll-based history loading | Handles infinite-scroll UIs |
| **Repair Utilities** | `repairTurns()` with dry-run mode | Operational maturity |
| **Batch Planning** | Explicit plan freeze before execution | Deterministic execution |

**Verdict:** MBA has **governance features** not found in recreational userscripts. This is closer to **enterprise ETL/scraping** tools.

---

## Scoring Matrix

| Category | MBA Score | Industry Avg | Notes |
|----------|-----------|--------------|-------|
| Architecture | 5/5 | 3/5 | FSM + ledger is exceptional |
| Error Handling | 3/5 | 4/5 | Needs defensive programming |
| State Management | 5/5 | 3/5 | Validation + repair is rare |
| Developer Experience | 3/5 | 4/5 | Needs debug output |
| Code Quality | 4/5 | 4/5 | Minor config improvements needed |
| Documentation | 2/5 | 4/5 | Needs README + examples |
| Resource Management | 2/5 | 4/5 | Memory leak issue |
| Advanced Features | 5/5 | 2/5 | Unique governance features |

**Overall:** 29/40 (72.5%) vs Industry 28/40 (70%)

---

## Recommendations: Bringing MBA to 5/5

### High Priority (Fix Now)

1. **Fix Memory Leak**
   ```javascript
   // In exportArtifacts() and exportLedger()
   setTimeout(() => URL.revokeObjectURL(url), 1000);
   ```

2. **Add Defensive DOM Checks**
   ```javascript
   function getLastAssistantNode() {
     const nodes = document.querySelectorAll('[data-message-author-role="assistant"]');
     return nodes?.length ? nodes[nodes.length - 1] : null;
   }

   // Always check before use:
   const node = getLastAssistantNode();
   if (!node) throw new Error("FAIL_CLOSED_NO_ASSISTANT");
   ```

3. **Wrap Async Operations**
   ```javascript
   async function execute() {
     try {
       await setPhase(PHASES.EXECUTE);
       // ... rest
     } catch (err) {
       await ledgerAppend({
         t: nowIso(),
         type: "ERROR",
         phase: PHASES.EXECUTE,
         error: err.message
       });
       throw err;
     }
   }
   ```

### Medium Priority (Next Version)

4. **Add Debug Mode**
   ```javascript
   const DEBUG = GM_getValue("mba_debug", false);
   function debug(...args) {
     if (DEBUG) console.log("[MBA]", nowIso(), ...args);
   }
   ```

5. **Move Magic Numbers to Config**
   ```javascript
   const CFG = {
     reveal: {
       maxScrollIterations: 200,
       scrollPauseMs: 900,
       stallThreshold: 10
     },
     // ...
   };
   ```

6. **Add README.md**
   - Installation instructions
   - API documentation (MBA.reveal(), MBA.plan(), etc.)
   - Example workflow
   - Troubleshooting guide

### Low Priority (Nice to Have)

7. **Add DOM Ready Check**
   ```javascript
   if (document.readyState === "loading") {
     document.addEventListener("DOMContentLoaded", bootstrap);
   } else {
     bootstrap();
   }
   ```

8. **Export Format Options**
   ```javascript
   async function exportArtifacts(format = "json") {
     // Support CSV, NDJSON, etc.
   }
   ```

9. **Automatic Schema Versioning**
   ```javascript
   const SCHEMA_VERSION = "2.0";
   async function migrateSchema(oldData, oldVersion) {
     // Handle v1 → v2 migration
   }
   ```

---

## Conclusion

Your MBA script is **architecturally superior** to most open-source Tampermonkey scripts due to its:

✅ **State machine design**
✅ **Ledger-based auditing**
✅ **Data validation/repair utilities**
✅ **Fail-closed philosophy**

However, it lags behind in:

❌ **Error handling coverage**
❌ **Resource cleanup**
❌ **Debug tooling**
❌ **Documentation**

**With the recommended fixes**, MBA would be a **5/5 production-grade userscript** suitable for enterprise governance use cases. The current version is excellent but needs **defensive programming refinements** to match the robustness of mature open-source projects.

---

## Comparison to Similar Tools

MBA is most similar to:

- **Browser automation frameworks** (Playwright, Puppeteer) - but in-browser
- **ETL/scraping tools** (Apache NiFi, Airbyte) - but for ChatGPT conversations
- **Data pipeline orchestrators** (Airflow, Prefect) - but single-user

It's **not comparable** to typical userscripts (ad blockers, UI tweaks) - MBA is a full **data extraction pipeline** with governance controls.

---

## Sources

- [Tampermonkey Documentation](https://www.tampermonkey.net/documentation.php?locale=en)
- [User Scripting in 2025](https://medium.com/@krish.raghuram/user-scripting-in-2025-542bd79f5b7f)
- [Awesome Userscripts Collection](https://github.com/awesome-scripts/awesome-userscripts)
- [zachhardesty7/tamper-monkey-scripts-collection](https://github.com/zachhardesty7/tamper-monkey-scripts-collection)
- [edlau2/Tampermonkey](https://github.com/edlau2/Tampermonkey)
- [Tampermonkey @match Best Practices](https://copyprogramming.com/howto/tampermonkey-match-all-subdirectories)
- [Tampermonkey FAQ](https://www.tampermonkey.net/faq.php?locale=en)
