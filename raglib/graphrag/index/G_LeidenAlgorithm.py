### This file is an implementation of the Leiden Algorithm, proposed in https://arxiv.org/abs/1810.08473
from collections import deque
from math import comb, inf, exp
from random import seed, choices, shuffle
from configparser import ConfigParser
from tqdm import tqdm

from utils.arango_client import ArangoDBClient

class LeidenProcessor:
    def __init__(self, arangoGraph : ArangoDBClient):
        """
        Initializes the Leiden Algorithm for a given graph.

        Parameters:
        - arangoGraph (ArangoDBClient) : The arango client, used to read the graphs data.
        """

        ### Vocabulary:
        ### - nodes / vertices : a unit of information (must be of hashable type)
        ### - edge : a weighted connection between two nodes
        ### - community: a set of vertices used to group them together
        ### - partition: a list of communities
        ### - graph: a dictionary containing the following values:
        ###     - vertices: a set containing all nodes present in the graph
        ###     - edges: a dictionary, associating each (node, node)-tuple with a weight (in both directions)
        ###     - edge_connectins: a set containing all connected (node, node)-tuples in both permutations

        # Saves the arangoDB graph
        self.arangoGraph = arangoGraph

        # Field to store the most recent partition generated using the leiden algorithm
        self.partition = None

        # Copies the graph from the arangoGraph into memory
        self.build_graph_from_arangoDB()

        # Set constant values
        self.gamma = 2.75 / len(self.graph["vertices"]) + 0.0025
        self.theta = 0.1
        self.max_cluster_size = 20
        self.max_depth = 6
        self.gamma_multiplier = 2
        
        # Gets the maximum value, for which exp(max_exp / self.theta) doesn't throw an error
        self.max_exp = 709 * self.theta

        seed(17032025)

    ### Method to fetch data from graph
    def build_graph_from_arangoDB(self):
        """
        Constructs a copy of the graph in the ArangoDB in memory
        """
        self.vertices = set((v['id'], v['key']) for v in self.arangoGraph.get_aql("for v in Node return {id: v._id, key: v._key}"))
        self.vertices |= set((v['id'], v['key']) for v in self.arangoGraph.get_aql("for v in File return {id: v._id, key: v._key}"))

        self.graph = {
            'vertices' : {v_id for v_id, _ in self.vertices},
            'edges' :  (edges := {
                (edge['from'], edge['to']) : edge['weight']
                for edge_collection in ["mentionedIn", "Relation"]
                for edges in [
                    self.arangoGraph.get_aql(f"for e in {edge_collection} return {{weight: e.weight, from: e._from, to: e._to}}"),
                    self.arangoGraph.get_aql(f"for e in {edge_collection} return {{weight: e.weight, from: e._to, to: e._from}}")
                ]
                for edge in edges
            }),
            'edge_connections' : set(edges.keys())
        }

    ### Methods to generate leiden communities
    def get_hierarchical_leiden_communities(self):
        """
        Constructs communities from a graph using a hierarchical Leiden Algorithm.

        Returns:
        A dictionary containing the resulting communities for each node_id in the ArangoDB graph.
        """
        if not self.partition:
            # Constructs the nested partition representing the complete hierarchical Leiden
            partition, depth = self.get_hierarchical_leiden(self.graph, self.gamma, self.max_depth)
        else:
            # Read the partition
            partition, depth = self.partition

        # Parses the nested partitions into an easy to read dictionary 
        return self.get_vertex_communities(partition, self.vertices, depth)

    def get_leiden_communities(self):
        """
        Constructs communities from a graph using the Leiden Algorithm.

        Returns:
        A dictionary containing the resulting community for each node_id in the ArangoDB graph.
        """
        if not self.partition:
            # Constructs the partition representing the complete Leiden
            partition = self.get_leiden_parition(self.graph, self.singleton_partition(self.graph), self.gamma)
        else:
            # Read the partition
            partition = self.partition[0]
            
        # Parses the partition into an easy to read dictionary
        return self.get_vertex_communities(partition, self.vertices, 1)

    def get_hierarchical_leiden(self, graph : {}, gamma : float, max_depth : int):
        """
        Constructs a nested partition for a provided graph using an hierarchical leiden approach.

        Parameters:
        - graph ({}) : a dictionary representing the graph, that should be partitioned.
        - gamma (float) : the current gamma value to be used in the leiden partitioning step.
        - max_depth (int) : the maximum depth of the hierarchical leiden communities

        Returns a tuple with:
        - The partitions calculated for the given graph
        - The total depht of the community system
        """
        # Calculates the current partitions using the Leiden Algorithm
        partition = self.get_leiden_parition(graph, self.singleton_partition(graph), gamma)
        # To prevent unnecessary nesting, if partitioning was unsuccessfull, return the communities directly
        if len(partition) <= 1: return partition[0], 0
        max_depth -= 1

        # Initializes a counter for the maximum depth
        depth = 1

        # Checks all communities, to be smaller than max_cluster_size
        for i in range(len(partition)):
            if max_depth and len(partition[i]) > self.max_cluster_size:

                # If the community is to big, a sub graph using only the community, is build
                sub_graph = {
                    'vertices' : partition[i],
                    'edges' :  graph["edges"],
                    'edge_connections' : graph["edge_connections"]
                }
                # Subpartitions are then calculated
                partition[i], current_depth = self.get_hierarchical_leiden(sub_graph, gamma * self.gamma_multiplier, max_depth)
                # and the depht updated, if necessary
                if current_depth >= depth:
                    depth = current_depth + 1
                
        self.partition = (partition, depth)
        return partition, depth

    def get_leiden_parition(self, graph : {}, partition : [{}], gamma : float):
        """
        Constructs partitions for a given graph using the leiden algorithm

        Parameters:
        - graph ({}) : a dictionary representing the graph, that schould be partitioned
        - partition ([{}]) : the starting partitions (usually generated using self.singleton_partition)
        - gamma (float) : the current gamma value to be used in the leiden algorithm

        Returns:
        A list of communities (partition) of the nodes in the graph
        """
        with tqdm(desc=f"Optimizing leiden subgraph ({len(graph['vertices'])} nodes)", leave = False) as pbar:
            while True:
                # Optimises partition by merging nodes into communities
                partition = self.move_nodes(graph, partition, gamma)

                # Counts communities and vertices
                partition_len = len(partition)
                vertex_count = len(graph['vertices'])
                # Updates progress on progress bar
                pbar.reset(total = partition_len)
                pbar.update(vertex_count)
                # Breaks if no optimasation could be achived
                if partition_len == vertex_count: break

                # Splits large or sparly connected communities
                refined_part = self.refine_partition(graph, partition, gamma)

                # Aggregates the graph (communities become nodes of the new graph)
                graph = self.aggregate_graph(graph, refined_part)
                # Update the partitions to use the newly generated community nodes
                partition = [{vertex for vertex in graph['vertices'] if set(vertex) <= set(self.flatten(community))} for community in partition]

        # return a flattened version of the partitions to get rid of node nesting
        self.partition = ([list(self.flatten(community)) for community in partition], 1)
        return self.partition[0]

    def get_community_graph(self):
        """
        Constructs a graph of communities using pre-generated partitions.

        Returns:
        A simple graph dictionary with the following format:
        {
            "vertices" : A set containing (communities as tuples, community degree, community index) tuples,
            "edges" : A dictionary with the connection weights for each community pair, representing the hierarchical structure in the format:
                (vertex_from, vertex_to) : [(weight, vertex_from_degree), (weight, vertex_from_degree), ...],
            "height" : The height of the community_graph tree, is also the highest vertex degree
        }
        """
        if not self.partition:
            # Constructs the nested partition representing the complete hierarchical Leiden
            partition, depth = self.get_hierarchical_leiden(self.graph, self.gamma, self.max_depth)
        else:
            # Read the partition
            partition, depth = self.partition

        partitions = self.get_community_nodes(partition, self.vertices, depth)

        edges = {}

        for partition_idx in range(len(partitions) - 1):
            for community_from in partitions[partition_idx]:
                community_from_set = set(community_from)
                for community_to in partitions[partition_idx + 1]:
                    community_to_set = set(community_to)
                    if community_to_set == community_from_set:
                        edges.setdefault((community_from, community_to), []).append((1, partition_idx + 1))
                    elif community_to_set <= community_from_set and \
                        (weight := self.count_connecting_edges(self.graph, community_from_set - community_to_set, community_to_set)) > 0:
                        edges.setdefault((community_from, community_to), []).append((weight, partition_idx + 1))

        graph_node = tuple(self.graph['vertices'])
        for community in partitions[0]:
            edges.setdefault((graph_node, community), []).append((1, 0))

        return {
            "vertices" : {(community, degree + 1, idx) for degree, partition in enumerate(partitions) for idx, community in enumerate(partition)} | {(graph_node, 0, 0)},
            "edges" : edges,
            "height" : len(partitions)
        }

    ### Methods used by the leiden algorithm directly
    def move_nodes(self, graph : {}, partition : [{}], gamma : float):
        """
        Merges nodes in communities using a local move algorithm

        Parameters:
        - graph ({}) : a dictionary representing the graph, that schould be partitioned
        - partition ([{}]) : the current partitions
        - gamma (float) : the current gamma value to be used in the leiden algorithm

        Returns:
        The resulting partition after moving
        """

        # Generates a queue, holding all vertices, that should be visited
        node_queue = list(graph['vertices'])
        shuffle(node_queue)

        # Generates a set, holding all vertices, that should be visited a second time
        next_queue = set()

        while True:
            while node_queue:
                # Get the current node and find its current community
                node = node_queue.pop()
                node_community = self.get_community_of_node(partition, node)

                # A field to store the maximum increase in the Constant Potts Model, a change can achive
                max_potts_value = 0

                # Test whether seperating the node from its community is a net positive move
                if (potts_value := self.delta_potts_model(graph, partition, gamma, node, node_community, set())) > 0:
                    # If so, save the increase in the Constant Potts Model
                    max_community = set()
                    max_potts_value = potts_value

                # Calculate the increase in the Constant Potts Model for moving the current node into each community
                for community in partition:
                    if (potts_value := self.delta_potts_model(graph, partition, gamma, node, node_community, community)) > max_potts_value:
                        # If the increase is better than any previously found increase, safe the current one instead
                        max_community = community
                        max_potts_value = potts_value
                
                # If a community was found, that increases the Constant Potts Model
                if max_potts_value > 0:
                    # Remove the node from its current community
                    node_community.remove(node)
                    if not node_community:
                        # Remove the current community from the list of communities, if it is now empty
                        partition.remove(node_community)

                    if max_community:
                        # Add the node the the best matching community, if it is not a new, empty set
                        max_community.add(node)
                    else:
                        # Else add a new seperate community for the node to the partitions
                        partition.append({node})

                    # Add all neighbors to the node queue, if they dont share the same community
                    for neighbor in self.get_graph_neighbors(graph, node):
                        if not neighbor in max_community:
                            next_queue.add(neighbor)

            if next_queue:
                # Refill the node queue, by readding node neighbors of visited nodes 
                node_queue = list(next_queue)
                shuffle(node_queue)
                next_queue = set()
            else:
                # No node can be further improved, exit loop now
                break

        # Returns the resulting partitions using the local move alforithm
        return partition

    def refine_partition(self, graph : {}, partition : [{}], gamma : float):
        """
        Refines the partition, by splitting large and poorly connected communities

        Parameters:
        - graph ({}) : a dictionary representing the graph, that schould be partitioned
        - partition ([{}]) : the current partitions
        - gamma (float) : the current gamma value to be used in the leiden algorithm

        Returns:
        The resulting refined partition after splitting communities
        """
        # Generate fresh communities, each holding one node of the graph
        refined_part = self.singleton_partition(graph)

        for community in partition:
            # Improve the new generated partition, by merging nodes inside the previously discovered communities
            refined_part = self.merge_nodes_subset(graph, refined_part, gamma, community)

        # Return the new refined partition
        return refined_part

    def merge_nodes_subset(self, graph : {}, partition : [{}], gamma : float, subset : {}):
        """
        Merges well connected nodes of a given subset into communities

        Parameters:
        - graph ({}) : a dictionary representing the graph, that schould be partitioned
        - partition ([{}]) : the current partitions
        - gamma (float) : the current gamma value to be used in the leiden algorithm
        - subset ({}) : the subset of nodes, which will be used to merge the nodes in

        Returns:
        The resulting refined partition after splitting communities
        """
        # Filter the subset for only well connected nodes
        well_connected_nodes = [node for node in subset 
            if self.count_connecting_edges(graph, {node}, subset - {node}) >= 
            (gamma * self.get_len(node) * (self.get_len(subset) - self.get_len(node)))]
        shuffle(well_connected_nodes)
        
        # Merge well_connected_nodes into communities
        for node in well_connected_nodes:
            # Only merge nodes, that are yet to be merged
            if len((node_community := self.get_community_of_node(partition, node))) > 1: continue

            # Filter all communities in the subset for well connected communities
            well_connected_communities = [community for community in partition
                if community <= subset and
                self.count_connecting_edges(graph, community, subset - community) >= 
                (gamma * self.get_len(community) * (self.get_len(subset) - self.get_len(community)))]

            # Calculate a propability distribution over all possible well connected communities using the increase in the Constant Potts Model as reference
            probabilities = [exp(709) if (delta_potts := self.delta_potts_model(graph, partition, gamma, node, node_community, c)) >=  self.max_exp
                else exp(delta_potts / self.theta) if delta_potts >= 0 else 0 for c in well_connected_communities]

            # Choose a random community, using the porpability distribution
            community = choices(well_connected_communities, probabilities)[0]

            # If the node is not already in that community:
            if not {node} <= community:
                # Remove the node from its current community and delete the current community, if now empty
                node_community.remove(node)
                if not node_community:
                    partition.remove(node_community)
                
                # Add the node the the new community
                community.add(node)
        
        # Return the resulting partition after mergint nodes in the subset
        return partition

    def aggregate_graph(self, graph : {}, partition : [{}]):
        """
        Aggregates the graph by transforming communities into new nodes

        Parameters:
        - graph ({}) : the graph that should be aggregated
        - partition ([{}]) : a list of communities. Each community will be a node in the new graph

        Returns:
        The aggregated graph
        """
        # Generate a temporary edge dictionary. Each idx tuple, representing two communities, returns the sum of connections of all nodes within
        community_count = len(partition)
        tmp_edges = {
            (com1, com2) : weight
            for com1 in range(community_count) for com2 in range(community_count)
            if (weight := sum(
                graph['edges'].get((node1, node2), 0)
                for node1 in partition[com1] for node2 in partition[com2]
            )) > 0
        }

        # Generate a dictionary, using the idx of a community to reference a new node (community parsed into tuple, to pretain hashability of nodes)
        vertices = {idx: tuple(self.flatten(community)) for idx,community in enumerate(partition)}
        
        # Generate a edge dictionary by parsing the index keys of the temporary edge dictionary into its node counterparts.
        edges = {
            (vertices[com1], vertices[com2]) : weight
            for (com1, com2), weight in tmp_edges.items()
        }
        
        # Return a new graph structure
        return {
            'vertices' : set(vertices.values()),
            'edges' : edges,
            'edge_connections' : set(edges.keys())
        }


    def singleton_partition(self, graph : {}):
        """
        Generates a partition, in which each node of the graph has its own community
        
        Parameters:
        - graph ({}) : The graph providing the vertices of the partition

        Returns:
        A list of communities
        """
        # Generates and returns singleton partitions
        return [{vertex} for vertex in graph['vertices']]

    ### Constant potts model formulas
    def constant_potts_model(self, graph : {}, partition : [{}], gamma : float):
        """
        Calculates the constant potts model of the current graph arangement

        Parameters:
        - graph ({}) : The graph containing the edge data for all edges
        - partition ([{}]) : The current communities of the graph
        - gamma (float) : The gamma value used to weigh the amount of possible connections

        Returns:
        The result of the constant potts model formula
        """
        return sum(
            self.count_connecting_edges_in(graph, community) - gamma * comb(self.get_len(community), 2) 
            for community in partition
        )

    def delta_potts_model(self, graph : {}, partition : [{}], gamma : float, changing_node, node_community : {}, changing_community : {}):
        """
        A optimised version for the constant potts model, solving the following equation:
        Constant potts model of the graph, simulated as if changing_node was in changing_community instead - 
            Constant potts model of the graph, with changing_node in its original community
        
        Parameters:
        - graph ({}) : The graph containing the edge data for all edges
        - partition ([{}]) : The current communities of the graph
        - gamma (float) : The gamma value used to weight the amount of possible connections
        - changing_node (hashable type) : The node for which a change in community should be simulated
        - node_community ({}) : The original community of the changing_node
        - changing_community ({}) : The destination community of the chaning_node in the simulation

        Returns:
        The change in the constant potts model, when simulating the node in another community
        """
        # If the node is already in its destination community, no change can be recorded
        if changing_node in changing_community : return 0

        # A community containing only the node
        single_community = {changing_node}
        # The length / size of the node (counts subnodes after aggregation step)
        node_length = self.get_len(changing_node)
        # The original community of the node without the node in it
        small_community = node_community - single_community

        def comb(c : float, n : float):
            """
            Calculates the solution for the following term:
            (c over 2) - (c+n over 2)

            Parameters:
            c, n (float): The variables used in the calculation

            Returns:
            The result of the calculation
            """
            return 0.5 * n * (1 - n) - n * c

        # Calculates the above formula of the constant potts model in this special case
        return (self.count_connecting_edges(graph, changing_community, single_community)
        - self.count_connecting_edges(graph, small_community, single_community)
        + gamma * (
            comb(self.get_len(changing_community), node_length)
            - comb(self.get_len(small_community), node_length)
        ))

    ### Graph helper methods
    def count_connecting_edges_in(self, graph : {}, community : {}):
        """
        Counts the connecting edges inside the given community.

        Parameters:
        graph ({}) : the graph containing edge weight data for all connections
        community ({}) : the community, in which the edges shall be counted

        Returns:
        The sum of the weights for all connections
        """
        return sum(
            graph['edges'].get((node1, node2), 0)
            for node1 in community for node2 in community if node1 > node2
        )

    def count_connecting_edges(self, graph : {}, community1 : {}, community2 : {}):
        """
        Counts the connecting edges between two communities.

        Parameters:
        graph ({}) : the graph containing edge weight data for all connections
        community1, community2 ({}) : The communities, where interconnecting connections should be counted

        Returns:
        The sum of the weight for all connections between the two communities
        """
        return sum(
            graph['edges'].get((node1, node2), 0)
            for node1 in community1 for node2 in community2
        )

    def get_community_of_node(self, partition : [{}], node):
        """
        Finds the community of a provided node.

        Parameters:
        partition ([{}]) : the list of communities, to be searched
        node : a node contained in the searched community

        Returns:
        the community containing the node or an empty set if unsuccessfull
        """
        for community in partition:
            if node in community: return community
        
        return set()

    def get_graph_neighbors(self, graph : {}, node):
        """
        Finds all connected nodes for a given node in a graph.

        Parameters:
        graph ({}) : the graph containing the edge connection data
        node : the node for which neighbors should be searched

        Returns:
        An iterator containing all connected nodes
        """
        for neighbor in graph['vertices']:
            if (node, neighbor) in graph['edge_connections']:
                yield neighbor

    def get_vertex_communities(self, partition : [{}], vertices : [], depth : int):
        """
        Converts a depth nested community array into an easy to read dictionary of the following format:
        {
            vertex_id : [LIST OF COMMUNITY IDS FOR EACH LEVEL UNTILL DEPTH], ...
        }

        Parameters:
        - partition ([{}]) : the nested community array to be converted
        - vertices ([]) : a list of (vertex_id, vertex_key) tuples, which can be used to find a given node in the arangoDB graph
        - depth (int) : the depth of the nesting in the community array
        
        Returns:
        The community dictionary
        """
        # All vertices are combined into a single community
        if (depth == 0):
            return {vertex_id : [idx] for idx, (vertex_id, _) in enumerate(vertices)}

        # Initializes the easy to read community dictionary
        communities = {vertex_id : [] for vertex_id, _ in vertices}

        # Initialize an array, which will be filled with the communities flattened to an index degree
        flat_partitions = [[] for _ in range(depth)]
        # fill the flat_partitions with flattened data
        for community in partition:
            self.flatten_partition_depth(community, depth, flat_partitions)

        # iterate over all flattening degrees and add the community index to the dictionary
        for flat_partition in flat_partitions:
            for idx, community in enumerate(flat_partition):
                for vertex in community:
                    communities[vertex].append(idx)

        # Returns the dictionary
        return communities

    def get_community_nodes(self, partition : [{}], vertices : [], depth : int):
        """
        Transforms a partition into its community vertices counterpart.

        Parameters:
        - partition ([{}]) : the nested community array to be converted
        - vertices ([]) : a list of (vertex_id, vertex_key) tuples, which can be used to find a given node in the arangoDB graph
        - depth (int) : the depth of the nesting in the community array
        
        Returns:
        The community nodes array
        """
        # Initialize an array, which will be filled with the communities flattened to an index degree
        flat_partitions = [[] for _ in range(depth + 1)]
        # fill the flat_partitions with flattened data
        for community in partition:
            self.flatten_partition_depth(community, depth + 1, flat_partitions)

        # Returns the flat partitions with communities transformed to tuples, to be hashable nodes
        return [[tuple(community) for community in partition] for partition in flat_partitions]

    def flatten_partition_depth(self, community : [], depth : int, mapping : [[]], idx : int = 0):
        """
        Helper function to recursivly flatten the community into multiple levels, storing each step into the mapping array

        Parameters:
        - community ([]) : the community to be flattened
        - depth (int) : the maximum depth of the nested community array
        - mapping ([[]]) : the array to be populated with flattened data
        - idx (int) : the current degree of flattening (starts at 0)
        """
        if isinstance(community, list):
            # Recursivly flatten the list content
            mapping[idx].append(list(self.flatten(community)))
            for sub_community in community:
                self.flatten_partition_depth(sub_community, depth, mapping, idx + 1)
        else:
            # If the community is a single value, flood fill the mapping until max depth is reached
            for i in range(idx, depth):
                mapping[i].append([community])

    # Miscellaneous helper methods
    def flatten(self, something):
        """
        Flattens a nested list / set / tuple into a single stream of data.

        Parameters:
        something : the list / set / tuple to be flattened

        Returns:
        An iterator providing all data of the input field
        """
        if isinstance(something, (list, set, tuple)):
            for content in something:
                yield from self.flatten(content)
        else:
            yield something
    
    def get_len(self, something):
        """
        Counts the total number of elements in a nested list / set / tuple.

        Parameters:
        something : the list / set / tuple, where elements should be counted

        Returns:
        The amount of items in the input field
        """
        return sum(1 for _ in self.flatten(something))