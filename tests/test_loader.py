from rdflib import RDF, URIRef

from semantic_benchmark import BenchmarkLoader


def test_load_shapes_exposes_bundled_shacl_graph():
    shapes = BenchmarkLoader.load_shapes()
    node_shape = URIRef("http://www.w3.org/ns/shacl#NodeShape")

    assert len(shapes) > 0
    assert next(shapes.subjects(RDF.type, node_shape), None) is not None
    assert "NodeShape" in shapes.serialize(format="turtle")
