"""
Mid-level Orchestrator:
Handles the full query → retrieve → prompt → answer flow
    pipeline: A component that handles querying end-to-end (retrieval + ranking + answer)
    -> retrieves → builds prompt → calls LLM
    -> Pluggable retrievers by name ("graph", "vector", "hybrid", etc.)
    -> Central control over retrieval logic inside the engine
"""
from typing import (
    Dict,
    List,
    Any,
    Callable,
    ClassVar,
    Optional,
    TypeVar,
    Union
)

import logging
logger = logging.getLogger(__name__)

import json
from traceback import format_exc
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from configparser import ConfigParser

from utils.llm_client import LLMClient
from utils.arango_client import ArangoDBClient

from models.enums import (
    RetrieverType,
    DatabaseType
)
from protocols.retriever import (
    BaseRetriever,
    BaseRetrieverConfig
)
from models.retriever import (
    GARAGRetrieverConfig,
    GraphRAGRetrieverConfig,
    NaiveRAGRetrieverConfig,
    NaiveRAGRetrieverConfig,
    VectorGRRetrieverConfig,
    VectorCypherGRRetrieverConfig,
    HybridGRRetrieverConfig,
    HybridCypherGRRetrieverConfig,
    Text2CypherRetrieverConfig
)
from graphrag.retriever import (
    GraphRAGRetriever,
    NaiveGraphRAGRetriever,
    GARAGRetriever,
    NaiveRAGRetriever,
    VectorGRRetriever,
    VectorCypherGRRetriever,
    HybridGRRetriever,
    HybridCypherGRRetriever,
    Text2CypherRetriever,
    TemplateRetriever
)

class QueryEngine:
    config: ConfigParser                                    # Config file with default settings
    documents: str                                          # Document path
    graph_db: Union[DatabaseType, ArangoDBClient]           # Graph database, for now only str input supported
    vector_db: Union[DatabaseType, Elasticsearch]           # Vector database, for now only str input supported
    llm: Optional[LLMClient] = None                         # LLM client for the query phase
    emb_model: Optional[SentenceTransformer] = None         # Embedding model
    retriever: Union[RetrieverType, BaseRetriever]          # Low level retriever class or retriever type
    retriever_config: Optional[Union[Dict[str, Any], BaseRetrieverConfig]]

    def __init__(
            self, 
            config: ConfigParser,
            documents: str,
            graph_db: Union[DatabaseType, ArangoDBClient],
            vector_db: Union[DatabaseType, Elasticsearch],
            retriever: Union[RetrieverType, BaseRetriever],
            llm: Optional[LLMClient] = None,
            emb_model: Optional[SentenceTransformer] = None,
            retriever_config: Optional[Union[Dict[str, Any], BaseRetrieverConfig]] = None
    ) -> None:
        # Get config file with default values
        self.config = config

        # Document path
        self.documents = documents

        # Database types
        self.graph_db = graph_db
        self.vector_db = vector_db

        # LLM client for the indexing phase
        self.llm = llm

        # Embedding model for the indexing phase
        self.emb_model = emb_model
        
        # Custom retriever config (injected with retriever='name', retriever_config= ..)
        # Using the parameter_schema for reference and merging with defaults
        if isinstance(retriever_config, (BaseRetrieverConfig, type(None))):
            self.retriever_config = retriever_config
        elif isinstance(retriever_config, dict):
            config_class = self._get_retriever_config_class(retriever)
            # Override default retriever settings
            self.retriever_config = config_class(**retriever_config)

        # Set retrieval technique
        if isinstance(retriever, RetrieverType):
            self.retriever = self._get_retriever(documents=self.documents,
                                                 config_parser=self.config, 
                                                 graph_db=self.graph_db,
                                                 vector_db=self.vector_db,
                                                 llm=self.llm,
                                                 emb_model=self.emb_model,
                                                 retriever=retriever,
                                                 retriever_config=self.retriever_config)
        elif isinstance(retriever, BaseRetriever):
            # retriever is partially instantiated with parameter or config, and later completed with graph_db, llm etc.
            retriever._set_context(documents=self.documents,
                                   config_parser=self.config,
                                   graph_db=self.graph_db,
                                   vector_db=self.vector_db,
                                   llm=self.llm,
                                   emb_model=self.emb_model)
            self.retriever = retriever
        
    @staticmethod
    def _get_retriever( 
            config_parser: ConfigParser,
            documents: str,
            graph_db: Union[DatabaseType, ArangoDBClient],
            vector_db: Union[DatabaseType, Elasticsearch],
            retriever: RetrieverType,
            llm: Optional[LLMClient] = None,
            emb_model: Optional[SentenceTransformer] = None,
            retriever_config: Optional[BaseRetrieverConfig] = None
    ) -> None:
        """ Get Retriever """
        class_args = {
            "config_parser": config_parser,
            "config": retriever_config,
            "documents": documents,
            "graph_db": graph_db,
            "vector_db": vector_db,
            "llm": llm,
            "emb_model": emb_model,
        }

        match retriever:
            case RetrieverType.GARAG:
                return GARAGRetriever(**class_args)
            case RetrieverType.NAIVEGR:
                return NaiveGraphRAGRetriever(**class_args)
            case RetrieverType.GRAPHRAG:
                return GraphRAGRetriever(**class_args)
            case RetrieverType.VECTOR:
                return NaiveRAGRetriever(**class_args)
            case RetrieverType.VECTORGR:
                return VectorGRRetriever(**class_args)
            case RetrieverType.VECTORCYPHERGR:
                return VectorCypherGRRetriever(**class_args)
            case RetrieverType.HYBRIDGR:
                return HybridGRRetriever(**class_args)
            case RetrieverType.HYBRIDCYPHERGR:
                return HybridCypherGRRetriever(**class_args)
            case RetrieverType.TEXT2CYPHER:
                return Text2CypherRetriever(**class_args)
            case _:
                raise ValueError(f"Unknown retriever type")

    @staticmethod
    def _get_retriever_config_class(retriever: RetrieverType) -> BaseRetrieverConfig:
         match retriever:
            case RetrieverType.GARAG:
                return GARAGRetrieverConfig
            case RetrieverType.NAIVEGR:
                return NaiveRAGRetrieverConfig
            case RetrieverType.GRAPHRAG:
                return GraphRAGRetrieverConfig
            case RetrieverType.VECTOR:
                return NaiveRAGRetrieverConfig
            case RetrieverType.VECTORGR:
                return VectorGRRetrieverConfig
            case RetrieverType.VECTORCYPHERGR:
                return VectorCypherGRRetrieverConfig
            case RetrieverType.HYBRIDGR:
                return HybridGRRetrieverConfig
            case RetrieverType.HYBRIDCYPHERGR:
                return HybridCypherGRRetrieverConfig
            case RetrieverType.TEXT2CYPHER:
                return Text2CypherRetrieverConfig
            case _:
                raise ValueError(f"Unknown retriever name")

    def query(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            retrieval_query: Optional[str] = None,
            **kwargs: Any
    ) -> Any:
        #prompt_build = self.prompt_builder.build(prompt, retrieved_docs) #ToDO
        return self.retriever.retrieve(prompt=prompt, messages=messages, retrieval_query=retrieval_query, **kwargs)
