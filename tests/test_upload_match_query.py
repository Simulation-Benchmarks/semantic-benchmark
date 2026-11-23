"""Check that upload replacement matches the exact benchmark RO."""

from rdflib import ConjunctiveGraph, Literal, URIRef

from semantic_benchmark.rohub.provenance import (
    ANNOTATION_PREDICATE,
    build_annotated_ro_uuids_query,
    build_available_fields_query,
    build_dynamic_query,
    build_legacy_available_fields_query,
    build_legacy_dynamic_query,
    build_legacy_run_named_graphs_query,
    build_run_named_graphs_query,
    build_runs_with_tool_parameters_query,
    build_tool_parameters_query,
)


def test_previous_upload_matches_exact_benchmark_ro() -> None:
    graph = ConjunctiveGraph()
    first_benchmark = URIRef("https://w3id.org/ro-id/benchmark-1")
    second_benchmark = URIRef("https://w3id.org/ro-id/benchmark-2")
    first_run = URIRef("https://w3id.org/ro-id/run-1")
    second_run = URIRef("https://w3id.org/ro-id/run-2")
    predicate = URIRef(ANNOTATION_PREDICATE)
    graph.add((first_run, predicate, first_benchmark))
    graph.add((second_run, predicate, second_benchmark))
    first_software = URIRef("https://example.org/software/first")
    second_software = URIRef("https://example.org/software/second")
    dataset_type = URIRef("http://schema.org/Dataset")
    software_type = URIRef("http://schema.org/SoftwareApplication")
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    version_predicate = URIRef("http://schema.org/version")
    for run, software in ((first_run, first_software), (second_run, second_software)):
        named_graph = graph.get_context(URIRef(f"{run}/graph"))
        named_graph.add((run, rdf_type, dataset_type))
        if run == second_run:
            action = URIRef(f"{run}/tool-action")
            named_graph.add((run, URIRef("http://schema.org/mentions"), action))
            named_graph.add((
                run,
                URIRef("http://purl.org/dc/terms/conformsTo"),
                URIRef("https://w3id.org/ro/wfrun/provenance/0.6"),
            ))
            named_graph.add((action, rdf_type, URIRef("http://schema.org/CreateAction")))
            named_graph.add((action, URIRef("http://schema.org/instrument"), software))
        named_graph.add((software, rdf_type, software_type))
        named_graph.add((software, version_predicate, Literal("2.0")))
        github_actions = URIRef(f"{run}/github-actions")
        named_graph.add((github_actions, rdf_type, software_type))
        named_graph.add((github_actions, URIRef("http://xmlns.com/foaf/0.1/name"), Literal("GitHub Actions")))
        if run == second_run:
            named_graph.add((github_actions, version_predicate, Literal("1.0")))

    query = build_annotated_ro_uuids_query(
        benchmark_name="example",
        benchmark_rohub_identifier="benchmark-2",
        use_production_rohub=True,
        software_url=str(second_software),
        software_version="2.0",
    )

    assert [row.subject for row in graph.query(query)] == [second_run]

    metadata_rows = [
        row
        for row in graph.query(build_run_named_graphs_query([str(second_run)]))
        if str(row.source) == "linked"
    ]
    assert len(metadata_rows) == 1
    assert metadata_rows[0].software_url == second_software
    assert str(metadata_rows[0].software_version) == "2.0"
    assert str(metadata_rows[0].profile) == "provenance"
    legacy_rows = list(graph.query(build_legacy_run_named_graphs_query([str(first_run)])))
    assert len(legacy_rows) == 1
    assert legacy_rows[0].software_url == first_software
    assert all(row.profile is None for row in graph.query(
        build_run_named_graphs_query([str(first_run)])
    ))
    assert list(graph.query(build_runs_with_tool_parameters_query([str(second_run)]))) == []


def test_tool_parameters_are_read_from_the_run_graph() -> None:
    graph = ConjunctiveGraph()
    run = URIRef("https://example.org/run")
    graph_id = URIRef("https://example.org/run/graph")
    software = URIRef("https://example.org/tool")
    parameter = URIRef("https://example.org/parameter")
    named = graph.get_context(graph_id)
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    schema = "http://schema.org/"
    named.add((run, rdf_type, URIRef(f"{schema}Dataset")))
    action = URIRef("https://example.org/tool-action")
    named.add((run, URIRef(f"{schema}mentions"), action))
    named.add((action, rdf_type, URIRef(f"{schema}CreateAction")))
    named.add((action, URIRef(f"{schema}instrument"), software))
    named.add((software, rdf_type, URIRef(f"{schema}SoftwareApplication")))
    named.add((software, URIRef("https://bioschemas.org/ComputationalWorkflow#input"), parameter))
    named.add((parameter, rdf_type, URIRef("https://bioschemas.org/FormalParameter")))
    named.add((parameter, URIRef("http://xmlns.com/foaf/0.1/name"), Literal("Grid.Cells0")))
    named.add((parameter, URIRef(f"{schema}additionalType"), Literal("Text")))
    named.add((parameter, URIRef(f"{schema}defaultValue"), Literal("40 40")))

    rows = list(graph.query(build_tool_parameters_query(str(run), str(graph_id))))
    assert len(rows) == 1
    assert str(rows[0].name) == "Grid.Cells0"
    assert str(rows[0].default_value) == "40 40"
    assert rows[0].description is None
    available = list(graph.query(build_runs_with_tool_parameters_query([str(run)])))
    assert [(row.run_id, row.graph) for row in available] == [(run, graph_id)]


def test_run_values_only_use_workflow_formal_parameters() -> None:
    graph = ConjunctiveGraph()
    run = URIRef("https://example.org/run")
    graph_id = URIRef(f"{run}/annotation")
    workflow_graph_id = URIRef(f"{run}/workflow")
    named = graph.get_context(graph_id)
    workflow_graph = graph.get_context(workflow_graph_id)
    schema = "http://schema.org/"
    workflow_terms = "https://bioschemas.org/ComputationalWorkflow#"
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    name = URIRef("http://xmlns.com/foaf/0.1/name")
    workflow = URIRef("https://example.org/main-workflow")
    software = URIRef("https://example.org/tool")
    action = URIRef("https://example.org/run-action")
    tool_action = URIRef("https://example.org/tool-action")
    configuration = URIRef("https://example.org/configuration")
    parameter = URIRef("https://example.org/workflow-parameter")
    tool_parameter = URIRef("https://example.org/tool-parameter")
    metric_definition = URIRef("https://example.org/metric-definition")
    metric_result = URIRef("https://example.org/metric-result")

    named.add((run, rdf_type, URIRef(f"{schema}Dataset")))
    named.add((run, URIRef(f"{schema}mentions"), tool_action))
    named.add((tool_action, rdf_type, URIRef(f"{schema}CreateAction")))
    named.add((tool_action, URIRef(f"{schema}instrument"), software))
    named.add((software, rdf_type, URIRef(f"{schema}SoftwareApplication")))
    named.add((software, name, Literal("Example tool")))
    named.add((software, URIRef(f"{workflow_terms}input"), tool_parameter))
    named.add((action, rdf_type, URIRef(f"{schema}CreateAction")))
    named.add((action, URIRef(f"{schema}object"), configuration))
    named.add((action, URIRef(f"{schema}result"), metric_result))
    named.add((configuration, rdf_type, URIRef(f"{schema}PropertyValue")))
    named.add((configuration, URIRef(f"{schema}exampleOfWork"), parameter))
    named.add((configuration, URIRef(f"{schema}exampleOfWork"), tool_parameter))
    for item, label, value in (
        (parameter, "radius", "1"),
        (tool_parameter, "solver_tolerance", "0.001"),
    ):
        named.add((item, rdf_type, URIRef("https://bioschemas.org/FormalParameter")))
        named.add((item, name, Literal(label)))
        named.add((item, URIRef(f"{schema}value"), Literal(value)))
    named.add((metric_result, rdf_type, URIRef(f"{schema}PropertyValue")))
    named.add((metric_result, name, Literal("error")))
    named.add((metric_result, URIRef(f"{schema}value"), Literal("0.25")))
    named.add((metric_result, URIRef(f"{schema}exampleOfWork"), metric_definition))
    named.add((metric_definition, rdf_type, URIRef("https://bioschemas.org/FormalParameter")))
    unrelated_metric = URIRef("https://example.org/unrelated-metric")
    named.add((action, URIRef(f"{schema}result"), unrelated_metric))
    named.add((unrelated_metric, rdf_type, URIRef(f"{schema}PropertyValue")))
    named.add((unrelated_metric, name, Literal("unrelated_error")))
    named.add((unrelated_metric, URIRef(f"{schema}value"), Literal("9")))
    workflow_graph.add((workflow, rdf_type, URIRef("https://bioschemas.org/ComputationalWorkflow")))
    workflow_graph.add((workflow, URIRef(f"{workflow_terms}input"), parameter))
    workflow_graph.add((workflow, URIRef(f"{workflow_terms}output"), metric_definition))

    fields = {(str(row.field_type), str(row.field_name)) for row in graph.query(
        build_available_fields_query([str(graph_id)])
    )}
    assert fields == {("parameter", "radius"), ("metric", "error")}
    rows = list(graph.query(build_dynamic_query(["radius"], ["error"], [str(graph_id)])))
    assert len(rows) == 1
    assert (str(rows[0].radius), str(rows[0].error)) == ("1", "0.25")
    legacy_fields = {(str(row.field_type), str(row.field_name)) for row in graph.query(
        build_legacy_available_fields_query([str(graph_id)])
    )}
    assert ("parameter", "solver_tolerance") in legacy_fields
    assert ("metric", "unrelated_error") in legacy_fields
    legacy_rows = list(graph.query(
        build_legacy_dynamic_query(["radius"], ["error"], [str(graph_id)])
    ))
    assert len(legacy_rows) == 1
    assert (str(legacy_rows[0].radius), str(legacy_rows[0].error)) == ("1", "0.25")
