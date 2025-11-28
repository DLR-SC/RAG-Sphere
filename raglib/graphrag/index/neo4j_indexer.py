import logging
logger = logging.getLogger(__name__)

from typing import Any, List
from configparser import ConfigParser

from models.enums import (
    IndexerType,
    DatabaseType
)
from protocols.indexer import (
    BaseIndexer,
    BaseIndexerConfig
)

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import SentenceTransformerEmbeddings
from neo4j_graphrag.types import EntityType
from neo4j_graphrag.schema import get_structured_schema
from neo4j_graphrag.indexes import (
    create_vector_index, 
    create_fulltext_index, 
    upsert_vectors, 
    drop_index_if_exists
)


def _test_connection(driver) -> None:
    try:
        with driver.session() as session:
            result = session.run("RETURN 1")
            print("Connection successful:", result.single()[0] == 1)
    except Exception as e:
        print("Connection failed:", e)
        

def _drop_index(driver, index_name: str) -> None:         
    # Dropping the index if it exists
    drop_index_if_exists(
        driver,
        index_name,
    )


def _graphrag_index(
        config: BaseIndexerConfig,
        config_parser: ConfigParser
) -> None:
    # DB Connection
    # Database credentials
    URI = config_parser.get("neo4j", "url")
    DB_NAME = config_parser.get("neo4j", "db_name")
    PASSWORD = config_parser.get("neo4j", "password")

    # Connect to Neo4j database
    logger.info("Connecting Neo4j client ...")
    driver = GraphDatabase.driver(URI, auth=(DB_NAME, PASSWORD))
    _test_connection(driver)
    
    # Define the subset of node_props you care about
    #TARGET_NODES = ["Procedure", "Command", "Event"]
    TARGET_NODES = config.target_nodes
    PROPERTY_LIMIT = config.property_limit

    # Embedding model
    EMBEDDER = config_parser.get("general", "default_embedding_model")
    embedder = SentenceTransformerEmbeddings(model = EMBEDDER)
    dimension = embedder.model.get_sentence_embedding_dimension()
    similarity_fn = config.similarity_fn

    # Add a shared "Searchable" label
    with driver.session() as session:
        session.run("MATCH (n) SET n:Searchable")

    if config.name==IndexerType.HYBRIDGR:
        # Extract schema
        logger.info("Extracting the graph schema ...")
        
        structured_schema = get_structured_schema(
            driver = driver, 
            is_enhanced = False, 
            database = DB_NAME, 
            timeout = None, 
            sanitize = False
        )
        
        # Extract properties from target nodes
        logger.info("Extracting properties from target nodes ...")
        
        if TARGET_NODES:
            target_nodes = TARGET_NODES
        else:
            target_nodes = ["Searchable"]

        counter = 0
        props_list = []
        for node in target_nodes:
            for prop in structured_schema["node_props"][node]:
                if counter > PROPERTY_LIMIT: # This is the limit before we get the max boolean clause error
                    break
                if prop["type"].upper() == "STRING": # Only String Properties
                    props_list.append(prop["property"])
                    counter += 1

        # Create full-text index
        logger.info("Creating full-text index ...")
        F_INDEX_NAME = config.f_index_name
        
        create_fulltext_index(
            driver = driver,
            name = F_INDEX_NAME,
            label = "Searchable",
            node_properties = props_list,
            fail_if_exists = True,
            neo4j_database = DB_NAME
        )

    # Create vector index
    logger.info("Creating vector index ...")
    V_INDEX_NAME = config.v_index_name
    
    create_vector_index(
        driver = driver,
        name = V_INDEX_NAME,
        label = "Searchable",
        embedding_property = "NodeEmbedding",
        dimensions = dimension,
        similarity_fn = similarity_fn,
        fail_if_exists = True,
        neo4j_database = DB_NAME
    )

    # Generate embeddings for all nodes (if not already present)
    logger.info("Generating embeddings for all nodes ...")
    #log = []
    node_ids = []
    node_vectors = []
    with driver.session() as session:
        result = session.run("MATCH (n:Searchable) RETURN elementId(n) AS nid, n")
        for record in result:
            nid = record["nid"]
            node = record["n"]
            node_dict = dict(node)
            # Exclude "Searchable" from labels
            node_labels = node.labels - {"Searchable"}
            label_text = f"label: {', '.join(node_labels)}" if node_labels else ""

            # Key-value pairs for all string properties
            kv_texts = [f"{k}: {v}" for k, v in node_dict.items() if isinstance(v, (str, int, float, bool))]
            
            # Combine into a single blob
            text_values = [label_text] + kv_texts if label_text else kv_texts
            text_blob = " ; ".join(text_values)

            if text_blob.strip():
                vector = embedder.embed_query(text_blob)
                node_ids.append(nid)
                node_vectors.append(vector)
                #log.append(text_blob)

    # Upsert embeddings into vector index
    logger.info("Upserting embeddings into the vector index ...")
    upsert_vectors(
        driver = driver,
        ids = node_ids,
        embedding_property = "NodeEmbedding",
        embeddings = node_vectors,
        entity_type = 'NODE',
        neo4j_database = DB_NAME
    )
    
    logger.info("Indexing completed!")



