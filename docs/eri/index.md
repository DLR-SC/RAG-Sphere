# External Retrieval Interface (ERI)

## About

The ERI acts as an interface, transforming a data source into an accessible storage for retrieval and other llm adjacent processes. It serves as a provider of helpful information to a given query.
[Published in 2025 by Hecking, Sommer, and Felderer](https://ieeexplore.ieee.org/document/11014986), this standard enables decentralized data storage, allowing external data to be integrated into AI workflows.
To use this service, the ERI-Standard defines methods for retrieving data from the source. These can be implemented in other workflows or integrated directly into LLM processes, as done by [AI Studio](http://mindworkai.org/).

Within this library, an ERI-Server is implemented, enabling users to configure and select specific retrieval algorithms, which are then accessible through an API.

## The ERI-Standard

The ERI-Standard defines various requests for server-client communication. The full documentation and specification are available in the [published paper](https://ieeexplore.ieee.org/document/11014986) and in the [official server implementation repository on GitHub](https://github.com/MindWorkAI/ERI).

For authentification purpose, users can fetch available methods using the `/auth/methods` path. These can the be used to retrieve a session token when fulfilling authentification at `/auth`.
The provided ERI-Server implementation allows for either `NONE` or `TOKEN` authentification. `NONE` provides free access to session tokens for all users, while `TOKEN` compares incoming Bearer authentication with a database of valid API keys.

To fetch general information about the provided data, the `/datasource` endpoint provides a set name and description of the source.

Information about available retrieval algorithms can be accessed under the `/retrieval/info` endpoint. Here, a short description of the processes and available parameters is provided. These methods can then be used by providing a query to the `/retrieval` endpoint. This executes the selected algorithm internally, returning the selected data to the user.

# Starting the ERI-Server

To start the ERI-Server, the following command can be used, executed in the raglib subdirectory: `uvicorn eri:app`

To configure the ERI-Server, read the [configuration documentation](config.md).
