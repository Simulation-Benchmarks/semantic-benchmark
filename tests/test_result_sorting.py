"""Data queries must not sort in SPARQL; results are sorted client-side."""

import pandas as pd

from semantic_benchmark.rohub import provenance
from semantic_benchmark.rohub.provenance import (
    build_dynamic_query,
    build_legacy_dynamic_query,
    sort_by_column,
)

GRAPHS = ["https://example.org/graph/a.ttl", "https://example.org/graph/b.ttl"]


def test_data_queries_have_no_order_by() -> None:
    # ORDER BY over several named graphs made the RoHub endpoint return no rows.
    for build in (build_dynamic_query, build_legacy_dynamic_query):
        query = build(["element_size"], ["l2_error"], GRAPHS)
        assert "ORDER BY" not in query.upper()


def test_sort_by_column_is_numeric_when_possible() -> None:
    data = pd.DataFrame({"element_size": ["0.1", "0.0125", "0.05"], "tool_name": ["a", "b", "c"]})

    result = sort_by_column(data, "element_size")

    assert list(result["element_size"]) == ["0.0125", "0.05", "0.1"]
    assert list(result.index) == [0, 1, 2]


def test_sort_by_column_falls_back_to_strings_and_is_stable() -> None:
    data = pd.DataFrame({"cell_type": ["triangle", "quadrilateral", "triangle"], "row": [1, 2, 3]})

    result = sort_by_column(data, "cell_type")

    assert list(result["cell_type"]) == ["quadrilateral", "triangle", "triangle"]
    assert list(result["row"]) == [2, 1, 3]


def test_sort_by_column_ignores_missing_column_and_empty_data() -> None:
    data = pd.DataFrame({"a": ["2", "1"]})
    assert sort_by_column(data, "missing").equals(data)
    assert sort_by_column(data, None).equals(data)
    empty = pd.DataFrame(columns=["a"])
    assert sort_by_column(empty, "a").empty


def test_query_metric_data_sorts_by_first_parameter(monkeypatch) -> None:
    unsorted = pd.DataFrame(
        {"tool_name": ["A", "B", "C"], "element_size": ["0.1", "0.0125", "0.05"], "l2_error": ["3", "1", "2"]}
    )
    sent = []

    def fake_query(query):
        sent.append(query)
        return unsorted

    monkeypatch.setattr(provenance, "query_sparql", fake_query)

    result = provenance.query_metric_data_from_named_graphs(["element_size"], ["l2_error"], GRAPHS)

    assert "ORDER BY" not in sent[0].upper()
    assert list(result["element_size"]) == ["0.0125", "0.05", "0.1"]
    assert list(result["l2_error"]) == ["1", "2", "3"]


def _patch_discovery(monkeypatch, new_fields, legacy_fields):
    monkeypatch.setattr(provenance, "find_annotated_ro_uuids", lambda *a, **k: ["u1", "u2"])
    monkeypatch.setattr(
        provenance, "find_named_graphs_for_uuids", lambda uuids, **k: dict(zip(uuids, GRAPHS))
    )
    monkeypatch.setattr(
        provenance,
        "discover_benchmark_fields",
        lambda graphs, *, legacy=False: legacy_fields if legacy else new_fields,
    )
    sent = []

    def fake_query(query):
        sent.append(query)
        return pd.DataFrame({"tool_name": ["A"], "element_size": ["0.1"], "l2_error": ["1"]})

    monkeypatch.setattr(provenance, "query_sparql", fake_query)
    return sent


def test_fetch_falls_back_to_legacy_query_for_older_crates(monkeypatch) -> None:
    sent = _patch_discovery(monkeypatch, ([], []), (["element_size"], ["l2_error"]))

    provenance.fetch_benchmark_data("bench", code_repository_url="https://example.org/repo")

    assert sent == [build_legacy_dynamic_query(["element_size"], ["l2_error"], GRAPHS)]


def test_fetch_uses_current_query_when_fields_are_found(monkeypatch) -> None:
    sent = _patch_discovery(monkeypatch, (["element_size"], ["l2_error"]), ([], []))

    provenance.fetch_benchmark_data("bench", code_repository_url="https://example.org/repo")

    assert sent == [build_dynamic_query(["element_size"], ["l2_error"], GRAPHS)]
