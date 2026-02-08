"""
Indexer Config
"""

from dataclasses import (
    dataclass, 
    field, 
    replace
)
from typing import (
    ClassVar,
    Dict,
    List,
    Any
)

from protocols.indexer import BaseIndexerConfig
from models.enums import (
    IndexerType
)

"""
Set default values
"""
@dataclass
class GARAGIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.GARAG
    max_chunk_size: int = 4096

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class GraphRAGIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.GRAPHRAG
    max_chunk_size: int = 4096

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class NaiveGRIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.NAIVEGR
    max_chunk_size: int = 4096

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class NaiveRAGIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.VECTOR
    max_chunk_size: int = 4096

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class VectorGRIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.VECTORGR
    similarity_fn: str = "cosine"
    v_index_name: str = "vector_index_all"

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class HybridGRIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.HYBRIDGR
    similarity_fn: str = "cosine"
    f_index_name: str = "ft_index_all"
    v_index_name: str = "vector_index_all"
    target_nodes: List[str] | None = None          # Using only properties from target nodes to create the fulltext index e.g. ["Procedure", "Command", "Event"]
    property_limit: int = 40                       # max. 80 with a short query
    
    def update(self, **kwargs):
        return replace(self, **kwargs)
    
@dataclass
class TemplateIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.TEMP
    chunk_size: int = 600
    chunk_overlap: int = 64

    def update(self, **kwargs):
        return replace(self, **kwargs)
    
