"""JSON-LD loading and SHACL validation for semantic benchmarks."""

from dataclasses import replace
from itertools import product
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pyshacl import validate
from rdflib import Graph, Literal, RDF, RDFS, URIRef

from semantic_benchmark.semantics.models import (
    FieldMapping,
    IOObject,
    MathematicalModel,
    NumericalParameter,
    NumericalVariable,
    ParameterEntry,
    ParameterSet,
    ProcessingStep,
    Publication,
    ResearchProblem,
    SemanticBenchmark,
    TextParameter,
    Tool,
)
from semantic_benchmark.semantics.vocabulary import (
    DATA_TYPE,
    DESCRIBED_BY,
    EVALUATES,
    HAS_EMPLOYED_TOOL,
    HAS_EXTRACT,
    HAS_FILE_OBJECT,
    HAS_FILE_OBJECT_ALT,
    HAS_INPUT,
    HAS_KIND_OF_QTY,
    HAS_NUMERICAL_VALUE,
    HAS_OUTPUT,
    HAS_PART,
    HAS_SOURCE,
    HAS_STRING_VALUE,
    HAS_UNIT,
    INVESTIGATES,
    JSON_PATH,
    M4I,
    REPRESENTS,
    T_BENCHMARK,
    T_FIELD,
    T_NUMERICAL_VARIABLE,
    T_PROCESSING_STEP,
    USES,
    USES_CONFIG,
    VERSION,
)


class BenchmarkLoader:
    """Load benchmark JSON-LD and report SHACL violations before object mapping.

    By default, every ``.ttl`` file in the bundled ``shapes`` directory is
    combined into one shapes graph. Validation does not abort loading; when
    the graph does not conform, the human-readable SHACL report is written next
    to the input file (or to ``validation_log_path`` when provided).
    """

    def __init__(
        self,
        jsonld_path: str | Path,
        *,
        validation_log_path: str | Path | None = None,
    ):
        self.path = Path(jsonld_path)
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        self.graph = Graph()
        self.graph.parse(str(self.path), format="json-ld")
        self.validation_log_path = (
            Path(validation_log_path)
            if validation_log_path is not None
            else self.path.with_suffix(".shacl.log")
        )
        self.conforms, self.validation_report = self._validate()
        self._field_mapping_by_variable_id = self._build_field_mapping_index()

    @staticmethod
    def _shape_files() -> list[Path]:
        shapes_directory = Path(__file__).parent / "shapes"
        files = sorted(shapes_directory.glob("*.ttl"))
        if not files:
            raise ValueError(f"No bundled SHACL .ttl files found in: {shapes_directory}")
        return files

    @classmethod
    def load_shapes(cls) -> Graph:
        """Return the bundled SHACL shapes as one RDF graph.

        The returned graph can be inspected, queried, or serialized with the
        standard :class:`rdflib.Graph` API.
        """
        shapes_graph = Graph()
        for shape_file in cls._shape_files():
            shapes_graph.parse(str(shape_file), format="turtle")
        return shapes_graph

    def _validate(self) -> tuple[bool, str]:
        conforms, _, report_text = validate(
            data_graph=self.graph,
            shacl_graph=self.load_shapes(),
            inference="rdfs",
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )
        report = str(report_text)
        if not conforms:
            self.validation_log_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).isoformat()
            self.validation_log_path.write_text(
                f"SHACL validation failed for {self.path}\n"
                f"Validated at {timestamp}\n\n{report.rstrip()}\n",
                encoding="utf-8",
            )
        return bool(conforms), report

    @staticmethod
    def _str(uri: URIRef) -> str:
        return str(uri)

    def _label(self, subject: URIRef) -> Optional[str]:
        value = self.graph.value(subject, RDFS.label)
        return str(value) if value else None

    def _scalar(self, subject: URIRef, predicate: URIRef):
        value = self.graph.value(subject, predicate)
        if value is None:
            return None
        return value.toPython() if isinstance(value, Literal) else str(value)

    def _parameter_value(self, subject: URIRef, predicate: URIRef):
        """Read RDF alternatives deterministically (JSON-LD arrays are sets)."""
        terms = sorted(self.graph.objects(subject, predicate), key=lambda term: term.n3())
        values = [term.toPython() if isinstance(term, Literal) else str(term)
                  for term in terms]
        if not values:
            return None
        return values[0] if len(values) == 1 else values

    def _iri(self, subject: URIRef, predicate: URIRef) -> Optional[str]:
        """Return an RDF resource as a fully expanded IRI when possible."""
        value = self.graph.value(subject, predicate)
        if value is None:
            return None

        iri = str(value)
        if "://" in iri:
            return iri

        try:
            return str(self.graph.namespace_manager.expand_curie(iri))
        except (KeyError, ValueError):
            return iri

    def _build_field_mapping_index(self) -> dict[str, FieldMapping]:
        mapping_by_variable_id: dict[str, FieldMapping] = {}
        for field_uri in self.graph.subjects(RDF.type, T_FIELD):
            variable_uri = self.graph.value(field_uri, REPRESENTS)
            if variable_uri is None:
                continue

            source_uri = self.graph.value(field_uri, HAS_SOURCE)
            extract_uri = self.graph.value(source_uri, HAS_EXTRACT) if source_uri else None
            file_object_uri = None
            if source_uri:
                file_object_uri = self.graph.value(source_uri, HAS_FILE_OBJECT)
                if file_object_uri is None:
                    file_object_uri = self.graph.value(source_uri, HAS_FILE_OBJECT_ALT)

            variable_id = self._str(variable_uri)
            mapping = FieldMapping(
                field_id=self._str(field_uri),
                data_type=self._scalar(field_uri, DATA_TYPE),
                source_id=self._str(source_uri) if source_uri else None,
                extract_id=self._str(extract_uri) if extract_uri else None,
                json_path=self._scalar(extract_uri, JSON_PATH) if extract_uri else None,
                file_object_id=self._str(file_object_uri) if file_object_uri else None,
                file_object_label=self._label(file_object_uri) if file_object_uri else None,
            )
            mapping_by_variable_id[variable_id] = mapping

            # Backward-compatible alias:
            # some benchmark files use field->represents "variable_*" while
            # benchmark.evaluates references "metric_*" ids for the same concept.
            if "variable_" in variable_id:
                mapping_by_variable_id[variable_id.replace("variable_", "metric_", 1)] = mapping
            elif "metric_" in variable_id:
                mapping_by_variable_id[variable_id.replace("metric_", "variable_", 1)] = mapping
        return mapping_by_variable_id

    def _field_mapping(self, variable_uri: URIRef) -> Optional[FieldMapping]:
        return self._field_mapping_by_variable_id.get(self._str(variable_uri))

    def build_numerical_parameter(self, uri: URIRef) -> NumericalParameter:
        return NumericalParameter(
            id=self._str(uri),
            label=self._label(uri),
            numerical_value=self._parameter_value(uri, HAS_NUMERICAL_VALUE),
            unit=self._scalar(uri, HAS_UNIT),
            unit_iri=self._iri(uri, HAS_UNIT),
            field_mapping=self._field_mapping(uri),
        )

    def build_text_parameter(self, uri: URIRef) -> TextParameter:
        return TextParameter(
            id=self._str(uri),
            label=self._label(uri),
            string_value=self._parameter_value(uri, HAS_STRING_VALUE),
            unit=self._scalar(uri, HAS_UNIT),
            unit_iri=self._iri(uri, HAS_UNIT),
            field_mapping=self._field_mapping(uri),
        )

    def build_numerical_variable(self, uri: URIRef) -> NumericalVariable:
        return NumericalVariable(
            id=self._str(uri),
            label=self._label(uri),
            unit=self._scalar(uri, HAS_UNIT),
            unit_iri=self._iri(uri, HAS_UNIT),
            quantity_kind=self._scalar(uri, HAS_KIND_OF_QTY),
            field_mapping=self._field_mapping(uri),
        )

    def build_parameter_entry(self, uri: URIRef) -> ParameterEntry:
        if self.graph.value(uri, HAS_STRING_VALUE) is not None:
            return self.build_text_parameter(uri)
        if self.graph.value(uri, HAS_NUMERICAL_VALUE) is not None:
            return self.build_numerical_parameter(uri)
        if (uri, RDF.type, T_NUMERICAL_VARIABLE) in self.graph:
            return self.build_numerical_variable(uri)
        return self.build_numerical_parameter(uri)

    def build_parameter_set(self, uri: URIRef) -> ParameterSet:
        return ParameterSet(
            id=self._str(uri),
            label=self._label(uri),
            identifier=self._scalar(uri, M4I.identifier),
            parts=[
                self.build_parameter_entry(part)
                for part in self.graph.objects(uri, HAS_PART)
            ],
        )

    def build_parameter_sets(self, uri: URIRef) -> list[ParameterSet]:
        """Expand a template into scalar configurations with stable identifiers.

        Scalar-only templates keep their original IDs. Multi-valued templates
        use ``--1``, ``--2``, ... suffixes, ordered by part IRI and RDF value.
        """
        template = self.build_parameter_set(uri)
        if not any(isinstance(getattr(part, field, None), list)
                   for part in template.parts
                   for field in ("string_value", "numerical_value")):
            return [template]

        choices = []
        for part in sorted(template.parts, key=lambda part: part.id):
            field = "string_value" if isinstance(part, TextParameter) else "numerical_value"
            value = getattr(part, field, None)
            choices.append([replace(part, **{field: option}) for option in value]
                           if isinstance(value, list) else [part])
        return [replace(template, id=f"{template.id}--{index}",
                        identifier=(f"{template.identifier}--{index}"
                                    if template.identifier else None),
                        parts=[replace(part) for part in combination])
                for index, combination in enumerate(product(*choices), start=1)]

    def build_tool(self, uri: URIRef) -> Tool:
        return Tool(id=self._str(uri), label=self._label(uri))

    def build_io_object(self, uri: URIRef) -> IOObject:
        return IOObject(id=self._str(uri), label=self._label(uri))

    def build_processing_step(self, uri: URIRef) -> ProcessingStep:
        return ProcessingStep(
            id=self._str(uri),
            label=self._label(uri),
            inputs=[
                self.build_io_object(input_entity)
                for input_entity in self.graph.objects(uri, HAS_INPUT)
            ],
            outputs=[
                self.build_io_object(output_entity)
                for output_entity in self.graph.objects(uri, HAS_OUTPUT)
            ],
            configurations=[
                expanded
                for config in self.graph.objects(uri, USES_CONFIG)
                for expanded in self.build_parameter_sets(config)
            ],
            employed_tools=[
                self.build_tool(tool)
                for tool in self.graph.objects(uri, HAS_EMPLOYED_TOOL)
            ],
        )

    @staticmethod
    def _runtime_requirement_errors(
        benchmark: SemanticBenchmark,
    ) -> list[str]:
        """Return missing runtime requirements for benchmark execution.

        These checks are intentionally narrower than SHACL validation. They
        capture the fields the benchmark runners need in order to generate
        configuration parameter files and launch workflows successfully.
        """
        errors: list[str] = []

        if not benchmark.parameter_sets:
            errors.append(
                "benchmark must define at least one parameter set via "
                "m4i:hasParameterSet"
            )
            return errors

        identifiers: set[str] = set()
        for parameter_set in benchmark.parameter_sets:
            if parameter_set.identifier in identifiers:
                errors.append(f"duplicate configuration identifier: {parameter_set.identifier!r}")
            if parameter_set.identifier:
                identifiers.add(parameter_set.identifier)
            parameter_set_name = parameter_set.label or parameter_set.id

            if not parameter_set.identifier:
                errors.append(
                    f"parameter set {parameter_set_name!r} is missing "
                    "m4i:identifier"
                )

            if not parameter_set.parts:
                errors.append(
                    f"parameter set {parameter_set_name!r} must contain at least "
                    "one parameter entry"
                )
                continue

            for parameter in parameter_set.parts:
                parameter_name = parameter.label or parameter.id

                if not parameter.label:
                    errors.append(
                        f"parameter {parameter.id!r} in parameter set "
                        f"{parameter_set_name!r} is missing rdfs:label"
                    )

                if isinstance(parameter, TextParameter):
                    if parameter.string_value is None:
                        errors.append(
                            f"text parameter {parameter_name!r} in parameter set "
                            f"{parameter_set_name!r} is missing "
                            "m4i:hasStringValue"
                        )
                    continue

                if isinstance(parameter, NumericalParameter):
                    if parameter.numerical_value is None:
                        errors.append(
                            f"numerical parameter {parameter_name!r} in "
                            f"parameter set {parameter_set_name!r} is missing "
                            "m4i:hasNumericalValue"
                        )
                    continue

                errors.append(
                    f"parameter {parameter_name!r} in parameter set "
                    f"{parameter_set_name!r} has no scalar value that can be "
                    "written to parameters.json; define m4i:hasNumericalValue "
                    "or m4i:hasStringValue"
                )

        return errors

    @classmethod
    def _raise_for_missing_runtime_requirements(
        cls,
        benchmark: SemanticBenchmark,
    ) -> None:
        """Raise ``ValueError`` when runtime-required benchmark data is missing."""
        errors = cls._runtime_requirement_errors(benchmark)
        if errors:
            details = "\n".join(f"- {error}" for error in errors)
            raise ValueError(
                "Benchmark JSON-LD is missing runtime-required properties:\n"
                f"{details}"
            )

    def load(self) -> SemanticBenchmark:
        benchmark_uri = next(self.graph.subjects(RDF.type, T_BENCHMARK), None)
        if benchmark_uri is None:
            raise ValueError("No m4i:Benchmark node found.")

        publication_uri = self.graph.value(benchmark_uri, DESCRIBED_BY)
        version = self._scalar(benchmark_uri, VERSION)

        benchmark = SemanticBenchmark(
            id=self._str(benchmark_uri),
            label=self._label(benchmark_uri),
            version=version,
            investigates=next(
                (
                    ResearchProblem(
                        id=self._str(research_problem_uri),
                        label=self._label(research_problem_uri),
                    )
                    for research_problem_uri in self.graph.objects(
                        benchmark_uri, INVESTIGATES
                    )
                ),
                None,
            ),
            uses=[
                MathematicalModel(
                    id=self._str(model_uri),
                    label=self._label(model_uri),
                )
                for model_uri in self.graph.objects(benchmark_uri, USES)
            ],
            evaluates=[
                self.build_numerical_variable(metric)
                for metric in self.graph.objects(benchmark_uri, EVALUATES)
            ],
            parameter_sets=[
                expanded
                for parameter_set in self.graph.objects(benchmark_uri, M4I.hasParameterSet)
                for expanded in self.build_parameter_sets(parameter_set)
            ],
            described_by=(
                Publication(
                    id=self._str(publication_uri),
                    label=self._label(publication_uri),
                )
                if publication_uri
                else None
            ),
            processing_steps=[
                self.build_processing_step(step)
                for step in self.graph.subjects(RDF.type, T_PROCESSING_STEP)
            ],
        )
        self._raise_for_missing_runtime_requirements(benchmark)
        return benchmark
