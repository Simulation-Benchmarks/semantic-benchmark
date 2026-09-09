import copy
import json
from pathlib import Path

import pytest
from rdflib import RDF, URIRef

from semantic_benchmark import BenchmarkLoader


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_configuration.json"
SH_NODE_SHAPE = URIRef("http://www.w3.org/ns/shacl#NodeShape")
M4I_BENCHMARK = URIRef("http://w3id.org/nfdi4ing/metadata4ing#Benchmark")
SH_TARGET_CLASS = URIRef("http://www.w3.org/ns/shacl#targetClass")


def test_load_shapes_exposes_bundled_shacl_graph():
    shapes = BenchmarkLoader.load_shapes()

    assert len(shapes) > 0
    assert next(shapes.subjects(RDF.type, SH_NODE_SHAPE), None) is not None
    assert next(shapes.subjects(SH_TARGET_CLASS, M4I_BENCHMARK), None) is not None
    assert "NodeShape" in shapes.serialize(format="turtle")


def _node(document, node_id):
    return next(node for node in document["@graph"] if node.get("@id") == node_id)


def _validate(tmp_path, document):
    benchmark_path = tmp_path / "benchmark.json"
    benchmark_path.write_text(json.dumps(document), encoding="utf-8")
    return BenchmarkLoader(benchmark_path)


def test_minimal_plate_with_hole_configuration_conforms(tmp_path):
    loader = _validate(tmp_path, json.loads(FIXTURE.read_text(encoding="utf-8")))

    assert loader.conforms
    assert "Conforms: True" in loader.validation_report
    assert not loader.validation_log_path.exists()


@pytest.mark.parametrize("version_property", ["schema:version", "http://schema.org/version"])
def test_benchmark_version_variants_are_validated_and_loaded(
    tmp_path, version_property
):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    version = _node(document, "local:benchmark").pop("schema:version")
    _node(document, "local:benchmark")[version_property] = version

    loader = _validate(tmp_path, document)
    benchmark = loader.load()

    assert loader.conforms
    assert benchmark.version == "1.0.0"


def test_minimal_configuration_demarshal_loads_expected_benchmark(tmp_path):
    loader = _validate(tmp_path, json.loads(FIXTURE.read_text(encoding="utf-8")))

    benchmark = loader.load()

    assert benchmark.id == "https://example.org/plate-with-hole/benchmark"
    assert benchmark.label == "Linear-elastic plate with a hole"
    assert benchmark.version == "1.0.0"

    assert benchmark.investigates is not None
    assert benchmark.investigates.id == "https://example.org/plate-with-hole/problem"
    assert benchmark.investigates.label == "Plate with a hole"

    assert benchmark.uses is not None
    assert benchmark.uses.id == "https://example.org/plate-with-hole/model"
    assert benchmark.uses.label == "Linear elasticity model"

    assert len(benchmark.evaluates) == 1
    metric = benchmark.evaluates[0]
    assert metric.id == "https://example.org/plate-with-hole/metric"
    assert metric.label == "maximum displacement error"
    assert metric.unit == "https://qudt.org/vocab/unit/M"
    assert metric.unit_iri == "https://qudt.org/vocab/unit/M"
    assert metric.quantity_kind == "http://qudt.org/vocab/quantitykind/Displacement"
    assert metric.field_mapping is not None
    assert metric.field_mapping.field_id == "https://example.org/plate-with-hole/field"
    assert metric.field_mapping.data_type == "https://schema.org/Double"
    assert metric.field_mapping.source_id == "https://example.org/plate-with-hole/source"
    assert metric.field_mapping.extract_id is not None
    assert metric.field_mapping.json_path == "/max_displacement_error/"
    assert (
        metric.field_mapping.file_object_id
        == "https://example.org/plate-with-hole/summary-file"
    )
    assert metric.field_mapping.file_object_label == "solution_metrics.json"

    assert len(benchmark.parameter_sets) == 1
    parameter_set = benchmark.parameter_sets[0]
    assert parameter_set.id == "https://example.org/plate-with-hole/configuration"
    assert parameter_set.label == "Minimal configuration"
    assert parameter_set.identifier == "minimal"
    assert len(parameter_set.parts) == 1
    radius = parameter_set.parts[0]
    assert radius.id == "https://example.org/plate-with-hole/radius"
    assert radius.label == "radius"
    assert radius.numerical_value == pytest.approx(0.33)
    assert radius.unit == "https://qudt.org/vocab/unit/M"
    assert radius.unit_iri == "https://qudt.org/vocab/unit/M"
    assert radius.field_mapping is None

    assert len(benchmark.processing_steps) == 1
    simulation = benchmark.processing_steps[0]
    assert simulation.id == "https://example.org/plate-with-hole/simulation"
    assert simulation.label == "Simulation run"
    assert [item.id for item in simulation.inputs] == [
        "https://example.org/plate-with-hole/parameter-file"
    ]
    assert [item.label for item in simulation.inputs] == ["parameters.json"]
    assert [item.id for item in simulation.outputs] == [
        "https://example.org/plate-with-hole/summary-file"
    ]
    assert [item.label for item in simulation.outputs] == ["solution_metrics.json"]
    assert len(simulation.configurations) == 1
    assert simulation.configurations[0].id == parameter_set.id
    assert simulation.configurations[0].identifier == parameter_set.identifier
    assert not simulation.employed_tools


@pytest.mark.parametrize(
    ("node_id", "property_name", "expected_path"),
    [
        ("local:benchmark", "label", "rdfs:label"),
        ("local:benchmark", "investigates", "m4i:investigates"),
        ("local:benchmark", "uses", "wd:P2283"),
        ("local:benchmark", "evaluates", "m4i:evaluates"),
        ("local:benchmark", "has parameter set", "m4i:hasParameterSet"),
        ("local:problem", "label", "rdfs:label"),
        ("local:model", "label", "rdfs:label"),
        ("local:metric", "label", "rdfs:label"),
        ("local:field", "dataType", "m4i:dataType"),
        ("local:field", "represents", "sio:SIO_000210"),
        ("local:field", "source", "cr:source"),
        ("local:source", "extract", "cr:extract"),
        ("local:source", "file object", "cr:FileObject"),
        ("local:configuration", "label", "rdfs:label"),
        ("local:configuration", "identifier", "m4i:identifier"),
        ("local:configuration", "has part", "obo:BFO_0000051"),
        ("local:simulation", "label", "rdfs:label"),
    ],
)
def test_required_properties_are_enforced(
    tmp_path, node_id, property_name, expected_path
):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, node_id)[property_name]

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    assert "MinCountConstraintComponent" in loader.validation_report
    assert expected_path in loader.validation_report


@pytest.mark.parametrize(
    ("node_id", "property_name", "invalid_value", "constraint"),
    [
        ("local:benchmark", "schema:version", 1, "DatatypeConstraintComponent"),
        ("local:metric", "label", 123, "DatatypeConstraintComponent"),
        ("local:summary-file", "label", 123, "DatatypeConstraintComponent"),
        (
            "local:summary-file",
            "schema:encodingFormat",
            123,
            "DatatypeConstraintComponent",
        ),
        ("local:source", "extract", {"jsonPath": 123}, "DatatypeConstraintComponent"),
        ("local:field", "represents", "metric", "NodeKindConstraintComponent"),
        ("local:configuration", "has part", "radius", "NodeKindConstraintComponent"),
    ],
)
def test_property_value_constraints_are_enforced(
    tmp_path, node_id, property_name, invalid_value, constraint
):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    _node(document, node_id)[property_name] = copy.deepcopy(invalid_value)

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    assert constraint in loader.validation_report


@pytest.mark.parametrize(
    ("node_id", "property_name"),
    [
        ("local:benchmark", "label"),
        ("local:benchmark", "schema:version"),
        ("local:metric", "has unit"),
        ("local:source", "file object"),
        ("local:field", "source"),
        ("local:configuration", "identifier"),
    ],
)
def test_single_value_properties_reject_duplicates(tmp_path, node_id, property_name):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    node = _node(document, node_id)
    original = node[property_name]
    distinct_value = (
        {"@id": "local:distinct-value"}
        if isinstance(original, dict)
        else f"{original}-distinct"
    )
    node[property_name] = [original, distinct_value]

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    assert "MaxCountConstraintComponent" in loader.validation_report


def test_data_source_extract_requires_a_string_json_path(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, "local:source")["extract"]["jsonPath"]

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    assert "MinCountConstraintComponent" in loader.validation_report
    assert "cr:jsonPath" in loader.validation_report


@pytest.mark.parametrize(
    ("node_id", "property_name", "wrong_target"),
    [
        ("local:benchmark", "investigates", "local:model"),
        ("local:benchmark", "uses", "local:problem"),
        ("local:benchmark", "evaluates", "local:model"),
        ("local:benchmark", "has parameter set", "local:model"),
        ("local:field", "source", "local:model"),
        ("local:source", "file object", "local:model"),
        ("local:simulation", "has input", "local:model"),
        ("local:simulation", "has output", "local:model"),
        ("local:simulation", "has configuration", "local:model"),
    ],
)
def test_referenced_resources_must_have_the_expected_class(
    tmp_path, node_id, property_name, wrong_target
):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    _node(document, node_id)[property_name] = {"@id": wrong_target}

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    assert "ClassConstraintComponent" in loader.validation_report


def test_invalid_document_writes_the_validation_report(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, "local:benchmark")["label"]

    loader = _validate(tmp_path, document)

    assert loader.validation_log_path.exists()
    log = loader.validation_log_path.read_text(encoding="utf-8")
    assert "SHACL validation failed" in log
    assert "MinCountConstraintComponent" in log


def test_invalid_document_still_loads_with_partial_data(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, "local:benchmark")["label"]

    loader = _validate(tmp_path, document)
    benchmark = loader.load()

    assert not loader.conforms
    assert benchmark.id == "https://example.org/plate-with-hole/benchmark"
    assert benchmark.label is None
    assert benchmark.version == "1.0.0"
    assert len(benchmark.evaluates) == 1
    assert len(benchmark.parameter_sets) == 1
