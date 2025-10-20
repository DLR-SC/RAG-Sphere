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
    Optional,
    Dict,
    List,
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
    vector_db_index_name: str = ""

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class GraphRAGRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.GRAPHRAG
    top_k: int = 1024                               # The maximum number of matching information to return
    community_degree: int = 1                       # The depth to search for in the communitygraph.
    confidence_cutoff: float = 40                   # Community selection confidence cutoff
    similarity_fn: str = "cosine"                               

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class NaiveRAGRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.NAIVEGR
    top_k: int = 1024                               # The maximum number of matching information to return
    confidence_cutoff: float = 0.04                 # Community selection confidence cutoff
    similarity_fn: str = "cosine" 
    vector_db_index_name: str = ""

    def update(self, **kwargs):
        return replace(self, **kwargs)

@dataclass
class NaiveRAGRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.VECTOR
    top_k: int = 1024                               # The maximum number of matching information to return
    confidence_cutoff: float = 0.04                 # Text chunk selection confidence cutoff
    similarity_fn: str = "cosine"
    vector_db_index_name: str = ""

    def update(self, **kwargs):
        return replace(self, **kwargs)


@dataclass
class VectorGRRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.VECTORGR
    top_k: int = 5                   
    similarity_fn: str = "cosine"
    f_index_name: str = "ft_index_all"
    v_index_name: str = "vector_index_all"
    return_properties: List[str] | None = None   # List of node properties to return.
    filters: Dict[str, Any] | None = None        # Filters for metadata pre-filtering. When performing a similarity search, one may have constraints to apply. For instance, filtering out movies released before 2000. This can be achieved using filters.

    def update(self, **kwargs):
        return replace(self, **kwargs)
    
@dataclass
class VectorCypherGRRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.VECTORCYPHERGR
    top_k: int = 5                   
    similarity_fn: str = "cosine"
    f_index_name: str = "ft_index_all"
    v_index_name: str = "vector_index_all"
    filters: Dict[str, Any] | None = None        # Filters for metadata pre-filtering. When performing a similarity search, one may have constraints to apply. For instance, filtering out movies released before 2000. This can be achieved using filters.

    def update(self, **kwargs):
        return replace(self, **kwargs)
    
@dataclass
class HybridGRRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.HYBRIDGR
    top_k: int = 5                  
    similarity_fn: str = "cosine"
    f_index_name: str = "ft_index_all"
    v_index_name: str = "vector_index_all"
    return_properties: List[str] | None = None   # List of node properties to return.

    def update(self, **kwargs):
        return replace(self, **kwargs)
 
@dataclass
class HybridCypherGRRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.HYBRIDCYPHERGR
    top_k: int = 5                  
    similarity_fn: str = "cosine"
    f_index_name: str = "ft_index_all"
    v_index_name: str = "vector_index_all"

    def update(self, **kwargs):
        return replace(self, **kwargs)
    
@dataclass
class Text2CypherRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.TEXT2CYPHER 
    top_k: int = 0                              # Unused in this retriever; Needed to be ERI complient        
    # Optional user input/query pairs for the LLM to use as examples.
    examples: List[str] = field(default_factory=lambda: ["USER INPUT: 'Which actors starred in the Matrix?' QUERY: MATCH (p:Person)-[:ACTED_IN]->(m:Movie) WHERE m.title = 'The Matrix' RETURN p.name"])
    
    def update(self, **kwargs):
        return replace(self, **kwargs)
    
@dataclass
class TemplateRetrieverConfig(BaseRetrieverConfig):
    name: ClassVar[RetrieverType] = RetrieverType.TEMP
    top_k: int = 1024
    similarity_metric: str = "cosine"

    def update(self, **kwargs):
        return replace(self, **kwargs)
    
    