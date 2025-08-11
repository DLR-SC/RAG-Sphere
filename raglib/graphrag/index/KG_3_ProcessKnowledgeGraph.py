from typing import (
    Optional
)

from configparser import ConfigParser
from tqdm import tqdm

from utils.arango_client import ArangoDBClient

from protocols.indexer import (
    BaseIndexerConfig
)

def process_knowledge_graph(
        config: Optional[BaseIndexerConfig],
        config_parser : Optional[ConfigParser],
        arango_client : ArangoDBClient
) -> None:
    """
    Adds edges from Knowledge graph nodes to their source files. Also scales the weights of the nodes inverse to the node count per file

    Parameters:
    - arango_client (ArangoDBClient): The ArangoDBClient containing the knowledge graph and file nodes
    """
    # Create collection for edges between nodes and files
    arango_client.create_edge_collection("mentionedIn", ["Node"], ["File"]).truncate()

    # Dictionary to count the source references per source
    source_refs = dict()

    # Get all nodes in the knowledge graph
    nodes = list(arango_client.get_aql("FOR v IN Node RETURN v"))
    for node in tqdm(nodes, desc = "Connecting nodes to sources"):
        # Get all connected vertices up to 3 edges away
        connected_vertices = set(arango_client.get_aql(f"FOR v IN 1..3 ANY '{node['_id']}' GRAPH {arango_client.graph_name} \
            OPTIONS {{ uniqueVertices: \"path\" }} RETURN v._key"))

        for source, count in node["source_ref"].items():
            # If source is total counter, continue
            if source == "_total": continue

            # Accumulate the occurences of the given source to the global count
            source_refs[source] = source_refs.get(source, 0) + count

            # If source is connected (up to 3 edges) to node, continue with next
            if source in connected_vertices: continue

            # Else connect the node to file directly
            fields = {
                "_from": node["_id"],
                "_to": "File/" + source,
                "weight": count,
                "label": "is mentioned in"
            }
            arango_client.add_edge("mentionedIn", fields)

    # Calculate a singular weight weight for every source
    for source, count in tqdm(source_refs.items(), desc = "Calculate source reference weight modifiers"):
        source_refs[source] = 1 / count
    
    # Adjust the weights of each nodes
    for node in tqdm(nodes, desc = "Assigning node weights"):
        weight = 0
        # Accumulate the weights provided by all source references
        for source, count in node["source_ref"].items():
            if source == "_total": continue
            
            weight += source_refs[source] * count
        
        # Update the weight in ArangoDB
        fields = {
            "_key": node["_key"],
            "weight": weight
        }
        arango_client.update_vertex("Node", fields)