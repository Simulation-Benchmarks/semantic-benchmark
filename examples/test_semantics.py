from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from semantic_benchmark import BenchmarkLoader, runner

UNIT_SYMBOLS = {
    "M": "m",
    "METRE": "m",
    "METER": "m",
    "PA": "Pa",
    "PASCAL": "Pa",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate, load, and generate parameter files for a semantic benchmark."
    )
    parser.add_argument("jsonld_file", type=Path, help="Path to the JSON-LD benchmark file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated_parameters"),
        help=(
            "Directory for generated parameter files (default: generated_parameters). "
            "Existing parameters_*.json files in this directory are replaced."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    loader = BenchmarkLoader(args.jsonld_file)

    print(f"File: {args.jsonld_file}")
    print(f"SHACL conforms: {loader.conforms}")
    if not loader.conforms:
        print(f"Validation log: {loader.validation_log_path}")
        print("Validation report:")
        print(loader.validation_report)

    benchmark = loader.load()
    print()
    print("Loaded benchmark:")
    print(f"  id: {benchmark.id}")
    print(f"  label: {benchmark.label}")
    print(f"  version: {benchmark.version}")
    print(
        "  investigates: "
        f"{benchmark.investigates.label if benchmark.investigates else None}"
    )
    print(f"  uses: {[model.label for model in benchmark.uses]}")

    print("  evaluates:")
    for metric in benchmark.evaluates:
        print(f"    - id: {metric.id}")
        print(f"      label: {metric.label}")
        print(f"      unit: {metric.unit}")
        print(f"      quantity_kind: {metric.quantity_kind}")
        if metric.field_mapping:
            print(f"      json_path: {metric.field_mapping.json_path}")
            print(f"      source_file: {metric.field_mapping.file_object_label}")

    print("  parameter_sets:")
    for parameter_set in benchmark.parameter_sets:
        print(f"    - id: {parameter_set.id}")
        print(f"      label: {parameter_set.label}")
        print(f"      identifier: {parameter_set.identifier}")
        for part in parameter_set.parts:
            value = getattr(part, "numerical_value", None)
            if value is None:
                value = getattr(part, "string_value", None)
            print(f"      part: {part.label} = {value} ({part.unit})")

    print("  processing_steps:")
    for step in benchmark.processing_steps:
        print(f"    - id: {step.id}")
        print(f"      label: {step.label}")
        print(f"      inputs: {[item.label for item in step.inputs]}")
        print(f"      outputs: {[item.label for item in step.outputs]}")
        print(f"      configurations: {[cfg.identifier for cfg in step.configurations]}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    parameter_files = runner.create_parameter_files(benchmark, output_dir, UNIT_SYMBOLS)
    print(f"\nCreated {len(parameter_files)} parameter files in {output_dir}:")
    for parameter_file in parameter_files:
        print(f"  {parameter_file.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
