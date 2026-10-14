"""Check that upload replacement matches the exact benchmark RO."""

from rdflib import ConjunctiveGraph, Literal, URIRef

from semantic_benchmark.rohub.provenance import (
    ANNOTATION_PREDICATE,
    build_annotated_ro_uuids_query,
    build_run_named_graphs_query,
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
        named_graph.add((software, rdf_type, software_type))
        named_graph.add((software, version_predicate, Literal("2.0")))

    query = build_annotated_ro_uuids_query(
        benchmark_name="example",
        benchmark_rohub_identifier="benchmark-2",
        use_production_rohub=True,
        software_url=str(second_software),
        software_version="2.0",
    )

    assert [row.subject for row in graph.query(query)] == [second_run]

    metadata_rows = list(graph.query(build_run_named_graphs_query([str(second_run)])))
    assert len(metadata_rows) == 1
    assert metadata_rows[0].software_url == second_software
    assert str(metadata_rows[0].software_version) == "2.0"
