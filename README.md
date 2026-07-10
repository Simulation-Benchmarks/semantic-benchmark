# semantic-benchmark

Reusable Python helpers for semantic benchmark descriptions, aggregate RO-Crate creation, and RoHub provenance workflows.

## Install

```bash
pip install "semantic-benchmark @ git+https://github.com/Simulation-Benchmarks/semantic-benchmark.git"
```

## Provided Modules

- `semantic_benchmark.semantics`: dataclasses and `BenchmarkLoader` for JSON-LD benchmark descriptions.
- `semantic_benchmark.rohub`: RoHub configuration, upload, download, annotation, and query helpers.
- `semantic_benchmark.rocrate`: aggregate RO-Crate creation and validation helpers.

The root `semantic_benchmark` package re-exports the semantic classes for backwards compatibility.
The legacy `semantic_benchmark.semantic` module also remains as a compatibility shim.

`semantic_benchmark.rohub.download_benchmark_resources(...)` downloads the
software source code and annotation collection resources from a RoHub research
object. The package also exposes the `download-semantic-benchmark` CLI.

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
