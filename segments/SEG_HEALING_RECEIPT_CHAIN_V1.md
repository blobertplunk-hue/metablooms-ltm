# SEG_HEALING_RECEIPT_CHAIN_V1

**Segment ID**: SEG_HEALING_CHAIN_V1
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: VALIDATED
**Proof Class**: INTEGRATION_EXECUTION

## Purpose
Maintain cryptographic hash chain of healing operations for tamper-evidence and audit.

## Healing Receipt Chain Schema

```python
@dataclass
class HealingReceiptChainEntry:
    receipt_type: str  # "HEALING_RECEIPT"
    healing_id: str
    timestamp_utc: str
    healing_type: str  # "PATCH" | "PROMOTE" | "ROLLBACK"
    status: str  # "APPLIED" | "ROLLED_BACK" | "FAILED"
    target_files: List[str]
    prior_healing_receipt_hash: Optional[str]  # null for genesis
    receipt_hash: str  # SHA256 of this receipt (excluding this field)
```

## Chain Initialization (Genesis)

```python
def initialize_healing_chain(os_root: Path) -> Path:
    """
    Initialize healing receipt chain with genesis receipt.

    Genesis receipt:
    - Has no prior_healing_receipt_hash
    - Marks the start of healing lineage
    - Must be validated for structural integrity

    Returns:
        Path to genesis healing receipt
    """
    healing_ledger_dir = os_root / "ledgers" / "healing"
    healing_ledger_dir.mkdir(parents=True, exist_ok=True)

    genesis_receipt = {
        "receipt_type": "HEALING_RECEIPT",
        "healing_id": "HEALING_GENESIS",
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "healing_type": "GENESIS",
        "status": "INITIALIZED",
        "target_files": [],
        "prior_healing_receipt_hash": None,
        "is_genesis": True
    }

    # Compute receipt hash
    receipt_hash = sha256_json(genesis_receipt)
    genesis_receipt["receipt_hash"] = receipt_hash

    # Write genesis receipt
    genesis_receipt_path = healing_ledger_dir / "HEALING_GENESIS.json"
    genesis_receipt_path.write_text(
        json.dumps(genesis_receipt, indent=2),
        encoding="utf-8"
    )

    return genesis_receipt_path
```

## Chain Append

```python
def append_healing_receipt(
    os_root: Path,
    healing_id: str,
    healing_type: str,
    status: str,
    target_files: List[str],
    rollback_performed: bool,
    metadata: Optional[Dict] = None
) -> Path:
    """
    Append healing receipt to chain with hash linkage.

    Flow:
    1. Discover latest healing receipt
    2. Read prior receipt hash
    3. Create new receipt with prior_healing_receipt_hash
    4. Compute new receipt hash
    5. Write to ledger

    Returns:
        Path to new healing receipt
    """
    healing_ledger_dir = os_root / "ledgers" / "healing"
    healing_ledger_dir.mkdir(parents=True, exist_ok=True)

    # Discover latest healing receipt
    latest_receipt_path = discover_latest_healing_receipt(os_root)

    if latest_receipt_path is None:
        # No prior healing - initialize genesis first
        latest_receipt_path = initialize_healing_chain(os_root)

    # Read prior receipt hash
    latest_receipt = json.loads(
        latest_receipt_path.read_text(encoding="utf-8")
    )
    prior_hash = latest_receipt["receipt_hash"]

    # Create new receipt
    new_receipt = {
        "receipt_type": "HEALING_RECEIPT",
        "healing_id": healing_id,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "healing_type": healing_type,
        "status": status,
        "target_files": target_files,
        "rollback_performed": rollback_performed,
        "prior_healing_receipt_hash": prior_hash
    }

    # Add optional metadata
    if metadata:
        new_receipt["metadata"] = metadata

    # Compute receipt hash
    receipt_hash = sha256_json(new_receipt)
    new_receipt["receipt_hash"] = receipt_hash

    # Write receipt
    new_receipt_path = healing_ledger_dir / f"{healing_id}.json"
    new_receipt_path.write_text(
        json.dumps(new_receipt, indent=2),
        encoding="utf-8"
    )

    return new_receipt_path
```

## Chain Discovery

```python
def discover_latest_healing_receipt(os_root: Path) -> Optional[Path]:
    """
    Discover the most recent healing receipt by timestamp.

    Algorithm:
    1. List all healing receipts in ledgers/healing/
    2. Parse timestamp from each receipt
    3. Return path to receipt with latest timestamp
    4. Return None if no receipts exist

    Returns:
        Path to latest healing receipt, or None
    """
    healing_ledger_dir = os_root / "ledgers" / "healing"

    if not healing_ledger_dir.exists():
        return None

    receipt_files = list(healing_ledger_dir.glob("*.json"))

    if not receipt_files:
        return None

    # Find latest by timestamp
    latest_receipt_path = None
    latest_timestamp = None

    for receipt_path in receipt_files:
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            timestamp = receipt.get("timestamp_utc")

            if timestamp:
                if latest_timestamp is None or timestamp > latest_timestamp:
                    latest_timestamp = timestamp
                    latest_receipt_path = receipt_path
        except Exception:
            # Skip malformed receipts
            continue

    return latest_receipt_path
```

## Chain Validation

```python
def validate_healing_receipt_chain(os_root: Path) -> ChainValidationResult:
    """
    Validate entire healing receipt chain for integrity.

    Validates:
    1. Genesis receipt exists and has no prior hash
    2. All non-genesis receipts reference valid prior receipt
    3. Hash chain is unbroken from genesis to latest
    4. Receipt hashes are valid (recompute and compare)
    5. No gaps in chain (every receipt's prior hash matches a real receipt)

    Returns:
        ChainValidationResult with status and any errors
    """
    healing_ledger_dir = os_root / "ledgers" / "healing"

    if not healing_ledger_dir.exists():
        return ChainValidationResult(
            valid=False,
            reason="Healing ledger directory does not exist"
        )

    receipt_files = sorted(healing_ledger_dir.glob("*.json"))

    if not receipt_files:
        return ChainValidationResult(
            valid=False,
            reason="No healing receipts found"
        )

    # Load all receipts
    receipts = []
    for receipt_path in receipt_files:
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipts.append(receipt)
        except Exception as e:
            return ChainValidationResult(
                valid=False,
                reason=f"Failed to parse receipt {receipt_path}: {e}"
            )

    # Sort by timestamp
    receipts.sort(key=lambda r: r.get("timestamp_utc", ""))

    # Validate genesis receipt
    genesis = receipts[0]

    if not _is_genesis_receipt(genesis):
        return ChainValidationResult(
            valid=False,
            reason="First receipt is not a valid genesis receipt"
        )

    # Validate genesis has no prior hash
    if genesis.get("prior_healing_receipt_hash") is not None:
        return ChainValidationResult(
            valid=False,
            reason="Genesis receipt has prior_healing_receipt_hash (should be null)"
        )

    # Validate genesis receipt hash
    try:
        _validate_receipt_hash(genesis)
    except Exception as e:
        return ChainValidationResult(
            valid=False,
            reason=f"Genesis receipt hash invalid: {e}"
        )

    # Build hash index for quick lookup
    hash_index = {r["receipt_hash"]: r for r in receipts}

    # Validate chain from second receipt onward
    for i, receipt in enumerate(receipts[1:], start=1):
        # Validate receipt hash
        try:
            _validate_receipt_hash(receipt)
        except Exception as e:
            return ChainValidationResult(
                valid=False,
                reason=f"Receipt {receipt['healing_id']} has invalid hash: {e}"
            )

        # Validate prior hash reference
        prior_hash = receipt.get("prior_healing_receipt_hash")

        if prior_hash is None:
            return ChainValidationResult(
                valid=False,
                reason=f"Non-genesis receipt {receipt['healing_id']} has no prior hash"
            )

        if prior_hash not in hash_index:
            return ChainValidationResult(
                valid=False,
                reason=f"Receipt {receipt['healing_id']} references unknown prior hash {prior_hash}"
            )

        # Validate prior receipt is actually prior in time
        prior_receipt = hash_index[prior_hash]
        if prior_receipt["timestamp_utc"] >= receipt["timestamp_utc"]:
            return ChainValidationResult(
                valid=False,
                reason=f"Receipt {receipt['healing_id']} timestamp not after prior receipt"
            )

    return ChainValidationResult(
        valid=True,
        chain_length=len(receipts),
        genesis_healing_id=genesis["healing_id"],
        latest_healing_id=receipts[-1]["healing_id"]
    )


def _is_genesis_receipt(receipt: dict) -> bool:
    """Check if receipt is a genesis receipt."""
    return (
        receipt.get("healing_type") == "GENESIS" or
        receipt.get("is_genesis") is True
    )


def _validate_receipt_hash(receipt: dict) -> None:
    """
    Validate receipt hash by recomputing.

    Raises:
        RuntimeError if hash is invalid
    """
    receipt_hash = receipt.get("receipt_hash")

    if not receipt_hash:
        raise RuntimeError("Receipt missing receipt_hash field")

    # Recompute hash (excluding receipt_hash field)
    receipt_without_hash = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    computed_hash = sha256_json(receipt_without_hash)

    if receipt_hash != computed_hash:
        raise RuntimeError(
            f"Receipt hash mismatch: expected {receipt_hash}, got {computed_hash}"
        )
```

## Chain Querying

```python
def get_healing_lineage(
    os_root: Path,
    healing_id: str,
    max_depth: int = 10
) -> List[Dict]:
    """
    Get lineage of healing operations leading to this healing.

    Returns list of receipts from genesis to specified healing_id,
    or up to max_depth ancestors.

    Returns:
        List of healing receipts in chronological order
    """
    healing_ledger_dir = os_root / "ledgers" / "healing"

    # Load target receipt
    target_receipt_path = healing_ledger_dir / f"{healing_id}.json"

    if not target_receipt_path.exists():
        raise ValueError(f"Healing receipt not found: {healing_id}")

    target_receipt = json.loads(
        target_receipt_path.read_text(encoding="utf-8")
    )

    # Build hash index
    receipt_files = list(healing_ledger_dir.glob("*.json"))
    hash_index = {}

    for receipt_path in receipt_files:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        hash_index[receipt["receipt_hash"]] = receipt

    # Walk backward through chain
    lineage = [target_receipt]
    current = target_receipt

    for _ in range(max_depth):
        prior_hash = current.get("prior_healing_receipt_hash")

        if prior_hash is None:
            # Reached genesis
            break

        if prior_hash not in hash_index:
            # Broken chain
            break

        prior_receipt = hash_index[prior_hash]
        lineage.append(prior_receipt)
        current = prior_receipt

    # Reverse to get chronological order (genesis first)
    lineage.reverse()

    return lineage


def get_healings_for_file(os_root: Path, file_path: str) -> List[Dict]:
    """
    Get all healing operations that modified a specific file.

    Returns:
        List of healing receipts that targeted this file
    """
    healing_ledger_dir = os_root / "ledgers" / "healing"

    if not healing_ledger_dir.exists():
        return []

    receipt_files = list(healing_ledger_dir.glob("*.json"))
    matching_healings = []

    for receipt_path in receipt_files:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        target_files = receipt.get("target_files", [])

        if file_path in target_files:
            matching_healings.append(receipt)

    # Sort by timestamp
    matching_healings.sort(key=lambda r: r.get("timestamp_utc", ""))

    return matching_healings
```

## Integration with Preflight Gate

```python
# metablooms/preflight/gates/gate_healing_receipt_chain.py

def run_gate(ctx):
    """
    P1 GATE: Verify healing receipt chain integrity.

    Enforces:
    - Healing chain exists and starts with genesis
    - All healing receipts are hash-chained correctly
    - No gaps or breaks in chain
    - All receipt hashes are valid
    """
    validation_result = validate_healing_receipt_chain(ctx.os_root)

    if not validation_result.valid:
        raise RuntimeError(
            f"P1_FAIL: HEALING_CHAIN_INVALID - {validation_result.reason}"
        )

    # Log chain status to boot receipt
    ctx.gate_metadata["healing_chain_length"] = validation_result.chain_length
    ctx.gate_metadata["healing_genesis"] = validation_result.genesis_healing_id
    ctx.gate_metadata["healing_latest"] = validation_result.latest_healing_id

    return  # PASS
```

## Healing Chain Audit Queries

```bash
# Count total healings
find ledgers/healing -name "*.json" | wc -l

# List all healings in chronological order
python -c "
import json
from pathlib import Path
receipts = []
for p in Path('ledgers/healing').glob('*.json'):
    r = json.loads(p.read_text())
    receipts.append(r)
receipts.sort(key=lambda x: x['timestamp_utc'])
for r in receipts:
    print(f\"{r['timestamp_utc']} - {r['healing_id']} - {r['status']}\")
"

# Verify chain integrity
python -c "
from validate_healing_chain import validate_healing_receipt_chain
result = validate_healing_receipt_chain(Path('.'))
print(f'Valid: {result.valid}')
print(f'Chain length: {result.chain_length}')
"

# Get healing lineage for specific healing
python -c "
from healing_chain import get_healing_lineage
lineage = get_healing_lineage(Path('.'), 'HEAL_001')
for receipt in lineage:
    print(f\"{receipt['healing_id']} -> \", end='')
print('END')
"
```

## Governance Rules
- P0: All healing operations MUST emit receipts
- P0: Healing receipts MUST be hash-chained
- P1: Healing chain MUST start with genesis receipt
- P1: Healing chain MUST be validated during preflight
- P2: Healing lineage MUST be queryable for audit

## Anti-Patterns (FORBIDDEN)
- ❌ Healing without emitting receipt
- ❌ Breaking hash chain (prior_hash not matching any receipt)
- ❌ Deleting healing receipts
- ❌ Modifying historical healing receipts
- ❌ Creating healing receipts with future timestamps
