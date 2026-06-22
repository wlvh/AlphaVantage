"""Hashing helpers used for raw artifacts and evidence spans.

Purpose:
    Centralize SHA-256 behavior so raw manifests, report manifests, and
    evidence span validation use identical UTF-8 hashing.

Call graph:
    av_client/sec_client/narrative_evidence/reporting -> sha256_*
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(*, data: bytes) -> str:
    """Hash bytes with SHA-256.

    Args:
        data: Raw byte payload.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(data).hexdigest()


def sha256_text(*, text: str) -> str:
    """Hash UTF-8 text with SHA-256.

    Args:
        text: Text value to encode as UTF-8.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return sha256_bytes(data=text.encode(encoding="utf-8"))


def sha256_file(*, path: Path) -> str:
    """Hash a local file with SHA-256.

    Args:
        path: File path to read as bytes.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return sha256_bytes(data=path.read_bytes())
