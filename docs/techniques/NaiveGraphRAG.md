# Naive GraphRAG

## Overview

The Naive GraphRAG variant leverages a custom implementation of the Microsoft GraphRAG Approach, incorporating key principles from VectorRAG to optimize query performance in this graph-based system.


## Method Details

Instead of generating partial answers using LLMs, community summaries are filtered through an embedding comparison in the Elasticsearch database. The information summaries of the most fitting communities are then returned to the user. Therefore, this approach can be seen as a naive RAG (Rapid Answer Generation) approach on community summaries. While this implementation reduces retrieval time compared to Graph Rag, precision on non-global questions is reduced.

1. **Document Processing**:

    - Input documents are segmented into manageable chunks for efficient processing.
    - A large language model (LLM) creates graph nodes and their connections for each text chunk.

1. **Thematic Summarization**:

    - The Leiden Algorithm is used to cluster the graph into well-connected communities.
    - These communities are further divided into subcommunities recursively to extract more detailed summaries.
    - For each community, a summarization of all relevant information is generated.
    - Resulting summaries are stored in a vector store as embeddings for efficient retrieval.

1. **Query Process**:

    - The user query is embedded to retrieve relevant summaries from the vector store.
    - The embedded query is used to filter and retrieve relevant summaries, which are then returned to the user.


## Benefits of this Approach

1. **Fast query time**: The query process relies on embeddings and vector similarity scores, making it optimized for speed.

1. **Global Sensmaking**: The usage of community summaries in the query process enables global sensmaking for filtering information.