"""Safe local storage for small DOCX learning materials. No public serving path."""
import hashlib
import os
import secrets
from pathlib import Path
from fastapi import HTTPException

MAX_BYTES = 15 * 1024 * 1024
MIME_DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def root_dir() -> Path:
    configured = os.environ.get(
        "RDP_PROTECTED_RESOURCE_DIR", ""
    ).strip()

    if not configured:
        raise HTTPException(
            503, "Protected resource storage is not configured."
        )

    original = Path(configured).expanduser()

    if not original.is_absolute():
        raise HTTPException(
            503, "Protected storage must use an absolute path."
        )

    # Check each existing path component BEFORE resolving or creating the root.
    # This rejects parent-directory symlinks as well as a symlink at the root.
    for component in (*reversed(original.parents), original):
        if component.is_symlink():
            raise HTTPException(503, 'Protected storage path contains a symbolic link.')

    p = original.resolve(strict=False)
    p.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Repeat the check after creating missing components. This reduces (but
    # does not eliminate) filesystem race risks; enforce trusted parent dirs.
    for component in (*reversed(original.parents), original):
        if component.is_symlink():
            raise HTTPException(503, 'Protected storage path contains a symbolic link.')

    if os.name == "posix":
        # Strict Unix permissions on production Linux.
        if p.stat().st_mode & 0o077:
            raise HTTPException(
                503, "Protected storage permissions are unsafe."
            )

    elif os.name == "nt":
        # Windows uses ACLs rather than Unix permission bits.
        # Do not treat st_mode as an authoritative ACL check.
        # Production resource storage must remain on Linux.
        pass

    else:
        raise HTTPException(
            503, "Unsupported protected-storage platform."
        )

    return p


def create_file(contents: bytes) -> tuple[str, str, int]:
    if not contents or len(contents) > MAX_BYTES or not contents.startswith(b'PK'):
        raise HTTPException(422, 'A nonempty DOCX file up to 15 MiB is required.')
    # Check ZIP structure: Office package, no encrypted or malicious-size entries.
    import zipfile, io
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as z:
            names = set(z.namelist())
            if 'word/document.xml' not in names or '[Content_Types].xml' not in names:
                raise ValueError('Missing DOCX structure')
            if len(names) > 2000 or sum(x.file_size for x in z.infolist()) > 100 * 1024 * 1024:
                raise ValueError('Oversized uncompressed DOCX')
            if any(x.flag_bits & 1 for x in z.infolist()):
                raise ValueError('Encrypted ZIP entry')
    except (zipfile.BadZipFile, ValueError) as exc:
        raise HTTPException(422, 'Invalid DOCX archive.') from exc
    key = secrets.token_hex(24) + '.docx'
    root = root_dir()
    fd = os.open(root / key, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(contents)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        (root / key).unlink(missing_ok=True)
        raise
    return key, hashlib.sha256(contents).hexdigest(), len(contents)


def read_path(key: str, checksum: str) -> Path:
    if not (len(key) == 53 and key.endswith('.docx') and all(c in '0123456789abcdef' for c in key[:-5])):
        raise HTTPException(404, 'Resource file not found.')
    path = root_dir() / key
    if not path.is_file() or path.is_symlink():
        raise HTTPException(404, 'Resource file not found.')
    # Validate content integrity before serving, not just metadata.
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    if not secrets.compare_digest(h.hexdigest(), checksum):
        raise HTTPException(503, 'Resource integrity check failed.')
    return path
