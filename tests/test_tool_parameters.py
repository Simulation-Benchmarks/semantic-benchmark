"""Tool parameters come from caller supplied Croissant definitions."""

import json

import pytest

from semantic_benchmark.rocrate.tool_parameters import extract_tool_parameters


def test_extract_tool_parameters_from_plain_text(tmp_path):
    pytest.importorskip("mlcroissant")
    (tmp_path / "settings.conf").write_text("[Engine]\nSpeed = 12.5\nEnabled = false\n")
    metadata = {
        "@context": {
            "@language": "en", "@vocab": "https://schema.org/",
            "sc": "https://schema.org/", "cr": "http://mlcommons.org/croissant/",
            "dct": "http://purl.org/dc/terms/", "conformsTo": "dct:conformsTo",
            "recordSet": "cr:recordSet", "field": "cr:field",
            "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
            "source": "cr:source", "fileObject": "cr:fileObject",
            "extract": "cr:extract", "fileProperty": "cr:fileProperty",
            "transform": "cr:transform", "regex": "cr:regex", "column": "cr:column",
        },
        "@type": "sc:Dataset", "name": "Tool settings", "description": "Test input",
        "license": "https://opensource.org/licenses/MIT",
        "conformsTo": "http://mlcommons.org/croissant/1.1",
        "distribution": {"@type": "cr:FileObject", "@id": "settings",
                         "name": "settings.conf", "contentUrl": "settings.conf",
                         "encodingFormat": "text/plain"},
        "recordSet": [{"@type": "cr:RecordSet", "@id": "parameters",
                       "name": "parameters", "field": [
            {"@type": "cr:Field", "@id": f"parameters/{name}",
             "name": name, "dataType": dtype,
             "source": {"fileObject": {"@id": "settings"},
                        "extract": {"fileProperty": "content"},
                        "transform": {"regex": regex}}}
            for name, dtype, regex in (
                ("Speed", "sc:Float", r"(?ms).*?^Speed\s*=\s*([0-9.]+)"),
                ("Enabled", "sc:Boolean", r"(?ms).*?^Enabled\s*=\s*(true|false)"),
            )
        ]}],
    }
    metadata_path = tmp_path / "tool.croissant.json"
    metadata_path.write_text(json.dumps(metadata))

    assert extract_tool_parameters(metadata_path) == [
        {"name": "Speed", "additionalType": "Float", "defaultValue": "12.5"},
        {"name": "Enabled", "additionalType": "Boolean", "defaultValue": "false"},
    ]

    metadata["recordSet"][0]["field"][0]["source"]["transform"]["regex"] = r"(missing)"
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="must capture one value: Speed"):
        extract_tool_parameters(metadata_path)
