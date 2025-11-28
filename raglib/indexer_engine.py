"""
Mid-level Orchestrator: 
Handles the indexing process (Pipeline)
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
    IndexerType,
    DatabaseType
)
from protocols.indexer import ( 
    BaseIndexer, 
    BaseIndexerConfig
)
from models.indexer import (
    GARAGIndexerConfig,
    GraphRAGIndexerConfig,
    NaiveGRIndexerConfig,
    NaiveRAGIndexerConfig,
    VectorGRIndexerConfig,
    HybridGRIndexerConfig
)
from graphrag.indexer import (
    GraphRAGIndexer,
    NaiveGraphRAGIndexer,
    GARAGIndexer,
    NaiveRAGIndexer,
    VectorGRIndexer,
    HybridGRIndexer
)

class IndexerEngine:
    config: ConfigParser                                    # Config file with default settings
    documents: str                                          # Document path
    graph_db: Union[DatabaseType, ArangoDBClient]           # Graph database, for now only str input supported
    vector_db: Union[DatabaseType, Elasticsearch]           # Vector database, for now only str input supported
    llm: Optional[LLMClient] = None                         # LLM client for the indexing phase
    emb_model: Optional[SentenceTransformer] = None         # Embedding model
    indexer: Union[IndexerType, BaseIndexer]                # Low level indexer class or indexer type
    indexer_config: Optional[Union[Dict[str, Any], BaseIndexerConfig]]
    
    def __init__(
            self, 
            config: ConfigParser,
            documents: str,
            graph_db: Union[DatabaseType, ArangoDBClient],
            vector_db: Union[DatabaseType, Elasticsearch],
            indexer: Union[IndexerType, BaseIndexer],
            llm: Optional[LLMClient] = None,
            emb_model: Optional[SentenceTransformer] = None,
            indexer_config: Optional[Union[Dict[str, Any], BaseIndexerConfig]] = None
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

        # Custom indexer config (injected with indexer='name', indexer_config= ..)
        # Using the parameter_schema for reference and merging with defaults
        if isinstance(indexer_config, (BaseIndexerConfig, type(None))):
            self.indexer_config = indexer_config
        elif isinstance(indexer_config, dict):
            config_class = self._get_indexer_config_class(indexer)
            # Override default indexer settings
            self.indexer_config = config_class(**indexer_config)

        # Set indexing technique
        if isinstance(indexer, IndexerType):
            self.indexer = self._get_indexer(documents=self.documents, 
                                             config_parser=self.config,
                                             graph_db=self.graph_db,
                                             vector_db=self.vector_db,
                                             llm=self.llm,
                                             emb_model=self.emb_model,
                                             indexer=indexer,
                                             indexer_config=self.indexer_config)
        elif isinstance(indexer, BaseIndexer):
            # Indexer is partially instantiated with parameter or config, and later completed with graph_db, llm etc.
            indexer._set_context(documents=self.documents,
                                 config_parser=self.config,
                                 graph_db=self.graph_db,
                                 vector_db=self.vector_db,
                                 llm=self.llm,
                                 emb_model=self.emb_model)
            self.indexer = indexer

    @staticmethod
    def _get_indexer(
            config_parser: ConfigParser,
            documents: str,
            graph_db: Union[DatabaseType, ArangoDBClient],
            vector_db: Union[DatabaseType, Elasticsearch],
            indexer: IndexerType,
            llm: Optional[LLMClient] = None,
            emb_model: Optional[SentenceTransformer] = None,
            indexer_config: Optional[BaseIndexerConfig] = None
    ) -> BaseIndexer:
        """ Get Indexer """
        class_args = {
            "config_parser": config_parser,
            "config": indexer_config,
            "documents": documents,
            "graph_db": graph_db,
            "vector_db": vector_db,
            "llm": llm,
            "emb_model": emb_model,
        }

        match indexer:
            case IndexerType.GARAG:
                return GARAGIndexer(**class_args)
            case IndexerType.NAIVEGR:
                return NaiveGraphRAGIndexer(**class_args)
            case IndexerType.GRAPHRAG:
                return GraphRAGIndexer(**class_args)
            case IndexerType.VECTOR:
                return NaiveRAGIndexer(**class_args)
            case IndexerType.VECTORGR:
                return VectorGRIndexer(**class_args)
            case IndexerType.HYBRIDGR:
                return HybridGRIndexer(**class_args)
            case _:
                raise ValueError(f"Unknown indexer type")

    @staticmethod
    def _get_indexer_config_class(indexer: IndexerType) -> BaseIndexerConfig:
         match indexer:
            case IndexerType.GARAG:
                return GARAGIndexerConfig
            case IndexerType.NAIVEGR:
                return NaiveGRIndexerConfig
            case IndexerType.GRAPHRAG:
                return GraphRAGIndexerConfig
            case IndexerType.VECTOR:
                return NaiveRAGIndexerConfig
            case IndexerType.VECTORGR:
                return VectorGRIndexerConfig
            case IndexerType.HYBRIDGR:
                return HybridGRIndexerConfig
            case _:
                raise ValueError(f"Unknown indexer name")

    def index(self, **kwargs: Any):
        return self.indexer.index(**kwargs)