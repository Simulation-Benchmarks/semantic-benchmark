"""Check discovery of runs linked to versioned RoHub benchmark objects."""

from rdflib import Graph, Literal, URIRef

from semantic_benchmark.rohub.provenance import build_published_runs_query


def test_published_runs_follow_benchmark_ro_and_version() -> None:
    graph = Graph()
    run = URIRef("https://w3id.org/ro-id/run-uuid")
    benchmark = URIRef("https://w3id.org/ro-id/benchmark-uuid")
    research_problem = URIRef("https://portal.mardi4nfdi.de/entity/Q6775295")
    graph.add((run, URIRef("http://w3id.org/nfdi4ing/metadata4ing#investigates"), benchmark))
    graph.add((run, URIRef("http://schema.org/datePublished"), Literal("2026-10-13")))
    graph.add(
        (
            run,
            URIRef("https://schema.org/codeRepository"),
            URIRef("https://github.com/Simulation-Benchmarks/example/tree/main"),
        )
    )
    graph.add((benchmark, URIRef("http://w3id.org/nfdi4ing/metadata4ing#investigates"), research_problem))
    graph.add((benchmark, URIRef("http://purl.org/dc/terms/title"), Literal("example (version 1.1.0)")))
    graph.add((benchmark, URIRef("https://schema.org/version"), Literal("1.1.0")))

    rows = list(graph.query(build_published_runs_query()))

    assert len(rows) == 1
    assert str(rows[0].benchmark_url) == str(benchmark)
    assert str(rows[0].benchmark_title) == "example (version 1.1.0)"
    assert str(rows[0].research_problem_uri) == str(research_problem)
    assert str(rows[0].branch_url) == "https://github.com/Simulation-Benchmarks/example/tree/main"
    assert str(rows[0].version) == "1.1.0"

    graph.remove((benchmark, URIRef("https://schema.org/version"), None))
    assert not list(graph.query(build_published_runs_query()))
