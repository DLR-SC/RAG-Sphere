from typing import (
    Tuple,
    Set,
    Dict,
    List,
    Any,
    Optional,
    Union
)
import logging
logger = logging.getLogger(__name__)

from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor
from elasticsearch import Elasticsearch
from configparser import ConfigParser
from threading import Lock
from random import shuffle
from tqdm import tqdm
from traceback import format_exc

from utils.arango_client import ArangoDBClient
from utils.llm_client import LLMClient
from graphrag.prompts import generate_community_answer

from models.enums import (
    RetrieverType,
    DatabaseType
)

from protocols.retriever import (
    BaseRetriever,
    BaseRetrieverConfig
)

class GenerationAPI:
    """
    A class that can be used to easily execute various RAG implementations on the data created before
    """
    def __init__(
            self,
            config: Optional[BaseRetrieverConfig] = None,
            config_parser: ConfigParser = None,
            documents: Optional[str] = None, 
            graph_db: Optional[Union[DatabaseType, ArangoDBClient]] = None, 
            vector_db: Optional[Union[DatabaseType, Elasticsearch]] = None, 
            llm: Optional[LLMClient] = None, 
            emb_model: Optional[SentenceTransformer] = None
    ) -> None:
        """
        Initializes the generation API and open config file.
        """
        self.config = config
        self.config_parser = config_parser

        self.llm = llm
        self.system_prompt = generate_community_answer.SYSTEM_PROMPT
        self.answer_format = generate_community_answer.ANSWER_FORMAT
        self.transformer = emb_model

        self.arango = None
        self.elastic_client = None

        parallel_limit = int(i) if (i := self.config_parser.get("general", "parallel_limit").strip()) != "" else 1
        self.threadPool = ThreadPoolExecutor(parallel_limit)
        self.lock = Lock()

    def init_arango(self):
        """
        Initializes the ArangoDB client.
        """
        if self.arango: 
            return

        logger.info("Initializing ArangoDB connection...")

        # Read all important config settings
        summary_db_name = "SC_Pub"

        # Start ArangoDB Client
        self.arango = ArangoDBClient(config=self.config_parser, 
                                     db_name=summary_db_name, 
                                     graph_name="None", 
                                     client_name="Summary DB")

    def init_elastic(self):
        """
        Initializes the elastic search model.
        """
        if self.elastic_client: return

        logger.info("Initializing Elastic engine...")

        # Read all important config settings
        elastic_url = self.config_parser.get("elastic", "url")

        # Start elastic client and transformer model
        self.RAG_index_name = "sc_pub_rag"
        self.GARAG_index_name = "sc_pub_garag"
        self.elastic_client = Elasticsearch(elastic_url)

        # Test elastic connection
        self.test_elastic_connection(self.elastic_client)
    
    @staticmethod
    def test_elastic_connection(elastic_client: Elasticsearch):
        """
        This method will test the health of the provided Elasticsearch client.

        Paramerters:
        - elastic_client (Elasticsearch): The client to test
        """
        # Retry 5 times, before exiting with the error
        for i in range(5):
            try:
                # Check health status
                elastic_client.options(request_timeout=30, retry_on_status=[104]).cluster.health()
                break
            except Exception as e:
                if i < 4: 
                    continue
                logger.error(f"! Elasticsearch Connection unavailable! Please check the parameters in the config file and Elasticsearch server status!\n{format_exc()}")
                
    def generate_graph_rag_answer(
            self, 
            prompt : str, 
            max_matches : int,
            community_degree : int = 1, 
            confidence_cutoff: int = 40,
            api_key : Optional[str] = None, 
            show_progress : Optional[bool] = False
    ) -> List[Dict]:
        """
        Searches for relevant information to the user prompt by letting llms extract the relevant parts from the community summaries

        Parameters:
        prompt (str): The user prompt to search information about
        max_matches (int): The maximum number of matching information to return
        /
        community_degree (int) = 1: The depth to search for in the communitygraph. Increasing this setting will lead to a significantly longer runtime
        api_key (str) = None: The api_key (if needed) to perform the llm requests. You might provide a static API Key in the configfile instead
        show_progress (bool) = False: Whether to show a progressbar for longer processes

        Returns: A list of dictionaries, containing "content", "source" and "document" information 
        """
        # Start required services
        self.init_arango()

        # Fetch all communities up to (including) the specified degree
        communities = []
        for degree in range(community_degree + 1):
            communities.extend(self.arango.get_aql(f"FOR v IN CommunityNode FILTER v.community_degree == {degree} && v.is_copy == false && v.is_leaf == false RETURN v"))

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

        # Add a progressbar, is show_progress is True
        pbar = tqdm(total = len(informations), desc="Generating llm information") if show_progress else None

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
            while True:
                # Generate an ai info response
                ai_info = self.llm.generate(prompt=generate_community_answer.USER_PROMPT.format(information = information, prompt = prompt),
                                            system=self.system_prompt,
                                            format=self.answer_format)
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

            # Return the extracted information
            return (ai_info["confidence"], ai_info["information"].strip(), source, document)
        
        # Generator a information generator for each information block in informations
        futures = []
        for information, source, document in informations:
            # Show progress is enabled -> add a field to update the progressbar
            if show_progress:
                futures.append(self.threadPool.submit(lambda args: (generate_community_information(*args), pbar.update())[0], [information, source, document]))
            # Show progress is disables -> generate information silently
            else:
                futures.append(self.threadPool.submit(generate_community_information, information, source, document))
        
        # Wait for all information to be collected
        informations = [future.result() for future in futures]
        # Close the Progressbar if it was drawn before
        if show_progress: pbar.close()

        # Counters and collectors for the final result
        result_count = 0
        results = []

        # Add all information until not important enough or limit is reached
        for confidence, information, source, document in sorted(informations, key = lambda i: i[0], reverse = True):
            # The provided information will be more confusing than helpful. Break the loop
            if confidence < confidence_cutoff: break
            # Information is added to the list of results
            if not result_count or result_count < max_matches:
                results.append({
                    "content": information,
                    "source": list(source),
                    "document": list(document)
                })
                if result_count: result_count += 1
            
        return results

    def generate_graph_rag_rag_answer(
            self, 
            prompt : str, 
            max_matches : int,
            confidence_cutoff: float = 0.04
    ) -> List[Dict]:
        """
        Searches for relevant information to the user prompt by comparing its embedding to those of the generated community summaries

        Parameters:
        prompt (str): The user prompt to search information about
        max_matches (int): The maximum number of matching information to return

        Returns: A list of dictionaries, containing "content", "source" and "document" information 
        """
        # Start required services
        self.init_elastic()
        # Set the number of max matches to 1024 if 0 was provided
        max_matches = max_matches or 1024

        # Build the query to use for NearestNeighbor search
        query = {
            "field": "content_vector",
            "query_vector": self.transformer.encode(prompt),
            "k": max_matches,
            "num_candidates": max(64, 1.5 * max_matches)
        }

        # Fetch matching communities from elastic db
        communities = self.elastic_client.search(index = self.GARAG_index_name, knn = query, source = ["content", "source", "document"])
        
        # Add all information until not important enough
        results = []
        for community in sorted(communities["hits"]["hits"], key = lambda c: c["_score"], reverse = True):
            # The provided information will be more confusing than helpful. Break the loop
            if community["_score"] < confidence_cutoff: break
            # Information is added to the list of results
            results.append({
                "content": community["_source"]["content"],
                "source": list(eval(community["_source"]["source"]).keys()),
                "document": list(eval(community["_source"]["document"]).keys())
            })
        
        return results

    def generate_rag_answer(
        self, 
        prompt : str, 
        max_matches : int,
        confidence_cutoff: float = 0.04
    ) -> List[Dict]:
        """
        Searches for relevant information to the user prompt by comparing its embedding to those of the original document contents

        Parameters:
        prompt (str): The user prompt to search information about
        max_matches (int): The maximum number of matching information to return

        Returns: A list of dictionaries, containing "content", "source" and "document" information 
        """
        # Start required services
        self.init_elastic()
        # Set the number of max matches to 1024 if 0 was provided
        max_matches = max_matches or 1024

        # Build the query to use for NearestNeighbor search
        query = {
            "field": "content_vector",
            "query_vector": self.transformer.encode(prompt),
            "k": max_matches,
            "num_candidates": max(64, 1.5 * max_matches)
        }

        # Fetch matching communities from elastic db
        communities = self.elastic_client.search(index = self.RAG_index_name, knn = query, source = ["content", "source", "document"])
        
        results = []
        for community in sorted(communities["hits"]["hits"], key = lambda c: c["_score"], reverse = True):
            # The provided information will be more confusing than helpful. Break the loop
            if community["_score"] < confidence_cutoff: break
            # Information is added to the list of results
            results.append({
                "content": community["_source"]["content"],
                "source": list(eval(community["_source"]["source"]).keys()),
                "document": list(eval(community["_source"]["document"]).keys())
            })
        
        return results
    
    def generate_garag_answer(
        self, prompt : str, 
        max_matches : int,
        confidence_cutoff: float = 0.04
    ) -> List[Dict]:
        """
        Searches for relevant information to the user prompt by comparing its embedding to those of the generated community summaries. 
        Then returns the original document contents those summaries are made out of
        Searches for relevant information to the user prompt by comparing its embedding to those of the original document contents

        Parameters:
        prompt (str): The user prompt to search information about
        max_matches (int): The maximum number of matching information to return

        Returns: A list of dictionaries, containing "content", "source" and "document" information 
        """
        # Start required services
        self.init_elastic()
        self.init_arango()

        # Set the number of max matches to 1024 if 0 was provided
        max_matches = max_matches or 1024

        # Build the query to use for NearestNeighbor search (double the max matches, as their sources are then used which might be less)
        query = {
            "field": "content_vector",
            "query_vector": self.transformer.encode(prompt),
            "k": max_matches * 2,
            "num_candidates": max(128, 3 * max_matches)
        }

        # Fetch communities with matching content
        valid_communities = self.elastic_client.search(index = self.GARAG_index_name, knn = query, source = ["source_ref"])

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
            file_node = self.arango.get_aql(f"FOR v IN File FILTER v._key == '{source_ref}' LIMIT 1 RETURN v").__next__()

            # Add it to the result array
            results.append({
                "content": file_node["content"],
                "source": list(file_node["source"].keys()),
                "document": list(file_node["document"].keys())
            })
            max_matches -= 1
            if max_matches == 0: break
        
        return results
