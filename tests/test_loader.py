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


def test_benchmark_https_schema_version_is_validated_and_loaded(tmp_path):
    loader = _validate(tmp_path, json.loads(FIXTURE.read_text(encoding="utf-8")))
    benchmark = loader.load()

    assert loader.conforms
    assert benchmark.version == "1.0.0"


def test_benchmark_http_schema_version_is_ignored_by_loader(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    version = _node(document, "local:benchmark").pop("schema:version")
    _node(document, "local:benchmark")["http://schema.org/version"] = version

    loader = _validate(tmp_path, document)
    benchmark = loader.load()

    assert loader.conforms
    assert benchmark.version is None


def test_minimal_configuration_demarshal_loads_expected_benchmark(tmp_path):
    loader = _validate(tmp_path, json.loads(FIXTURE.read_text(encoding="utf-8")))

    benchmark = loader.load()

    assert benchmark.id == "https://example.org/plate-with-hole/benchmark"
    assert benchmark.label == "Linear-elastic plate with a hole"
    assert benchmark.version == "1.0.0"

    assert benchmark.investigates is not None
    assert benchmark.investigates.id == "https://example.org/plate-with-hole/problem"
    assert benchmark.investigates.label == "Plate with a hole"

    assert len(benchmark.uses) == 1
    assert benchmark.uses[0].id == "https://example.org/plate-with-hole/model"
    assert benchmark.uses[0].label == "Linear elasticity model"

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
        ("local:benchmark", "evaluates", "m4i:evaluates"),
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
    ("node_id", "property_name"),
    [
        ("local:benchmark", "investigates"),
        ("local:benchmark", "uses"),
    ],
)
def test_optional_benchmark_links_can_be_omitted(tmp_path, node_id, property_name):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, node_id)[property_name]

    loader = _validate(tmp_path, document)
    benchmark = loader.load()

    assert loader.conforms
    if property_name == "investigates":
        assert benchmark.investigates is None
    else:
        assert benchmark.uses == []


def test_missing_parameter_sets_raise_a_runtime_error(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, "local:benchmark")["has parameter set"]

    loader = _validate(tmp_path, document)

    assert loader.conforms
    with pytest.raises(ValueError, match="m4i:hasParameterSet"):
        loader.load()


def test_missing_parameter_set_identifier_raises_a_runtime_error(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, "local:configuration")["identifier"]

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    with pytest.raises(ValueError, match="m4i:identifier"):
        loader.load()


def test_missing_parameter_label_raises_a_runtime_error(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, "local:radius")["label"]

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    with pytest.raises(ValueError, match="missing rdfs:label"):
        loader.load()


def test_missing_parameter_value_raises_a_runtime_error(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del _node(document, "local:radius")["has numerical value"]

    loader = _validate(tmp_path, document)

    assert loader.conforms
    with pytest.raises(ValueError, match="m4i:hasNumericalValue"):
        loader.load()


def test_benchmark_loads_multiple_models(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["@graph"].extend(
        [
            {
                "@id": "local:model-2",
                "@type": "mathmod:MathematicalModel",
                "label": "Plane stress approximation",
            },
        ]
    )
    benchmark_node = _node(document, "local:benchmark")
    benchmark_node["uses"] = [
        benchmark_node["uses"],
        {"@id": "local:model-2"},
    ]

    loader = _validate(tmp_path, document)
    benchmark = loader.load()

    assert loader.conforms
    assert [model.id for model in benchmark.uses] == [
        "https://example.org/plate-with-hole/model",
        "https://example.org/plate-with-hole/model-2",
    ]
    assert [model.label for model in benchmark.uses] == [
        "Linear elasticity model",
        "Plane stress approximation",
    ]


def test_benchmark_rejects_multiple_research_problems(tmp_path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["@graph"].append(
        {
            "@id": "local:problem-2",
            "@type": "mathmod:ResearchProblem",
            "label": "Stress concentration analysis",
        }
    )
    benchmark_node = _node(document, "local:benchmark")
    benchmark_node["investigates"] = [
        benchmark_node["investigates"],
        {"@id": "local:problem-2"},
    ]

    loader = _validate(tmp_path, document)

    assert not loader.conforms
    assert "MaxCountConstraintComponent" in loader.validation_report


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


def _sweep_document():
    document = json.loads(FIXTURE.read_text())
    document['@context']['has string value'] = {'@id': 'm4i:hasStringValue'}
    _node(document, 'local:radius')['has numerical value'] = [0, 2]
    document['@graph'].append({
        '@id': 'local:cell', '@type': 'numerical variable',
        'label': 'cell_type', 'has string value': ['triangle', 'quadrilateral'],
    })
    document['@graph'].append({
        '@id': 'local:degree', 'label': 'degree', 'has numerical value': 1,
    })
    _node(document, 'local:configuration')['has part'] = [
        {'@id': 'local:radius'}, {'@id': 'local:cell'}, {'@id': 'local:degree'},
    ]
    return document


def test_array_parameters_expand_and_write_scalar_files(tmp_path):
    from semantic_benchmark import runner

    loader = _validate(tmp_path, _sweep_document())
    assert loader.conforms
    benchmark = loader.load()
    assert len(benchmark.parameter_sets) == 4
    assert benchmark.processing_steps[0].configurations == benchmark.parameter_sets
    assert len({config.id for config in benchmark.parameter_sets}) == 4
    assert [config.identifier for config in benchmark.parameter_sets] == [
        'minimal--1', 'minimal--2', 'minimal--3', 'minimal--4',
    ]
    paths = runner.create_parameter_files(benchmark, tmp_path, {'M': 'm'}, strict_units=True)
    payloads = [json.loads(path.read_text()) for path in paths]
    assert {(p['cell_type'], p['radius[m]'], p['degree']) for p in payloads} == {
        ('triangle', 0, 1), ('triangle', 2, 1),
        ('quadrilateral', 0, 1), ('quadrilateral', 2, 1),
    }
    for config in benchmark.parameter_sets:
        radius = next(part for part in config.parts if part.label == 'radius')
        assert radius.unit_iri == 'https://qudt.org/vocab/unit/M'
    assert loader.load() == benchmark


def test_sweep_order_is_independent_of_array_and_part_order(tmp_path):
    document = _sweep_document()
    expected = _validate(tmp_path, document).load()
    _node(document, 'local:radius')['has numerical value'].reverse()
    _node(document, 'local:cell')['has string value'].reverse()
    _node(document, 'local:configuration')['has part'].reverse()
    assert _validate(tmp_path, document).load().parameter_sets == expected.parameter_sets


@pytest.mark.parametrize('value', [0, [0], [0, 0]])
def test_single_numeric_choice_keeps_original_identifier(tmp_path, value):
    document = json.loads(FIXTURE.read_text())
    _node(document, 'local:radius')['has numerical value'] = value
    config = _validate(tmp_path, document).load().parameter_sets[0]
    assert config.identifier == 'minimal'
    assert config.parts[0].numerical_value == 0


def test_empty_array_is_rejected_as_missing_value(tmp_path):
    document = json.loads(FIXTURE.read_text())
    _node(document, 'local:radius')['has numerical value'] = []
    with pytest.raises(ValueError, match='no scalar value'):
        _validate(tmp_path, document).load()


def test_expansion_rejects_identifier_collision(tmp_path):
    document = _sweep_document()
    document['@graph'].append({
        '@id': 'local:other', 'identifier': 'minimal--1',
        'has part': {'@id': 'local:degree'},
    })
    _node(document, 'local:benchmark')['has parameter set'] = [
        {'@id': 'local:configuration'}, {'@id': 'local:other'},
    ]
    with pytest.raises(ValueError, match='duplicate configuration identifier'):
        _validate(tmp_path, document).load()


def test_empty_string_is_a_text_parameter(tmp_path):
    document = _sweep_document()
    _node(document, 'local:cell')['has string value'] = ''
    benchmark = _validate(tmp_path, document).load()
    assert len(benchmark.parameter_sets) == 2
    for config in benchmark.parameter_sets:
        assert next(p for p in config.parts if p.label == 'cell_type').string_value == ''


def test_scalar_and_array_templates_expand_independently(tmp_path):
    document = _sweep_document()
    document['@graph'].append({
        '@id': 'local:scalar', 'identifier': 'scalar',
        'has part': {'@id': 'local:degree'},
    })
    refs = [{'@id': 'local:configuration'}, {'@id': 'local:scalar'}]
    _node(document, 'local:benchmark')['has parameter set'] = refs
    _node(document, 'local:simulation')['has configuration'] = refs
    benchmark = _validate(tmp_path, document).load()
    assert len(benchmark.parameter_sets) == 5
    assert benchmark.processing_steps[0].configurations == benchmark.parameter_sets
    scalar = next(c for c in benchmark.parameter_sets if c.identifier == 'scalar')
    assert scalar.id == 'https://example.org/plate-with-hole/scalar'
    assert scalar.parts[0].numerical_value == 1
    first, second = benchmark.parameter_sets[:2]
    first.parts[0].label = 'changed'
    assert second.parts[0].label != 'changed'
