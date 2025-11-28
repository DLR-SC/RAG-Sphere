from typing import (
    Optional,
    List,
    Tuple,
    Set
)
from utils.arango_client import ArangoDBClient
from utils.llm_client import LLMClient
from eri_components.components import RetrievalAnswer, AllowedTypes
from graphrag.prompts import generate_community_answer
from concurrent.futures import ThreadPoolExecutor
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from random import shuffle

def _graph_rag_retrieve(
    prompt: str,
    graph_db: ArangoDBClient,
    llm: LLMClient,
    max_matches: Optional[int] = 10,
    community_degree: Optional[int] = 1,
    confidence_cutoff: Optional[int] = 40,
    parallel_limit: Optional[int] = 1
) -> List[RetrievalAnswer]:
    # Set optional parameters
    max_matches = 10 if max_matches is None else max(1, max_matches)
    community_degree = 1 if community_degree is None else max(0, community_degree)
    confidence_cutoff = 40 if confidence_cutoff is None else max(0, min(100, confidence_cutoff))
    parallel_limit = 1 if parallel_limit is None else max(1, parallel_limit)

    # Fetch all communities up to (including) the specified degree
    communities = []
    for degree in range(community_degree + 1):
        communities.extend(graph_db.get_aql(f"FOR v IN CommunityNode FILTER v.community_degree == {degree} && v.is_copy == false && v.is_leaf == false RETURN v"))

    # Shuffle the communities in a random order. This leads to no preference of communities over another
    shuffle(communities)

    # A field to store the informations representing the entire community corpus, split into managable size
    informations = []

    # Adds source trackers for each information block
    current_source = set()
    current_document = set()
    current_len = 0
    current_information = ""

    # Stitch the communities together in random order, checking to not overflow the contextsize
    while communities:
        # Get next community from stack
        community = communities.pop()

        # Calculate length of information if it would be joined to prior text
        current_len += len(community["content"]) + 1
        # Information would be too long, split it right here
        if current_len >= 4096:
            # Add prior information as finished element
            informations.append((current_information, current_source, current_document))
            # Reset source and information to only contain next community
            current_source = set(community["source"].keys())
            current_document = set(community["document"].keys())
            current_len = len(community["content"])
            current_information = community["content"]
        # Append the community to prior information
        else:
            current_source |= set(community["source"].keys())
            current_document |= set(community["document"].keys())
            current_information += "\n" + community["content"]

    # Append the last information block
    informations.append((current_information, current_source, current_document))

    def generate_community_information(information, source, document) -> Tuple[int, str, Set[str], Set[str]]:
        """
        A private function to extract information from a given information block

        Parameters:
        - information (str): The information of multiple communities appended together
        - source (set(str)): A set of the source names of the community information
        - document (set(str)): A set of the document names of the community information

        Returns: A tuple of the generated confidence score, the extracted information and the source and document references
        """
        # Try and extract a valid prompt from the llm
        for _ in range(10):
            # Generate an ai info response
            ai_info = llm.generate(prompt=generate_community_answer.USER_PROMPT.format(information = information, prompt = prompt),
                                        system=generate_community_answer.SYSTEM_PROMPT,
                                        format=generate_community_answer.ANSWER_FORMAT)
            # Strip the response to the json object bounds 
            ai_info = ai_info[ai_info.find("{") : ai_info.rfind("}") + 1]

            # Try to extract the json object a python object
            try: ai_info = eval(ai_info)
            # Retry on failure
            except: continue

            # Check for the object to be a dictionary
            if type(ai_info) != dict: continue
            # Check for the needed keys in the dictionary
            if not "confidence" in ai_info or not "information" in ai_info: continue
            # Check for the needed types in the dictionary
            if not type(ai_info["information"]) == str: continue
            if not type(ai_info["confidence"]) == int: continue
            # Response is valid
            break
        else:
            # Request failed 10 times, skip this request
            return (0, "", {}, {})

        # Return the extracted information
        return (ai_info["confidence"], ai_info["information"].strip(), source, document)

    # Generator a information generator for each information block in informations
    futures = []
    threadPool = ThreadPoolExecutor(parallel_limit)
    for information, source, document in informations:
        futures.append(threadPool.submit(generate_community_information, information, source, document))

    # Wait for all information to be collected
    informations = [future.result() for future in futures]

    # Collectors for the final result
    results = []

    # Add all information until not important enough or limit is reached
    for confidence, information, source, document in sorted(informations, key = lambda i: i[0], reverse = True):
        # The provided information will be more confusing than helpful. Break the loop
        if confidence < confidence_cutoff: break
        # Information is added to the list of results
        if len(results) < max_matches:
            results.append(RetrievalAnswer(**{
                "name": list(source).__repr__(),
                "category": "extracted data from multiple different files (sources)",
                "path": list(document).__repr__(),
                "type": AllowedTypes.TEXT,
                "matchedContent":  information,
                "surroundingContent": [],
                "links": []
            }))

    if len(results) == 0:
        return [RetrievalAnswer(**{
            "name": "NO DOCUMENTS FOUND",
            "category": "extracted data from multiple different files (sources)",
            "path": "",
            "type": AllowedTypes.NONE,
            "matchedContent":  "",
            "surroundingContent": [],
            "links": []
        })]
    else:
        return results

def _naive_graph_rag_retrieve(
    prompt: str,
    vector_db: Elasticsearch,
    vector_db_index_name : str,
    emb_model : SentenceTransformer,
    max_matches: Optional[int] = 10,
    confidence_cutoff: Optional[float] = 0.04
) -> List[RetrievalAnswer]:
    # Set optional parameters
    max_matches = 10 if max_matches is None else max(1, max_matches)
    confidence_cutoff = 0.04 if confidence_cutoff is None else max(0, min(1, confidence_cutoff))

    # Build the query to use for NearestNeighbor search
    query = {
        "field": "content_vector",
        "query_vector": emb_model.encode(prompt),
        "k": max_matches,
        "num_candidates": max(64, 1.5 * max_matches)
    }

    # Fetch matching communities from elastic db
    communities = vector_db.search(index = vector_db_index_name, knn = query, source = ["content", "source", "document"])
    
    # Add all information until not important enough
    results = []
    for community in sorted(communities["hits"]["hits"], key = lambda c: c["_score"], reverse = True):
        # The provided information will be more confusing than helpful. Break the loop
        if community["_score"] < confidence_cutoff: break
        # Information is added to the list of results
        results.append(RetrievalAnswer(**{
            "name": list(eval(community["_source"]["source"]).keys()).__repr__(),
            "category": "extracted data from multiple different files (sources)",
            "path": list(eval(community["_source"]["document"]).keys()).__repr__(),
            "type": AllowedTypes.TEXT,
            "matchedContent": community["_source"]["content"],
            "surroundingContent": [],
            "links": []
        }))
    
    if len(results) == 0:
        return [RetrievalAnswer(**{
            "name": "NO DOCUMENTS FOUND",
            "category": "extracted data from multiple different files (sources)",
            "path": "",
            "type": AllowedTypes.NONE,
            "matchedContent":  "",
            "surroundingContent": [],
            "links": []
        })]
    else:
        return results

def _garag_retrieve(
    prompt: str,
    graph_db: ArangoDBClient,
    vector_db: Elasticsearch,
    vector_db_index_name : str,
    emb_model : SentenceTransformer,
    max_matches: Optional[int] = 10,
    confidence_cutoff: Optional[float] = 0.04
) -> List[RetrievalAnswer]:
    # Set optional parameters
    max_matches = 10 if max_matches is None else max(1, max_matches)
    confidence_cutoff = 0.04 if confidence_cutoff is None else max(0, min(1, confidence_cutoff))

    # Build the query to use for NearestNeighbor search (double the max matches, as their sources are then used which might be less)
    query = {
        "field": "content_vector",
        "query_vector": emb_model.encode(prompt),
        "k": max_matches * 2,
        "num_candidates": max(128, 3 * max_matches)
    }

    # Fetch communities with matching content
    valid_communities = vector_db.search(index = vector_db_index_name, knn = query, source = ["source_ref"])

    # A storage to accumulate the source references of the matching communities
    source_refs = dict()

    # Add all matching communitie references to the reference dict
    for community in valid_communities["hits"]["hits"]:
        if community["_score"] < confidence_cutoff: continue # confidence_cutoff

        # Get the reference dictionary of the community
        source_ref = eval(community["_source"]["source_ref"])

        # Add the influence of each sourc of the community to the total source storage
        for source, count in source_ref.items():
            if source == "_total": continue
            source_refs[source] = source_refs.get(source, 0) + community["_score"] * count / source_ref["_total"]

    # Add at most max_matches initial document contents to the result using the source reference pointers to them
    results = []
    for source_ref, _ in sorted(source_refs.items(), key = lambda s: s[1], reverse = True):
        # Fetch node described by source reference
        file_node = graph_db.get_aql(f"FOR v IN File FILTER v._key == '{source_ref}' LIMIT 1 RETURN v").__next__()

        # Add it to the result array
        results.append(RetrievalAnswer(**{
            "name": list(file_node["source"].keys()).__repr__(),
            "category": "extracted data from multiple different files (sources)",
            "path": list(file_node["document"].keys()).__repr__(),
            "type": AllowedTypes.TEXT,
            "matchedContent": file_node["content"],
            "surroundingContent": [],
            "links": []
        }))
        max_matches -= 1
        if max_matches == 0: break
    
    if len(results) == 0:
        return [RetrievalAnswer(**{
            "name": "NO DOCUMENTS FOUND",
            "category": "extracted data from multiple different files (sources)",
            "path": "",
            "type": AllowedTypes.NONE,
            "matchedContent":  "",
            "surroundingContent": [],
            "links": []
        })]
    else:
        return results

def _naive_rag_retrieve(
    prompt: str,
    vector_db: Elasticsearch,
    vector_db_index_name : str,
    emb_model : SentenceTransformer,
    max_matches: Optional[int] = 10,
    confidence_cutoff: Optional[float] = 0.04
) -> List[RetrievalAnswer]:
    # Set optional parameters
    max_matches = 10 if max_matches is None else max(1, max_matches)
    confidence_cutoff = 0.04 if confidence_cutoff is None else max(0, min(1, confidence_cutoff))

    # Build the query to use for NearestNeighbor search
    query = {
        "field": "content_vector",
        "query_vector": emb_model.encode(prompt),
        "k": max_matches,
        "num_candidates": max(64, 1.5 * max_matches)
    }

    # Fetch matching communities from elastic db
    communities = vector_db.search(index = vector_db_index_name, knn = query, source = ["content", "source", "document"])

    results = []
    for community in sorted(communities["hits"]["hits"], key = lambda c: c["_score"], reverse = True):
        # The provided information will be more confusing than helpful. Break the loop
        if community["_score"] < confidence_cutoff: break
        # Information is added to the list of results
        results.append(RetrievalAnswer(**{
            "name": list(eval(community["_source"]["source"]).keys()).__repr__(),
            "category": "extracted data from multiple different files (sources)",
            "path": list(eval(community["_source"]["document"]).keys()).__repr__(),
            "type": AllowedTypes.TEXT,
            "matchedContent": community["_source"]["content"],
            "surroundingContent": [],
            "links": []
        }))
    
    if len(results) == 0:
        return [RetrievalAnswer(**{
            "name": "NO DOCUMENTS FOUND",
            "category": "extracted data from multiple different files (sources)",
            "path": "",
            "type": AllowedTypes.NONE,
            "matchedContent":  "",
            "surroundingContent": [],
            "links": []
        })]
    else:
        return results
