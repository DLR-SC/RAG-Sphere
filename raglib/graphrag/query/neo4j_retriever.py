import logging
logger = logging.getLogger(__name__)

import json
from typing import Any, List, Dict
from configparser import ConfigParser
from protocols.indexer import (
    BaseIndexer,
    BaseIndexerConfig
)
from models.enums import (
    RetrieverType,
    DatabaseType
)

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import SentenceTransformerEmbeddings
from neo4j_graphrag.llm import OllamaLLM
from neo4j_graphrag.retrievers import (
    VectorRetriever, 
    VectorCypherRetriever,
    HybridRetriever,
    HybridCypherRetriever,
    Text2CypherRetriever,
)
from neo4j_graphrag.schema import get_structured_schema, format_schema
from neo4j_graphrag.generation import GraphRAG


def _test_connection(driver):
    try:
        with driver.session() as session:
            result = session.run("RETURN 1")
            print("Connection successful:", result.single()[0] == 1)
    except Exception as e:
        print("Connection failed:", e)

def _graphrag_retrieve(
        prompt: str, 
        messages: List[Dict[str,str]],
        config: BaseIndexerConfig,
        config_parser: ConfigParser = None,
        retrieval_query: str = "MATCH (node)-[:AUTHORED_BY]->(author:Author)" "RETURN author.name",
        **kwargs: Any
) -> Any:
    # DB Connection
    # Database credentials
    URI = config_parser.get("neo4j", "url")
    DB_NAME = config_parser.get("neo4j", "db_name")
    PASSWORD = config_parser.get("neo4j", "password")

    # Connect to Neo4j database
    driver = GraphDatabase.driver(URI, auth=(DB_NAME, PASSWORD))
    _test_connection(driver)
    
    # LLM
    API_KEY = config_parser.get("llm_query", "api_key").strip()
    BASE_URL = config_parser.get("llm_query", "base_url")
    MODEL_NAME = config_parser.get("llm_query", "model_name")
    LLM_OPTIONS_STR = config_parser.get("llm_query", "options")
    LLM_OPTIONS = json.loads(LLM_OPTIONS_STR)
    
    llm = OllamaLLM(
        model_name=MODEL_NAME,
        model_params={"options": LLM_OPTIONS},
        host=BASE_URL,
        headers = {"Authorization": f"Bearer {API_KEY}"}
    )

    # Embedding model
    EMBEDDER = config_parser.get("general", "default_embedding_model")
    embedder = SentenceTransformerEmbeddings(model = EMBEDDER)
        
    # When performing a similarity search, one may have constraints to apply. For instance, filtering out movies released before 2000. This can be achieved using filters.
    if config.name==RetrieverType.VECTORGR or config.name==RetrieverType.VECTORGR: #cypher
        filters = config.filters

    # Initialize the retriever
    match config.name:
        case RetrieverType.VECTORGR:
            V_INDEX_NAME = config.v_index_name
            return_properties = config.return_properties
            retriever = VectorRetriever(
                driver=driver,
                index_name=V_INDEX_NAME,
                return_properties = return_properties,
                embedder=embedder,
                neo4j_database=DB_NAME
            )
            retriever_config = {
                "top_k": config.top_k,
                "filters": config.filters 
                } 
        case RetrieverType.VECTORCYPHERGR: # Add result formatter
            V_INDEX_NAME = config.v_index_name
            retrieval_query = retrieval_query
            retriever = VectorCypherRetriever(
                driver=driver,
                index_name=V_INDEX_NAME,
                retrieval_query = retrieval_query,
                embedder=embedder,
                neo4j_database=DB_NAME
            )
            retriever_config = { # Add query_params
                "top_k": config.top_k,
                "filters": config.filters 
                } 
        case RetrieverType.HYBRIDGR: # Add ranker and alpha support
            V_INDEX_NAME = config.v_index_name
            F_INDEX_NAME = config.f_index_name
            return_properties = config.return_properties
            retriever = HybridRetriever(
                driver=driver,
                vector_index_name=V_INDEX_NAME,
                fulltext_index_name=F_INDEX_NAME,
                return_properties = return_properties,
                embedder=embedder,
                neo4j_database=DB_NAME
            )
            retriever_config = { "top_k": config.top_k }
        case RetrieverType.HYBRIDCYPHERGR: # Add result formatter
            V_INDEX_NAME = config.v_index_name
            F_INDEX_NAME = config.f_index_name
            retriever = HybridCypherRetriever(
                driver=driver,
                vector_index_name=V_INDEX_NAME,
                fulltext_index_name=F_INDEX_NAME,
                retrieval_query = retrieval_query,
                embedder=embedder,
                neo4j_database=DB_NAME
            )
            retriever_config = { 
                "top_k": config.top_k 
            } # Add query_params

    # Initialize the RAG pipeline
    rag = GraphRAG(
        retriever=retriever, 
        llm=llm
    )

    # Query the graph
    response = rag.search(
        query_text = prompt, 
        retriever_config = retriever_config,
        return_context = True
    )
    
    return {
        "answer" : response.answer,
        "retriever_result": response.retriever_result.items,
        "query_vector": response.retriever_result.metadata["query_vector"]
    }


def _remove_searchable(structured_schema, exclude_label="Searchable"):
    cleaned = structured_schema.copy()

    # 1. Remove nodes with Searchable label
    cleaned["node_props"] = {
        k: v for k, v in structured_schema["node_props"].items()
        if exclude_label not in k
    }

    # 2. Remove relationship property definitions for Searchable
    cleaned["rel_props"] = {
        k: v for k, v in structured_schema["rel_props"].items()
        if exclude_label not in k
    }

    # 3. Remove relationships where start or end is Searchable
    cleaned["relationships"] = [
        rel for rel in structured_schema["relationships"]
        if exclude_label not in rel["start"]
        and exclude_label not in rel["end"]
        and exclude_label not in rel["type"]
    ]
    return cleaned


def _text2cypher_retrieve(
        prompt: str, 
        messages: List[Dict[str,str]],
        config: BaseIndexerConfig,
        config_parser: ConfigParser = None,
        **kwargs: Any
) -> Any:
    # DB Connection
    # Database credentials
    URI = config_parser.get("neo4j", "url")
    DB_NAME = config_parser.get("neo4j", "db_name")
    PASSWORD = config_parser.get("neo4j", "password")

    # Connect to Neo4j database
    driver = GraphDatabase.driver(URI, auth=(DB_NAME, PASSWORD))
    _test_connection(driver)
    
    # LLM
    API_KEY = config_parser.get("llm_query", "api_key").strip()
    BASE_URL = config_parser.get("llm_query", "base_url")
    MODEL_NAME = config_parser.get("llm_query", "model_name")
    LLM_OPTIONS_STR = config_parser.get("llm_query", "options")
    print(LLM_OPTIONS_STR)
    LLM_OPTIONS = json.loads(LLM_OPTIONS_STR)

    llm = OllamaLLM(
        model_name=MODEL_NAME,
        model_params={"options": LLM_OPTIONS},
        host=BASE_URL,
        headers = {"Authorization": f"Bearer {API_KEY}"}
    )
    
    # Extract Graph Schema
    structured_schema = get_structured_schema(
        driver=driver, 
        is_enhanced=False, 
        database="neo4j", 
        timeout=None, 
        sanitize=False
    )

    # Clean Graph Schema from "Searchable"
    cleaned_schema = _remove_searchable(structured_schema=structured_schema)

    # Serialize Graph Schema
    formatted_schema = format_schema(
        schema = cleaned_schema,
        is_enhanced = False
    )

    # Provide user input/query pairs for the LLM to use as examples
    examples = config.examples

    # Initialize the retriever
    retriever = Text2CypherRetriever(
        driver = driver,
        llm = llm,
        neo4j_schema = formatted_schema,
        examples = examples,
    )
    
    response = retriever.search(query_text = prompt)
    
    return {
        "cypher" : response.metadata["cypher"],
        "retriever_result": response.items
    }