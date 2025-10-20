"""
Orchestration class for the available RAG techniques.
- user-facing wrapper
"""
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

import logging
logger = logging.getLogger(__name__)

import os
import json
from traceback import format_exc
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from configparser import ConfigParser

from utils.llm_client import LLMClient
from utils.arango_client import ArangoDBClient
from graphrag.prompts import check_connection

from indexer_engine import IndexerEngine
from query_engine import QueryEngine

from protocols.rag import BaseRAG
from protocols.indexer import (
    BaseIndexer,
    BaseIndexerConfig
)
from protocols.retriever import (
    BaseRetriever,
    BaseRetrieverConfig
)
from models.enums import (
    IndexerType, 
    RetrieverType, 
    DatabaseType,
    SUPPORTED_COMBINATIONS
)

""" 

"""
class RAG(BaseRAG):
    config: ConfigParser                                                    # Config file with default settings
    documents: Optional[str]                                                # Document path
    graph_db: Optional[Union[str, ArangoDBClient]]                          # Graph database, for now only str input supported
    vector_db: Optional[Union[str, Elasticsearch]]                          # Vector database, for now only str input supported
    indexer: Optional[Union[str, BaseIndexer]]                              # Low level indexer class or indexer name
    retriever: Optional[Union[str, BaseRetriever]]                          # Low level retriever class or indexer name
    indexer_config: Optional[Union[Dict[str, Any], BaseIndexerConfig]]      # 
    retriever_config: Optional[Union[Dict[str, Any], BaseRetrieverConfig]]  # 
    llm_index: Optional[LLMClient]                                          # LLM client for the indexing phase
    llm_query: Optional[LLMClient]                                          # LLM client for the query phase
    emb_model: Optional[Union[str, SentenceTransformer]]                    # Embedding model
    query_engine: QueryEngine
    indexer_engine: IndexerEngine

    def __init__(
            self, 
            documents: Optional[str] = None,
            graph_db: Optional[Union[str, ArangoDBClient]] = None,
            vector_db: Optional[Union[str, Elasticsearch]] = None,
            indexer: Optional[Union[str, BaseIndexer]] = None,
            indexer_config: Optional[Union[Dict[str, Any], BaseIndexerConfig]] = None,   
            retriever_config: Optional[Union[Dict[str, Any], BaseRetrieverConfig]] = None,
            retriever: Optional[Union[str, BaseRetriever]] = None,
            llm_index: Optional[LLMClient] = None,
            llm_query: Optional[LLMClient] = None,
            emb_model: Optional[Union[str, SentenceTransformer]] = None,
            verbosity: Optional[int] = 1
    ) -> None:
        # Configure the verbosity
        self._set_global_logging_level(verbosity)
        logger.info("RAG initialized with verbosity %s", verbosity)

        # Load config file with default values
        self.config = ConfigParser()
        self.config.read("../resources/config.ini")

        # indexer_config & retriever_config
        if isinstance(indexer_config, (dict, BaseIndexerConfig, type(None))):
            self.indexer_config = indexer_config
        else:
            raise ValueError("indexer_config must be of type 'dict' or 'BaseIndexerConfig'")

        if isinstance(retriever_config, (dict, BaseRetrieverConfig, type(None))):
            self.retriever_config = retriever_config
        else:
            raise ValueError("retriever_config must be of type 'dict' or 'BaseRetrieverConfig'")
        
        ## Rag Techniques (default or custom config)
        # indexer input validation -> write _set_indexer()
        if indexer is None:
            self.indexer = None
        elif isinstance(indexer, str):
            try:
                self.indexer = IndexerType(indexer)
                logger.info(f"The indexing technique is set to: '{indexer}'\n")
            except ValueError:
                raise ValueError(f"Invalid indexer name: '{indexer}'. Supported: {[e.value for e in IndexerType]}")
        elif isinstance(indexer, BaseIndexer):
            self.indexer = indexer
            logger.info(f"The indexing technique is set to: '{indexer.name}'\n")
        else:
            raise ValueError("indexer must be of type 'str' or 'BaseIndexer'")
            
        # retriever input validation -> write _set_retriever()
        if retriever is None:
            self.retriever = None
        elif isinstance(retriever, str):
            try:
                self.retriever = RetrieverType(retriever)
                logger.info(f"The retrieval technique is set to: '{retriever}'\n")
            except ValueError:
                raise ValueError(f"Invalid retriever name: '{retriever}'. Supported: {[e.value for e in RetrieverType]}")
        elif isinstance(retriever, BaseRetriever):
            self.retriever = retriever
            logger.info(f"The retrieval technique is set to: ''{retriever.name}'\n")
        else:
            raise ValueError("retriever must be of type 'str' or 'BaseRetriever'")

        # Load default techniques & Check if the (indexer, retriever) combination is supported
        if self.indexer is None and self.retriever is None:
            self._set_default_technique()
        else:
            self._validate_supported_combination(self.indexer, self.retriever)

        # Document path
        if documents is None:
            default_path = self.config.get("general", "data_dir")
            logger.info("The document path has not been specified.")
            logger.info(f"Using default path: '{default_path}'\n")
            self.documents = default_path
        elif isinstance(documents, str):
            self.documents = documents
            logger.info(f"Document path is set to: '{documents}'\n")
        else:
            raise ValueError("documents must be of type 'str'")

        # GraphDB input validation and enum conversion
        if graph_db is None:
            logger.info("The graph database has not been specified.")
            logger.info("Using default graph database: 'Neo4j'\n")
            self.graph_db = DatabaseType.NEO4J
        elif isinstance(graph_db, str):
            try:
                self.graph_db = DatabaseType(graph_db)
                logger.info(f"Graph Database is set to: '{graph_db}'\n")
            except ValueError:
                raise ValueError(f"Invalid graph_db: '{graph_db}'. Supported: {[e.value for e in DatabaseType]}")
        else:
            raise ValueError("graph_db must be of type 'str'")

        # VectorDB input validation and enum conversion
        if vector_db is None:
            logger.info("The vector database has not been specified.")
            logger.info("Using default vector database: 'Neo4j'\n")
            self.vector_db = DatabaseType.NEO4J
        elif isinstance(vector_db, str):
            try:
                self.vector_db = DatabaseType(vector_db)
                logger.info(f"Vector database is set to: '{vector_db}'\n")
            except ValueError:
                raise ValueError(f"Invalid vector_db: '{vector_db}'. Supported: {[e.value for e in DatabaseType]}")
        else:
            raise ValueError("vector_db must be of type 'str'")

        ## Get LLM Clients (injected or default from the config)
        # Index LLM input validation
        if llm_index is None:
            default_model = self.config.get("llm_index", "model_name")
            logger.info("The indexing LLM has not been specified.")
            logger.info(f"Using the default indexing LLM: '{default_model}'\n")
            self.llm_index = None
            if self.graph_db!=DatabaseType.NEO4J:
                self.llm_index = self._get_llm(config=self.config, index=True)
        elif isinstance(llm_index, LLMClient):
            self.llm_index = llm_index
            logger.info(f"The indexing LLM is set to: '{llm_index.model_name}'\n")
        else:
            raise ValueError("llm_index must be of type 'LLMClient'")

        # Query LLM input validation
        if llm_query is None:
            default_model = self.config.get("llm_query", "model_name")
            logger.info("The query LLM has not been specified.")
            logger.info(f"Using the default query LLM: '{default_model}'\n")
            self.llm_query = None
            if self.graph_db!=DatabaseType.NEO4J:
                self.llm_query = self._get_llm(config=self.config, query=True)
        elif isinstance(llm_query, LLMClient):
            logger.info(f"The query LLM is set to: '{llm_query.model_name}'\n")
            self.llm_query = llm_query
        else:
            raise ValueError("llm_query must be of type 'LLMClient'")

        # Test llm connection (llm_index and llm_query)
        if self.llm_index and self.llm_query:
            self.test_llm_connection(llm_index=self.llm_index, llm_query=self.llm_query)

        # Loading Embedding model and input validation
        if emb_model is None:
            default_model = self.config.get("general", "default_embedding_model")
            logger.info("The embedding model has not been specified.")
            logger.info(f"Using the default embedding model: '{default_model}'")
            self.emb_model = None
            if self.graph_db!=DatabaseType.NEO4J:
                self.emb_model = SentenceTransformer(default_model)
            logger.info(f"Successfully loaded\n")
        elif isinstance(emb_model, SentenceTransformer):
            self.emb_model = emb_model
        elif isinstance(emb_model, str):
            logger.info(f"The embedding model is set to: '{emb_model}'")
            if self.graph_db!=DatabaseType.NEO4J:
                self.emb_model = SentenceTransformer(emb_model)
                logger.info(f"Successfully loaded\n")
        else:
            raise ValueError("emb_model must be of type 'str' or 'SentenceTransformer'")

        # Load the Indexer Engine
        self.indexer_engine = IndexerEngine(
            documents=self.documents,
            llm=self.llm_index,
            emb_model=self.emb_model,
            graph_db=self.graph_db,
            vector_db=self.vector_db,
            indexer=self.indexer,
            indexer_config=self.indexer_config,
            config=self.config
        )

        # Load the Query Engine
        self.query_engine = QueryEngine(
            documents=self.documents,
            llm=self.llm_query,
            emb_model=self.emb_model,
            graph_db=self.graph_db,
            vector_db=self.vector_db,
            retriever=self.retriever,
            retriever_config=self.retriever_config,
            config=self.config
        )

    def index(
        self, 
        verbosity: Optional[int] = 1, 
        **kwargs: Any
    ) -> None:
        if verbosity:
            self._set_global_logging_level(verbosity)
        if self.indexer is None:
            logger.warning("No indexing technique has been specified.")
        else:
            self.indexer_engine.index(**kwargs)

    def query(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            retrieval_query: Optional[str] = None,
            verbosity: Optional[int] = 1,
            **kwargs: Any
    ) -> Any:
        if verbosity:
            self._set_global_logging_level(verbosity)
        if self.retriever is None:
            logger.warning("No retrieval technique has been specified.")
        else:
            return self.query_engine.query(prompt, messages, retrieval_query=retrieval_query, **kwargs)

    def _get_llm(
            self, 
            config : ConfigParser, 
            index: bool = False, 
            query: bool = False
    ) -> LLMClient:
        """ Load the llm client for the index or query phase with the setting from the config file """
        # Read llm service specifications
        if index:
            provider = config.get("llm_index", "provider")
            base_url = config.get("llm_index", "base_url")
            api_key = config.get("llm_index", "api_key").strip()
            model_name = config.get("llm_index", "model_name")
            options_str = config.get("llm_index", "options")
            options = json.loads(options_str)

        if query:
            provider = config.get("llm_query", "provider")
            base_url = config.get("llm_query", "base_url")
            api_key = config.get("llm_query", "api_key").strip()
            model_name = config.get("llm_query", "model_name")
            options_str = config.get("llm_query", "options")
            options = json.loads(options_str)

        # Load the llm client
        llm_client = LLMClient(
            provider=provider,
            base_url=base_url, 
            api_key=api_key, 
            model_name=model_name,
            options=options)
        
        return llm_client

    def test_llm_connection(self, llm_index: LLMClient, llm_query: LLMClient):
        """
        This method will test the llm service specified by the config file by issuing a small test request.

        Parameters:
        - config (ConfigParser): The ConfigParser of the provided config file
        """
        logger.info("Testing the LLM connection...")
        model = llm_index.model_name
        options = llm_index.options
        try:
            # Try to send a test prompt and wait for a response
            r_index = llm_index.generate(new_model=model,
                                         prompt=check_connection.USER_PROMPT, 
                                         system=check_connection.SYSTEM_PROMPT,
                                         format=check_connection.ANSWER_FORMAT,
                                         new_options=options)
            logger.info(f"Indexing LLM answer: {r_index}")
            r_query = llm_query.generate(new_model=model,
                                         prompt=check_connection.USER_PROMPT, 
                                         system=check_connection.SYSTEM_PROMPT,
                                         format=check_connection.ANSWER_FORMAT,
                                         new_options=options)
            logger.info(f"Query LLM answer: {r_query}\n")
        except Exception as e:
            logger.warning("LLM Connection unavailable! Please check the parameters in the config file and llm server status!")
     
    @staticmethod
    def _get_enum_type(
        obj, 
        enum_class: Union[IndexerType, RetrieverType], 
        base_class: Union[BaseIndexer, BaseRetriever]
    ) -> Union[IndexerType, RetrieverType]:
        """ Get the enum type of the specified technique """
        if obj is None:
            return None
        elif isinstance(obj, enum_class):
            return obj
        elif isinstance(obj, base_class):
            return enum_class(obj.name)
        else:
            raise TypeError(f"Expected {enum_class.__name__} or {base_class.__name__}, got {type(obj).__name__}")

    @staticmethod
    def _supported_combinations_repr():
        lines = []
        for indexer, retriever in SUPPORTED_COMBINATIONS:
            indexer_str = f"'{indexer.value}'" if indexer else "'None'"
            retriever_str = f"'{retriever.value}'" if retriever else "'None'"
            lines.append(f"  - Indexer: {indexer_str:<20} Retriever: {retriever_str:<20}")
        return '\n'.join(lines)
    
    def _get_supported_combinations(self):
        logger.info(f"\nSupported combinations are:\n{self._supported_combinations_repr()}")

    def _validate_supported_combination(self, indexer, retriever):
        """ Validating if the given (indexer, retriever) combination is supported """
        indexer_type = self._get_enum_type(indexer, IndexerType, BaseIndexer)
        retriever_type = self._get_enum_type(retriever, RetrieverType, BaseRetriever)

        if (indexer_type, retriever_type) not in SUPPORTED_COMBINATIONS:
            indexer_str = f"'{indexer_type.value}'" if indexer_type else "'None'"
            retriever_str = f"'{retriever_type.value}'" if retriever_type else "'None'"
            raise ValueError(
                f"\nUnsupported combination:\n  - Indexer: {indexer_str:<20} Retriever: {retriever_str:<20}\n"
                f"\nSupported combinations are:\n{self._supported_combinations_repr()}"
            )
        
    def _set_default_technique(self):
        """ Setting the default indexing and retrieval technique """
        default_indexing = self.config.get("general", "default_indexing")
        default_query = self.config.get("general", "default_query")
        logger.info("No technique has been specified.")
        logger.info(f"Loading default indexing technique: '{default_indexing}")
        logger.info(f"Loading default retrieval technique: '{default_query}'\n")
        self.indexer = IndexerType(default_indexing)
        self.retriever = RetrieverType(default_query)

    def _set_global_logging_level(self, verbosity: Optional[int] = 1):
        verbosity_map = {
           -1: logging.ERROR,
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
        }
        level = verbosity_map.get(verbosity, logging.INFO)

        log_path = "../resources/initialization.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Remove existing handlers to avoid duplicates
        while root_logger.handlers:
            root_logger.removeHandler(root_logger.handlers[0])

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # File handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

if __name__ == "__main__":
    # r=RAG()
    pass
