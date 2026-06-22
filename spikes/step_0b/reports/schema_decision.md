# Step 0B Schema Decision

## Conclusion

PASS WITH REQUIRED CHANGES.

The spike is reproducible and source-honest, but the formal Silver schema must add source observation identity, mapping lineage, applicability, and composite lineage before AV V1 hardens.

## Required Semantic Key

`semantic_key = hash(company_id, metric_key, period_type, period_start, period_end, canonical_dimensions)`.

`source_system` and comparison query scope must not enter `semantic_key`.

## Required Observation Identity

`observation_id = hash(source_system, semantic_key, provider metric key or SEC concept, source artifact hash, source record key, normalized source value, and revision metadata)`.

AV and SEC can therefore share one semantic key while retaining different source observations.

If a source has no selected observation, `observation_id` must be `NULL` rather than a hash of empty source fields.

Source-honest rows should preserve `raw_value` and store any comparison-only value separately.

## Period Rules

`period_start`, `period_end`, and `period_type` are required in Silver. Instant facts should use `period_start = period_end` in curated Silver rather than relying on nulls.

## Dimensions and Reporting Scope

`dimensions` should be a JSON/MAP structure covering entity scope, reporting basis, statement role, consolidation scope, segment, and future SEC dimensions.

## Mapping Rule ID

`mapping_rule_id` is required. It should version the canonical metric mapping, candidate concept list, applicability policy, period policy, and normalization policy.

## Applicability

Store `applicability_status` separately from `comparison_status`: `APPLICABLE`, `NOT_APPLICABLE`, `INDUSTRY_LIMITED`, or `REQUIRES_REVIEW`.

## Composite Metric Lineage

Composite observations need a child component table or JSON lineage array with component concept, value, unit, sign, accession, filed date, raw artifact hash, and formula role.

## Required Silver Changes Before AV V1

- Add `semantic_key` and `observation_id` as separate fields.
- Add `source_system`, `source_artifact_hash`, `fetched_at`, and raw path.
- Add `mapping_rule_id` and `mapping_version`.
- Add `applicability_status` and `comparison_status`.
- Add composite lineage support for total debt and future formulas.
- Treat `period_start` as required in curated Silver.

## Deferred to SEC Financial Stage

- Full SEC concept search across dimensional and statement-role variants.
- YTD-to-quarter derivation.
- Industry-specific banking metrics.
- Production amendment and restatement policy.

## Owners and Next Steps

- Data model owner: update metric observation DDL with the fields listed above.
- AV V1 owner: implement ingestion against this schema using AV raw-first observations.
- SEC stage owner: keep this spike as evidence, but do not promote SEC financial fetching into AV V1.
