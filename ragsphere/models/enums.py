""" Enum classes """
from typing import (
    List,
    Dict,
    Tuple,
    Set,
    Any,
    Callable,
    ClassVar,
    Optional,
    TypeVar,
    Union
)

from enum import Enum

class IndexerType(str, Enum):
    GARAG = "garag"
    NAIVEGR = "naivegraphrag"
    GRAPHRAG = "graphrag"
    VECTOR = "naiverag"
    VECTORGR = "vectorgraphrag"
    HYBRIDGR = "hybridgraphrag"
    TEMP = "template"

class RetrieverType(str, Enum):
    GARAG = "garag"
    NAIVEGR = "naivegraphrag"
    GRAPHRAG = "graphrag"
    VECTOR = "naiverag"
    VECTORGR = "vectorgraphrag"
    VECTORCYPHERGR = "vectorcyphergraphrag"
    HYBRIDGR = "hybridgraphrag"
    HYBRIDCYPHERGR = "hybridcyphergraphrag"
    TEXT2CYPHER = "text2cypher"
    TEMP = "template"

class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    ELASTICSEARCH = "elasticsearch"
    ARANGODB = "arangodb"
    NEO4J = "neo4j"

SUPPORTED_COMBINATIONS: List[Tuple[IndexerType, RetrieverType]] = [
    (IndexerType.GARAG, None),
    (IndexerType.GRAPHRAG, None),
    (IndexerType.NAIVEGR, None),
    (IndexerType.VECTOR, None),
    (None, RetrieverType.GARAG),
    (None, RetrieverType.GRAPHRAG),
    (None, RetrieverType.NAIVEGR),
    (None, RetrieverType.VECTOR),
    (IndexerType.GARAG, RetrieverType.GARAG),
    (IndexerType.GARAG, RetrieverType.GRAPHRAG),
    (IndexerType.GARAG, RetrieverType.NAIVEGR),
    (IndexerType.GARAG, RetrieverType.VECTOR),
    (IndexerType.GRAPHRAG, RetrieverType.GARAG),
    (IndexerType.GRAPHRAG, RetrieverType.GRAPHRAG),
    (IndexerType.GRAPHRAG, RetrieverType.NAIVEGR),
    (IndexerType.GRAPHRAG, RetrieverType.VECTOR),
    (IndexerType.NAIVEGR, RetrieverType.GARAG),
    (IndexerType.NAIVEGR, RetrieverType.GRAPHRAG),
    (IndexerType.NAIVEGR, RetrieverType.NAIVEGR),
    (IndexerType.NAIVEGR, RetrieverType.VECTOR),
    (IndexerType.VECTOR, RetrieverType.VECTOR),
    (IndexerType.VECTORGR, RetrieverType.VECTORGR),
    (IndexerType.VECTORGR, RetrieverType.VECTORCYPHERGR),
    (IndexerType.VECTORGR, None),
    (IndexerType.HYBRIDGR, RetrieverType.HYBRIDGR),
    (IndexerType.HYBRIDGR, RetrieverType.HYBRIDCYPHERGR),
    (IndexerType.HYBRIDGR, RetrieverType.VECTORGR),
    (IndexerType.HYBRIDGR, RetrieverType.VECTORCYPHERGR),
    (IndexerType.HYBRIDGR, None),
    (None, RetrieverType.TEXT2CYPHER),
    # ADD MORE
]