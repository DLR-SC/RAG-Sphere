# Configuration

## General

The configuration of the ERI-Server can be done using the `eri.ini` configuration file.

This file is split into multiple sections: 

- A general configuration of the ERI-Server. This section modifies the behaviour of the entire interface.
- An optional list of sections for the provided retrieval algorithm. All retrieval algorithms configured within such a section are available for the user when querying the interface

## Configuring the Interface

To configure the general interface settings, found in the `ERI Settings` section, please follow these steps closely:

1. **Label your data source**: To enable users to easily identify what information can be retrieved using the interface, a name and description must be provided. These can be entered into the `data_source_name` and `data_source_description` fields.
1. **Set privacy settings**: To restrict the usage of external LLMs on internal data, the type of allowed LLM providers can be set. Please enter one of `SELF_HOSTED | ANY` into the `allowed_provider_type` field. 
1. **Configure data access**: To limit the access to the ERI-Server, and thus to the information handled by such, the type of available authorization method can be set. Please enter one of `NONE | TOKEN` into the `authorization_methods` fields or, to enable multiple options, enter a JSON formatted list of the respective methods as strings instead. For more information about the available authorization methods, please refer to [authorization methods](#authorization-methods).
1. **[Optional] Enable https**: To start the Server on HTTPS, please provide the paths to a valid SSL certificate and key in the `ssl_cert_path` and `ssl_key_path` fields, respectively. The Server is started in HTTPS mode if both fields are provided; otherwise, HTTP is used instead. 
1. **Setup the authentication database** *Not necessary when only using `NONE` authentication*: The needed data for authentication validation is stored in a postgres database. The connection to this database has to be specified here. Please provide a JSON formatted dictionary with the following properties to the `postgres_connection` option: `username, password, url, database_name`. For more information about the database, refer to [authorization methods](#authorization-methods).

To enable selected retrieval algorithms, follow the steps specific to the desired method.

## GARAG

To enable GARAG as a retrieval process, please paste the following skeleton into the configuration file and follow these steps closely:

```ini
[GARAG]
config = 
emb_model = 
elastic_db_url = 
arango_db = 
```

1. **Enable custom configuration**: To configure the retriever, please provide a JSON formatted dictionary using the properties below in the `config` field.
    - `top_k (int; 0 < x)`: The maximum number of hits to retrieve. May be set by an user during a retrieval request.
    - `confidence_cutoff (float; 0 < x < 1)`: A value to specify a minimum similiarity between the query and the retrieved information. May be set by an user during a retrieval request.
    - `vector_db_index_name (string)`: The index to be used for searching relevant information.
1. **Specify the embedding model used**: Enter the name of the embedding model used to convert requests into vectors into the `emb_model` field. This has to match the model used during the indexing phase.
1. **Set the Elasticsearch connection**: Enter the url to the Elasticsearch server into the `elastic_db_url` field, on which the vector index can be found.
1. **Set the ArangoDB connection**: Please specify the connection to ArangoDB as a JSON formatted dictionary using the properties below in the `arango_db` field. The graph_name should point to the community graph build during the indexing phase.

#### GARAG config
```JSON
{
    "top_k": int,
    "confidence_cutoff": float,
    "vector_db_index_name": string
}
```

#### ArangoDB config
```JSON
{
    "url": string,
    "username": string,
    "password": string,
    "db_name": string,
    "graph_name": string
}
```

## GraphRAG

To enable GraphRAG as a retrieval process, please paste the following skeleton into the configuration file and follow these steps closely:

```ini
[GraphRAG]
config = 
llm = 
arango_db = 
```

1. **Enable custom configuration**: To configure the retriever, please provide a JSON formatted dictionary using the properties below in the `config` field.
    - `top_k (int; 0 < x)`: The maximum number of hits to retrieve. May be set by an user during a retrieval request.
    - `confidence_cutoff (int; 0 < x < 100)`: A value to specify a minimum similiarity between the query and the retrieved information. May be set by an user during a retrieval request.
    - `community_degree (int; 0 < x)`: The maximum community degree to be used during retrieval. A higher value will incorporate more precise summaries, resulting in a higher node count and longer query time. May be set by an user during a retrieval request.
1. **Set the LLM connection**: Please specify the connection to a LLM service as a JSON formatted dictionary using the properties below in the `llm` field. This LLM is used to gernerate and evaluate partial answers.
1. **Set the ArangoDB connection**: Please specify the connection to ArangoDB as a JSON formatted dictionary using the properties below in the `arango_db` field. The graph_name should point to the community graph build during the indexing phase.

#### GraphRAG config
```JSON
{
    "top_k": int,
    "confidence_cutoff": int,
    "community_degree": int
}
```

#### LLM config
```JSON
{
    "provider": "ollama" | "openai",
    "base_url": string,
    "api_key": string (optional),
    "model_name": string (optional),
    "options": dictionary
}
```

#### ArangoDB config
```JSON
{
    "url": string,
    "username": string,
    "password": string,
    "db_name": string,
    "graph_name": string
}
```

## NaiveGraphRAG

To enable NaiveGraphRAG as a retrieval process, please paste the following skeleton into the configuration file and follow these steps closely:

```ini
[NaiveGraphRAG]
config = 
emb_model = 
elastic_db_url = 
```

1. **Enable custom configuration**: To configure the retriever, please provide a JSON formatted dictionary using the properties below in the `config` field.
    - `top_k (int; 0 < x)`: The maximum number of hits to retrieve. May be set by an user during a retrieval request.
    - `confidence_cutoff (float; 0 < x < 1)`: A value to specify a minimum similiarity between the query and the retrieved information. May be set by an user during a retrieval request.
    - `vector_db_index_name (string)`: The index to be used for searching relevant information.
1. **Specify the embedding model used**: Enter the name of the embedding model used to convert requests into vectors into the `emb_model` field. This has to match the model used during the indexing phase.
1. **Set the Elasticsearch connection**: Enter the url to the Elasticsearch server into the `elastic_db_url` field, on which the vector index can be found.

#### NaiveGraphRAG config
```JSON
{
    "top_k": int,
    "confidence_cutoff": float,
    "vector_db_index_name": string
}
```

## NaiveRAG

To enable NaiveRAG as a retrieval process, please paste the following skeleton into the configuration file and follow these steps closely:

```ini
[NaiveRAG]
config = 
emb_model = 
elastic_db_url = 
```

1. **Enable custom configuration**: To configure the retriever, please provide a JSON formatted dictionary using the properties below in the `config` field.
    - `top_k (int; 0 < x)`: The maximum number of hits to retrieve. May be set by an user during a retrieval request.
    - `confidence_cutoff (float; 0 < x < 1)`: A value to specify a minimum similiarity between the query and the retrieved information. May be set by an user during a retrieval request.
    - `vector_db_index_name (string)`: The index to be used for searching relevant information.
1. **Specify the embedding model used**: Enter the name of the embedding model used to convert requests into vectors into the `emb_model` field. This has to match the model used during the indexing phase.
1. **Set the Elasticsearch connection**: Enter the url to the Elasticsearch server into the `elastic_db_url` field, on which the vector index can be found.

#### NaiveRAG config
```JSON
{
    "top_k": int,
    "confidence_cutoff": float,
    "vector_db_index_name": string
}
```

## VectorGR

To enable VectorGR as a retrieval process, please paste the following skeleton into the configuration file and follow these steps closely:

```ini
[VectorGR]
config = 
emb_model = 
llm = 
neo4j_db = 
```

1. **Enable custom configuration**: To configure the retriever, please provide a JSON formatted dictionary using the properties below in the `config` field.
    - `top_k (int; 0 < x)`: The maximum number of hits to retrieve. May be set by an user during a retrieval request.
    - `v_index_name (string)`: 
    - `return_properties (List[string])`: List of node properties to return.
    - `filters (Dictionary[string, Any])`: Filters for metadata pre-filtering. When performing a similarity search, one may have constraints to apply. May be set by an user during a retrieval request.
1. **Specify the embedding model used**: Enter the name of the embedding model used to convert requests into vectors into the `emb_model` field. This has to match the model used during the indexing phase.
1. **Set the LLM connection**: Please specify the connection to a LLM service as a JSON formatted dictionary using the properties below in the `llm` field. This LLM is used to gernerate and evaluate partial answers.
1. **Set the Neo4J connection**: Please specify the connection to ArangoDB as a JSON formatted dictionary using the properties below in the `neo4j_db` field. The graph_name should point to the community graph build during the indexing phase.

#### VectorGR config
```JSON
{
    "top_k": int,
    "v_index_name": string,
    "return_properties": List[string],
    "filters": Dictionary[string, Any]
}
```

#### LLM config
```JSON
{
    "provider": "ollama" | "openai",
    "base_url": string,
    "api_key": string (optional),
    "model_name": string (optional),
    "options": dictionary
}
```

#### Neo4JDB config
```JSON
{
    "url": string,
    "db_name": string,
    "password": string
}
```

## HybridGR

To enable HybridGR as a retrieval process, please paste the following skeleton into the configuration file and follow these steps closely:

```ini
[HybridGR]
config = 
emb_model = 
llm = 
neo4j_db = 
```

1. **Enable custom configuration**: To configure the retriever, please provide a JSON formatted dictionary using the properties below in the `config` field.
    - `top_k (int; 0 < x)`: The maximum number of hits to retrieve. May be set by an user during a retrieval request.
    - `v_index_name (string)`: 
    - `f_index_name (string)`: 
    - `return_properties (List[string])`: List of node properties to return.
1. **Specify the embedding model used**: Enter the name of the embedding model used to convert requests into vectors into the `emb_model` field. This has to match the model used during the indexing phase.
1. **Set the LLM connection**: Please specify the connection to a LLM service as a JSON formatted dictionary using the properties below in the `llm` field. This LLM is used to gernerate and evaluate partial answers.
1. **Set the Neo4J connection**: Please specify the connection to ArangoDB as a JSON formatted dictionary using the properties below in the `neo4j_db` field. The graph_name should point to the community graph build during the indexing phase.

#### HybridGR config
```JSON
{
    "top_k": int,
    "v_index_name": string,
    "f_index_name": string,
    "return_properties": List[string]
}
```

#### LLM config
```JSON
{
    "provider": "ollama" | "openai",
    "base_url": string,
    "api_key": string (optional),
    "model_name": string (optional),
    "options": dictionary
}
```

#### Neo4JDB config
```JSON
{
    "url": string,
    "db_name": string,
    "password": string
}
```

## Text2Cypher

To enable Text2Cypher as a retrieval process, please paste the following skeleton into the configuration file and follow these steps closely:

```ini
[Text2Cypher]
config = 
llm = 
neo4j_db = 
```

1. **Enable custom configuration**: To configure the retriever, please provide a JSON formatted dictionary using the properties below in the `config` field.
    - `examples`: Optional user input/query pairs for the LLM to use as examples.
1. **Set the LLM connection**: Please specify the connection to a LLM service as a JSON formatted dictionary using the properties below in the `llm` field. This LLM is used to gernerate and evaluate partial answers.
1. **Set the Neo4J connection**: Please specify the connection to ArangoDB as a JSON formatted dictionary using the properties below in the `neo4j_db` field. The graph_name should point to the community graph build during the indexing phase.

#### Text2Cypher config
```JSON
{
    "examples": List[string]
}
```

#### LLM config
```JSON
{
    "provider": "ollama" | "openai",
    "base_url": string,
    "api_key": string (optional),
    "model_name": string (optional),
    "options": dictionary
}
```

#### Neo4JDB config
```JSON
{
    "url": string,
    "db_name": string,
    "password": string
}
```

## Authorization methods

### NONE

This method is used to allow free access to all users. Everyone can generate a session token without restrictions, which can the be used to retrieve data from the data source.

### TOKEN

This method retricts access to the data source by requireing an API key, provided as a Bearer token, when generating a session token. Valid API keys are stored in a Postgres database, allowing other services to manage these keys.

To use the `TOKEN` authorization method, a table named `API_Key` must be created in the Postgres database. This can be done using the following command:
```sql
CREATE TABLE IF NOT EXISTS API_Key (
    key varchar PRIMARY KEY, 
    user varchar
);
```

This table is created automatialy on startup, if it does not already exist.
During authentication, the provided token is compared to all key fields within the `API_Key` table. If a match is found, access is granted; otherwise, unauthorized access is denied.

### Specifying the postgres connection

When a database is needed, please provide a JSON formatted dictionary using the following properties in the `postgres_connection` field in the `ERI Settings` section:

```JSON
{
    "username": string,
    "password": string,
    "url": string,
    "database_name": string
}
```
