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