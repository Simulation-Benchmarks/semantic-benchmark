"""Download benchmark resources from RoHub research objects."""

from __future__ import annotations

import argparse
import logging
from uuid import UUID

import rohub

from semantic_benchmark.rohub.provenance import login_to_rohub

SOFTWARE_SOURCE_CODE_TYPE = "Software source code"
ANNOTATION_COLLECTION_TYPE = "Annotation Collection"

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


def select_resource_identifier(resources, resource_type: str) -> str:
    """Return the single resource identifier matching the requested RoHub type."""
    required_columns = {"identifier", "type"}
    missing_columns = required_columns.difference(resources.columns)
    if missing_columns:
        raise ValueError(
            "Resource list is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    matching_resources = resources.loc[
        resources["type"] == resource_type, "identifier"
    ].dropna()

    if matching_resources.empty:
        raise ValueError(f"No resource found with type: {resource_type}")

    if len(matching_resources) > 1:
        raise ValueError(
            f"Expected one resource with type '{resource_type}', "
            f"found {len(matching_resources)}."
        )

    return str(matching_resources.iloc[0])


def download_benchmark_resource(
    identifier: str,
    resource_filename: str,
    resource_type: str,
) -> str:
    """Load a research object and download its resource of the given type."""
    research_object = rohub.ros_load(identifier)
    resources = research_object.list_resources()
    resource_identifier = select_resource_identifier(resources, resource_type)

    LOGGER.info(
        "Downloading %s resource %s to %s",
        resource_type,
        resource_identifier,
        resource_filename,
    )
    rohub.resource_download(resource_identifier, resource_filename)
    return resource_identifier


def download_benchmark_resources(
    identifier: str,
    username: str,
    password: str,
    zip_resource_filename: str | None = None,
    semantic_resource_filename: str | None = None,
    use_production_rohub: bool = False,
) -> dict[str, str]:
    """Authenticate with RoHub and download selected benchmark resources."""
    if not zip_resource_filename and not semantic_resource_filename:
        raise ValueError(
            "Provide zip_resource_filename, semantic_resource_filename, or both."
        )

    login_to_rohub(
        username=username,
        password=password,
        use_production_rohub=use_production_rohub,
    )

    downloaded_resources = {}

    if zip_resource_filename:
        downloaded_resources[SOFTWARE_SOURCE_CODE_TYPE] = (
            download_benchmark_resource(
                identifier=identifier,
                resource_filename=zip_resource_filename,
                resource_type=SOFTWARE_SOURCE_CODE_TYPE,
            )
        )

    if semantic_resource_filename:
        downloaded_resources[ANNOTATION_COLLECTION_TYPE] = (
            download_benchmark_resource(
                identifier=identifier,
                resource_filename=semantic_resource_filename,
                resource_type=ANNOTATION_COLLECTION_TYPE,
            )
        )

    return downloaded_resources


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
        "--zip-resource-filename",
        type=str,
        default=None,
        help="Output filename for the Software source code resource.",
    )
    parser.add_argument(
        "--semantic-resource-filename",
        type=str,
        default=None,
        help="Output filename for the Annotation Collection resource.",
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
        zip_resource_filename=args.zip_resource_filename,
        semantic_resource_filename=args.semantic_resource_filename,
        use_production_rohub=args.use_production_rohub,
    )


if __name__ == "__main__":
    main()
