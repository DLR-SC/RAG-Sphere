from typing import Optional
from arango import ArangoClient
from arango.collection import VertexCollection, EdgeCollection
from arango.exceptions import GraphListError, GraphPropertiesError, ServerStatusError
from configparser import ConfigParser
from getpass import getpass
import logging
logger = logging.getLogger(__name__)

class ArangoDBClient:
    def __init__(self, 
        config : ConfigParser, 
        url : Optional[str] = None, 
        username : Optional[str] = None,
        password : Optional[str] = None,
        db_name : Optional[str] = None, 
        graph_name : Optional[str] = None, 
        client_name : str = "ArangoDBClient"
        ):
        """
        Opens a connection to a Specific arangoDB graph.

        Parameters:
        - config (ConfigParser) : The config parser, containing all necessary information. 
            The following information will be extracted, if not provided explicitly:
            - arangodb/url : The url to the ArangoDB client
            - arangodb/username : The name of the user, used for the connection
            - arangodb/password : The password for the user, used for the connection. If empty, a password will be requested via user input on the console.
            - arangodb/db_name : The name of the ArangoDB database (if not provided as extra value).
            - arangodb/graph_name : The name of the graph in the ArangoDB databse (if not provided as extra value).
        - db_name (str) : The name of the ArangoDB database
        - graph_name (str) : The name of the graph in the ArangoDB database. 'None' literal to not use any graph.
        - client_name (str) : A name for this AranfoDB client. Will be used when asking for user input (default: 'ArangoDBClient').
        """

        # Reads information about the ArangoDB client
        self.client = ArangoClient(hosts = url if url is not None else config.get("arangodb", "url"))

        # Reads information about the graph
        self.db_name = db_name if db_name is not None else config.get("arangodb", "db_name")
        self.graph_name = graph_name if graph_name is not None else config.get("arangodb", "graph_name")

        # Rads information about the user. The password might be requested, if not present in config
        username = username if username is not None else config.get("arangodb", "username")
        password = password if password is not None else pw if (pw := config.get("arangodb", "password")) != "None" else getpass(prompt = f"{client_name} requests ArangoDB password ({username}): ")

        # Connects to the graph on the ArangoDB client    
        self.db = self.client.db(self.db_name, username = username, password = password)
        try:
            self.db.status()
        except ServerStatusError:
            try:
                sys_db = self.client.db('_system', username=username, password=password)
                if sys_db.has_database(self.db_name):
                    raise ValueError(f"Arango user '{username}' has insufficient rights to connect to database '{self.db_name}'!")
                sys_db.create_database(self.db_name)
                logger.info(f"Created new ArangoDB database '{self.db_name}'.")
                self.db = self.client.db(self.db_name, username = username, password = password)
            except:
                raise ValueError(f"Arango user '{username}' can neither connect to nor create database '{self.db_name}'!")

        if self.graph_name != "None":
            self.graph = self.db.graph(self.graph_name)
            try:
                self.graph.properties()
            except GraphPropertiesError:
                try:
                    self.db.create_graph(self.graph_name)
                    self.graph = self.db.graph(self.graph_name)
                    logger.info(f"Created new graph '{self.graph_name}' in ArangoDB database '{self.db_name}'.")
                except GraphListError:
                    raise ValueError(f"Arango user {username} can not connect to graph {self.graph_name} in database {self.db_name}!")
        else:
            self.graph = None

        self.vertex_collections = {}
        self.edge_collections = {}

    def get_aql(self, aql_string : str):
        """
        Runs an AQL query on the current database and returns the result.

        Parameters:
        - aql_string (str) : the query to be run
        
        Returns:
        The result of the aql query.
        """
        return self.db.aql.execute(aql_string)

    def get_type_from_id(self, arangoID : str) -> str:
        """
        Converts the id of a Arango node or edge into its type.

        Parameters:
        - arangoID (str) : The id of the node / edge in the ArangoDB

        Returns:
        The type of the node / edge

        Example:
        'Disease/4805d4bb591216f2ba7a8e8848226792' -> 'Disease'
        """
        return arangoID.split('/', 1)[0]

    def get_node_description(self, node, condition = None) -> str:
        """
        Builds a basic description of each node, using its neighboring nodes and edges.

        Parameters:
        - node : The node to be described
        - condition : A method to filter hrough the used nodes using their labels

        Returns:
        A description following the format:
        '[node] [relationship1] [node1],[node2],[node5]. [node] [relationship2] [node3],[node4].'
        """

        desc = ""
        for edge_definition in self.graph.edge_definitions():
            #Fetch all nodes connected from the node by a 'edge_definition' edge
            outboundNodes = list(self.db.aql.execute(f"FOR v, e in 1..1 outbound '{node['_id']}' graph '{self.graph_name}' OPTIONS {{'edgeCollections':'{edge_definition['edge_collection']}'}} return [v[\"label\"], e[\"label\"]]"))
            relations = {}
            for vertex, edge in outboundNodes:
                if condition == None or condition(vertex):
                    relations.setdefault(edge, []).append(vertex)
            for edge in relations.keys():
                #Group the nodes in groups of 5 to improve readability and add them to the description
                for nodeChunk in (relations[edge][n:n + 5] for n in range (0, len(relations[edge]), 5)):
                    desc += f"{node['label']} has relation '{edge}' with " + ", ".join(f"{elem}" for elem in nodeChunk) + ". "

            #Fetch all nodes connected from the node by a 'edge_definition' edge
            inboundNodes = list(self.db.aql.execute(f"FOR v, e in 1..1 inbound '{node['_id']}' graph '{self.graph_name}' OPTIONS {{'edgeCollections':'{edge_definition['edge_collection']}'}} return [v[\"label\"], e[\"label\"]]"))
            relations = {}
            for vertex, edge in inboundNodes:
                if condition == None or condition(vertex):
                    relations.setdefault(edge, []).append(vertex)
            for edge in relations.keys():
                #Group the nodes in groups of 5 to improve readability and add them to the description
                for nodeChunk in (relations[edge][n:n + 5] for n in range (0, len(relations[edge]), 5)):
                    desc += ", ".join(f"{elem}" for elem in nodeChunk) + f" have relation '{edge}' with {node['label']}. "

        desc = desc[:-1] if desc else f"{node['label']}."

        return desc

    # Below are methods to manipulate vertices
    def get_vertex_count(self) -> int:
        """
        Counts all vertices in the ArangoDB graph without loading them into memory.

        Returns:
        The count of the vertices in the ArangoDB graph.
        """
        return sum(self.db.aql.execute(f"return length(for v in {collection} return v)").__next__() for collection in self.graph.vertex_collections())
    def read_all_vertices(self):
        """
        Reads all vertices in the ArangoDB graph.

        Returns:
        All vertices as a flat iterator
        """
        return (node for collection in self.graph.vertex_collections() for node in self.db.collection(collection))
    def create_new_vertex_collection(self, collection_name : str):
        """
        Creates a new vertex collection.
        If one is already present, it is cleared.

        Parameters:
        - collection_name (str) : the name of the collection
        """
        if collection_name in self.vertex_collections:
            collection = self.vertex_collections[collection_name]
            collection.truncate()
            for index in collection.indexes()[1:]:
                collection.delete_index(index['id'])
        elif self.graph.has_vertex_collection(collection_name):
            collection = self.graph.vertex_collection(collection_name)
            collection.truncate()
            self.vertex_collections[collection_name] = collection
            for index in collection.indexes()[1:]:
                collection.delete_index(index['id'])
        else:
            collection = self.graph.create_vertex_collection(collection_name)
            self.vertex_collections[collection_name] = collection
    def get_vertex_collection(self, collection_name : str) -> VertexCollection:
        """
        Finds the vertex_collection with the specified collection_name.
        If none is available, a new collection is created.

        Parameters:
        - collection_name (str) : the name of the collection

        Returns:
        The collection from the database with thee name or a newly generated collection 
        """
        if collection_name in self.vertex_collections:
            collection = self.vertex_collections[collection_name]
        elif self.graph.has_vertex_collection(collection_name):
            collection = self.graph.vertex_collection(collection_name)
            # collection.truncate() # If collection gets truncated, all existing vertices will be deleted
            self.vertex_collections[collection_name] = collection
        else:
            collection = self.graph.create_vertex_collection(collection_name)
            self.vertex_collections[collection_name] = collection

        return collection
    def add_vertex_index(self, collection_name : str, index_fields : {}):
        """
        Adds a given index to a vertex_collection.

        Parameters:
        - collection_name (str) : the name of the vertex collection
        - index_fields ({}) : the fields to be added as indexes
        """
        return self.get_vertex_collection(collection_name).add_index(index_fields)
    def add_vertex(self, vertex_collection : str, vertex_fields : {}):
        """
        Adds a new vertex to the vertex_collection.

        Parameters:
        - vertex_collection (str) : the name of the vertex_collection
        - vertex_fields ({}) : the vertex_fields to be added
        """
        return self.get_vertex_collection(vertex_collection).insert(vertex_fields)
    def update_vertex(self, vertex_collection : str, vertex_fields : {}):
        """
        Updates an existing vertex in the vertex_collection

        Parameters:
        - vertex_collection (str) : the name of the vertex_collection
        - vertex_fields ({}) : the vertex_fields to be updated
        """
        return self.get_vertex_collection(vertex_collection).update(vertex_fields)


    # Below are methods to manipulate edges
    def get_edge_count(self):
        """
        Counts all edges in the ArangoDB graph without loading them into memory.

        Returns:
        The count of the edges in the ArangoDB graph.
        """
        return sum(self.db.aql.execute(f"return length(for e in {collection['edge_collection']} return e)").__next__() for collection in self.graph.edge_definitions())
    def read_all_edges(self):
        """
        Reads all edges in the ArangoDB graph.

        Returns:
        All edges as a flat iterator
        """
        return (edge for collection in self.graph.edge_definitions() for edge in self.db.collection(collection["edge_collection"]))
    def create_edge_collection(self, collection_name : str, nodes_from : [str], nodes_to : [str]):
        """
        Generates a new edge collection.

        Parameters:
        - collection_name (str) : the name of the collection
        - nodes_from [str] : the names of the source vertex collections
        - nodes_to [str] : the names of the destination vertex collections
        """
        if collection_name in self.edge_collections or self.graph.has_edge_collection(collection_name):
            collection = self.graph.edge_collection(collection_name)
            # collection.truncate()
            for index in collection.indexes()[2:]:
                collection.delete_index(index['id'])
            self.edge_collections[collection_name] = collection 
        else:
            self.edge_collections[collection_name] = self.graph.create_edge_definition(
                edge_collection = collection_name, from_vertex_collections = nodes_from, to_vertex_collections = nodes_to)
        
        return self.edge_collections[collection_name]

    def get_edge_collection(self, collection_name : str) -> EdgeCollection:
        """
        Finds the edge_collection with the specified collection_name.
        If none is available, an error is thrown.

        Parameters:
        - collection_name (str) : the name of the collection

        Returns:
        The collection from the database with thee name.
        """
        if collection_name in self.edge_collections:
            collection = self.edge_collections[collection_name]
        elif self.graph.has_edge_collection(collection_name):
            collection = self.graph.edge_collection(collection_name)
            # collection.truncate() # If collection gets truncated, all existing nodes will be deleted
            self.edge_collections[collection_name] = collection
        else:
            return False
            raise ValueError(f"Edge Collection '{collection_name}' unknown. Please create it first with create_edge_collection")

        return collection
    def add_edge_index(self, collection_name : str, index_fields : {}):
        """
        Adds a given index to a edge_collection.

        Parameters:
        - collection_name (str) : the name of the edge collection
        - index_fields ({}) : the fields to be added as indexes
        """
        return self.get_edge_collection(collection_name).add_index(index_fields)
    def add_edge(self, edge_collection : str, edge_fields : {}):
        """
        Adds a new edge to the edge_collection.

        Parameters:
        - edge_collection (str) : the name of the edge_collection
        - edge_fields ({}) : the edge_fields to be added
        """
        return self.get_edge_collection(edge_collection).insert(edge_fields)
    def update_edge(self, edge_collection : str, edge_fields : {}):
        """
        Updates an existing edge in the edge_collection

        Parameters:
        - edge_collection (str) : the name of the edge_collection
        - edge_fields ({}) : the edge_fields to be updated
        """
        return self.get_edge_collection(edge_collection).update(edge_fields)