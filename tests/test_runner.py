import json
from types import SimpleNamespace

import pytest

from semantic_benchmark.runner import (
    build_provenance_reporter_args,
    create_parameter_files,
    parameter_json_key,
    prepare_benchmark,
    prepare_configuration,
    resolve_unit_symbol,
)


def test_reporter_always_uses_provenance_run_crate_profile():
    arguments = build_provenance_reporter_args(
        "case",
        tool_name="solver",
        report_name="Report",
        report_description="Description",
        report_license="MIT",
    )
    assert arguments[-2:] == [
        "--report-metadata4ing-profile",
        "provenance-run-crate-0.5",
    ]


def test_resolve_unit_symbol_accepts_curie_uri_and_exact_keys():
    symbols = {"M": "m", "unit:RAD-PER-SEC": "rad/s"}
    assert resolve_unit_symbol("unit:M", symbols) == "m"
    assert resolve_unit_symbol("https://example.org/M", symbols) == "m"
    assert resolve_unit_symbol("unit:RAD-PER-SEC", symbols) == "rad/s"


def test_parameter_key_omits_unknown_unit():
    parameter = SimpleNamespace(label="speed", unit="unit:UNKNOWN")
    assert parameter_json_key(parameter, {}) == "speed"


def test_prepare_configuration_copies_workflow_files(tmp_path):
    (tmp_path / "Snakefile").write_text("rule all:\n")
    (tmp_path / "parameters_old.json").write_text("{}")
    parameter_file = tmp_path / "parameters_case.json"
    parameter_file.write_text(json.dumps({"configuration": "case", "x[m]": 1}))

    configuration, output_dir = prepare_configuration(parameter_file, tmp_path)

    assert configuration == "case"
    assert json.loads((output_dir / "parameters.json").read_text())["x[m]"] == 1
    assert (output_dir / "Snakefile").exists()
    assert not (output_dir / "parameters_old.json").exists()


def test_prepare_configuration_requires_identifier(tmp_path):
    parameter_file = tmp_path / "parameters_bad.json"
    parameter_file.write_text("{}")
    with pytest.raises(ValueError, match="Missing configuration"):
        prepare_configuration(parameter_file, tmp_path)


def test_create_parameter_files_can_reject_unknown_units(tmp_path):
    parameter = SimpleNamespace(label="speed", unit="unit:UNKNOWN", numerical_value=1)
    benchmark = SimpleNamespace(
        parameter_sets=[SimpleNamespace(identifier="case", parts=[parameter])]
    )
    with pytest.raises(ValueError, match="Unrecognized unit"):
        create_parameter_files(benchmark, tmp_path, {}, strict_units=True)


def test_prepare_benchmark_creates_shared_directories_and_parameters(
    tmp_path, monkeypatch
):
    benchmark = SimpleNamespace(parameter_sets=[])
    loader = SimpleNamespace(load=lambda: benchmark)
    monkeypatch.setattr(
        "semantic_benchmark.runner.BenchmarkLoader", lambda benchmark_file: loader
    )

    result = prepare_benchmark(
        tmp_path / "benchmark.jsonld",
        tmp_path,
        {},
        shared_directories=("conda_envs", "apptainer_envs"),
    )

    assert result is benchmark
    assert (tmp_path / "conda_envs").is_dir()
    assert (tmp_path / "apptainer_envs").is_dir()
