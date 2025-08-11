""" Abstract Indexer Classes """

from abc import ABC, abstractmethod
from typing import (
    Any, 
    Dict,
    List, 
    Union,
    Callable,
    Optional,
    ClassVar
)

from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from configparser import ConfigParser

from utils.llm_client import LLMClient
from utils.arango_client import ArangoDBClient

from models.enums import (
    IndexerType,
    DatabaseType
)
""" ToDO: Pydantic/BaseModel config validation
"""
class BaseIndexerConfig(ABC):
    name: ClassVar[IndexerType]
    parameter_schema: ClassVar[Dict[str, Any]] = {}
    
class BaseIndexer(ABC):
    # For documentation and validation purposes 
    name: ClassVar[IndexerType]
    config: BaseIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    @abstractmethod
    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[BaseIndexerConfig] = None,
            cls_indexer_config: Optional[BaseIndexerConfig] = None,
            documents: Optional[str] = None, 
            config_parser: ConfigParser = None,
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        # Indexing config (injected with Indexer(config=IndexerConfig) or Indexer(config_dict))
        if config:
            self.config = config
        else:
            # Default indexer config
            self.config = cls_indexer_config()
        # Override the default settings with a given parameter dict config
        if parameter:
            self.config = self.config.update(**parameter)
        
        # Get config file with default values
        self.config_parser = config_parser

        # Document path
        self.documents = documents

        # Database types
        self.graph_db = graph_db
        self.vector_db = vector_db

        # LLM client for the indexing phase
        self.llm = llm

        # Embedding model for the indexing phase
        self.emb_model = emb_model

    def _set_context(
            self,
            documents: Optional[str] = None, 
            config_parser: ConfigParser = None,
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        """ 
        Set the context for late injection
        set_context() allows to inject the remaining components after construction. 
        """
        # Get config file with default values
        self.config_parser = config_parser
        
        # Document path
        self.documents = documents

        # Database types
        self.graph_db = graph_db
        self.vector_db = vector_db

        # LLM client for the indexing phase
        self.llm = llm

        # Embedding model for the indexing phase
        self.emb_model = emb_model
    
    @abstractmethod
    def index(self):
        """Indexing"""
        pass

class BaseGraphIndexer(BaseIndexer):
    name: ClassVar[IndexerType]
    config: BaseIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    @abstractmethod
    def build_graph(self) -> Any:
        """Construct knowledge graph from documents."""
        pass

class BaseVectorIndexer(BaseIndexer):
    name: ClassVar[IndexerType]
    config: BaseIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    @abstractmethod
    def build_vector_index(self) -> Any:
        """Construct vector index."""
        pass
