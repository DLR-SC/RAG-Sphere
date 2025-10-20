"""
The retrieval logic of graph-based retrieval techniques.
--> Each retrieval method is self-contained
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
import traceback

from utils.llm_client import LLMClient
from utils.arango_client import ArangoDBClient

from models.enums import (
    RetrieverType,
    DatabaseType
)
from models.retriever import (
    GARAGRetrieverConfig,
    GraphRAGRetrieverConfig,
    NaiveRAGRetrieverConfig,
    NaiveRAGRetrieverConfig,
    VectorGRRetrieverConfig,
    HybridGRRetrieverConfig,
    Text2CypherRetrieverConfig,
    TemplateRetrieverConfig
)
from protocols.retriever import (
    BaseRetriever,
    BaseRetrieverConfig
)

from eri_components.components import RetrievalAnswer, AllowedTypes
from graphrag.query.graphRAG_retriever import _graph_rag_retrieve, _garag_retrieve, _naive_graph_rag_retrieve, _naive_rag_retrieve
from graphrag.query.neo4j_retriever import _graphrag_retrieve, _text2cypher_retrieve

class GARAGRetriever(BaseRetriever):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType] = RetrieverType.GARAG
    config: GARAGRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[GARAGRetrieverConfig] = None,
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
            cls_retriever_config=GARAGRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> List[Any]:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")

        # Retrieval
        result = _garag_retrieve(
            prompt=prompt,
            graph_db=self.graph_db,
            vector_db=self.vector_db,
            vector_db_index_name=config.vector_db_index_name,
            emb_model=self.emb_model,
            max_matches=config.top_k,
            confidence_cutoff=config.confidence_cutoff,
        )
        return result

class GraphRAGRetriever(BaseRetriever):
    # For documentation and validation purposes
    name: ClassVar[RetrieverType] = RetrieverType.GRAPHRAG
    config: GraphRAGRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[GraphRAGRetrieverConfig] = None,
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
            cls_retriever_config=GraphRAGRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> List[Any]:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        result = _graph_rag_retrieve(
            prompt=prompt,
            llm=self.llm,
            graph_db=self.graph_db,
            max_matches=config.top_k,
            community_degree=config.community_degree,
            confidence_cutoff=config.confidence_cutoff
        )
        return result

class NaiveGraphRAGRetriever(BaseRetriever):
    # For documentation and validation purposes
    name: ClassVar[RetrieverType] = RetrieverType.NAIVEGR
    config: NaiveRAGRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[NaiveRAGRetrieverConfig] = None,
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
            cls_retriever_config=NaiveRAGRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> List[Any]:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        result = _naive_graph_rag_retrieve(
            prompt=prompt,
            vector_db=self.vector_db,
            vector_db_index_name=config.vector_db_index_name,
            emb_model=self.emb_model,
            max_matches=config.top_k,
            confidence_cutoff=config.confidence_cutoff
        )
        return result
    
class NaiveRAGRetriever(BaseRetriever):
    # For documentation and validation purposes
    name: ClassVar[RetrieverType] = RetrieverType.VECTOR
    config: NaiveRAGRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[NaiveRAGRetrieverConfig] = None,
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
            cls_retriever_config=NaiveRAGRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> List[Any]:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        result = _naive_rag_retrieve(
            prompt=prompt,
            vector_db=self.vector_db,
            vector_db_index_name=config.vector_db_index_name,
            emb_model=self.emb_model,
            max_matches=config.get("top_k") or self.config.top_k,
            confidence_cutoff=config.confidence_cutoff
        )
        return result
    

class VectorGRRetriever(BaseRetriever):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType] = RetrieverType.VECTORGR
    config: VectorGRRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[VectorGRRetrieverConfig] = None,
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
            cls_retriever_config=VectorGRRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> Any:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _graphrag_retrieve(
            prompt = prompt,
            messages = messages,
            config = config,
            config_parser = self.config_parser,
        )
        
class VectorCypherGRRetriever(BaseRetriever):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType] = RetrieverType.VECTORGR
    config: VectorGRRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[VectorGRRetrieverConfig] = None,
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
            cls_retriever_config=VectorGRRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            retrieval_query: Optional[str] = None,
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> Any:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _graphrag_retrieve(
            prompt = prompt,
            messages = messages,
            retrieval_query = retrieval_query,
            config = config,
            config_parser = self.config_parser,
        )
    
class HybridGRRetriever(BaseRetriever):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType] = RetrieverType.HYBRIDGR
    config: HybridGRRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[HybridGRRetrieverConfig] = None,
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
            cls_retriever_config=HybridGRRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> Any:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _graphrag_retrieve(
            prompt = prompt,
            messages = messages,
            config = config,
            config_parser = self.config_parser,
        )
    

class HybridCypherGRRetriever(BaseRetriever):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType] = RetrieverType.HYBRIDGR
    config: HybridGRRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[HybridGRRetrieverConfig] = None,
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
            cls_retriever_config=HybridGRRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            retrieval_query: Optional[str] = None,
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> Any:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _graphrag_retrieve(
            prompt = prompt,
            messages = messages,
            retrieval_query = retrieval_query,
            config = config,
            config_parser = self.config_parser,
        )

    
class Text2CypherRetriever(BaseRetriever):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType] = RetrieverType.TEXT2CYPHER
    config: Text2CypherRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[Text2CypherRetrieverConfig] = None,
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
            cls_retriever_config=Text2CypherRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None,
            **kwargs: Any
    ) -> Any:
        """ Run retrieval logic """
        config = self.config.update(**kwargs)
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _text2cypher_retrieve(
            prompt = prompt,
            messages = messages,
            config = config,
            config_parser = self.config_parser,
        )
    
    
class TemplateRetriever(BaseRetriever):
    # For documentation and validation purposes 
    name: ClassVar[RetrieverType] = RetrieverType.TEMP
    config: TemplateRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[TemplateRetrieverConfig] = None,
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
            cls_retriever_config=TemplateRetrieverConfig,
            documents=documents,
            config_parser=config_parser,
            graph_db=graph_db,
            vector_db=vector_db,
            llm=llm,
            emb_model=emb_model
        )

    def retrieve(
            self, 
            prompt: Optional[str] = None, 
            messages: Optional[List[Dict[str,str]]] = None
    ) -> List[Any]:
        pass
