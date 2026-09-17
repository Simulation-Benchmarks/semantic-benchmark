# semantic-benchmark

Reusable Python helpers for semantic benchmark descriptions, aggregate RO-Crate creation, and RoHub provenance workflows.

## Install

```bash
pip install semantic-benchmark
```

Install optional features with extras:

```bash
pip install "semantic-benchmark[rocrate]"
pip install "semantic-benchmark[rohub]"
pip install "semantic-benchmark[all]"
```

To install the latest unreleased version directly from GitHub:

```bash
pip install "semantic-benchmark[all] @ git+https://github.com/Simulation-Benchmarks/semantic-benchmark.git"
```

## Provided Modules

- `semantic_benchmark.semantics`: dataclasses and `BenchmarkLoader` for JSON-LD benchmark descriptions.
- `semantic_benchmark.rohub`: RoHub configuration, upload, download, annotation, and query helpers.
- `semantic_benchmark.rocrate`: aggregate RO-Crate creation and validation helpers.
- `semantic_benchmark.runner`: shared parameter-file, workspace, resource staging,
  archive, logging, and aggregate RO-Crate helpers for project benchmark runners.

`semantic_benchmark.semantics` is available from the base installation.
`semantic_benchmark.rocrate` requires the `rocrate` extra.
`semantic_benchmark.rohub` requires the `rohub` extra.

The root `semantic_benchmark` package re-exports the semantic classes for backwards compatibility.
The legacy `semantic_benchmark.semantic` module also remains as a compatibility shim.

Loaded numerical variables and parameters expose both `unit` (the original
JSON-LD value) and `unit_iri` (the full IRI expanded through the document's
namespace bindings). Consumers should use `unit_iri` when creating links.

`semantic_benchmark.rohub.download_benchmark_resources(...)` downloads the
requested benchmark resources from a RoHub research object. The semantic file
is selected from the `Annotation Collection` resource in `list_resources()`.
Passing `path="benchmark"` (CLI: `--path benchmark`) exports the complete research
object using `ros_export_to_rocrate(..., use_format="zip")` and extracts its
contents directly into `benchmark/`. If `path` / `--path` is omitted, the crate
is extracted into the current directory. The directory is created if needed, and
the temporary ZIP is removed afterward. The returned mapping contains the research object identifier
under `RO-Crate` and the annotation resource identifier under
`Annotation Collection` for the requested downloads.
The package also exposes the
`download-semantic-benchmark` CLI.

`upload-semantic-benchmark` calls `upload_provenance_rocrate(...)` directly.
It accepts `--provenance_folderpath` (the RO-Crate ZIP), `--benchmark-name`,
`--username`, `--password`, and optional `--code-repository-url`,
`--used-software-url`, and `--use-production-rohub` arguments.

`semantic_benchmark.rocrate.create_main_ro(...)` can validate the generated
aggregate crate by passing `validation_profile`. The package writes the RO-Crate
zip, unpacks it to a validation directory, and runs `validate_rocrate(...)`.

Repository-specific projects can override the packaged RoHub defaults with:

```python
import semantic_benchmark.rohub as rohub

rohub.configure_repository_settings(
    rohub_config={...},
)
```

## Parameter sweeps with JSON-LD arrays

A parameter's `has numerical value` or `has string value` may be a scalar or
an array of alternatives. For example, reference both of these nodes from the
same parameter set's `has part` property:

```json
[
  {
    "@id": "local:cell_type",
    "label": "cell_type",
    "has string value": ["triangle", "quadrilateral"]
  },
  {
    "@id": "local:degree",
    "label": "isoparametric_element_degree",
    "has numerical value": [1, 2]
  }
]
```

Use a JSON-LD context mapping these value properties to `m4i:hasStringValue`
and `m4i:hasNumericalValue`, as in the existing examples. `BenchmarkLoader.load()`
expands each parameter set independently into the Cartesian product: this
example produces four configurations. Scalars are repeated in every combination.
All loaded configuration parts contain scalar values, so solvers and
`runner.create_parameter_files()` continue to receive ordinary scalar parameters.
Processing-step configuration references expand identically for provenance.

A template identified as `sweep` produces identifiers `sweep--1`, `sweep--2`,
etc., and corresponding `parameters_sweep--1.json` files. Its node IDs receive
the same suffixes. Scalar-only sets and arrays with one distinct choice retain
the original IDs and identifiers. Identifier collisions raise an error instead
of overwriting output files.

JSON-LD arrays represent unordered RDF alternatives, so duplicate RDF values
collapse. Expansion sorts parameter IRIs and RDF value spellings to give stable
identifiers regardless of array order (this is lexical, not numerical ordering).
Empty arrays have no value and are rejected for runtime parameters. The lower-level
`build_parameter_set()` returns a template whose values may be lists;
`build_parameter_sets()` and `load()` return expanded scalar configurations.

When testing this feature from a local checkout, install the modified package
into the Python environment used by the benchmark runner:

```bash
python -m pip install -e ../semantic-benchmark
```

Run that command from a sibling benchmark repository. Add `[all]` to the local
package path if the workflow also needs the optional provenance dependencies.

See [the complete array example](examples/array-configurations.json), which
combines two radii, two cell types, and two element degrees into eight runs.
