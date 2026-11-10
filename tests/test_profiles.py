"""Profile inputs for aggregate RO-Crate creation."""

from pathlib import Path

import pytest
from rocrate.rocrate import ROCrate

from semantic_benchmark.profiles import load_aggregate_profile
from semantic_benchmark.rocrate.create import (
    _add_software_node,
    _add_tool_parameters,
    add_tool_parameter,
    parse_args,
)
from semantic_benchmark import runner
from semantic_benchmark import rocrate
from semantic_benchmark.semantics import AggregateProfile, SemanticBenchmark


def profile_file(tmp_path: Path) -> Path:
    path = tmp_path / "aggregate-crate.yml"
    path.write_text(
        'software-name: "FEniCS"\n'
        'software-version: "0.9.0"\n'
        'software-url: "https://example.org/software"\n'
        'crate-license: "https://example.org/license"\n'
        'agent-name: "Example Author"\n'
        'agent-orcid: "https://orcid.org/0000-0000-0000-0000"\n'
        'crate-name: "Example crate"\n'
        'crate-description: "Example run"\n'
    )
    return path


def test_load_aggregate_profile(tmp_path: Path) -> None:
    metadata = load_aggregate_profile(profile_file(tmp_path))
    assert metadata == AggregateProfile(
        software_name="FEniCS",
        software_version="0.9.0",
        software_url="https://example.org/software",
        crate_license="https://example.org/license",
        crate_name="Example crate",
        crate_description="Example run",
        agent_name="Example Author",
        agent_orcid="https://orcid.org/0000-0000-0000-0000",
    )
    assert metadata.crate_description == "Example run"
    renamed = tmp_path / "custom-profile.yml"
    profile_file(tmp_path).rename(renamed)
    assert load_aggregate_profile(renamed) == metadata
    with pytest.raises(IsADirectoryError):
        load_aggregate_profile(tmp_path)


def test_tool_parameter_links_to_software() -> None:
    benchmark = SemanticBenchmark(id="example")
    add_tool_parameter(benchmark, "cell_type", "Text", "triangle", "Mesh cell type")
    crate = ROCrate()
    _add_software_node(crate, "#tool", "FEniCS")
    _add_tool_parameters(crate, "#tool", benchmark.tool_parameters)

    software = crate.get("#tool").as_jsonld()
    parameter = crate.get(software["input"][0]["@id"]).as_jsonld()
    assert parameter["@type"] == "FormalParameter"
    assert parameter["name"] == "cell_type"
    assert parameter["additionalType"] == "Text"
    assert parameter["defaultValue"] == "triangle"
    assert parameter["description"] == "Mesh cell type"

    with pytest.raises(ValueError, match="name"):
        add_tool_parameter(benchmark, "", "Text", "triangle")


def test_missing_metadata_is_reported(tmp_path: Path) -> None:
    path = profile_file(tmp_path)
    path.write_text(path.read_text().replace('crate-name: "Example crate"\n', ''))
    with pytest.raises(ValueError, match="missing"):
        load_aggregate_profile(path)


def test_build_subcrate_args_from_exact_file(tmp_path: Path) -> None:
    profile = tmp_path / "custom-subcrate.yml"
    profile.write_text(
        'report-rocrate-filename: "workflow-run"\n'
        'report-rocrate-run-name: "Plate benchmark"\n'
    )
    assert runner.build_subcrate_args(profile) == [
        "--reporter", "rocrate",
        "--report-rocrate-filename", "workflow-run",
        "--report-rocrate-run-name", "Plate benchmark",
    ]
    with pytest.raises(IsADirectoryError):
        runner.build_subcrate_args(tmp_path)


def test_runner_uses_profile_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    monkeypatch.setattr(rocrate, "create_main_ro", lambda **kwargs: captured.update(kwargs))
    benchmark = SemanticBenchmark(id="example")
    monkeypatch.setattr(runner, "BenchmarkLoader", lambda path: type("Loader", (), {"load": lambda self: benchmark})())
    prepared = runner.prepare_benchmark(
        tmp_path / "benchmark.json", tmp_path, {},
        aggregate_profile=profile_file(tmp_path),
    )
    assert prepared.aggregate_profile.software_version == "0.9.0"
    runner.create_aggregate_rocrate(
        tmp_path, prepared, tmp_path / "crate.zip",
        subcrate_paths=[], workflow_path=tmp_path / "workflow.yml",
    )
    assert captured["aggregate_profile"] is prepared.aggregate_profile
    assert captured["aggregate_profile"].crate_description == "Example run"


def test_cli_requires_profile_and_rejects_individual_metadata(tmp_path: Path) -> None:
    command = [
        "--benchmark-file", "benchmark.json", "--simulation-result-path", "results",
        "--subcrate-path", "run.zip", "--rocrate-path", "aggregate.zip",
        "--workflow-path", "workflow.yml",
    ]
    with pytest.raises(SystemExit):
        parse_args(command)
    with pytest.raises(SystemExit):
        parse_args(command + ["--profile", str(profile_file(tmp_path)), "--crate-name", "override"])
    with pytest.raises(SystemExit):
        parse_args(command + ["--profile", str(profile_file(tmp_path)), "--branch-name", "main"])
    args = parse_args(command + ["--profile", str(profile_file(tmp_path))])
    assert args.profile == profile_file(tmp_path)
