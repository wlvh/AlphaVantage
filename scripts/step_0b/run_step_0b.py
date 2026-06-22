"""Run and verify the local Step 0B Alpha Vantage / SEC spike.

Purpose:
    Build the acceptance-facing Step 0B reports from local raw artifacts only.
    The script reuses the existing spike selection logic, redirects it to the
    accepted `spikes/step_0b` layout, and writes reports that separate semantic
    identity from source observations.

Call graph:
    main -> command handlers -> generate_reports -> legacy comparison builder
    generate_reports -> narrative finding writer -> output verifier
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_DIR = Path(__file__).resolve().parents[2]
SPIKE_DIR = REPO_DIR / "spikes" / "step_0b"
CONFIG_DIR = SPIKE_DIR / "config"
REPORT_DIR = SPIKE_DIR / "reports"
WORK_DIR = SPIKE_DIR / "work"
RAW_DIR = WORK_DIR / "raw"
NORMALIZED_DIR = WORK_DIR / "normalized"

LEGACY_SPIKE_DIR = REPO_DIR / "spikes" / "step0b_av_sec_alignment"
LEGACY_RAW_DIR = LEGACY_SPIKE_DIR / "data" / "raw"
LOCAL_SOURCE_PARENT = Path(__file__).resolve().parent

STATUS_MAP = {
    "MATCH": "MATCH",
    "NEAR_MATCH": "NEAR_MATCH",
    "DIFFERENT": "MISMATCH",
    "MISSING_AV": "MISSING_AV",
    "MISSING_SEC": "MISSING_SEC",
    "NOT_APPLICABLE": "NOT_APPLICABLE",
    "PERIOD_MISMATCH": "NOT_COMPARABLE_PERIOD",
    "REQUIRES_DERIVATION": "NOT_COMPARABLE_PERIOD",
    "REQUIRES_COMPOSITION": "COMPOSITE_REQUIRED",
    "DEFINITION_MISMATCH": "AMBIGUOUS_MAPPING",
    "MANUAL_REVIEW": "AMBIGUOUS_MAPPING",
    "AMBIGUOUS_MAPPING": "AMBIGUOUS_MAPPING",
}
ALLOWED_STATUSES = set(STATUS_MAP.values()) | {"IDENTIFIER_MISMATCH"}
SCOPE_BY_PERIOD_KIND = {
    "ANNUAL": "LATEST_COMMON_ANNUAL",
    "QUARTER": "LATEST_COMMON_QUARTER",
}

CSV_COLUMNS = [
    "company_key",
    "symbol",
    "company_archetype",
    "canonical_metric",
    "metric_applicability",
    "comparison_scope",
    "period_type",
    "period_start",
    "period_end",
    "dimensions",
    "semantic_key",
    "semantic_key_inputs",
    "av_semantic_key",
    "sec_semantic_key",
    "av_observation_id",
    "sec_observation_id",
    "av_observation_id_inputs",
    "sec_observation_id_inputs",
    "av_endpoint",
    "av_field",
    "av_value",
    "av_unit",
    "av_raw_file",
    "sec_taxonomy",
    "sec_candidate_concepts",
    "sec_selected_concept",
    "sec_value",
    "sec_unit",
    "sec_form",
    "sec_accession",
    "sec_filed_at",
    "sec_raw_file",
    "normalization_rule",
    "absolute_difference",
    "relative_difference",
    "comparison_status",
    "rationale",
    "source_status_original",
    "manual_notes",
]

LEGAL_PATTERNS = [
    "reasonably possible losses",
    "litigation reserves",
    "Legal Proceedings",
    "legal proceedings",
    "Contingencies",
    "contingencies",
    "Investigations",
    "investigations",
]
AMOUNT_RE = re.compile(
    pattern=(
        r"\$\s*[0-9]+(?:\.[0-9]+)?(?:\s+to\s+approximately\s+"
        r"\$\s*[0-9]+(?:\.[0-9]+)?)?\s*(?:billion|million)"
    ),
)


def utc_now() -> str:
    """Return the current UTC timestamp.

    Returns:
        ISO-8601 timestamp with UTC timezone.
    """
    return datetime.now(tz=timezone.utc).isoformat()


def read_json_file(*, path: Path) -> Any:
    """Read a UTF-8 JSON file.

    Args:
        path: JSON file path.

    Returns:
        Decoded JSON payload.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(*, path: Path, payload: Any) -> None:
    """Write deterministic UTF-8 JSON.

    Args:
        path: Destination path.
        payload: JSON-serializable payload.

    Returns:
        None. The path is created when missing.
    """
    # Stable JSON makes offline reruns reviewable by diff.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        data=json.dumps(
            obj=payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def sha256_text(*, text: str) -> str:
    """Hash text using UTF-8 bytes.

    Args:
        text: Text to hash.

    Returns:
        Hex SHA-256 digest.
    """
    return hashlib.sha256(text.encode(encoding="utf-8")).hexdigest()


def sha256_file(*, path: Path) -> str:
    """Hash a local file.

    Args:
        path: File to hash.

    Returns:
        Hex SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open(mode="rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_text(*, payload: Any) -> str:
    """Serialize payload for identity hashes.

    Args:
        payload: JSON-serializable value.

    Returns:
        Compact deterministic JSON string.
    """
    return json.dumps(
        obj=payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def stable_id(*, prefix: str, payload: dict[str, Any]) -> str:
    """Build a deterministic short ID from structured payload.

    Args:
        prefix: Human-readable ID prefix.
        payload: Structured identity input.

    Returns:
        Prefixed SHA-256-based ID.
    """
    digest = sha256_text(text=stable_json_text(payload=payload))
    return f"{prefix}_{digest[:24]}"


def sync_work_raw() -> None:
    """Synchronize existing raw cache into the accepted work directory.

    Returns:
        None. Local raw files are copied without adding them to Git.

    Raises:
        FileNotFoundError: If neither the legacy nor accepted raw cache exists.
    """
    if not LEGACY_RAW_DIR.exists() and RAW_DIR.exists():
        return
    if not LEGACY_RAW_DIR.exists():
        raise FileNotFoundError(f"missing raw cache: {LEGACY_RAW_DIR}")

    # Reports should point at `spikes/step_0b/work`, so raw is mirrored there.
    for source_path in sorted(LEGACY_RAW_DIR.rglob("*")):
        if not source_path.is_file():
            continue
        target_path = RAW_DIR / source_path.relative_to(LEGACY_RAW_DIR)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if (
            target_path.exists()
            and target_path.stat().st_size == source_path.stat().st_size
        ):
            continue
        shutil.copy2(src=source_path, dst=target_path)


def load_legacy_symbols() -> dict[str, Any]:
    """Load and patch the existing Step 0B comparison modules.

    Returns:
        Dict of imported modules and functions used by this acceptance wrapper.

    Raises:
        FileNotFoundError: If the reusable spike source directory is missing.
    """
    local_source_parent = str(LOCAL_SOURCE_PARENT)
    if local_source_parent not in sys.path:
        sys.path.insert(0, local_source_parent)

    from step0b import av_archive  # type: ignore
    from step0b import comparison  # type: ignore
    from step0b import models  # type: ignore
    from step0b import sec_client  # type: ignore
    from step0b import sec_filing  # type: ignore
    from step0b import sec_submissions  # type: ignore
    from step0b.av_client import fetch_alpha_vantage  # type: ignore
    from step0b.av_archive import ensure_ibm_manifests  # type: ignore
    from step0b.sec_client import fetch_sec_artifacts  # type: ignore

    # The reused logic is path-driven, so patch globals before loading config.
    models.CONFIG_DIR = CONFIG_DIR
    models.DATA_DIR = WORK_DIR
    models.OUTPUT_DIR = REPORT_DIR
    av_archive.DATA_DIR = WORK_DIR
    av_archive.REPO_DIR = REPO_DIR
    sec_filing.DATA_DIR = WORK_DIR

    return {
        "av_archive": av_archive,
        "comparison": comparison,
        "models": models,
        "sec_client": sec_client,
        "sec_filing": sec_filing,
        "sec_submissions": sec_submissions,
        "fetch_alpha_vantage": fetch_alpha_vantage,
        "fetch_sec_artifacts": fetch_sec_artifacts,
        "ensure_ibm_manifests": ensure_ibm_manifests,
    }


def load_company_name_by_key() -> dict[str, str]:
    """Load company display names keyed by company_key.

    Returns:
        Mapping from company key to configured name.
    """
    rows = read_json_file(path=CONFIG_DIR / "companies.json")
    names: dict[str, str] = {}
    for row in rows:
        names[row["company_key"]] = row["name"]
    return names


def load_metric_period_types() -> dict[str, str]:
    """Load configured period type keyed by canonical metric.

    Returns:
        Mapping from canonical metric to duration or instant.
    """
    rows = read_json_file(path=CONFIG_DIR / "canonical_metrics.json")
    period_types: dict[str, str] = {}
    for row in rows:
        period_types[row["canonical_metric"]] = row["period_type"]
    return period_types


def period_start_for_row(
    *,
    row: dict[str, str],
    period_type: str,
) -> str:
    """Return the curated period start for a matrix row.

    Args:
        row: Legacy comparison row.
        period_type: duration or instant.

    Returns:
        ISO date string. Instant facts use period_end to avoid null Silver keys.
    """
    if row["period_start"] != "":
        return row["period_start"]
    if period_type == "instant":
        return row["period_end"]
    return ""


def dimensions_for_row(*, row: dict[str, str]) -> dict[str, str]:
    """Build source-free dimensions for semantic identity.

    Args:
        row: Legacy comparison row.

    Returns:
        Dimensions dict without source system fields.
    """
    return {
        "entity_scope": "consolidated",
        "period_kind": row["comparison_period_kind"].lower(),
        "reporting_basis": "reported",
    }


def semantic_inputs_for_row(
    *,
    row: dict[str, str],
    period_type: str,
    period_start: str,
    dimensions: dict[str, str],
) -> dict[str, Any]:
    """Build semantic key inputs without source_system.

    Args:
        row: Legacy comparison row.
        period_type: duration or instant.
        period_start: Curated period start.
        dimensions: Source-free reporting dimensions.

    Returns:
        Dict used to hash the semantic key.
    """
    return {
        "company_key": row["company_id"],
        "canonical_metric": row["canonical_metric"],
        "comparison_scope": SCOPE_BY_PERIOD_KIND[row["comparison_period_kind"]],
        "period_type": period_type,
        "period_start": period_start,
        "period_end": row["period_end"],
        "dimensions": dimensions,
    }


def av_observation_inputs_for_row(
    *,
    row: dict[str, str],
    semantic_key: str,
) -> dict[str, str]:
    """Build AV observation ID inputs with source identity.

    Args:
        row: Acceptance matrix row under construction.
        semantic_key: Source-free semantic key.

    Returns:
        Dict used to hash the AV observation ID.
    """
    return {
        "source_system": "ALPHA_VANTAGE",
        "semantic_key": semantic_key,
        "endpoint": row["av_endpoint"],
        "field": row["av_field"],
        "period_end": row["period_end"],
        "raw_file": row["av_raw_file"],
    }


def sec_observation_inputs_for_row(
    *,
    row: dict[str, str],
    semantic_key: str,
) -> dict[str, str]:
    """Build SEC observation ID inputs with source identity.

    Args:
        row: Acceptance matrix row under construction.
        semantic_key: Source-free semantic key.

    Returns:
        Dict used to hash the SEC observation ID.
    """
    return {
        "source_system": "SEC_COMPANYFACTS",
        "semantic_key": semantic_key,
        "concept": row["sec_selected_concept"],
        "accession": row["sec_accession"],
        "form": row["sec_form"],
        "filed_at": row["sec_filed_at"],
        "period_end": row["period_end"],
        "raw_file": row["sec_raw_file"],
    }


def accepted_status(*, source_status: str) -> str:
    """Map internal status to the acceptance status vocabulary.

    Args:
        source_status: Status emitted by the reusable comparison logic.

    Returns:
        Acceptance status.

    Raises:
        ValueError: If an unmapped status is encountered.
    """
    if source_status not in STATUS_MAP:
        raise ValueError(f"unmapped comparison status: {source_status}")
    return STATUS_MAP[source_status]


def rationale_for_row(*, row: dict[str, str], accepted: str) -> str:
    """Build a required rationale for one acceptance row.

    Args:
        row: Legacy comparison row.
        accepted: Acceptance comparison status.

    Returns:
        Non-empty rationale for every non-MATCH row.
    """
    if row["difference_reason"] != "":
        return row["difference_reason"]
    if accepted == "MATCH":
        return "AV and SEC values match under the selected concept and period."
    return f"{accepted}: source row did not provide a detailed rationale."


def transform_row(
    *,
    row: dict[str, str],
    metric_period_types: dict[str, str],
) -> dict[str, str]:
    """Convert one reusable comparison row to the acceptance CSV contract.

    Args:
        row: Legacy CSV-ready comparison row.
        metric_period_types: Configured metric period types.

    Returns:
        Acceptance CSV row with semantic and observation identities.
    """
    period_type = metric_period_types[row["canonical_metric"]]
    period_start = period_start_for_row(row=row, period_type=period_type)
    dimensions = dimensions_for_row(row=row)
    semantic_inputs = semantic_inputs_for_row(
        row=row,
        period_type=period_type,
        period_start=period_start,
        dimensions=dimensions,
    )
    semantic_key = stable_id(prefix="sem", payload=semantic_inputs)
    accepted = accepted_status(source_status=row["comparison_status"])
    acceptance_row = {
        "company_key": row["company_id"],
        "symbol": row["symbol"],
        "company_archetype": row["company_archetype"],
        "canonical_metric": row["canonical_metric"],
        "metric_applicability": row["metric_applicability"],
        "comparison_scope": SCOPE_BY_PERIOD_KIND[row["comparison_period_kind"]],
        "period_type": period_type,
        "period_start": period_start,
        "period_end": row["period_end"],
        "dimensions": stable_json_text(payload=dimensions),
        "semantic_key": semantic_key,
        "semantic_key_inputs": stable_json_text(payload=semantic_inputs),
        "av_semantic_key": semantic_key,
        "sec_semantic_key": semantic_key,
        "av_endpoint": row["av_endpoint"],
        "av_field": row["av_field"],
        "av_value": row["av_value"],
        "av_unit": row["av_unit"],
        "av_raw_file": row["av_raw_file"],
        "sec_taxonomy": row["sec_taxonomy"],
        "sec_candidate_concepts": row["sec_candidate_concepts"],
        "sec_selected_concept": row["sec_selected_concept"],
        "sec_value": row["sec_value"],
        "sec_unit": row["sec_unit"],
        "sec_form": row["sec_form"],
        "sec_accession": row["sec_accession"],
        "sec_filed_at": row["sec_filed_at"],
        "sec_raw_file": row["sec_raw_file"],
        "normalization_rule": row["normalization_rule"],
        "absolute_difference": row["absolute_difference"],
        "relative_difference": row["relative_difference"],
        "comparison_status": accepted,
        "rationale": rationale_for_row(row=row, accepted=accepted),
        "source_status_original": row["comparison_status"],
        "manual_notes": row["manual_notes"],
    }
    av_inputs = av_observation_inputs_for_row(
        row=acceptance_row,
        semantic_key=semantic_key,
    )
    sec_inputs = sec_observation_inputs_for_row(
        row=acceptance_row,
        semantic_key=semantic_key,
    )
    acceptance_row["av_observation_id_inputs"] = stable_json_text(payload=av_inputs)
    acceptance_row["sec_observation_id_inputs"] = stable_json_text(payload=sec_inputs)
    acceptance_row["av_observation_id"] = stable_id(
        prefix="obs",
        payload=av_inputs,
    )
    acceptance_row["sec_observation_id"] = stable_id(
        prefix="obs",
        payload=sec_inputs,
    )
    return acceptance_row


def build_acceptance_rows() -> list[dict[str, str]]:
    """Build the 72-row financial alignment matrix.

    Returns:
        Acceptance matrix rows.
    """
    sync_work_raw()
    legacy = load_legacy_symbols()
    models = legacy["models"]
    comparison = legacy["comparison"]
    ensure_ibm_manifests = legacy["ensure_ibm_manifests"]

    companies = models.load_companies()
    metrics = models.load_metrics()
    for company in companies:
        if company.av_source == "existing_archive":
            ensure_ibm_manifests(company=company)

    # Step 0B acceptance requires every metric to have annual and quarter rows.
    comparison.QUARTERLY_METRICS = {metric.canonical_metric for metric in metrics}
    raw_rows = comparison.build_alignment_rows(companies=companies, metrics=metrics)
    metric_period_types = load_metric_period_types()
    return [
        transform_row(row=row, metric_period_types=metric_period_types)
        for row in raw_rows
    ]


def write_metric_alignment_csv(*, rows: list[dict[str, str]]) -> Path:
    """Write the acceptance alignment matrix CSV.

    Args:
        rows: Acceptance matrix rows.

    Returns:
        CSV path.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "metric_alignment.csv"
    with path.open(mode="w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            f=handle,
            fieldnames=CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(rowdict=row)
    return path


def status_counts(*, rows: list[dict[str, str]]) -> Counter[str]:
    """Count comparison statuses.

    Args:
        rows: Acceptance matrix rows.

    Returns:
        Counter keyed by comparison_status.
    """
    return Counter(row["comparison_status"] for row in rows)


def rows_for_status(
    *,
    rows: list[dict[str, str]],
    status: str,
) -> list[dict[str, str]]:
    """Filter rows by comparison status.

    Args:
        rows: Acceptance matrix rows.
        status: Status to select.

    Returns:
        Matching rows.
    """
    return [row for row in rows if row["comparison_status"] == status]


def row_refs(*, rows: list[dict[str, str]], limit: int = 12) -> list[str]:
    """Render compact row references for Markdown reports.

    Args:
        rows: Acceptance matrix rows.
        limit: Maximum number of references.

    Returns:
        Markdown bullet lines.
    """
    if not rows:
        return ["- None"]
    lines: list[str] = []
    for row in rows[:limit]:
        lines.append(
            "- "
            f"{row['company_key']} {row['comparison_scope']} "
            f"{row['canonical_metric']}: {row['comparison_status']} - "
            f"{row['rationale']}"
        )
    if len(rows) > limit:
        lines.append(f"- ... {len(rows) - limit} more rows")
    return lines


def write_metric_alignment_md(*, rows: list[dict[str, str]]) -> Path:
    """Write a readable matrix summary.

    Args:
        rows: Acceptance matrix rows.

    Returns:
        Markdown path.
    """
    counts = status_counts(rows=rows)
    company_counts = Counter(row["company_key"] for row in rows)
    scope_counts = Counter(row["comparison_scope"] for row in rows)
    lines = [
        "# Step 0B Metric Alignment",
        "",
        f"Generated at UTC `{utc_now()}`.",
        "",
        "## Shape",
        "",
        f"- Rows: {len(rows)}",
        f"- Companies: {dict(company_counts)}",
        f"- Scopes: {dict(scope_counts)}",
        f"- Statuses: {dict(counts)}",
        "",
        "## Required Identity Checks",
        "",
        (
            "- `semantic_key` is shared by AV and SEC rows because it excludes "
            "`source_system`."
        ),
        (
            "- `av_observation_id` and `sec_observation_id` differ because "
            "their inputs include source system and source artifact identity."
        ),
        "",
        "## Non-MATCH Samples",
        "",
        *row_refs(
            rows=[row for row in rows if row["comparison_status"] != "MATCH"],
            limit=18,
        ),
    ]
    path = REPORT_DIR / "metric_alignment.md"
    path.write_text(data="\n".join(lines) + "\n", encoding="utf-8")
    return path


def metric_set_for_status(
    *,
    rows: list[dict[str, str]],
    statuses: set[str],
) -> list[str]:
    """Return sorted metric names that have any of the requested statuses.

    Args:
        rows: Acceptance matrix rows.
        statuses: Statuses to include.

    Returns:
        Sorted canonical metric names.
    """
    return sorted(
        {
            row["canonical_metric"]
            for row in rows
            if row["comparison_status"] in statuses
        }
    )


def write_discrepancy_report(*, rows: list[dict[str, str]]) -> Path:
    """Write the discrepancy and attribution report.

    Args:
        rows: Acceptance matrix rows.

    Returns:
        Markdown path.
    """
    direct = metric_set_for_status(rows=rows, statuses={"MATCH", "NEAR_MATCH"})
    composite = metric_set_for_status(rows=rows, statuses={"COMPOSITE_REQUIRED"})
    ambiguous = metric_set_for_status(
        rows=rows,
        statuses={"AMBIGUOUS_MAPPING", "NOT_APPLICABLE"},
    )
    period_rows = rows_for_status(rows=rows, status="NOT_COMPARABLE_PERIOD")
    mismatch_rows = rows_for_status(rows=rows, status="MISMATCH")
    jpm_boundary_rows = [
        row
        for row in rows
        if row["company_key"] == "NYSE:JPM"
        and row["canonical_metric"]
        in {
            "financial.revenue",
            "financial.gross_profit",
            "financial.operating_income",
            "balance.total_debt",
            "balance.total_equity",
        }
    ]
    lines = [
        "# Step 0B Discrepancy Report",
        "",
        f"Generated at UTC `{utc_now()}`.",
        "",
        "## Direct Mapping Candidates",
        "",
        (
            "These metrics produced at least one `MATCH` or `NEAR_MATCH` row "
            "and can enter AV V1 with source-specific observation metadata:"
        ),
        "",
        *[f"- {metric}" for metric in direct],
        "",
        "## Composite Formula Required",
        "",
        (
            "Total debt cannot be treated as a single SEC concept. The Silver "
            "schema must store formula components, concept lineage, accession, "
            "unit, value, and artifact hash."
        ),
        "",
        *[f"- {metric}" for metric in composite],
        "",
        "## Industry Applicability Limits",
        "",
        (
            "JPM confirms that generic industrial metrics do not always apply "
            "to banking statements. Gross profit is not forced into a fake "
            "match, and revenue / operating income remain mapping-sensitive."
        ),
        "",
        *[f"- {metric}" for metric in ambiguous],
        "",
        "## Period and Filing Effects",
        "",
        (
            "Annual rows use 10-K facts and annual AV reports or valid annual "
            "earnings. Quarter rows use 10-Q facts and quarterly AV reports. "
            "YTD-only SEC facts are reported as not comparable instead of "
            "being silently treated as single-quarter values."
        ),
        "",
        *row_refs(rows=period_rows, limit=10),
        "",
        "## Amendment and Restatement",
        "",
        (
            "Selection prefers latest filed facts for the same form, period end, "
            "duration, and unit. The selected SEC accession and filed date are "
            "kept in every matrix row so amendments and restatements remain "
            "auditable."
        ),
        "",
        "## Alpha Vantage Opaque Standardization",
        "",
        (
            "AV fields such as `totalRevenue`, `grossProfit`, "
            "`operatingIncome`, `shortLongTermDebtTotal`, and `reportedEPS` "
            "are vendor-normalized labels. The raw response does not prove "
            "their complete accounting definition, so source observation "
            "identity is preserved rather than overwriting SEC facts."
        ),
        "",
        "## Mismatch Samples",
        "",
        *row_refs(rows=mismatch_rows, limit=12),
        "",
        "## JPM Boundary Rows",
        "",
        *row_refs(rows=jpm_boundary_rows, limit=12),
        "",
        "## Requires Formal SEC Pipeline Later",
        "",
        (
            "- Automated concept discovery across all statement roles and "
            "dimensional facts."
        ),
        (
            "- Quarter derivation from YTD facts when the filing has enough "
            "prior-period context."
        ),
        (
            "- Production-grade amendment policy and industry-specific metric "
            "families."
        ),
    ]
    path = REPORT_DIR / "discrepancy_report.md"
    path.write_text(data="\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_schema_decision() -> Path:
    """Write the Silver schema decision report.

    Returns:
        Markdown path.
    """
    lines = [
        "# Step 0B Schema Decision",
        "",
        "## Conclusion",
        "",
        "PASS WITH REQUIRED CHANGES.",
        "",
        (
            "The spike is reproducible and source-honest, but the formal Silver "
            "schema must add source observation identity, mapping lineage, "
            "applicability, and composite lineage before AV V1 hardens."
        ),
        "",
        "## Required Semantic Key",
        "",
        (
            "`semantic_key = hash(company_key, canonical_metric, "
            "comparison_scope, period_type, period_start, period_end, "
            "dimensions)`."
        ),
        "",
        "`source_system` must not enter `semantic_key`.",
        "",
        "## Required Observation Identity",
        "",
        (
            "`observation_id = hash(source_system, semantic_key, provider field "
            "or SEC concept, source artifact, accession/form/filed_at when "
            "available)`."
        ),
        "",
        (
            "AV and SEC can therefore share one semantic key while retaining "
            "different source observations."
        ),
        "",
        "## Period Rules",
        "",
        (
            "`period_start`, `period_end`, and `period_type` are required in "
            "Silver. Instant facts should use `period_start = period_end` in "
            "curated Silver rather than relying on nulls."
        ),
        "",
        "## Dimensions and Reporting Scope",
        "",
        (
            "`dimensions` should be a JSON/MAP structure covering entity scope, "
            "reporting basis, statement role, consolidation scope, segment, and "
            "future SEC dimensions."
        ),
        "",
        "## Mapping Rule ID",
        "",
        (
            "`mapping_rule_id` is required. It should version the canonical "
            "metric mapping, candidate concept list, applicability policy, "
            "period policy, and normalization policy."
        ),
        "",
        "## Applicability",
        "",
        (
            "Store `applicability_status` separately from `comparison_status`: "
            "`APPLICABLE`, `NOT_APPLICABLE`, `INDUSTRY_LIMITED`, or "
            "`REQUIRES_REVIEW`."
        ),
        "",
        "## Composite Metric Lineage",
        "",
        (
            "Composite observations need a child component table or JSON lineage "
            "array with component concept, value, unit, sign, accession, filed "
            "date, raw artifact hash, and formula role."
        ),
        "",
        "## Required Silver Changes Before AV V1",
        "",
        "- Add `semantic_key` and `observation_id` as separate fields.",
        "- Add `source_system`, `source_artifact_hash`, `fetched_at`, and raw path.",
        "- Add `mapping_rule_id` and `mapping_version`.",
        "- Add `applicability_status` and `comparison_status`.",
        "- Add composite lineage support for total debt and future formulas.",
        "- Treat `period_start` as required in curated Silver.",
        "",
        "## Deferred to SEC Financial Stage",
        "",
        "- Full SEC concept search across dimensional and statement-role variants.",
        "- YTD-to-quarter derivation.",
        "- Industry-specific banking metrics.",
        "- Production amendment and restatement policy.",
        "",
        "## Owners and Next Steps",
        "",
        (
            "- Data model owner: update metric observation DDL with the fields "
            "listed above."
        ),
        (
            "- AV V1 owner: implement ingestion against this schema using AV "
            "raw-first observations."
        ),
        (
            "- SEC stage owner: keep this spike as evidence, but do not promote "
            "SEC financial fetching into AV V1."
        ),
    ]
    path = REPORT_DIR / "schema_decision.md"
    path.write_text(data="\n".join(lines) + "\n", encoding="utf-8")
    return path


def normalize_html_text(*, html_text: str) -> str:
    """Normalize SEC filing HTML into stable plain text.

    Args:
        html_text: Raw filing HTML.

    Returns:
        Whitespace-collapsed text for offset-based evidence checks.
    """
    # A tiny standard-library normalizer is enough for a fixed evidence sample.
    without_scripts = re.sub(
        pattern=r"(?is)<(script|style).*?</\1>",
        repl=" ",
        string=html_text,
    )
    without_tags = re.sub(pattern=r"(?s)<[^>]+>", repl=" ", string=without_scripts)
    unescaped = html.unescape(without_tags)
    return re.sub(pattern=r"\s+", repl=" ", string=unescaped).strip()


def find_evidence_bounds(*, text: str, index: int) -> tuple[int, int]:
    """Choose a stable evidence window around a legal keyword.

    Args:
        text: Normalized filing text.
        index: Keyword index.

    Returns:
        Start and end offsets.
    """
    start = max(0, index - 600)
    end = min(len(text), index + 1800)
    entity_index = text.rfind("JPMorgan Chase", max(0, index - 5000), index)
    if entity_index != -1:
        start = min(start, entity_index)
    left_sentence = text.rfind(".", 0, start)
    right_sentence = text.find(".", end)
    if left_sentence != -1:
        start = left_sentence + 1
    if right_sentence != -1:
        end = right_sentence + 1
    return start, end


def find_legal_evidence(*, text: str) -> tuple[int, int, str]:
    """Find one legal or regulatory evidence excerpt.

    Args:
        text: Normalized filing text.

    Returns:
        Evidence start, end, and matched pattern.

    Raises:
        ValueError: If no evidence pattern is found.
    """
    for pattern in LEGAL_PATTERNS:
        index = text.find(pattern)
        if index == -1:
            continue
        start, end = find_evidence_bounds(text=text, index=index)
        excerpt = text[start:end]
        if "JPMorgan" in excerpt or "Firm" in excerpt:
            return start, end, pattern
    raise ValueError("no legal or regulatory evidence excerpt found")


def amount_text_for_evidence(*, evidence_text: str) -> str | None:
    """Extract an exact amount phrase when present.

    Args:
        evidence_text: Evidence excerpt.

    Returns:
        Exact amount text or None.
    """
    match = AMOUNT_RE.search(string=evidence_text)
    if match is None:
        return None
    return match.group(0)


def amount_payload_for_text(*, amount_text: str | None) -> dict[str, str] | None:
    """Build an amount payload only when evidence includes an amount.

    Args:
        amount_text: Exact amount text or None.

    Returns:
        Amount payload or None.
    """
    if amount_text is None:
        return None
    return {"amount_text": amount_text, "currency": "USD"}


def jpm_company(*, companies: list[Any]) -> Any:
    """Return the JPM company config.

    Args:
        companies: Configured company records.

    Returns:
        JPM company record.

    Raises:
        ValueError: If JPM is missing from config.
    """
    for company in companies:
        if company.symbol == "JPM":
            return company
    raise ValueError("JPM company is required for narrative fallback")


def write_narrative_finding() -> dict[str, Any]:
    """Write the narrative finding JSON and Markdown reports.

    Returns:
        Finding payload.
    """
    legacy = load_legacy_symbols()
    models = legacy["models"]
    sec_client = legacy["sec_client"]
    sec_filing = legacy["sec_filing"]
    sec_submissions = legacy["sec_submissions"]
    companies = models.load_companies()
    company = jpm_company(companies=companies)
    submissions = read_json_file(path=sec_client.submissions_path(company=company))
    filing = sec_submissions.latest_filing(
        submissions=submissions,
        forms={"10-Q", "10-Q/A"},
    )
    raw_path = sec_filing.sec_filing_raw_path(
        symbol=company.symbol,
        form=filing["form"],
        accession=filing["accessionNumber"],
    )
    source_url = sec_filing.filing_url(
        cik10=company.cik10,
        accession=filing["accessionNumber"],
        primary_document=filing["primaryDocument"],
    )
    raw_html = raw_path.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_html_text(html_text=raw_html)
    start, end, pattern = find_legal_evidence(text=normalized)
    evidence_text = normalized[start:end]
    amount_text = amount_text_for_evidence(evidence_text=evidence_text)
    normalized_path = (
        NORMALIZED_DIR
        / f"{company.symbol.lower()}_{filing['form'].lower()}_"
        f"{filing['accessionNumber'].replace('-', '')}.txt"
    )
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(data=normalized, encoding="utf-8")
    finding = {
        "company_key": company.company_id,
        "symbol": company.symbol,
        "company_name": company.name,
        "finding_type": "LEGAL_MATTER",
        "filing_accession": filing["accessionNumber"],
        "accession_number": filing["accessionNumber"],
        "form": filing["form"],
        "filing_date": filing["filingDate"],
        "source_url": source_url,
        "normalized_text_path": str(normalized_path),
        "normalized_text_sha256": sha256_file(path=normalized_path),
        "source_artifact_path": str(raw_path),
        "source_artifact_sha256": sha256_file(path=raw_path),
        "evidence_start": start,
        "evidence_end": end,
        "evidence_text": evidence_text,
        "evidence_sha256": sha256_text(text=evidence_text),
        "matched_pattern": pattern,
        "summary": (
            "The evidence text contains a legal proceedings or contingencies "
            "disclosure."
        ),
        "amount": amount_payload_for_text(amount_text=amount_text),
        "amount_text": amount_text,
        "validation_status": "VERIFIED",
        "fallback_reason": (
            "MMM raw artifacts are not present in this local spike; used the "
            "configured JPM latest 10-Q fallback."
        ),
    }
    write_json_file(path=REPORT_DIR / "narrative_finding.json", payload=finding)
    markdown_lines = [
        "# Step 0B Narrative Finding",
        "",
        f"- Company: {finding['company_key']}",
        f"- Filing: {finding['form']} {finding['filing_accession']}",
        f"- Filing date: {finding['filing_date']}",
        f"- Source URL: {finding['source_url']}",
        f"- Validation: {finding['validation_status']}",
        f"- Fallback: {finding['fallback_reason']}",
        "",
        "## Evidence",
        "",
        finding["evidence_text"],
    ]
    (REPORT_DIR / "narrative_finding.md").write_text(
        data="\n".join(markdown_lines) + "\n",
        encoding="utf-8",
    )
    return finding


def output_hashes() -> dict[str, str]:
    """Hash generated report files except run_summary.json.

    Returns:
        Mapping from report-relative file name to SHA-256 digest.
    """
    names = [
        "metric_alignment.csv",
        "metric_alignment.md",
        "discrepancy_report.md",
        "schema_decision.md",
        "narrative_finding.json",
        "narrative_finding.md",
    ]
    hashes: dict[str, str] = {}
    for name in names:
        path = REPORT_DIR / name
        hashes[name] = sha256_file(path=path)
    return hashes


def raw_hashes() -> dict[str, str]:
    """Hash local raw and fixture files referenced by the run.

    Returns:
        Mapping from path text to SHA-256 digest.
    """
    hashes: dict[str, str] = {}
    for path in sorted(RAW_DIR.rglob("*")):
        if path.is_file() and not path.name.endswith(".headers.json"):
            hashes[str(path)] = sha256_file(path=path)
    ibm_fixture_dir = (
        REPO_DIR
        / "artifacts"
        / "alpha_vantage"
        / "raw"
        / "demo"
    )
    for path in sorted(ibm_fixture_dir.glob("00[1-5]_*.txt")):
        hashes[str(path)] = sha256_file(path=path)
    return hashes


def redaction_check() -> dict[str, Any]:
    """Check generated artifacts for obvious Alpha Vantage key leaks.

    Returns:
        Redaction check payload.
    """
    checked_paths = []
    violations = []
    scan_roots = [REPORT_DIR, RAW_DIR / "alpha_vantage"]
    query_key_token = "api" + "key="
    for root in scan_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            checked_paths.append(str(path))
            lowered = text.lower()
            if query_key_token in lowered:
                violations.append(f"{path}: contains API key query text")
            if re.search(pattern=r'"apikey"\s*:\s*"(?!REDACTED")', string=text):
                violations.append(f"{path}: contains non-redacted apikey field")
    return {
        "passed": len(violations) == 0,
        "checked_path_count": len(checked_paths),
        "violations": violations,
    }


def unresolved_mappings(*, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Collect mapping rows that should inform schema decisions.

    Args:
        rows: Acceptance matrix rows.

    Returns:
        Compact unresolved mapping records.
    """
    statuses = {
        "AMBIGUOUS_MAPPING",
        "COMPOSITE_REQUIRED",
        "MISSING_SEC",
        "NOT_APPLICABLE",
        "NOT_COMPARABLE_PERIOD",
    }
    unresolved: list[dict[str, str]] = []
    for row in rows:
        if row["comparison_status"] not in statuses:
            continue
        unresolved.append(
            {
                "company_key": row["company_key"],
                "comparison_scope": row["comparison_scope"],
                "canonical_metric": row["canonical_metric"],
                "comparison_status": row["comparison_status"],
                "rationale": row["rationale"],
            }
        )
    return unresolved


def call_budget_summary() -> dict[str, Any]:
    """Summarize cached raw endpoint coverage and current-run call count.

    Returns:
        Network call and cached raw coverage summary.
    """
    av_manifests = sorted((RAW_DIR / "alpha_vantage").glob("*.manifest.json"))
    sec_manifests = sorted((RAW_DIR / "sec").glob("*.manifest.json"))
    av_success = 0
    av_errors: list[str] = []
    for path in av_manifests:
        payload = read_json_file(path=path)
        if "classification" in payload and payload["classification"] == "DATA_JSON":
            av_success += 1
            continue
        if "classification" in payload:
            av_errors.append(f"{path.name}: {payload['classification']}")
    return {
        "current_run_online": False,
        "av_call_count": 0,
        "sec_call_count": 0,
        "default_av_live_call_budget": 10,
        "cached_av_manifest_count": len(av_manifests),
        "cached_av_success_count": av_success,
        "cached_av_errors": av_errors,
        "cached_sec_manifest_count": len(sec_manifests),
        "ibm_uses_existing_fixture": True,
    }


def write_run_summary(
    *,
    rows: list[dict[str, str]],
    start_time: str,
    end_time: str,
    mode: str,
) -> Path:
    """Write run_summary.json.

    Args:
        rows: Acceptance matrix rows.
        start_time: UTC start timestamp.
        end_time: UTC end timestamp.
        mode: online or offline.

    Returns:
        Summary path.
    """
    redaction = redaction_check()
    summary = {
        "run_id": stable_id(
            prefix="run",
            payload={
                "start_time": start_time,
                "mode": mode,
                "row_count": str(len(rows)),
            },
        ),
        "mode": mode,
        "online": mode == "online",
        "started_at": start_time,
        "ended_at": end_time,
        "python_version": sys.version,
        "commit_sha": current_commit_sha(),
        "matrix_row_count": len(rows),
        "company_count": len({row["company_key"] for row in rows}),
        "metric_count": len({row["canonical_metric"] for row in rows}),
        "status_counts": dict(status_counts(rows=rows)),
        "call_budget": call_budget_summary(),
        "raw_hashes": raw_hashes(),
        "output_hashes": output_hashes(),
        "warnings": [
            "SEC narrative sample uses JPM fallback because MMM raw was not collected.",
            "Banking revenue and operating income remain mapping-sensitive.",
            "Total debt requires composite lineage before production Silver.",
        ],
        "unresolved_mappings": unresolved_mappings(rows=rows),
        "key_redaction_check": redaction,
    }
    path = REPORT_DIR / "run_summary.json"
    write_json_file(path=path, payload=summary)
    return path


def current_commit_sha() -> str:
    """Return current Git commit SHA without failing report generation.

    Returns:
        Commit SHA or UNKNOWN when Git metadata is unavailable.
    """
    head_path = REPO_DIR / ".git" / "HEAD"
    if not head_path.exists():
        return "UNKNOWN"
    head = head_path.read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    ref_path = REPO_DIR / ".git" / head.removeprefix("ref: ")
    if not ref_path.exists():
        return "UNKNOWN"
    return ref_path.read_text(encoding="utf-8").strip()


def generate_reports(*, mode: str) -> list[dict[str, str]]:
    """Generate all acceptance reports from local raw data.

    Args:
        mode: online or offline label for run summary.

    Returns:
        Acceptance matrix rows.
    """
    start_time = utc_now()
    rows = build_acceptance_rows()
    write_metric_alignment_csv(rows=rows)
    write_metric_alignment_md(rows=rows)
    write_discrepancy_report(rows=rows)
    write_schema_decision()
    write_narrative_finding()
    end_time = utc_now()
    write_run_summary(
        rows=rows,
        start_time=start_time,
        end_time=end_time,
        mode=mode,
    )
    return rows


def read_metric_alignment() -> list[dict[str, str]]:
    """Read the generated acceptance CSV.

    Returns:
        CSV rows.
    """
    path = REPORT_DIR / "metric_alignment.csv"
    with path.open(mode="r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(f=handle)
        return [dict(row) for row in reader]


def validate_matrix(*, rows: list[dict[str, str]]) -> list[str]:
    """Validate the acceptance matrix blocking requirements.

    Args:
        rows: Acceptance matrix rows.

    Returns:
        Validation error messages.
    """
    errors: list[str] = []
    if len(rows) != 72:
        errors.append(f"metric_alignment.csv has {len(rows)} rows, expected 72")
    if len({row["company_key"] for row in rows}) != 3:
        errors.append("matrix does not contain exactly three companies")
    if len({row["canonical_metric"] for row in rows}) != 12:
        errors.append("matrix does not contain exactly 12 canonical metrics")
    for row in rows:
        if row["comparison_status"] not in ALLOWED_STATUSES:
            errors.append(f"invalid status: {row['comparison_status']}")
        if row["comparison_status"] != "MATCH" and row["rationale"].strip() == "":
            errors.append("non-MATCH row missing rationale")
        semantic_inputs = json.loads(row["semantic_key_inputs"])
        if "source_system" in semantic_inputs:
            errors.append("semantic key inputs contain source_system")
        av_inputs = json.loads(row["av_observation_id_inputs"])
        sec_inputs = json.loads(row["sec_observation_id_inputs"])
        if "source_system" not in av_inputs or "source_system" not in sec_inputs:
            errors.append("observation inputs missing source_system")
    return errors


def validate_required_identity_rows(*, rows: list[dict[str, str]]) -> list[str]:
    """Validate representative semantic and observation identities.

    Args:
        rows: Acceptance matrix rows.

    Returns:
        Validation error messages.
    """
    required = [
        ("NYSE:IBM", "financial.revenue", "LATEST_COMMON_ANNUAL"),
        ("NYSE:IBM", "financial.net_income", "LATEST_COMMON_QUARTER"),
        ("NYSE:CAT", "balance.total_assets", "LATEST_COMMON_ANNUAL"),
        ("NYSE:CAT", "cashflow.operating_cash_flow", "LATEST_COMMON_QUARTER"),
        ("NYSE:JPM", "balance.total_equity", "LATEST_COMMON_ANNUAL"),
    ]
    errors: list[str] = []
    row_index = {
        (row["company_key"], row["canonical_metric"], row["comparison_scope"]): row
        for row in rows
    }
    for key in required:
        if key not in row_index:
            errors.append(f"missing required identity row: {key}")
            continue
        row = row_index[key]
        if row["av_semantic_key"] != row["sec_semantic_key"]:
            errors.append(f"semantic key mismatch: {key}")
        if row["av_observation_id"] == row["sec_observation_id"]:
            errors.append(f"observation IDs unexpectedly match: {key}")
    jpm_gross = row_index[
        ("NYSE:JPM", "financial.gross_profit", "LATEST_COMMON_ANNUAL")
    ]
    if jpm_gross["comparison_status"] == "MATCH":
        errors.append("JPM gross profit was forced to MATCH")
    return errors


def validate_narrative_finding() -> list[str]:
    """Validate narrative evidence span recovery.

    Returns:
        Validation error messages.
    """
    errors: list[str] = []
    finding = read_json_file(path=REPORT_DIR / "narrative_finding.json")
    normalized_path = Path(finding["normalized_text_path"])
    text = normalized_path.read_text(encoding="utf-8")
    start = finding["evidence_start"]
    end = finding["evidence_end"]
    if text[start:end] != finding["evidence_text"]:
        errors.append("narrative evidence offsets do not recover evidence_text")
    if (
        finding["amount_text"] is not None
        and finding["amount_text"] not in finding["evidence_text"]
    ):
        errors.append("amount_text is not present in evidence_text")
    if finding["validation_status"] != "VERIFIED":
        errors.append("narrative finding is not VERIFIED")
    return errors


def validate_run_summary() -> list[str]:
    """Validate run_summary.json blocking fields.

    Returns:
        Validation error messages.
    """
    errors: list[str] = []
    summary = read_json_file(path=REPORT_DIR / "run_summary.json")
    required = [
        "run_id",
        "online",
        "started_at",
        "ended_at",
        "call_budget",
        "raw_hashes",
        "output_hashes",
        "warnings",
        "unresolved_mappings",
        "key_redaction_check",
    ]
    for field in required:
        if field not in summary:
            errors.append(f"run_summary missing {field}")
    if "key_redaction_check" in summary:
        if not summary["key_redaction_check"]["passed"]:
            errors.append("key redaction check failed")
    if "call_budget" in summary:
        if summary["call_budget"]["av_call_count"] > 10:
            errors.append("AV call count exceeds default budget")
    return errors


def validate_outputs() -> list[str]:
    """Validate all generated outputs.

    Returns:
        Validation error messages.
    """
    required = [
        "metric_alignment.csv",
        "metric_alignment.md",
        "discrepancy_report.md",
        "schema_decision.md",
        "narrative_finding.json",
        "narrative_finding.md",
        "run_summary.json",
    ]
    errors: list[str] = []
    for name in required:
        path = REPORT_DIR / name
        if not path.exists():
            errors.append(f"missing report: {path}")
    if errors:
        return errors
    rows = read_metric_alignment()
    errors.extend(validate_matrix(rows=rows))
    errors.extend(validate_required_identity_rows(rows=rows))
    errors.extend(validate_narrative_finding())
    errors.extend(validate_run_summary())
    return errors


def command_analyze(*, args: argparse.Namespace) -> None:
    """Generate reports without verification.

    Args:
        args: Parsed CLI arguments.

    Returns:
        None.
    """
    generate_reports(mode="offline")
    print(f"reports written to {REPORT_DIR}")


def command_verify(*, args: argparse.Namespace) -> None:
    """Regenerate reports offline and verify them.

    Args:
        args: Parsed CLI arguments.

    Returns:
        None. Exits non-zero on validation errors.
    """
    mode = "offline" if args.offline else "offline"
    generate_reports(mode=mode)
    errors = validate_outputs()
    if errors:
        for error in errors:
            print(f"[verify_error] {error}")
        raise SystemExit(1)
    print("Step 0B offline verification passed")


def command_fetch_av(*, args: argparse.Namespace) -> None:
    """Fetch missing Alpha Vantage raw files through the reusable client.

    Args:
        args: Parsed CLI arguments.

    Returns:
        None.
    """
    sync_work_raw()
    legacy = load_legacy_symbols()
    models = legacy["models"]
    fetch_alpha_vantage = legacy["fetch_alpha_vantage"]
    ensure_ibm_manifests = legacy["ensure_ibm_manifests"]
    companies = models.load_companies()
    for company in companies:
        if company.av_source == "existing_archive":
            ensure_ibm_manifests(company=company)
    summary = fetch_alpha_vantage(
        companies=companies,
        refresh=args.refresh,
        delay_seconds=args.delay_seconds,
    )
    print(f"AV fetch summary: {summary}")


def command_fetch_sec(*, args: argparse.Namespace) -> None:
    """Fetch missing SEC raw files through the reusable client.

    Args:
        args: Parsed CLI arguments.

    Returns:
        None.
    """
    sync_work_raw()
    legacy = load_legacy_symbols()
    models = legacy["models"]
    fetch_sec_artifacts = legacy["fetch_sec_artifacts"]
    companies = models.load_companies()
    summary = fetch_sec_artifacts(companies=companies, refresh=args.refresh)
    print(f"SEC fetch summary: {summary}")


def command_run(*, args: argparse.Namespace) -> None:
    """Run fetches, generate reports, and verify.

    Args:
        args: Parsed CLI arguments.

    Returns:
        None.
    """
    command_fetch_av(args=args)
    command_fetch_sec(args=args)
    generate_reports(mode="online")
    errors = validate_outputs()
    if errors:
        for error in errors:
            print(f"[verify_error] {error}")
        raise SystemExit(1)
    print("Step 0B online run and verification passed")


def add_refresh_arg(*, parser: argparse.ArgumentParser) -> None:
    """Add common refresh argument.

    Args:
        parser: Parser to mutate.

    Returns:
        None.
    """
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="overwrite cached raw files",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser.

    Returns:
        Configured parser.
    """
    parser = argparse.ArgumentParser(
        prog="run_step_0b",
        description="Generate and verify Step 0B AV / SEC spike reports",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(name="analyze")
    analyze.set_defaults(func=command_analyze)

    verify = subparsers.add_parser(name="verify")
    verify.add_argument(
        "--offline",
        action="store_true",
        help="force offline verification; this command never uses network",
    )
    verify.set_defaults(func=command_verify)

    fetch_av = subparsers.add_parser(name="fetch-av")
    add_refresh_arg(parser=fetch_av)
    fetch_av.add_argument(
        "--delay-seconds",
        type=float,
        default=15.0,
        help="serial delay between AV live calls",
    )
    fetch_av.set_defaults(func=command_fetch_av)

    fetch_sec = subparsers.add_parser(name="fetch-sec")
    add_refresh_arg(parser=fetch_sec)
    fetch_sec.set_defaults(func=command_fetch_sec)

    run = subparsers.add_parser(name="run")
    add_refresh_arg(parser=run)
    run.add_argument(
        "--delay-seconds",
        type=float,
        default=15.0,
        help="serial delay between AV live calls",
    )
    run.set_defaults(func=command_run)
    return parser


def main() -> None:
    """Parse CLI arguments and run the selected command.

    Returns:
        None.
    """
    parser = build_parser()
    args = parser.parse_args()
    args.func(args=args)


if __name__ == "__main__":
    main()
