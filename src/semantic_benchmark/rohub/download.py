"""Download benchmark resources from RoHub research objects."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from uuid import UUID

import rohub

LOGGER = logging.getLogger(__name__)
LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"


def validate_uuid(value: str) -> str:
    """Validate a command-line UUID while preserving its original string form."""
    try:
        UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Expected a UUID identifier, got: {value}"
        ) from exc
    return value


def _matching_resource_names(resource) -> set[str]:
    """Build comparable resource names from a RoHub resource row."""
    candidates = set()
    for column in ("name", "filename", "title"):
        value = resource.get(column)
        if isinstance(value, str) and value:
            candidates.add(value)
            candidates.add(Path(value).name)

    path_value = resource.get("path")
    if isinstance(path_value, str) and path_value:
        candidates.add(path_value)
        candidates.add(Path(path_value).name)
    return candidates


def select_resource_identifier(resources, resource_name: str) -> str:
    """Return the single resource identifier matching the requested resource name."""
    required_columns = {"identifier"}
    missing_columns = required_columns.difference(resources.columns)
    if missing_columns:
        raise ValueError(
            "Resource list is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    if not {"name", "filename", "title", "path"}.intersection(resources.columns):
        raise ValueError(
            "Resource list is missing any supported name columns: "
            "name, filename, title, path"
        )

    requested_name = Path(resource_name).name
    candidate_resources = resources
    if "source" in resources.columns:
        internal_resources = resources.loc[resources["source"] == "internal"]
        if not internal_resources.empty:
            candidate_resources = internal_resources

    matching_identifiers = []
    for _, resource in candidate_resources.iterrows():
        if requested_name in _matching_resource_names(resource):
            identifier = resource.get("identifier")
            if identifier:
                matching_identifiers.append(str(identifier))

    if not matching_identifiers:
        raise ValueError(f"No resource found with name: {requested_name}")

    if len(matching_identifiers) > 1:
        raise ValueError(
            f"Expected one resource named '{requested_name}', "
            f"found {len(matching_identifiers)}."
        )

    return matching_identifiers[0]


def download_benchmark_resource(
    identifier: str,
    resource_filename: str,
    resource_name: str,
) -> str:
    """Load a research object and download its named resource."""
    research_object = rohub.ros_load(identifier)
    resources = research_object.list_resources()
    resource_identifier = select_resource_identifier(resources, resource_name)

    LOGGER.info(
        "Downloading resource %s (%s) to %s",
        resource_name,
        resource_identifier,
        resource_filename,
    )
    rohub.resource_download(resource_identifier, resource_filename)
    return resource_identifier


def download_benchmark_resources(
    identifier: str,
    username: str,
    password: str,
    semantic_resource_filename: str | None = None,
    use_production_rohub: bool = False,
) -> dict[str, str]:
    """Authenticate with RoHub and download the semantic benchmark resource."""
    from semantic_benchmark.rohub.provenance import login_to_rohub

    if not semantic_resource_filename:
        raise ValueError("Provide semantic_resource_filename.")

    login_to_rohub(
        username=username,
        password=password,
        use_production_rohub=use_production_rohub,
    )

    resource_name = Path(semantic_resource_filename).name
    resource_identifier = download_benchmark_resource(
        identifier=identifier,
        resource_filename=semantic_resource_filename,
        resource_name=resource_name,
    )
    return {"semantic_resource": resource_identifier}


def parse_args(argv=None):
    """Parse command-line arguments for benchmark resource downloads."""
    parser = argparse.ArgumentParser(
        description="Download benchmark resources from a RoHub research object."
    )
    parser.add_argument(
        "--identifier",
        type=validate_uuid,
        required=True,
        help="UUID identifier of the RoHub research object.",
    )
    parser.add_argument(
        "--username",
        type=str,
        required=True,
        help="Username for RoHub.",
    )
    parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="Password for RoHub.",
    )
    parser.add_argument(
        "--semantic-resource-filename",
        type=str,
        required=True,
        help="Output filename for the semantic benchmark resource.",
    )
    parser.add_argument(
        "--use-production-rohub",
        action="store_true",
        help="Use production RoHub instead of the development instance.",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Run the command-line entrypoint."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args = parse_args()
    download_benchmark_resources(
        identifier=args.identifier,
        username=args.username,
        password=args.password,
        semantic_resource_filename=args.semantic_resource_filename,
        use_production_rohub=args.use_production_rohub,
    )


if __name__ == "__main__":
    main()
