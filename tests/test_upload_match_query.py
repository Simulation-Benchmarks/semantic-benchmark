"""Check that upload replacement matches the exact benchmark RO."""

from rdflib import Graph, URIRef

from semantic_benchmark.rohub.provenance import (
    ANNOTATION_PREDICATE,
    build_annotated_ro_uuids_query,
)


def test_previous_upload_matches_exact_benchmark_ro() -> None:
    graph = Graph()
    first_benchmark = URIRef("https://w3id.org/ro-id/benchmark-1")
    second_benchmark = URIRef("https://w3id.org/ro-id/benchmark-2")
    first_run = URIRef("https://w3id.org/ro-id/run-1")
    second_run = URIRef("https://w3id.org/ro-id/run-2")
    predicate = URIRef(ANNOTATION_PREDICATE)
    graph.add((first_run, predicate, first_benchmark))
    graph.add((second_run, predicate, second_benchmark))

    query = build_annotated_ro_uuids_query(
        benchmark_name="example",
        benchmark_rohub_identifier="benchmark-2",
        use_production_rohub=True,
    )

    assert [row.subject for row in graph.query(query)] == [second_run]
