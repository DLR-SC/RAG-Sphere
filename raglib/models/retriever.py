"""
Query Config
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

from protocols.retriever import BaseRetrieverConfig

from models.enums import (
    RetrieverType
)

"""
Set default values from the config.ini file
"""
@dataclass
class GARAGRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.GARAG
    top_k: int = 1024                               # The maximum number of matching information to return
    similarity_metric: str = "cosine"                 
    confidence_cutoff: float = 0.04             

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class GraphRAGRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.GRAPHRAG
    top_k: int = 1024                               # The maximum number of matching information to return
    community_degree: int = 1                       # The depth to search for in the communitygraph.
    confidence_cutoff: float = 40                   # Community selection confidence cutoff
    similarity_metric: str = "cosine"                               

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class NaiveGRRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.NAIVEGR
    top_k: int = 1024                               # The maximum number of matching information to return
    confidence_cutoff: float = 0.04                 # Community selection confidence cutoff
    similarity_metric: str = "cosine" 

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class NaiveRAGRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.VECTOR
    top_k: int = 1024                               # The maximum number of matching information to return
    confidence_cutoff: float = 0.04                 # Text chunk selection confidence cutoff
    similarity_metric: str = "cosine"

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class TemplateRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.TEMP
    top_k: int = 1024
    similarity_metric: str = "cosine"

    def update(self, **kwargs):
        return replace(self, **kwargs)
    
    