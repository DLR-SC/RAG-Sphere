from typing import (
    Optional,
    Tuple
)

from concurrent.futures import ThreadPoolExecutor, wait
from configparser import ConfigParser
from collections import deque
from random import choices
from tqdm import tqdm

from utils.llm_client import LLMClient
from graphrag.prompts import create_community_summary
from utils.arango_client import ArangoDBClient

from protocols.indexer import (
    BaseIndexerConfig
)


def summarize_communities(
        config: Optional[BaseIndexerConfig],
        config_parser : ConfigParser,
        llm_client: LLMClient,
        community_graph : ArangoDBClient,
) -> None:
    """
    Summarizes the content of a community into a single description for every community in the community graph

    Parameters:
    config (ConfigParser): The config file containing the setting for the summarizer
    community_graph (ArangoDBClient): The ArangoDBClient holding the complete community graph
    """
    # Read llm service specifications
    parallel_limit = int(i) if (i := config_parser.get("general", "parallel_limit").strip()) != "" else 0

    # community summarizer llm 
    llm_client = llm_client

    # Limit the number of chars of the content provided to the summarizer to approx. fit into a 4096 token context
    max_char_count = 4096 * (3.5) - len(create_community_summary.SYSTEM_PROMPT)

    # Get the most general community of the community graph
    graph_vertex = community_graph.get_aql(f"FOR v IN CommunityNode FILTER v.community_key == '00000/00000' LIMIT 1 RETURN v").__next__()
    # Get all communities connected to the general graph_vertex node
    vertices = list(community_graph.get_aql(f"FOR v IN 0..999999999 OUTBOUND '{graph_vertex['_id']}' GRAPH 'community_graph' RETURN v"))

    # Seperate all communities by community degree
    communities = {}
    for vertex in vertices:
        communities.setdefault(vertex["community_degree"], []).append(vertex)
    
    def get_content(vertex : dict) -> Tuple[int, str]:
        """
        Private function to generate a simple description of the provided vertex

        Parameters:
        - vertex (dict): The vertex to get the description of

        Returns: A tuple of the length of the description and the descripton itself
        """
        desc = f"{vertex['label']}: {vertex['content']}\n"
        return (len(desc), desc) 

    # Summarize all vertecies and safe their summaries
    with tqdm(total = len(vertices), desc="Summarizing communities") as pbar:
        with ThreadPoolExecutor(max_workers = 1) as executor:
            def sum_vertex(vertex : dict):
                """
                A private function to generate a summary for a single vertex

                Parameters:
                - vertex (dict): The vertex to generate a summary for
                """
                # Vertex already has a summary. Skip it
                if vertex['content'] != '_':
                    return
                
                # Get all subcommunities of the current vertex
                sub_vertices = list(community_graph.get_aql(f"FOR v IN OUTBOUND '{vertex['_id']}' GRAPH 'community_graph' RETURN v"))

                # Vertex only has one child, so content can just be copied
                if len(sub_vertices) == 1:
                    fields = {
                        "_key" : vertex["_key"],
                        "label" : sub_vertices[0]["label"],
                        "content" : sub_vertices[0]["content"],
                        "is_leaf" : sub_vertices[0]["is_leaf"],
                        "weight" : sub_vertices[0]["weight"],
                        "is_copy" : False
                    }
                    community_graph.update_vertex("CommunityNode", fields)

                    # Changes child node to be a copy of parent
                    fields = {
                        "_key" : sub_vertices[0]["_key"],
                        "is_copy" : True
                    }
                    community_graph.update_vertex("CommunityNode", fields)
                    return

                # Fetch the contents of the child vertices
                nodes = [(*get_content(v), v["weight"], v["_id"], v["is_leaf"]) for v in sub_vertices]
                weights = [node[2] for node in nodes]

                # Calculate the current length of the contents
                current_len = sum(node[0] for node in nodes)

                # A string, where the final contents will be collected
                summary = ""
                # A value to store the total weight of all contents used
                total_weight = 0

                if current_len >= max_char_count:
                    # If the current_len is already too much, add as many nodes, as possible
                    current_len = 0
                    while any(weights):
                        node_id = choices(list(range(len(nodes))), weights)[0]
                        weights[node_id] = 0

                        if current_len + nodes[node_id][0] >= max_char_count:
                            continue

                        summary += nodes[node_id][1]
                        current_len += nodes[node_id][0]
                        total_weight += nodes[node_id][2]
                else:
                    while any(weights):
                        node_id = choices(list(range(len(nodes))), weights)[0]

                        weights[node_id] = 0

                        if nodes[node_id][4]:
                            # If the vertex is a leaf, it can not be splitted further and will be added to the summary
                            summary += nodes[node_id][1]
                            total_weight += nodes[node_id][2]
                        else:
                            # Find all child vertices of the current vertex
                            sub_vertices = list(community_graph.get_aql(f"FOR v IN OUTBOUND '{nodes[node_id][3]}' GRAPH 'community_graph' RETURN v"))
                            # Generate their content strings
                            sub_nodes = [(*get_content(v), v["weight"], v["_id"], v["is_leaf"]) for v in sub_vertices]
                            # And count their total length
                            node_len = sum(node[0] for node in sub_nodes)

                            if current_len - nodes[node_id][0] + node_len < max_char_count:
                                # If adding them to the summary instead of the content of the current vertex is possible
                                # Add all sub_vertex contents to the node list
                                nodes.extend(sub_nodes)
                                weights.extend(node[2] for node in sub_nodes)

                                # And change the current length to reflect that change
                                current_len = current_len - nodes[node_id][0] + node_len
                            else:
                                # If adding the child vertices is not possible, the current one must be added to the final summary string
                                summary += nodes[node_id][1]
                                total_weight += nodes[node_id][2]

                # Generate a LLM response, as long as it is not in the right format
                while True:
                    # Generate a response
                    ai_summary = llm_client.generate(prompt=create_community_summary.USER_PROMPT.format(information = summary),
                                                     system=create_community_summary.SYSTEM_PROMPT,
                                                     format=create_community_summary.ANSWER_FORMAT)
                    try:
                        ai_summary = eval(ai_summary)
                    # Try to read the data anyway
                    except:
                        if not "\"description\":" in ai_summary: continue
                        ai_summary = ai_summary.split("\"description\":", maxsplit = 1)
                        if "}" in ai_summary[0] or "{" in ai_summary[1]: continue

                        if not "\"label\":" in ai_summary[0]: continue
                        label = ai_summary[0].split("\"label\":", maxsplit = 1)[1].strip(" ,\"'\n")
                        description = ai_summary[1].strip(" \"'}\n")

                        ai_summary = {
                            "label": label,
                            "description": description
                        }

                        break
                
                    if not "label" in ai_summary or not "description" in ai_summary: continue
                    if len(ai_summary["label"]) < 5 or len(ai_summary["description"]) < 20: continue
                    break


                # Update the vertex
                fields = {
                    "_key" : vertex["_key"],
                    "label" : ai_summary["label"].strip(),
                    "content" : ai_summary["description"].strip(),
                    "weight": total_weight,
                    "is_copy": False
                }
                community_graph.update_vertex("CommunityNode", fields)

            # Generate a summary for all communities, starting by the lowest level communities
            for community_degree in sorted(list(communities.keys()), reverse = True):
                futures = list()
                for vertex in communities[community_degree]:
                    futures.append(executor.submit(lambda args: (sum_vertex(*args), pbar.update(), pbar.refresh()), [vertex]))

                wait(futures)
