from typing import (
    Dict,
    List
)

from concurrent.futures import ThreadPoolExecutor
from re import findall, finditer, search, sub
from configparser import ConfigParser
from threading import Lock
from traceback import format_exc
from tqdm import tqdm

from utils.llm_client import LLMClient
from graphrag.prompts import convert_to_graph
from utils.arango_client import ArangoDBClient
from graphrag.index.KG_convert_to_relations import _try_get_relations

from protocols.indexer import (
    BaseIndexerConfig
)

_LOCK = Lock()


def _update_source_dict(origin : Dict, source : Dict) -> Dict:
    """
    Adds the values and keys accumulately to the content of the origin dict.

    Parameters:
    - origin (dict): The dict containing the original values
    - source (dict): The dict whose contents are to be added

    Returns:
    The combined dictionary
    """
    for source, count in source.items():
        origin[source] = origin.get(source, 0) + count
    
    return origin

def _insert_relations(relations : List[Dict], source_ref : Dict, source: Dict, document : Dict, arango_client : ArangoDBClient):
    """
    Inserts a relation into the knowledge graph, creating nodes and edges in the process. Nodes are also linked to their source documents.

    Parameters:
    - relations ([dict]): A list of dictionaries containing "From", "To" and "Relation" entries
    - source_ref (dict): The reference to the node constructing this relation
    - source (dict): The direct source descriptor of the node constructing this relation
    - document (dict): The name of the files constructing this relation
    - arango_client (ArangoDBClient): The ArangoDBClient to insert the relation into 
    """
    for relation in relations:
        # If relation is not dict, skip
        if not type(relation) == dict: continue
        # If a value is missing, skip this relation
        if not "From" in relation or not "To" in relation or not "Relation" in relation: continue

        # Clean relation strings
        relation["From"] = sub(r'[^A-Za-z0-9_\-.@()+=;$!*%:,}{\]["]+', '', relation["From"].replace(" ", "_"))
        relation["To"] = sub(r'[^A-Za-z0-9_\-.@()+=;$!*%:,}{\]["]+', '', relation["To"].replace(" ", "_"))
        relation["Relation"] = sub(r'[^A-Za-z0-9_\-.@()+=;$!*%:,}{\]["]+', '', relation["Relation"].replace(" ", "_"))
        if not relation["From"] or not relation["To"] or not relation["Relation"]: continue

        # If relation is self referenzing, skip this relation
        if relation["From"] == relation["To"]: continue
        
        try:
            with _LOCK:
                # Get from node
                from_node = (list(arango_client.get_aql("FOR v IN Node FILTER v._key == '{}' LIMIT 1 RETURN v".format(relation['From']))) or [None])[0]
                if from_node == None:
                    # Add a new from node with the source values of the parent node provided
                    fields = {
                        "_key": relation["From"],
                        "label": relation["From"].replace("_", " "),
                        "source_ref": source_ref,
                        "source": source,
                        "document": document
                    }
                    from_node = arango_client.add_vertex("Node", fields)
                else:
                    # Accumulate the source values of the known node to those of the parent node
                    fields = {
                        "_key": from_node["_key"],
                        "source": _update_source_dict(from_node["source"], source),
                        "source_ref": _update_source_dict(from_node["source_ref"], source_ref),
                        "document": _update_source_dict(from_node["document"], document),
                    }
                    arango_client.update_vertex("Node", fields)

                # Get to node
                to_node = (list(arango_client.get_aql("FOR v IN Node FILTER v._key == '{}' LIMIT 1 RETURN v".format(relation['To']))) or [None])[0]
                if to_node == None:
                    # Add a new to node with the source values of the parent node provided
                    fields = {
                        "_key": relation["To"],
                        "label": relation["To"].replace("_", " "),
                        "source_ref": source_ref,
                        "source": source,
                        "document": document
                    }
                    to_node = arango_client.add_vertex("Node", fields)
                else:
                    # Accumulate the source values of the known node to those of the parent node
                    fields = {
                        "_key": to_node["_key"],
                        "source": _update_source_dict(to_node["source"], source),
                        "source_ref": _update_source_dict(to_node["source_ref"], source_ref),
                        "document": _update_source_dict(to_node["document"], document),
                    }
                    arango_client.update_vertex("Node", fields)
                
                # Get edge
                edge = list(arango_client.get_aql("FOR e IN Relation FILTER e._from == '{}' && e._to == '{}' && e.label == '{}' LIMIT 1 RETURN e"\
                    .format(from_node['_id'], to_node['_id'], relation['Relation'])))
                if not edge:
                    # Add new edge
                    arango_client.add_edge("Relation", {
                        "_from": from_node["_id"], 
                        "_to": to_node["_id"], 
                        "label": relation["Relation"],
                        "weight": 1
                    })
                else:
                    # Increase weight of edge node
                    arango_client.update_edge("Relation", {
                        "_key": edge[0]["_key"],
                        "weight": edge[0]["weight"] + 1
                    })
        except:
            print(relation)
            print(format_exc())

def generate_knowledge_graph(
        config: BaseIndexerConfig, 
        config_parser : ConfigParser, 
        ner_model: LLMClient,
        arango_client : ArangoDBClient
) -> None:
    """
    Generates a knowledge graph using the File nodes present in the arango_client as resources

    Parameters:
    config (ConfigParser): The config file containing the setting for the converter
    arango_client (ArangoDBClient): The arango_client used to generate the knowledge graph into.
    """
    # Read config values
    config=config
    parallel_limit = int(config_parser.get("general", "parallel_limit").strip()) #in dataclass config
    ner_re_llm = ner_model
    answer_format = convert_to_graph.ANSWER_FORMAT
    
    # Setup arangodb enviromnent
    arango_client.get_vertex_collection("Node")
    arango_client.create_edge_collection("Relation", ["Node"], ["Node"])

    files = list(arango_client.get_aql("FOR v IN File RETURN v"))

    # Convert each files content into a list of relations
    with tqdm(total = len(files), desc = "NER_RE_LLM interpretation") as pbar:
        with ThreadPoolExecutor(max_workers = parallel_limit) as executor:
            for file in files:
                # Check if file was already parsed to knowledge graph
                if file.get("is_graph", False): 
                    pbar.update()
                    pbar.refresh()
                    continue

                def generate_ner_results(content, file_key, source, document):
                    """
                    Private method used to parse the content string into relations and insert them into ArangoDB
                    """
                    # Try 8 times to create valid relations from a llm prompt
                    for _ in range(8):
                        # Get the prompt result
                        llm_result = ner_re_llm.generate(prompt=convert_to_graph.USER_PROMPT.format(information = content),
                                                         system=convert_to_graph.SYSTEM_PROMPT,
                                                         format=convert_to_graph.ANSWER_FORMAT)

                        # Try to convert them into lists of relations
                        relations = _try_get_relations(llm_result)
                        # Retry on fail
                        if relations == None: continue
                        # Retry on wrong relations content
                        if type(relations) == list and any(relations) and type(relations[0]) == dict: break
                    else:
                        # Could not generate valid response in 8 tries. Skip this content entirely
                        with _LOCK:
                            arango_client.update_vertex("File", {"_key": file_key, "is_graph": True})
                        return

                    # Insert the relations into the ArangoDB Graph
                    _insert_relations(relations, {file_key: 1, "_total": 1}, source, document, arango_client)

                    # Add parsed flag to file
                    with _LOCK:
                        arango_client.update_vertex("File", {"_key": file_key, "is_graph": True})

                # Generate and add relations to graph. Then advance the Progressbar
                executor.submit(lambda args: (generate_ner_results(*args), pbar.update(), pbar.refresh()), [file["content"], file["_key"], file["source"], file["document"]])