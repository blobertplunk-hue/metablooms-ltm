# SEG_METABLOOMS_EVIDENCE_STORE_V1

**Segment ID**: SEG_MB_EVIDENCE_V1
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: PRODUCTION_IMPLEMENTATION
**Proof Class**: RUNTIME_EXECUTION
**Source**: MetaBlooms OS `/home/user/metablooms-os-debug/metablooms/evidence/`

## Purpose
Document the hash-verified artifact storage system with path traversal protection, resource quotas, and cross-process locking.

## Core Module: store_v1.py

### EvidenceStore Class

```python
class EvidenceStore:
    """
    Evidence store with SHA256 verification and resource quotas.

    Security:
    - Path traversal protection via safe_component()
    - Safe path joining via safe_join_under()
    - Cross-process locking via FileLock

    Resource Management:
    - min_free_bytes: Minimum free disk space (default 1GB)
    - max_artifact_bytes: Maximum single artifact size (default 100MB)
    - max_total_task_bytes: Maximum total evidence per task (default 1GB)
    """

    def __init__(
        self,
        root: Path,
        min_free_bytes: int = 1073741824,  # 1GB
        max_artifact_bytes: int = 104857600,  # 100MB
        max_total_task_bytes: int = 1073741824  # 1GB
    ):
        self.root = root
        self.min_free_bytes = min_free_bytes
        self.max_artifact_bytes = max_artifact_bytes
        self.max_total_task_bytes = max_total_task_bytes
```

### Attempt Directory Allocation

```python
def alloc_attempt_dir(self, task_id: str, attempt_num: int) -> Path:
    """
    Allocate attempt directory for evidence storage.

    Directory structure:
    <root>/<task_id>/attempt_<attempt_num>/

    Flow:
    1. Validate task_id via safe_component()
    2. Create directory with parents
    3. Check resource quotas
    4. Return path

    Returns:
        Path to attempt directory

    Raises:
        ValueError: If task_id unsafe or quotas exceeded
    """
    safe_task_id = safe_component(task_id)
    attempt_dir = safe_join_under(
        self.root,
        safe_task_id,
        f"attempt_{attempt_num}"
    )

    attempt_dir.mkdir(parents=True, exist_ok=True)

    # Check quotas
    self._check_disk_quota()
    self._check_task_quota(safe_task_id)

    return attempt_dir
```

### SHA256 File Hashing

```python
def sha256_file(self, file_path: Path) -> str:
    """
    Compute SHA256 hash of file.

    Algorithm:
    1. Open file in binary mode
    2. Read in chunks (64KB)
    3. Update SHA256 incrementally
    4. Return hex digest

    Returns:
        SHA256 hex string (64 characters)
    """
    hasher = hashlib.sha256()

    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)

    return hasher.hexdigest()
```

### Resource Quota Enforcement

```python
def _check_disk_quota(self) -> None:
    """
    Check minimum free disk space.

    Raises:
        RuntimeError: If free space < min_free_bytes
    """
    stat = shutil.disk_usage(self.root)
    if stat.free < self.min_free_bytes:
        raise RuntimeError(
            f"Insufficient disk space: {stat.free} < {self.min_free_bytes}"
        )

def _check_task_quota(self, task_id: str) -> None:
    """
    Check total evidence size for task.

    Raises:
        RuntimeError: If task evidence > max_total_task_bytes
    """
    task_dir = self.root / task_id
    if not task_dir.exists():
        return

    total_size = sum(
        f.stat().st_size
        for f in task_dir.rglob('*')
        if f.is_file()
    )

    if total_size > self.max_total_task_bytes:
        raise RuntimeError(
            f"Task evidence quota exceeded: {total_size} > {self.max_total_task_bytes}"
        )
```

### Cross-Process Locking

```python
def write_with_lock(self, file_path: Path, content: str) -> None:
    """
    Write file with cross-process locking.

    Uses FileLock from concurrency/lock_v1.py

    Flow:
    1. Acquire file lock (blocking with timeout)
    2. Write content
    3. Release lock (automatic via context manager)
    """
    lock_path = file_path.with_suffix('.lock')

    with FileLock(lock_path, timeout=10):
        file_path.write_text(content, encoding='utf-8')
```

## Security Module: security/path_safety_v1.py

### Path Traversal Protection

```python
def safe_component(component: str) -> str:
    """
    Validate path component is safe (no traversal).

    Forbidden patterns:
    - .. (parent directory)
    - / or \\ (path separators)
    - Absolute paths

    Returns:
        Safe component

    Raises:
        ValueError: If component unsafe
    """
    if '..' in component:
        raise ValueError(f"Unsafe component (parent ref): {component}")

    if '/' in component or '\\' in component:
        raise ValueError(f"Unsafe component (path separator): {component}")

    if os.path.isabs(component):
        raise ValueError(f"Unsafe component (absolute path): {component}")

    return component


def safe_join_under(root: Path, *components: str) -> Path:
    """
    Safely join path components under root.

    Flow:
    1. Validate each component via safe_component()
    2. Join under root
    3. Resolve to absolute path
    4. Verify result is under root

    Returns:
        Safe absolute path under root

    Raises:
        ValueError: If result escapes root
    """
    for component in components:
        safe_component(component)

    result = (root / Path(*components)).resolve()

    try:
        result.relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"Path escapes root: {result}")

    return result
```

## Concurrency Module: concurrency/lock_v1.py

### FileLock Context Manager

```python
class FileLock:
    """
    Cross-process file locking (context manager).

    Platforms:
    - POSIX: fcntl.flock()
    - Windows: msvcrt.locking()

    Timeout: 10 seconds (configurable)
    """

    def __init__(self, lock_path: Path, timeout: int = 10):
        self.lock_path = lock_path
        self.timeout = timeout
        self._lock_file = None

    def __enter__(self):
        """Acquire lock (blocking with timeout)."""
        start_time = time.time()

        while True:
            try:
                self._lock_file = open(self.lock_path, 'w')

                if HAS_FCNTL:
                    # Unix
                    fcntl.flock(
                        self._lock_file.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                else:
                    # Windows
                    msvcrt.locking(
                        self._lock_file.fileno(),
                        msvcrt.LK_NBLCK,
                        1
                    )

                return self

            except (BlockingIOError, IOError):
                if time.time() - start_time > self.timeout:
                    raise RuntimeError("LOCK_ACQUIRE_TIMEOUT")
                time.sleep(0.1)

    def __exit__(self, *args):
        """Release lock."""
        if self._lock_file:
            if HAS_FCNTL:
                fcntl.flock(
                    self._lock_file.fileno(),
                    fcntl.LOCK_UN
                )
            self._lock_file.close()
            self.lock_path.unlink(missing_ok=True)
```

## Evidence Validation: evidence/receipt_validate_v1.py

### Receipt Validation

```python
def validate_receipt(receipt: Dict, receipt_path: Path) -> bool:
    """
    Validate receipt structure and integrity.

    Checks:
    1. Required fields present (receipt_type, timestamp_utc, receipt_hash)
    2. SHA256 hash matches (recompute and compare)
    3. Referenced evidence exists

    Returns:
        True if valid

    Raises:
        ReceiptValidationError: If validation fails
    """
    # Check required fields
    required_fields = ["receipt_type", "timestamp_utc", "receipt_hash"]
    for field in required_fields:
        if field not in receipt:
            raise ReceiptValidationError(f"Missing field: {field}")

    # Validate hash
    receipt_copy = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    computed_hash = sha256_json(receipt_copy)

    if receipt["receipt_hash"] != computed_hash:
        raise ReceiptValidationError(
            f"Hash mismatch: {receipt['receipt_hash']} != {computed_hash}"
        )

    # Validate evidence references
    if "evidence" in receipt:
        for evidence_ref in receipt["evidence"]:
            evidence_path = receipt_path.parent / evidence_ref
            if not evidence_path.exists():
                raise ReceiptValidationError(
                    f"Evidence missing: {evidence_ref}"
                )

    return True
```

## Integration with Runtime

```python
# From runtime/sandbox_exec_v1.py
def sandbox_execute(task_spec: Dict, iteration: int) -> Dict:
    # Initialize evidence store
    evidence_store = EvidenceStore(
        root=Path("/mnt/data/evidence"),
        min_free_bytes=1073741824,
        max_artifact_bytes=104857600,
        max_total_task_bytes=1073741824
    )

    # Allocate attempt directory
    attempt_dir = evidence_store.alloc_attempt_dir(
        task_id=task_spec["task_id"],
        attempt_num=iteration
    )

    # Execute command and capture output
    stdout_path = attempt_dir / "stdout.txt"
    stderr_path = attempt_dir / "stderr.txt"

    result = subprocess.run(
        task_spec["command"],
        stdout=open(stdout_path, 'w'),
        stderr=open(stderr_path, 'w'),
        timeout=task_spec["timeout"]
    )

    # Compute SHA256 hashes
    stdout_sha256 = evidence_store.sha256_file(stdout_path)
    stderr_sha256 = evidence_store.sha256_file(stderr_path)

    # Generate receipt
    receipt = {
        "receipt_type": "SANDBOX_EXECUTION_RECEIPT",
        "timestamp_utc": utcnow(),
        "task_id": task_spec["task_id"],
        "exit_code": result.returncode,
        "evidence": {
            "stdout": str(stdout_path),
            "stdout_sha256": stdout_sha256,
            "stderr": str(stderr_path),
            "stderr_sha256": stderr_sha256
        }
    }

    receipt_hash = sha256_json(receipt)
    receipt["receipt_hash"] = receipt_hash

    # Write receipt with locking
    receipt_path = attempt_dir / "receipt.json"
    evidence_store.write_with_lock(
        receipt_path,
        json.dumps(receipt, indent=2)
    )

    return receipt
```

## Governance Rules
- P0: All evidence MUST have SHA256 hashes
- P0: Evidence store MUST enforce resource quotas
- P0: Evidence store MUST prevent path traversal
- P0: Evidence writing MUST use cross-process locking
- P1: Receipts MUST reference evidence with paths and hashes
- P1: Evidence SHOULD be retained for audit period

## Anti-Patterns (FORBIDDEN)
- ❌ Writing evidence without SHA256 hashing
- ❌ Bypassing path traversal protection
- ❌ Exceeding resource quotas
- ❌ Writing evidence without locking
- ❌ Deleting evidence before audit period ends
- ❌ Modifying evidence after writing
