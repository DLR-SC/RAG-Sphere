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
class TemplateIndexerConfig(BaseIndexerConfig):
    name: ClassVar[IndexerType] = IndexerType.TEMP
    chunk_size: int = 600
    chunk_overlap: int = 64

    def update(self, **kwargs):
        return replace(self, **kwargs)
    
