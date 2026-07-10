"""RoHub helpers for semantic benchmark provenance."""

_DOWNLOAD_EXPORTS = {
    "ANNOTATION_COLLECTION_TYPE",
    "SOFTWARE_SOURCE_CODE_TYPE",
    "download_benchmark_resource",
    "download_benchmark_resources",
    "select_resource_identifier",
    "validate_uuid",
}

_PROVENANCE_EXPORTS = {
    "ROHUB_CONFIG",
    "ANNOTATION_PREDICATE",
    "BENCHMARK_BASE_URL",
    "CODE_REPOSITORY_PREDICATE",
    "SOFTWARE_USED_PREDICATE",
    "SCHEMA_PREFIX",
    "FORMAL_PARAMETER_TYPE",
    "FOAF_NAME",
    "sanitize_variable_name",
    "configure_rohub",
    "login_to_rohub",
    "benchmark_annotation_object",
    "build_benchmark_ro_uuids_query",
    "build_annotated_ro_uuids_query",
    "query_sparql",
    "build_named_graph_query",
    "query_metric_data_from_named_graphs",
    "filter_by_tool",
    "find_benchmark_ro_uuids",
    "extract_uuids_from_subjects",
    "find_annotated_ro_uuids",
    "find_named_graphs_for_uuids",
    "fetch_benchmark_data",
    "load_benchmark_metric_data",
    "delete_research_objects_by_annotations",
    "upload_research_object",
    "wait_for_job_success",
    "add_benchmark_annotation",
    "upload_provenance_rocrate",
}

__all__ = [
    "configure_repository_settings",
    *sorted(_DOWNLOAD_EXPORTS),
    *sorted(_PROVENANCE_EXPORTS),
]


def _load_provenance_module():
    from semantic_benchmark.rohub import provenance

    return provenance


def _load_download_module():
    from semantic_benchmark.rohub import download

    return download


def configure_repository_settings(
    rohub_config: dict | None = None,
) -> None:
    """Override packaged settings with repository-specific settings."""
    if rohub_config is not None:
        provenance = _load_provenance_module()
        provenance.ROHUB_CONFIG = rohub_config
        globals()["ROHUB_CONFIG"] = rohub_config


def __getattr__(name: str):
    if name in _DOWNLOAD_EXPORTS:
        download = _load_download_module()
        value = getattr(download, name)
        globals()[name] = value
        return value

    if name in _PROVENANCE_EXPORTS:
        provenance = _load_provenance_module()
        value = getattr(provenance, name)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
