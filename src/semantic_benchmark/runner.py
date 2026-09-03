"""Reusable building blocks for semantic benchmark command-line runners."""

import json
import logging
import re
import shutil
import zipfile
from pathlib import Path
from collections.abc import Iterable
from typing import Any, Mapping

from . import rocrate
from .semantics import BenchmarkLoader, SemanticBenchmark, TextParameter

LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"


def configure_logging() -> None:
    """Configure the default logging used by benchmark runners."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def extract_archive(archive: Path, output_dir: Path) -> None:
    """Extract a benchmark archive into *output_dir*."""
    with zipfile.ZipFile(archive.expanduser().resolve(), "r") as zip_ref:
        zip_ref.extractall(output_dir)


def create_shared_directory(benchmark_dir: Path, name: str) -> Path:
    """Create and return a shared workflow directory."""
    shared_dir = benchmark_dir / name
    shared_dir.mkdir(parents=True, exist_ok=True)
    return shared_dir


def resolve_unit_symbol(unit: str, unit_symbols: Mapping[str, str]) -> str | None:
    """Resolve a unit by exact spelling or by its URI/CURIE fragment."""
    if unit in unit_symbols:
        return unit_symbols[unit]
    fragment = re.split(r"[:/#]", unit)[-1].upper()
    return unit_symbols.get(fragment)


def parameter_json_key(parameter: Any, unit_symbols: Mapping[str, str]) -> str:
    """Build a parameter key, adding a unit suffix when it can be resolved."""
    if not parameter.unit:
        return parameter.label
    symbol = resolve_unit_symbol(parameter.unit, unit_symbols)
    return f"{parameter.label}[{symbol}]" if symbol else parameter.label


def parameter_json_value(parameter: Any) -> Any:
    """Extract the scalar value from a semantic benchmark parameter."""
    if isinstance(parameter, TextParameter):
        return parameter.string_value
    return getattr(parameter, "numerical_value", None)


def create_parameter_files(
    benchmark: SemanticBenchmark,
    output_dir: Path,
    unit_symbols: Mapping[str, str],
    *,
    strict_units: bool = False,
) -> list[Path]:
    """Create one ``parameters_*.json`` file per benchmark configuration."""
    for stale_file in output_dir.glob("parameters_*.json"):
        stale_file.unlink()

    created = []
    for configuration in benchmark.parameter_sets:
        if not configuration.identifier:
            continue
        payload = {"configuration": configuration.identifier}
        for parameter in configuration.parts:
            if (
                parameter.unit
                and strict_units
                and not resolve_unit_symbol(parameter.unit, unit_symbols)
            ):
                raise ValueError(
                    f"Unrecognized unit {parameter.unit!r}; add it to unit_symbols."
                )
            payload[parameter_json_key(parameter, unit_symbols)] = parameter_json_value(
                parameter
            )
        parameter_file = output_dir / f"parameters_{configuration.identifier}.json"
        parameter_file.write_text(json.dumps(payload, indent=4) + "\n")
        created.append(parameter_file)
    return created


def prepare_benchmark(
    benchmark_file: Path,
    benchmark_dir: Path,
    unit_symbols: Mapping[str, str],
    *,
    archive: Path | None = None,
    shared_directories: Iterable[str] = (),
    strict_units: bool = False,
) -> SemanticBenchmark:
    """Prepare common inputs and load a semantic benchmark run.

    Optionally extracts a workflow archive, creates shared workflow
    directories, and always generates the configuration parameter files.
    """
    if archive is not None:
        extract_archive(archive, benchmark_dir)
    for directory_name in shared_directories:
        create_shared_directory(benchmark_dir, directory_name)

    benchmark = BenchmarkLoader(benchmark_file).load()
    create_parameter_files(
        benchmark,
        benchmark_dir,
        unit_symbols,
        strict_units=strict_units,
    )
    return benchmark


def prepare_configuration(
    parameter_file: Path,
    benchmark_dir: Path,
) -> tuple[str, Path]:
    """Create a configuration result directory and populate its common files."""
    configuration_data = json.loads(parameter_file.read_text())
    configuration = configuration_data.get("configuration")
    if not configuration:
        raise ValueError(f"Missing configuration value in {parameter_file}")

    output_dir = benchmark_dir / "results" / configuration
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "parameters.json").write_text(
        json.dumps(configuration_data, indent=2)
    )
    for item in benchmark_dir.iterdir():
        if item.is_file() and not (
            item.name.startswith("parameters_") and item.suffix == ".json"
        ):
            shutil.copy(item, output_dir / item.name)
    return configuration, output_dir


def build_provenance_reporter_args(
    configuration: str,
    *,
    tool_name: str,
    report_name: str,
    report_description: str,
    report_license: str,
) -> list[str]:
    """Build metadata4ing reporter arguments for a workflow invocation."""
    return [
        "--reporter",
        "metadata4ing",
        "--report-metadata4ing-filename",
        f"{tool_name}-{configuration}",
        "--report-metadata4ing-name",
        report_name,
        "--report-metadata4ing-description",
        report_description,
        "--report-metadata4ing-license",
        report_license,
        "--report-metadata4ing-profile",
        "provenance-run-crate-0.5",
    ]


def create_aggregate_rocrate(
    results_dir: Path,
    benchmark: SemanticBenchmark,
    rocrate_path: Path,
    *,
    software_name: str,
    crate_license: str,
    crate_name: str,
    crate_description: str,
    validation_dir: Path | None = None,
) -> None:
    """Create the aggregate RO-Crate shared by benchmark runners."""
    options = {}
    if validation_dir is not None:
        options["validation_dir"] = validation_dir
    rocrate.create_main_ro(
        path=str(results_dir),
        benchmark_object=benchmark,
        rocrate_path=str(rocrate_path),
        software_name=software_name,
        crate_license=crate_license,
        crate_name=crate_name,
        crate_description=crate_description,
        validation_profile="provenance-run-crate-0.5",
        **options,
    )
