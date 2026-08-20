"""RDF namespaces, predicates, and types used by semantic benchmark metadata."""

from rdflib import Namespace, URIRef

M4I = Namespace("http://w3id.org/nfdi4ing/metadata4ing#")
OBO = Namespace("http://purl.obolibrary.org/obo/")
CR = Namespace("http://mlcommons.org/croissant/")
SCHEMA = Namespace("https://schema.org/")

HAS_NUMERICAL_VALUE = M4I.hasNumericalValue
HAS_STRING_VALUE = M4I.hasStringValue
HAS_UNIT = M4I.hasUnit
HAS_KIND_OF_QTY = M4I.hasKindOfQuantity
HAS_PART = OBO.BFO_0000051
HAS_INPUT = OBO.RO_0002233
HAS_OUTPUT = OBO.RO_0002234
USES_CONFIG = M4I.usesConfiguration
HAS_EMPLOYED_TOOL = M4I.hasEmployedTool
DATA_TYPE = M4I.dataType
JSON_PATH = CR.jsonPath
INVESTIGATES = M4I.investigates
EVALUATES = M4I.evaluates
USES = URIRef("http://www.wikidata.org/entity/P2283")
DESCRIBED_BY = URIRef("https://mardi4nfdi.github.io/MathModDB/P104")
REPRESENTS = URIRef("http://semanticscience.org/resource/SIO_000210")
HAS_SOURCE = CR.source
HAS_EXTRACT = CR.extract
VERSION = SCHEMA.version
VERSION_ALT = URIRef("http://schema.org/version")

HAS_FILE_OBJECT = URIRef("http://mlcommons.org/croissant/FileObject")
HAS_FILE_OBJECT_ALT = URIRef("http://mlcommons.org/croissant/fileObject")

T_BENCHMARK = M4I.Benchmark
T_NUMERICAL_VARIABLE = M4I.NumericalVariable
T_PROCESSING_STEP = M4I.ProcessingStep
T_FIELD = CR.Field
