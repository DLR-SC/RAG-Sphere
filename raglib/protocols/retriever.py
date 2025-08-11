""" Abstract Retriever Classes """

from abc import ABC, abstractmethod
from typing import (
    List, 
    Any, 
    Union,
    Optional,
    ClassVar, 
    Dict
)
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from configparser import ConfigParser

from utils.llm_client import LLMClient
from utils.arango_client import ArangoDBClient

from models.enums import (
    RetrieverType,
    DatabaseType
)

class BaseRetrieverConfig(ABC):
    name: ClassVar[RetrieverType]
    parameter_schema: ClassVar[Dict[str, Any]] = {}

class BaseRetriever(ABC):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType]
    config: BaseRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    @abstractmethod
    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[BaseRetrieverConfig] = None,
            cls_retriever_config: Optional[BaseRetrieverConfig] = None,
            documents: Optional[str] = None, 
            config_parser: ConfigParser = None,
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        # Retrieval config (injected with Retriever(config=RetrieverConfig) or Retriever(config_dict))
        if config:
            self.config = config
        else:
            # Default retriever config
            self.config = cls_retriever_config()
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
    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None
    ) -> list[str]:
        """Retrieve relevant documents/nodes based on the query."""
        pass

class BaseGraphRetriever(BaseRetriever):
    name: ClassVar[RetrieverType]
    config: BaseRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    @abstractmethod
    def traverse_graph(self, query: str) -> List[Any]:
        """Graph-specific traversal logic."""
        pass

class BaseVectorRetriever(BaseRetriever):
    name: ClassVar[RetrieverType]
    config: BaseRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    @abstractmethod
    def embed_query(self, query: str) -> List[Any]:
        """Return vector embedding for the query."""
        pass