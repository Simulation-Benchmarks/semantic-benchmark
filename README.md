# semantic-benchmark

`semantic-benchmark` turns a JSON-LD benchmark description into configurations for a simulation runner and combines completed runs into a validated main RO-Crate. It also provides commands for exchanging benchmark crates with RoHub. The package supplies building blocks; each simulation project runs its own solver and workflow.

## Install

Requires Python 3.10 or newer.

```bash
python -m pip install semantic-benchmark
```

For main RO-Crate creation, install the validator as well:

```bash
python -m pip install "semantic-benchmark[rocrate]"
```

To work from this repository, use `python -m pip install -e ".[rocrate,test]"`.

## Load a benchmark and prepare runs

`BenchmarkLoader` reads and validates the JSON-LD description. `runner.prepare_benchmark` loads it and writes one `parameters_<configuration>.json` file per configuration into an **existing** working directory. It replaces any existing `parameters_*.json` files there.

```python
from pathlib import Path
from semantic_benchmark import runner

work_dir = Path("work")
work_dir.mkdir(exist_ok=True)
benchmark = runner.prepare_benchmark(
    Path("benchmark.jsonld"),
    work_dir,
    {"METRE": "m", "PASCAL": "Pa"},
    main_profile=Path("main-crate.yml"),
)

for parameter_file in sorted(work_dir.glob("parameters_*.json")):
    configuration, result_dir = runner.prepare_configuration(parameter_file, work_dir)
    # Run your solver with result_dir / "parameters.json" and save its results there.
```

The unit mapping adds suffixes such as `[m]` to parameter keys when a unit resolves. Unmapped units leave the parameter name unchanged. `prepare_benchmark` can also unpack an archive, copy resources, and create shared directories; see [`runner.py`](src/semantic_benchmark/runner.py).

Parameter values can be arrays in JSON-LD. The loader expands each parameter set into the Cartesian product of its values, so a two-choice parameter and a three-choice parameter produce six configurations. See [`examples/array-configurations.json`](examples/array-configurations.json). To inspect a description and generate parameter files directly:

```bash
python examples/test_semantics.py examples/array-configurations.json --output-dir generated_parameters
```

## Create the main RO-Crate

Each completed run needs a reporter RO-Crate ZIP and a result directory containing the metric files described in the benchmark. Pass the exact ZIP paths and a YAML workflow file to the runner:

```python
runner.create_main_rocrate(
    work_dir / "results",
    benchmark,
    Path("main-rocrate.zip"),
    subcrate_paths=[Path("work/results/run-1/workflow-run.zip")],
    workflow_path=Path("workflow.yml"),
)
```

The loaded `main_profile` supplies the software and crate metadata. For example:

```yaml
software-name: "Example solver"
software-version: "1.0"
software-url: "https://example.org/solver"
crate-license: "https://opensource.org/licenses/MIT"
crate-name: "Example benchmark results"
crate-description: "Simulation results and provenance"
authors:
  - name: "Example Author"
    orcid: "https://orcid.org/0000-0000-0000-0000"
creator:
  name: "Example Creator"
  orcid: "https://orcid.org/0000-0000-0000-0001"
```

`authors` must contain at least one person. The generated crate links configurations, metric values, workflows, software, and run crates, then validates against `workflow-run-crate-0.5`. A runner may attach tool-specific software inputs with `semantic_benchmark.rocrate.create.add_tool_parameter(benchmark, name, additional_type, default_value, description=None)` before creating the crate.

The same operation is available as `create-semantic-benchmark-rocrate`; run it with `--help` for its required paths.

## RoHub commands

`download-semantic-benchmark` exports a research object's RO-Crate into a directory. Add `--semantic-resource-filename` to download its Annotation Collection resource separately.

```bash
download-semantic-benchmark \
  --identifier <research-object-uuid> \
  --username <user> --password <password> \
  --path benchmark
```

`upload-semantic-benchmark` uploads a completed provenance ZIP and links it to its benchmark research object:

```bash
upload-semantic-benchmark \
  --provenance_folderpath main-rocrate.zip \
  --benchmark-name "Example benchmark" \
  --benchmark-rohub-identifier <benchmark-ro-uuid> \
  --username <user> --password <password>
```

Both commands use the development RoHub instance by default; add `--use-production-rohub` for production. See each command's `--help` for further options.

## Development

```bash
python -m pip install -e ".[rocrate,test]"
python -m pytest
```
