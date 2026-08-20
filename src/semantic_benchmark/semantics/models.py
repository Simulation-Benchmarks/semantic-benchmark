"""Domain models for a semantic benchmark description."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class KGNode:
    id: str
    label: Optional[str] = None


@dataclass
class ResearchProblem(KGNode):
    pass


@dataclass
class MathematicalModel(KGNode):
    pass


@dataclass
class Publication(KGNode):
    pass


@dataclass
class FieldMapping:
    field_id: str
    data_type: Optional[str] = None
    source_id: Optional[str] = None
    extract_id: Optional[str] = None
    json_path: Optional[str] = None
    file_object_id: Optional[str] = None
    file_object_label: Optional[str] = None


@dataclass
class NumericalVariable(KGNode):
    unit: Optional[str] = None
    quantity_kind: Optional[str] = None
    field_mapping: Optional[FieldMapping] = None
    unit_iri: Optional[str] = None


@dataclass
class NumericalParameter(KGNode):
    numerical_value: Optional[float] = None
    unit: Optional[str] = None
    field_mapping: Optional[FieldMapping] = None
    unit_iri: Optional[str] = None


@dataclass
class TextParameter(KGNode):
    string_value: Optional[str] = None
    unit: Optional[str] = None
    field_mapping: Optional[FieldMapping] = None
    unit_iri: Optional[str] = None


ParameterEntry = Union[NumericalParameter, TextParameter, NumericalVariable]


@dataclass
class ParameterSet(KGNode):
    identifier: Optional[str] = None
    parts: list[ParameterEntry] = field(default_factory=list)


@dataclass
class Tool(KGNode):
    pass


@dataclass
class IOObject(KGNode):
    pass


@dataclass
class ProcessingStep(KGNode):
    inputs: list[IOObject] = field(default_factory=list)
    outputs: list[IOObject] = field(default_factory=list)
    configurations: list[ParameterSet] = field(default_factory=list)
    employed_tools: list[Tool] = field(default_factory=list)


@dataclass
class SemanticBenchmark(KGNode):
    version: Optional[str] = None
    investigates: Optional[ResearchProblem] = None
    uses: Optional[MathematicalModel] = None
    evaluates: list[NumericalVariable] = field(default_factory=list)
    parameter_sets: list[ParameterSet] = field(default_factory=list)
    described_by: Optional[Publication] = None
    processing_steps: list[ProcessingStep] = field(default_factory=list)
