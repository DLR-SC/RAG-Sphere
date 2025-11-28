from typing import (
    Optional
)

from configparser import ConfigParser
from tqdm import tqdm

from utils.arango_client import ArangoDBClient
from graphrag.index.G_LeidenAlgorithm import LeidenProcessor

from protocols.indexer import (
    BaseIndexerConfig
)


def build_communities(
        config: Optional[BaseIndexerConfig],
        config_parser : Optional[ConfigParser],
        knowledge_graph : ArangoDBClient, 
        community_graph : ArangoDBClient,
) -> None:
    """
    Uses the leiden algorithm to build communities within the knowledge graph
    """
    # Construct vertex communities
    leiden = LeidenProcessor(knowledge_graph)
    vertex_communities = leiden.get_hierarchical_leiden_communities()

    # Save the vertex community of each node and file into ArangoDB
    for vertex_id, communities in tqdm(vertex_communities.items(), desc="Saving vertex communities"):
        # Add a list of community ids, reflecting the communities on different levels
        fields = {
            "_id" : vertex_id,
            "communities" : communities
        }
        # Add a community field for every communitylevel of the community construct
        for idx, community in enumerate(communities):
            fields["community_{:03}".format(idx + 1)] = community
        knowledge_graph.update_vertex(knowledge_graph.get_type_from_id(vertex_id), fields)

    # Get the graph of the communities
    leiden_community_graph = leiden.get_community_graph()
    # Add a storage to map each community to the arango node
    community_keys = dict()
    # Add a storage to map each node to its connected edges
    node_edges = dict()

    # Save the data for each old community to be reused when identical communities got created
    data_saves = dict()
    try:
        for community in tqdm(list(community_graph.get_aql("FOR v IN CommunityNode RETURN v")), desc="Copying old graph data"):
            if community["content"] == "_": continue
            data_saves[tuple(community["vertices"] + community["edges"])] = {
                "label": community["label"],
                "content": community["content"],
                "source": community["source"],
                "source_ref": community["source_ref"],
                "document": community["document"],
                "is_leaf": community["is_leaf"],
                "is_copy": community["is_copy"],
                "weight": community["weight"],
            }
    except: pass

    # Add indices to the communities for faster lookup
    community_graph.create_new_vertex_collection("CommunityNode")
    community_graph.add_vertex_index("CommunityNode", {'type': 'persistent', 'fields': ['community_key'], 'unique': True})
    community_graph.add_vertex_index("CommunityNode", {'type': 'persistent', 'fields': ['community_degree'], 'unique': False})

    # Loop over every community vertex in the graph and add it to the ArangoDB
    for community, degree, index in tqdm(leiden_community_graph["vertices"], desc="Constructing community nodes"):
        # Generate a unique identifier for the community
        community_key = "{:05}/{:05}".format(degree, index)

        # Add dictionaries to accumulate the various sources of the community
        sources = dict()
        source_refs = dict()
        documents = dict()
        edges = set()

        # Add the source and document references from each node of the community
        for vertex_id in community:
            # Get the ArangoDB node of the vertex
            vertex = knowledge_graph.get_aql(f"FOR v IN {knowledge_graph.get_type_from_id(vertex_id)} FILTER v._id == '{vertex_id}' LIMIT 1 RETURN v").__next__()
            # Accumulate all source tags
            for source, count in vertex['source'].items():
                sources[source] = sources.get(source, 0) + count
            for source_ref, count in vertex['source_ref'].items():
                source_refs[source_ref] = source_refs.get(source_ref, 0) + count
            for document, count in vertex['document'].items():
                documents[document] = documents.get(document, 0) + count

            # Accumulate all connected edges
            if not vertex_id in node_edges:
                node_edges[vertex_id] = set(knowledge_graph.get_aql(f"FOR v,e IN 1..1 ANY '{vertex_id}' GRAPH knowledge_graph RETURN e._id"))
            edges |= node_edges[vertex_id]
        
        # Construct a basic node, filled with the child nodes and source references
        fields = {
            "label" : "_",
            "content" : "_",
            "vertices" : sorted(list(community)),
            "edges": sorted(list(edges)),
            "source" : sources,
            "source_ref" : source_refs,
            "document" : documents,
            "community_degree" : degree,
            "community_index" : index,
            "community_key" : community_key,
            "is_leaf" : False,
            "is_copy" : False,
            "weight" : 0
        }
        community_keys[(community, degree)] = community_graph.add_vertex("CommunityNode", fields)

    # Add an edge collection to connect the communities into an hierarchical structure
    community_graph.create_edge_collection("communityEdge", ["CommunityNode"], ["CommunityNode"]).truncate()

    # Add all edges between the communities
    for (from_vertex, to_vertex), edges in tqdm(leiden_community_graph["edges"].items(), desc="Constructing community edges"):
        for weight, degree in edges:
            # Get the nodes the edge bridges between
            from_node = community_keys[(from_vertex, degree)]
            to_node = community_keys[(to_vertex, degree + 1)]

            # Add an edge to connect the nodes
            fields = {
                "weight" : weight,
                "_from" : from_node['_id'],
                "_to" : to_node['_id']
            }
            community_graph.add_edge("communityEdge", fields)
    
    # Get the most general node of the community graph
    graph_vertex = community_graph.get_aql(f"FOR v IN CommunityNode FILTER v.community_key == '00000/00000' LIMIT 1 RETURN v").__next__()

    # Add a description for each leave node and insert the saved data
    for community in tqdm(list(community_graph.get_aql(f"FOR v IN CommunityNode RETURN v")), desc="Loading node descriptions"):
        # Insert saved data
        if (save := data_saves.get(tuple(community["vertices"] + community["edges"]), None)) != None:
            community_graph.update_vertex("CommunityNode", save | {"_key": community["_key"]})
        # Create new leave descriptions
        elif community["community_degree"] == leiden_community_graph["height"]:
            vertex = community["vertices"][0]
            # Get the knowledge graph node representing this single vertex
            knowledge_node = knowledge_graph.get_aql(f"FOR v IN {knowledge_graph.get_type_from_id(vertex)} FILTER v._id == '{vertex}' LIMIT 1 RETURN v").__next__()

            # Describe the surroundings of the knowledgegraph node as its content
            fields = {
                "_key": community["_key"],
                "label": knowledge_node["label"],
                "content": knowledge_graph.get_node_description(knowledge_node),
                "weight": knowledge_node["weight"],
                "is_leaf": True
            }
            community_graph.update_vertex("CommunityNode", fields)