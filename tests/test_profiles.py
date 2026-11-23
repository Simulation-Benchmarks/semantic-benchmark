"""Profile inputs for main RO-Crate creation."""

import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from rocrate.rocrate import ROCrate

from semantic_benchmark.profiles import load_main_profile
from semantic_benchmark.rocrate.create import (
    _add_configuration_nodes,
    _add_evaluates_nodes,
    _add_formal_parameter,
    _add_software_node,
    _add_tool_parameters,
    _add_workflow_node,
    add_tool_parameter,
    parse_args,
)
from semantic_benchmark import runner
from semantic_benchmark import rocrate
from semantic_benchmark.semantics import (
    FieldMapping,
    MainProfile,
    NumericalParameter,
    NumericalVariable,
    ParameterSet,
    ProcessingStep,
    SemanticBenchmark,
)
from semantic_benchmark.semantics.models import ProfilePerson


def profile_file(tmp_path: Path) -> Path:
    path = tmp_path / "main-crate.yml"
    path.write_text(
        'software-name: "FEniCS"\n'
        'software-version: "0.9.0"\n'
        'software-url: "https://example.org/software"\n'
        'crate-license: "https://example.org/license"\n'
        'authors:\n  - name: "Example Author"\n    orcid: "https://orcid.org/0000-0000-0000-0000"\n'
        '  - name: "Second Author"\n    orcid: "https://orcid.org/0000-0000-0000-0001"\n'
        'creator:\n  name: "Mahdi Jafarkhani"\n  orcid: "https://orcid.org/0009-0008-6162-8404"\n'
        'crate-name: "Example crate"\n'
        'crate-description: "Example run"\n'
    )
    return path


def test_load_main_profile(tmp_path: Path) -> None:
    metadata = load_main_profile(profile_file(tmp_path))
    assert metadata == MainProfile(
        software_name="FEniCS",
        software_version="0.9.0",
        software_url="https://example.org/software",
        crate_license="https://example.org/license",
        crate_name="Example crate",
        crate_description="Example run",
        authors=(
            ProfilePerson("Example Author", "https://orcid.org/0000-0000-0000-0000"),
            ProfilePerson("Second Author", "https://orcid.org/0000-0000-0000-0001"),
        ),
        creator=ProfilePerson("Mahdi Jafarkhani", "https://orcid.org/0009-0008-6162-8404"),
    )
    assert metadata.crate_description == "Example run"
    renamed = tmp_path / "custom-profile.yml"
    profile_file(tmp_path).rename(renamed)
    assert load_main_profile(renamed) == metadata
    with pytest.raises(IsADirectoryError):
        load_main_profile(tmp_path)


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


def test_workflow_defines_benchmark_inputs_and_outputs(tmp_path: Path) -> None:
    run_folder = tmp_path / "run-1"
    run_folder.mkdir()
    (run_folder / "results.json").write_text('{"metrics": {"error": 0.25}}')
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: example\n")
    parameter = NumericalParameter(id="radius", label="Radius", numerical_value=1.0)
    metric = NumericalVariable(
        id="error",
        label="Error",
        field_mapping=FieldMapping(
            field_id="error", file_object_label="results.json", json_path="/metrics/error"
        ),
    )
    benchmark = SemanticBenchmark(
        id="example",
        processing_steps=[
            ProcessingStep(
                id="step", configurations=[ParameterSet(id="config", parts=[parameter])]
            )
        ],
        evaluates=[metric],
    )
    add_tool_parameter(benchmark, "Grid.Cells0", "Integer", "40")
    crate = ROCrate()
    workflow_inputs: dict[str, dict[str, str]] = {}
    _add_configuration_nodes(crate, benchmark, workflow_inputs)
    output = _add_formal_parameter(crate, metric, {})
    results = _add_evaluates_nodes(crate, benchmark, [run_folder], {metric.id: output})
    _add_software_node(crate, "#tool", "Example tool")
    _add_tool_parameters(crate, "#tool", benchmark.tool_parameters)
    _add_workflow_node(
        crate, workflow_file, "#tool", "Example tool",
        (ProfilePerson("Example Author", "https://orcid.org/0000-0000-0000-0000"),),
        ProfilePerson("Example Author", "https://orcid.org/0000-0000-0000-0000"),
        list(workflow_inputs.values()), [output],
    )

    workflow = crate.get(workflow_file.name).as_jsonld()
    software = crate.get("#tool").as_jsonld()
    result = crate.get(results[0]["result_ids"][0]["@id"]).as_jsonld()
    assert {"File", "SoftwareSourceCode", "ComputationalWorkflow", "HowTo"}.issubset(
        set(workflow["@type"])
    )
    assert workflow["input"] == list(workflow_inputs.values())
    assert workflow["output"] == [output]
    assert result["exampleOfWork"] == output
    assert len(software["input"]) == 1
    assert software["input"][0]["@id"] not in workflow_inputs

    archive_path = tmp_path / "crate.zip"
    crate.write_zip(archive_path)
    with ZipFile(archive_path) as archive:
        metadata = json.loads(archive.read("ro-crate-metadata.json"))
    saved_workflow = next(
        node for node in metadata["@graph"] if node["@id"] == workflow_file.name
    )
    assert saved_workflow["input"] == workflow["input"]
    assert saved_workflow["output"] == workflow["output"]


def test_missing_metadata_is_reported(tmp_path: Path) -> None:
    path = profile_file(tmp_path)
    path.write_text(path.read_text().replace('crate-name: "Example crate"\n', ''))
    with pytest.raises(ValueError, match="missing"):
        load_main_profile(path)


def test_people_require_valid_structure(tmp_path: Path) -> None:
    path = profile_file(tmp_path)
    original = path.read_text()
    for old, new in [
        ('authors:\n  - name: "Example Author"\n    orcid: "https://orcid.org/0000-0000-0000-0000"\n  - name: "Second Author"\n    orcid: "https://orcid.org/0000-0000-0000-0001"\n', 'authors: []\n'),
        ('name: "Second Author"', 'name: ""'),
        ('creator:\n  name: "Mahdi Jafarkhani"\n  orcid: "https://orcid.org/0009-0008-6162-8404"\n', 'creator: "Mahdi Jafarkhani"\n'),
    ]:
        path.write_text(original.replace(old, new))
        with pytest.raises(ValueError):
            load_main_profile(path)


def test_workflow_has_multiple_authors_and_distinct_creator(tmp_path: Path) -> None:
    workflow = tmp_path / "Snakefile"
    workflow.write_text("rule all:\n    input: []\n")
    crate = ROCrate()
    authors = (
        ProfilePerson("Author One", "https://orcid.org/0000-0000-0000-0000"),
        ProfilePerson("Author Two", "https://orcid.org/0000-0000-0000-0001"),
    )
    creator = ProfilePerson("Creator", "https://orcid.org/0000-0000-0000-0002")
    _add_workflow_node(crate, workflow, "https://example.org/software", "Example tool", authors, creator, [], [])
    nodes = {node["@id"]: node for node in crate.metadata.generate()["@graph"]}
    workflow_node = nodes[workflow.name]
    assert workflow_node["author"] == [{"@id": person.orcid} for person in authors]
    assert workflow_node["creator"] == {"@id": creator.orcid}
    assert all(nodes[person.orcid]["name"] == person.name for person in (*authors, creator))


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
        main_profile=profile_file(tmp_path),
    )
    assert prepared.main_profile.software_version == "0.9.0"
    runner.create_main_rocrate(
        tmp_path, prepared, tmp_path / "crate.zip",
        subcrate_paths=[], workflow_path=tmp_path / "workflow.yml",
    )
    assert captured["main_profile"] is prepared.main_profile
    assert captured["main_profile"].crate_description == "Example run"


def test_cli_requires_profile_and_rejects_individual_metadata(tmp_path: Path) -> None:
    command = [
        "--benchmark-file", "benchmark.json", "--simulation-result-path", "results",
        "--subcrate-path", "run.zip", "--rocrate-path", "main.zip",
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
