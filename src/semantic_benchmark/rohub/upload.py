"""Command-line interface for uploading benchmark provenance to RoHub."""

import argparse

from semantic_benchmark.rohub.provenance import upload_provenance_rocrate


def parse_args(argv=None):
    """Parse command-line arguments for RoHub provenance upload."""
    parser = argparse.ArgumentParser(
        description="Upload benchmark provenance RO-Crates to RoHub."
    )
    parser.add_argument(
        "--provenance_folderpath",
        type=str,
        required=True,
        help="Path to the provenance RO-Crate ZIP file",
    )
    parser.add_argument(
        "--benchmark-name",
        type=str,
        required=True,
        help="Name of the benchmark to be uploaded",
    )
    parser.add_argument(
        "--username",
        type=str,
        required=True,
        help="Username for RoHub",
    )
    parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="Password for RoHub",
    )
    parser.add_argument(
        "--code-repository-url",
        type=str,
        default=None,
        help="Full GitHub branch URL to annotate as schema.org/codeRepository",
    )
    parser.add_argument(
        "--used-software-url",
        type=str,
        default=None,
        help="Software identifier URL to annotate as prov:used",
    )
    parser.add_argument(
        "--use-production-rohub",
        action="store_true",
        default=False,
        help="Use production RoHub instead of the development instance.",
    )
    return parser.parse_args(argv)


def main():
    """Upload a provenance RO-Crate using the supplied arguments."""
    args = parse_args()
    upload_provenance_rocrate(
        provenance_folderpath=args.provenance_folderpath,
        benchmark_name=args.benchmark_name,
        username=args.username,
        password=args.password,
        code_repository_url=args.code_repository_url,
        used_software_url=args.used_software_url,
        use_production_rohub=args.use_production_rohub,
    )


if __name__ == "__main__":
    main()
