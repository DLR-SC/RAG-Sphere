"""
The graph construction logic of graph-based retrieval techniques.
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
from models.indexer import (
    GARAGIndexerConfig,
    GraphRAGIndexerConfig,
    NaiveGRIndexerConfig,
    NaiveRAGIndexerConfig,
    VectorGRIndexerConfig,
    HybridGRIndexerConfig,
    TemplateIndexerConfig
)

from protocols.indexer import (
    BaseIndexer,
    BaseIndexerConfig
)

from graphrag.index.KG_1_LoadData import load_data
from graphrag.index.KG_2_ConvertTextsToGraph import generate_knowledge_graph
from graphrag.index.KG_3_ProcessKnowledgeGraph import process_knowledge_graph
from graphrag.index.KG_4_InitLeidenCommunities import build_communities
from graphrag.index.KG_5_CreateCommunitySummaries import summarize_communities
from graphrag.index.KG_6_CreateCommunityIndices import generate_community_indices
from graphrag.index.neo4j_indexer import _graphrag_index

class GARAGIndexer(BaseIndexer):
    # For documentation and validation purposes 
    name: ClassVar[IndexerType] = IndexerType.GARAG
    config: GARAGIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[GARAGIndexerConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        super().__init__(
            parameter=parameter,
            config=config,
            cls_indexer_config=GARAGIndexerConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def index(self, **kwargs: Any):
        logger.info(f"DOING '{self.name.value}' INDEXING WITH {self.config}")

        # Indexing
        _index(
            config=self.config,
            config_parser=self.config_parser,
            documents=self.documents,
            graph_db=self.graph_db,
            vector_db=self.vector_db,
            llm=self.llm,
            emb_model=self.emb_model
        )

class GraphRAGIndexer(BaseIndexer):
    # For documentation and validation purposes
    name: ClassVar[IndexerType] = IndexerType.GRAPHRAG
    config: GraphRAGIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[GraphRAGIndexerConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        super().__init__(
            parameter=parameter,
            config=config,
            cls_indexer_config=GraphRAGIndexerConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def index(self, **kwargs: Any):
        logger.info(f"DOING '{self.name.value}' INDEXING WITH {self.config}")

        # Indexing
        _index(
            config=self.config,
            config_parser=self.config_parser,
            documents=self.documents,
            graph_db=self.graph_db,
            vector_db=self.vector_db,
            llm=self.llm,
            emb_model=self.emb_model
        )

class NaiveGraphRAGIndexer(BaseIndexer):
    # For documentation and validation purposes
    name: ClassVar[IndexerType] = IndexerType.NAIVEGR
    config: NaiveGRIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[NaiveGRIndexerConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        super().__init__(
            parameter=parameter,
            config=config,
            cls_indexer_config=NaiveGRIndexerConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def index(self, **kwargs: Any):
        logger.info(f"DOING '{self.name.value}' INDEXING WITH {self.config}")

        # Indexing
        _index(
            config=self.config,
            config_parser=self.config_parser,
            documents=self.documents,
            graph_db=self.graph_db,
            vector_db=self.vector_db,
            llm=self.llm,
            emb_model=self.emb_model
        )

class NaiveRAGIndexer(BaseIndexer):
    # For documentation and validation purposes
    name: ClassVar[IndexerType] = IndexerType.VECTOR
    config: NaiveRAGIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[NaiveRAGIndexerConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        super().__init__(
            parameter=parameter,
            config=config,
            cls_indexer_config=NaiveRAGIndexerConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def index(self, **kwargs: Any):
        logger.info(f"DOING '{self.name.value}' INDEXING WITH {self.config}")
        
        # Indexing -> Adjust the indexing method to vector indexing!
        _index(
            config=self.config,
            config_parser=self.config_parser,
            documents=self.documents,
            graph_db=self.graph_db,
            vector_db=self.vector_db,
            llm=self.llm,
            emb_model=self.emb_model
        )


class VectorGRIndexer(BaseIndexer):
    # For documentation and validation purposes 
    name: ClassVar[IndexerType] = IndexerType.VECTORGR
    config: VectorGRIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[VectorGRIndexerConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        super().__init__(
            parameter=parameter,
            config=config,
            cls_indexer_config=VectorGRIndexerConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def index(self, **kwargs: Any) -> None:
        logger.info(f"DOING '{self.name.value}' INDEXING WITH {self.config}")
        
        _graphrag_index(
            config = self.config,
            config_parser = self.config_parser
        )

class HybridGRIndexer(BaseIndexer):
    # For documentation and validation purposes 
    name: ClassVar[IndexerType] = IndexerType.HYBRIDGR
    config: HybridGRIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[HybridGRIndexerConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        super().__init__(
            parameter=parameter,
            config=config,
            cls_indexer_config=HybridGRIndexerConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def index(self, **kwargs: Any) -> None:
        logger.info(f"DOING '{self.name.value}' INDEXING WITH {self.config}")
        
        _graphrag_index(
            config = self.config,
            config_parser = self.config_parser
        )
    

class TemplateIndexer(BaseIndexer):
    # For documentation and validation purposes 
    name: ClassVar[IndexerType] = IndexerType.TEMP
    config: TemplateIndexerConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[TemplateIndexerConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        super().__init__(
            parameter=parameter,
            config=config,
            cls_indexer_config=TemplateIndexerConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def index(self):
        pass



def _index(
        config: BaseIndexerConfig,
        config_parser: ConfigParser = None,
        documents: Optional[str] = None, 
        graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
        vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
        llm: Optional[LLMClient] = None, 
        emb_model: Optional[SentenceTransformer] = None
) -> None:
    # Counter variables for better print output
    total_method_calls = 6
    method_counter = 0
    def counter_inc():
        nonlocal method_counter
        method_counter += 1
        return method_counter
    
    # Load elastic client
    if vector_db==DatabaseType.ELASTICSEARCH:
        logger.info("Connecting ElasticSearch client...")
        elastic_url = config_parser.get("elastic", "url")
        elastic_client = Elasticsearch(elastic_url)

    # Test elastic connection
    test_elastic_connection(elastic_client)

    # Elastic related config
    rag_index_name = "sc_pub_rag"
    garag_index_name = "sc_pub_garag"
    elastic_rag = (elastic_client, emb_model, rag_index_name)
    elastic_garag = (elastic_client, emb_model, garag_index_name)
    
    # Load arangodb client
    arango_knowledge_graph_client = None
    arango_community_graph_client = None
    if graph_db==DatabaseType.ARANGODB and config.name!=IndexerType.VECTOR:
        logger.info("Connecting ArangoDB clients...\n")
        db_name = "SC_Pub"
        arango_knowledge_graph_client = ArangoDBClient(config_parser, db_name = db_name, graph_name = "knowledge_graph")
        arango_community_graph_client = ArangoDBClient(config_parser, db_name = db_name, graph_name = "community_graph")
    
    ########################
    logger.info(f"({counter_inc()}/{total_method_calls}) Loading files into ArangoDB / ElasticSearch...\n")
    try_method(method=load_data, 
               error_message="Error whilst reading file data!",
               config=config,
               config_parser=config_parser, 
               documents=documents,
               arango_client=arango_knowledge_graph_client, 
               elastic_tuple=elastic_rag)
    
    # Return if we are doing vectorrag
    if config.name==IndexerType.VECTOR:
        return

    logger.info(f"({counter_inc()}/{total_method_calls}) Generating knowledge graph...\n")
    try_method(method=generate_knowledge_graph,
               error_message="Error whilst generating knowledge graph!",
               config=config,
               config_parser=config_parser, 
               ner_model=llm,
               arango_client=arango_knowledge_graph_client)

    logger.info(f"({counter_inc()}/{total_method_calls}) Processing knowledge graph...\n")
    try_method(method=process_knowledge_graph,
               error_message="Error whilst formating knowledge graph!",
               config=config,
               config_parser=config_parser,
               arango_client=arango_knowledge_graph_client)

    logger.info(f"({counter_inc()}/{total_method_calls}) Generating a community graph...\n")
    try_method(method=build_communities, 
               error_message="Error whilst building graph communities!",
               config=config,
               config_parser=config_parser,
               knowledge_graph=arango_knowledge_graph_client, 
               community_graph=arango_community_graph_client)

    logger.info(f"({counter_inc()}/{total_method_calls}) Summarizing community information...\n")
    try_method(method=summarize_communities,
               error_message="Error whilst creating community summaries!",
               config=config,
               config_parser=config_parser,
               llm_client=llm,
               community_graph=arango_community_graph_client)

    logger.info(f"({counter_inc()}/{total_method_calls}) Creating elastic search indices for community information...\n")
    try_method(method=generate_community_indices,
               error_message="Error whilst creating community summary embeddings!",
               config=config,
               config_parser=config_parser,
               community_graph=arango_community_graph_client, 
               elastic_tuple=elastic_garag)

    logger.info(f"Indexing completed!")
    #########################


def try_method(method, error_message : str, **kwargs):
    """
    This method tries to run "method" using the arguments provided. 
    When an Exeption is raised, the error message is logged to the log file.
    """
    try:
        method(**kwargs)
    except:
        logger.error(f"! {error_message}\n! A major error ocurred during Initialization. Exiting script...\n{format_exc()}")


def test_elastic_connection(elastic_client: Elasticsearch):
    """
    This method will test the health of the provided Elasticsearch client.

    Paramerters:
    - elastic_client (Elasticsearch): The client to test
    """
    # Retry 5 times, before exiting with the error
    for i in range(5):
        try:
            # Check health status
            elastic_client.options(request_timeout=30, retry_on_status=[104]).cluster.health()
            break
        except Exception as e:
            if i < 4: 
                continue
            logging.error(f"! Elasticsearch Connection unavailable! Please check the parameters in the config file and Elasticsearch server status!\n{format_exc()}")
