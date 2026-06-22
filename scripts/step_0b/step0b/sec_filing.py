"""SEC filing document URL and path helpers.

Purpose:
    Build reproducible filing main-document URLs from submissions metadata and
    keep local file names stable enough for offline reruns.

Call graph:
    sec_client/narrative_evidence/comparison -> filing_url/sec_raw_path
"""

from __future__ import annotations

from pathlib import Path

from step0b.models import DATA_DIR


def cik_no_leading_zeroes(*, cik10: str) -> str:
    """Return the SEC archive CIK path segment.

    Args:
        cik10: Ten-digit CIK string.

    Returns:
        CIK without leading zeroes.
    """
    return str(int(cik10))


def accession_no_dashes(*, accession: str) -> str:
    """Return an accession number without dashes.

    Args:
        accession: SEC accession number with dashes.

    Returns:
        Accession path segment without dashes.
    """
    return accession.replace("-", "")


def filing_url(*, cik10: str, accession: str, primary_document: str) -> str:
    """Build the SEC archive URL for a filing primary document.

    Args:
        cik10: Ten-digit CIK string.
        accession: SEC accession number with dashes.
        primary_document: Primary document file name from submissions JSON.

    Returns:
        Full SEC filing URL.
    """
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{cik_no_leading_zeroes(cik10=cik10)}/"
        f"{accession_no_dashes(accession=accession)}/"
        f"{primary_document}"
    )


def sec_raw_path(*, symbol: str, artifact_kind: str, suffix: str) -> Path:
    """Build a SEC raw artifact path.

    Args:
        symbol: Company ticker.
        artifact_kind: submissions, companyfacts, 10-k, or 10-q.
        suffix: File suffix without leading dot.

    Returns:
        Absolute path under data/raw/sec.
    """
    return (
        DATA_DIR
        / "raw"
        / "sec"
        / f"{symbol.lower()}_{artifact_kind}.{suffix}"
    )


def sec_filing_raw_path(*, symbol: str, form: str, accession: str) -> Path:
    """Build a SEC filing HTML raw path.

    Args:
        symbol: Company ticker.
        form: SEC form such as 10-K.
        accession: SEC accession number.

    Returns:
        Absolute path under data/raw/sec.
    """
    safe_form = form.lower().replace("/", "-")
    safe_accession = accession.replace("-", "")
    return (
        DATA_DIR
        / "raw"
        / "sec"
        / f"{symbol.lower()}_{safe_form}_{safe_accession}.html"
    )


def sec_manifest_path(*, raw_path: Path) -> Path:
    """Return the manifest path next to a SEC raw artifact.

    Args:
        raw_path: Raw artifact path.

    Returns:
        Manifest path.
    """
    return raw_path.with_suffix(f"{raw_path.suffix}.manifest.json")


def sec_headers_path(*, raw_path: Path) -> Path:
    """Return the headers path next to a SEC raw artifact.

    Args:
        raw_path: Raw artifact path.

    Returns:
        Headers path.
    """
    return raw_path.with_suffix(f"{raw_path.suffix}.headers.json")
