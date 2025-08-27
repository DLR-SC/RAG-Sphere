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
    NaiveGRRetrieverConfig,
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
from graphrag.query.generation_api import GenerationAPI
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
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {self.config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")

        # Retrieval
        result = _retrieve(
            config=self.config,
            config_parser=self.config_parser,
            prompt=prompt, 
            messages=messages,
            documents=self.documents, 
            graph_db=self.graph_db, 
            vector_db=self.vector_db, 
            llm=self.llm, 
            emb_model=self.emb_model
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
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {self.config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        result = _retrieve(
            config=self.config,
            config_parser=self.config_parser,
            prompt=prompt, 
            messages=messages,
            documents=self.documents, 
            graph_db=self.graph_db, 
            vector_db=self.vector_db, 
            llm=self.llm, 
            emb_model=self.emb_model
        )
        return result

class NaiveGraphRAGRetriever(BaseRetriever):
    # For documentation and validation purposes
    name: ClassVar[RetrieverType] = RetrieverType.NAIVEGR
    config: NaiveGRRetrieverConfig
    parameter_schema: ClassVar[Dict[str, Any]] = {}

    def __init__(
            self,
            parameter: Optional[Dict[str, Any]] = None, 
            config: Optional[NaiveGRRetrieverConfig] = None,
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
            cls_retriever_config=NaiveGRRetrieverConfig,
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
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {self.config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        result = _retrieve(
            config=self.config,
            config_parser=self.config_parser,
            prompt=prompt, 
            messages=messages,
            documents=self.documents, 
            graph_db=self.graph_db, 
            vector_db=self.vector_db, 
            llm=self.llm, 
            emb_model=self.emb_model
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
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {self.config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        result = _retrieve(
            config=self.config,
            config_parser=self.config_parser,
            prompt=prompt, 
            messages=messages,
            documents=self.documents, 
            graph_db=self.graph_db, 
            vector_db=self.vector_db, 
            llm=self.llm, 
            emb_model=self.emb_model
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
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {self.config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _graphrag_retrieve(
            prompt = prompt,
            messages = messages,
            config = self.config,
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
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {self.config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _graphrag_retrieve(
            prompt = prompt,
            messages = messages,
            config = self.config,
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
        logger.info(f"DOING '{self.name.value}' RETRIEVAL WITH {self.config}")
        logger.info(f"USING THE FOLLOWING QUERY: '{prompt}'")
        
        # Retrieval
        return _text2cypher_retrieve(
            prompt = prompt,
            messages = messages,
            config = self.config,
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
    
    
def _retrieve(
        config: BaseRetrieverConfig,
        config_parser: ConfigParser,
        prompt: Optional[str] = None, 
        messages: Optional[List[Dict[str,str]]] = None,
        documents: Optional[str] = None, 
        graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
        vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
        llm: Optional[LLMClient] = None, 
        emb_model: Optional[SentenceTransformer] = None,
) -> List[RetrievalAnswer]:
    query_api = GenerationAPI(config=config,
                              config_parser=config_parser,
                              documents=documents,
                              graph_db=graph_db,
                              vector_db=vector_db,
                              llm=llm,
                              emb_model=emb_model)
    
    # Create answer after the ERI format
    answer = {
        "name": "Knowledge Graph",
        "category": "extracted data from multiple different files (sources)",
        "path": "",
        "type": AllowedTypes.NONE,
        "matchedContent":  "",
        "surroundingContent": [],
        "links": []
    }

    # Extract and apply the retrieval method
    match config.name:
        case RetrieverType.GARAG:
            results = query_api.generate_garag_answer(prompt=prompt, 
                                                      max_matches=config.top_k,
                                                      confidence_cutoff=config.confidence_cutoff)
        case RetrieverType.NAIVEGR:
            results = query_api.generate_graph_rag_rag_answer(prompt=prompt, 
                                                             max_matches=config.top_k,
                                                             confidence_cutoff=config.confidence_cutoff)
        case RetrieverType.GRAPHRAG:
            results = query_api.generate_graph_rag_answer(prompt=prompt, 
                                                         max_matches=config.top_k, 
                                                         community_degree=config.community_degree,
                                                         confidence_cutoff=config.confidence_cutoff)
        case RetrieverType.VECTOR:
            results = query_api.generate_rag_answer(prompt=prompt, 
                                                   max_matches=config.top_k,
                                                   confidence_cutoff=config.confidence_cutoff)
    
    # Convert the results into a list of RetrievalAnswers (ERI format):
    answer["type"] = AllowedTypes.TEXT
    answers = []
    for result in results:
        answer["matchedContent"] = result["content"]
        answer["name"] = str(result["source"])
        answer["path"] = str(result["document"])
        answers.append(RetrievalAnswer(**answer))
    if(len(answers) == 0):
        return [RetrievalAnswer(**answer)]
    
    logger.debug(str(answers))
    return answers