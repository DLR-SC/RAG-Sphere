from typing import (
    Tuple,
    Optional
)

from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from configparser import ConfigParser
from uuid import uuid4
from tqdm import tqdm

from utils.arango_client import ArangoDBClient

from protocols.indexer import (
    BaseIndexerConfig
)


def generate_community_indices(
        config: Optional[BaseIndexerConfig],
        config_parser : ConfigParser, 
        community_graph : ArangoDBClient, 
        elastic_tuple : Tuple[Elasticsearch, SentenceTransformer, str]
) -> None:
    """
    Generate an elasticsearch embedding for all communities in the community graph
    """
    # Setup elastic enviromnent
    elastic_client, transformer, index_name = elastic_tuple
    elastic_client.options(ignore_status = [400,404]).indices.delete(index = index_name)
    elastic_mappings = {
        "properties": {
            "content_vector": {
                "type": "dense_vector",
                "dims": 384,
                "index": "true",
                "similarity": "l2_norm"
            },
            "content": {"type": "text"},
            "source_ref": {"type": "text"},
            "source": {"type": "text"},
            "document": {"type": "text"}
        }
    }
    elastic_client.indices.create(index = index_name, mappings = elastic_mappings)

    # Fetch all communities in the community graph
    communities = list(community_graph.get_aql(f"FOR v IN CommunityNode FILTER v.is_copy == false && v.is_leaf == false RETURN v"))
    # Embed all community contents into vectors
    embeddings = transformer.encode([community['content'] for community in communities], show_progress_bar = True)
    # Add each community with its information and content vector into elasticsearch
    for community, content_vector in tqdm(list(zip(communities, embeddings)), desc="Indexing communities"):
        embedded =  {
            "content_vector": content_vector,
            "content": community["content"],
            "source_ref": community["source_ref"].__repr__(),
            "source": community["source"].__repr__(),
            "document": community["document"].__repr__()
        }

        elastic_client.index(index = index_name, id = uuid4(), document = embedded)
        