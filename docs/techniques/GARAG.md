# GARAG: <br/> Graph-Assisted Retrieval-Augmented Generation

## Overview

GARAG is an advanced Retrieval-Augmented Generation (RAG) system that prioritizes the accuracy and integrity of information. Building upon the Microsoft GraphRAG pipeline, this approach leverages knowledge graphs to extract relevant information. In contrast to Microsoft GraphRAG, GARAG employs a novel filtering mechanism using the knowledge graph, which first filters out irrelevant information before returning extracts from the original document.

## Method Details

1. **Document Processing**:

    - Input documents are segmented into manageable chunks for efficient processing.
    - A large language model (LLM) creates graph nodes and their connections for each text chunk.
    - References to the original documents as sources are preserved and cumulated for each node, ensuring contextual information is maintained.

1. **Thematic Summarization**:

    - The Leiden Algorithm is used to cluster the graph into well-connected communities.
    - These communities are further divided into subcommunities recursively to extract more detailed summaries.
    - For each community, a summarization of all relevant information is generated.
    - Original document sources are accumulated within each community, ensuring contextual integrity.
    - Resulting summaries are stored in a vector store as embeddings for efficient retrieval.

1. **Query Process**:

    - The user query is embedded and used to retrieve relevant summaries from the vector store.
    - The resulting vector similarity score of each hit is used as a weight for the respective cumulated sources.
    - Weighted source references are then accumulated over the extracted information.
    - Using the weighted scores, the text of original documents is returned to the user.

## Benefits of this Approach

1. **Garanteed Information Integrity**: By extracting unaltered extracts from original documents, GARAG ensures the integrity of provided text, eliminating potential biases or distortions.

1. **Fast query time**: The query process relies on embeddings and vector similarity scores, making it optimized for speed.

1. **Global Sensmaking**: Although GARAG does not provide community summaries directly, the usage of these summaries in the query process enables global sensmaking for filtering information.




### GRAPH RAG

An implementation inspired by Graph RAG by Microsoft. The data is read and transformed into a knowledge graph, stored in ArangoDB. The resulting nodes are then grouped by their topic and summarized resulting in thematic subgraphs. During a query, these thematic summaries and the user prompt are then passed to a LLM, which generates partial answers on the information provided and a confidence value, stating the helpfulness of the provided answer. These partial answers are then ranked by their confidence and the best results are returned to the user.

This algorithm takes an extra argument, the community level to search on. There, a level of 0 describes the usage of a single node, capturing the entire information corpus in a small description. Higher values yield more nodes, therefore providing a more precise description on multiple topics. The maximum level can only be inferred by a manual lookup in the GraphDB used. Higher values always also supply the descriptions of all nodes of lower community level. A value of 1 or 2 is advisable.

This kind of initialization takes very long, but might be worth it, as following querys are not matched by text similarity but by the topic they reside in. The generated knowledge graph is shared between Graph Rag, Graph Rag Rag, and Garag. When using this implementation, keep in mind that a longer retrieval time is expected.


### GARAG

An implementation that reduces the hallucination of the filtered information. Communities with fitting information are first found using an embedding comparison in the Elasticsearch database. The original sources (the raw data used to generate the knowledge graph) of these communities are then ranked by their influence on these summaries and the accuracy of the vector comparison of those with the user query. The top original sources are then returned to the user. Therefore, this approach can be seen as Graph-Assisted RAG (or GARAG). It returns the same kind of information that would be obtained from a normal RAG query on the original documents, using a complex, topic-based decision-making process, instead of a direct vector comparison. It is recommended to use this method, as it combines a very fast retrieval time with good precision.
