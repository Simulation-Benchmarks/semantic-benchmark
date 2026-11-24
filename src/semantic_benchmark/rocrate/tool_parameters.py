"""Extract software inputs from caller supplied Croissant metadata."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any


def _one_or_many(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else [value]


def extract_tool_parameters(
    metadata_path: str | Path,
    source_dir: str | Path | None = None,
    *,
    record_set: str | None = None,
) -> list[dict[str, str]]:
    """Read Croissant fields from files relative to ``source_dir``.

    Plain text ``fileProperty: content`` sources are wrapped as one CSV cell so
    mlcroissant can apply their regex transforms to text rather than bytes.
    Other supported Croissant sources are passed through to mlcroissant.
    """
    import mlcroissant

    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    distributions = _one_or_many(metadata["distribution"])
    record_sets = _one_or_many(metadata["recordSet"])
    selected = (
        next((item for item in record_sets if item.get("@id") == record_set), None)
        if record_set else record_sets[0]
    )
    if selected is None:
        raise ValueError(f"Croissant RecordSet not found: {record_set}")
    fields = _one_or_many(selected["field"])
    field_types = {
        field["@id"]: field.get("additionalType")
        or field["dataType"].rsplit(":", 1)[-1]
        for field in fields
    }
    source_root = Path(source_dir or Path(metadata_path).parent).resolve()
    mapping: dict[str, Path] = {}

    with tempfile.TemporaryDirectory(prefix="croissant-tool-") as directory:
        temporary = Path(directory)
        for distribution in distributions:
            file_id = distribution["@id"]
            content_url = Path(distribution["contentUrl"])
            if content_url.is_absolute() or ".." in content_url.parts:
                raise ValueError(f"Croissant source must be relative to source_dir: {content_url}")
            source_path = (source_root / content_url).resolve()
            if not source_path.is_relative_to(source_root) or not source_path.is_file():
                raise FileNotFoundError(source_path)
            mapping[file_id] = source_path
            actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if declared_hash := distribution.get("sha256"):
                if actual_hash != declared_hash:
                    raise ValueError(f"Croissant checksum differs for {source_path}")
            distribution["sha256"] = actual_hash

        for index, distribution in enumerate(distributions):
            file_id = distribution["@id"]
            text_fields = [
                field for field in fields
                if field.get("source", {}).get("fileObject", {}).get("@id") == file_id
                and field["source"].get("extract", {}).get("fileProperty") == "content"
                and field["source"].get("transform", {}).get("regex")
            ]
            if not text_fields:
                continue
            if distribution["encodingFormat"] != "text/plain":
                raise ValueError(f"Content regex source must be text/plain: {file_id}")
            source_text = mapping[file_id].read_text(encoding="utf-8")
            for field in text_fields:
                pattern = re.compile(field["source"]["transform"]["regex"])
                match = pattern.match(source_text)
                if not match or pattern.groups != 1:
                    raise ValueError(f"Croissant regex must capture one value: {field['name']}")
            wrapped_path = temporary / f"source-{index}.csv"
            with wrapped_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["content"])
                writer.writerow([source_text])
            distribution["encodingFormat"] = "text/csv"
            distribution["sha256"] = hashlib.sha256(wrapped_path.read_bytes()).hexdigest()
            mapping[file_id] = wrapped_path
            for field in text_fields:
                field["source"]["extract"] = {"column": "content"}
                # Keep the source spelling (for example ``1e-2`` or ``false``)
                # instead of mlcroissant's numeric and boolean cast.
                field["dataType"] = "sc:Text"

        dataset = mlcroissant.Dataset(metadata, mapping=mapping)
        records = list(dataset.records(record_set=selected["@id"]))
        if len(records) != 1:
            raise ValueError(f"Expected one tool parameter record, got {len(records)}")
        result = []
        for field in fields:
            value = records[0].get(field["@id"])
            if value is None:
                raise ValueError(f"Croissant did not extract {field['name']}")
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            if isinstance(value, bool):
                value = str(value).lower()
            kind = field_types[field["@id"]]
            parameter = {
                "name": field["name"],
                "additionalType": kind,
                "defaultValue": str(value).strip(),
            }
            if "description" in field:
                parameter["description"] = field["description"]
            result.append(parameter)
        return result
