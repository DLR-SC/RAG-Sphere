# Vector RAG

## Overview

Vector RAG is a lightweight Retrieval-Augmented Generation (RAG) system that leverages embedding-based retrieval to efficiently retrieve relevant information. This approach, also known as naive RAG, has gained popularity due to its simplicity and efficiency.

## Method Details

1. **Document indexing**:

    - Input focuments are segmented into managable chunks for efficient processing.
    - These chunks are then storead in a vectore store as embeddings for efficient retrieval.

1. **Query Process**:

    - The user query is embedded to retrieve relevant summaries from the vector store.
    - The embedded query is used to filter and retrieve relevant summaries, which are then returned to the user.


## Benefits of this Approach

1. **Very efficient indexing and query**: By relying solely on embeddings for retrieval, this system enjoys fast indexing and query processing times.

1. **Great Baseline**: The simplicity of this algorithm makes it an ideal baseline for comparing various retrieval methods, providing a reliable starting point for evaluating the effectiveness of more complex approaches.