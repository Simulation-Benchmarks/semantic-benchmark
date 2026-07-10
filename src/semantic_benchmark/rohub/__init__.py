"""RoHub helpers for semantic benchmark provenance."""

from semantic_benchmark.rohub import provenance as _provenance
from semantic_benchmark.rohub.provenance import *  # noqa: F401,F403

_DOWNLOAD_EXPORTS = {
    "ANNOTATION_COLLECTION_TYPE",
    "SOFTWARE_SOURCE_CODE_TYPE",
    "download_benchmark_resource",
    "download_benchmark_resources",
    "select_resource_identifier",
    "validate_uuid",
}


def configure_repository_settings(
    rohub_config: dict | None = None,
) -> None:
    """Override packaged settings with repository-specific settings."""
    if rohub_config is not None:
        _provenance.ROHUB_CONFIG = rohub_config
        globals()["ROHUB_CONFIG"] = rohub_config


def __getattr__(name: str):
    if name in _DOWNLOAD_EXPORTS:
        from semantic_benchmark.rohub import download

        value = getattr(download, name)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
