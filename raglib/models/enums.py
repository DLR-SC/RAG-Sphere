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
    TEMP = "template"

class RetrieverType(str, Enum):
    GARAG = "garag"
    NAIVEGR = "naivegraphrag"
    GRAPHRAG = "graphrag"
    VECTOR = "naiverag"
    TEMP = "template"

class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    ELASTICSEARCH = "elasticsearch"
    ARANGODB = "arangodb"

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
    (IndexerType.VECTOR, RetrieverType.VECTOR)
    # ADD MORE
]