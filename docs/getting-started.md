# Getting Started

## Requirements

| Name                | Installation                                                 | Purpose                                                                             |
| ------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Python ^3.10    | [Download](https://www.python.org/downloads/)                | The library is Python-based.                                                        |


## Install Dependencies

```python
pip3 install -r requirements.txt
```

## Set Up Your Workspace Variables

- `config.ini` contains the environment variables and settings required to run the pipeline. You can modify this file to change the settings for the pipeline.


## Quickstart Guide

If you just want to get started quickly, follow the steps provided here. When wanting to dive deeper, read [Initialization](#initialization) instead.

1. Download the repo onto a machine running docker
1. Configure the following settings in the [config file](resources/config.ini):
    * Point `[general] data_dir` to your data or move the data into a subfolder `/dir` of this folder
    * Change `[arangodb] url` to use the ip of your machine. A docker container will start the database on port `13401`
    * Change `[database] host` to the ip of your machine. A docker container will start a postgres db on port `13404`
    * Change `[elastic] url` to use the ip of your machine. A docker container will start elastic db on port `13403`
    * Change `[LLM] base_url` to an Ollama endpoint of your choice. This service will not be started when running this setup. For small datasets, you might use `https://ollama.nimbus.dlr.de/ollama` (the url of the [DLR-intern Ollama nimbus server](https://ollama.nimbus.dlr.de))
    * If needed, insert an api_key into `[LLM] static_api_key`. When using the nimbus server, this is required

2. Make sure, that the specified Ollama service runs the model `llama3.2:latest` (recommended) or switch to another model by changing `[LLM] model_name`
3. Provide file read and write rights to the database data directory, so the docker containers can create needed files. This can be done with `chmod a+rw db/* -R`
4. Run `./run.sh init` in the current directory. This starts the data initialization and may take multiple days. To check the status of the initialization, read the [inizialization log](resources/initialization.log), created on startup in the [resources folder](resources/)
5. Once the initialization is completed - check the [initialization log](resources/initialization.log) for a `>>> Initialization completed!` message at the end - shutdown any remaining docker resources by running `./run.sh down`


## Initialization with docker

Before running the Initialization, follow these steps to make sure, that everything is setup:

1. Make sure the data is in the right format:
    - This project requires a single folder as an input for the data
    - This folder may contain any number of files or folders
    - Each folder may include multiple subfolders, zip archives and documents
    - For a list of valid file types look at [valid file types](#valid-file-types)
1. Check the docker setup to follow your guidelines:
    - Check [all dockerfiles](docker/) to follow your local naming conventions
    - Check the ports in the [db compose file](docker/docker-compose_db.yml)
2. Check your Ollama provider:
    - Either access an already existing ollama service, or create a new one to be used for this project
    - Make sure, the Ollama instance is running
    - We recommend the model `llama3.2:latest`. See the [documentation](https://github.com/ollama/ollama/blob/main/docs/api.md#pull-a-model) for installation steps.
3. Check the config file:
    - Point `[general] data_dir` to your data or move the data into a subfolder `/dir` of this folder
    - Change `[arangodb] url` to the correct url. The default port is `13401`
    - Change `[elastic] url` to use the ip of your machine. The default port is `13403`
    - Change `[LLM] base_url` to the correct url of the provider. See [the LLM section](#llm) for more information
    - Change `[LLM] model_name` to the correct model name. For `Llama3.2` this defaults to `llama3.2:latest`
    - When using an Ollama instance with an API key access restriction, input your key into `[LLM] static_api_key`
4. Provide file read and write rights to the database data directory, so the docker containers can create needed files. This can be done with `chmod a+rw db/* -R`
5. Run the setup script:
    - Run `./run.sh init`. This script might take multiple days to complete. Just be patient
    - Any errors will be printed into the [initialization log file](resources/initialization.log)
    - After completion, run `./run.sh down` to remove any leftover docker resources

An in depth description of all values in the config file is provided in the section [Config.ini](#configini).

## Initialization without docker

Before running the Initialization, follow these steps to make sure, that everything is setup:

1. Make sure the data is in the right format:
    - This project requires a single folder as an input for the data
    - This folder may contain any number of files or folders
    - Each folder may include multiple subfolders, zip archives and documents
    - For a list of valid file types look at [valid file types](#valid-file-types)
1. Start database services:
    - Start an [ArangoDB Instance](https://arangodb.com/community-server/)
    - Start an [ElasticDB Instance](https://www.elastic.co/de/elasticsearch) 
1. Check your Ollama provider:
    - Either access an already existing ollama service, or create a new one to be used for this project
    - Make sure, the Ollama instance is running
    - We recommend the model `llama3.2:latest`. See the [documentation](https://github.com/ollama/ollama/blob/main/docs/api.md#pull-a-model) for installation steps.
1. Check the config file:
    - Point `[general] data_dir` to your data or move the data into a subfolder `/dir` of this folder
    - Change `[arangodb] url` to the correct url
    - Change `[arangodb] db_name` to a fitting name. This db will store the provided data in various formats
    - Change `[elastic] url` to use the ip of your machine
    - Change `[elastic] RAG_index_name & GARAG_index_name` to a fitting name. These indices will be used for RAG and GARAG retrieval
    - Change `[LLM] url` to the correct url of the provider. See [the LLM section](#llm) for more information
    - Change `[LLM] model_name` to the correct model name. For `Llama3.2` this defaults to `llama3.2:latest`
    - When using an Ollama instance with an API key access restriction, input your key into `[LLM] static_api_key`
1. Install the required python dependencies:
    - Setup a new conda environment with `python >= 3.10`
    - Install the dependencies, listed in [requirements.txt](requirements.txt)
1. Run the setup script:
    - Run `python Quickstart.py`
    - This script might take multiple days to complete. Just be patient
    - Any errors will be printed into the [initialization log file](resources/initialization.log)

An in depth description of all values in the config file is provided in the section [Config.ini](#configini).


## Provided retrieval implementations

### RAG

A naive rag implementation. All files are read and their content is split into chunks, preserving chapters where possible. Their embeddings are then stored into an Elasticsearch database, which will be queried for every user prompt.

### GRAPH RAG

An implementation inspired by Graph RAG by Microsoft. The data is read and transformed into a knowledge graph, stored in ArangoDB. The resulting nodes are then grouped by their topic and summarized resulting in thematic subgraphs. During a query, these thematic summaries and the user prompt are then passed to a LLM, which generates partial answers on the information provided and a confidence value, stating the helpfulness of the provided answer. These partial answers are then ranked by their confidence and the best results are returned to the user.

This algorithm takes an extra argument, the community level to search on. There, a level of 0 describes the usage of a single node, capturing the entire information corpus in a small description. Higher values yield more nodes, therefore providing a more precise description on multiple topics. The maximum level can only be inferred by a manual lookup in the GraphDB used. Higher values always also supply the descriptions of all nodes of lower community level. A value of 1 or 2 is advisable.

This kind of initialization takes very long, but might be worth it, as following querys are not matched by text similarity but by the topic they reside in. The generated knowledge graph is shared between Graph Rag, Graph Rag Rag, and Garag. When using this implementation, keep in mind that a longer retrieval time is expected.

### NAIVE GRAPH RAG

An implementation that reduces the query time of the Graph Rag implementation. Instead of generating partial answers using LLMs, community summaries are filtered through an embedding comparison in the Elasticsearch database. The information summaries of the most fitting communities are then returned to the user. Therefore, this approach can be seen as a naive RAG (Rapid Answer Generation) approach on community summaries. While this implementation reduces retrieval time compared to Graph Rag, precision on non-global questions is reduced.

### GARAG

An implementation that reduces the hallucination of the filtered information. Communities with fitting information are first found using an embedding comparison in the Elasticsearch database. The original sources (the raw data used to generate the knowledge graph) of these communities are then ranked by their influence on these summaries and the accuracy of the vector comparison of those with the user query. The top original sources are then returned to the user. Therefore, this approach can be seen as Graph-Assisted RAG (or GARAG). It returns the same kind of information that would be obtained from a normal RAG query on the original documents, using a complex, topic-based decision-making process, instead of a direct vector comparison. It is recommended to use this method, as it combines a very fast retrieval time with good precision.

## Config.ini

The config.ini file controlls the entire projekt. Each value is directly used by the programm. This is a list of all the values, their meaning and their default value.

The config file itself can be found [here](resources/config.ini). An example config file of a woring setup can be seen [here](resources/example_config.ini).


### general

General settings affecting core parts of the program
- **data_dir** (path): The path to the folder containing the data, that will be used for the chatbot. This value has to be set by the user, when running the script [KG_1_LoadData.py](KG_1_LoadData.py) during initialization. `Default: not set`
  
- **parallel_limit** (int): The maximum amount of threads running in parallel during the program. Also represents the maximum number of threads simoultaniously waiting for a response from a large language model. `Default: 8`
  
- **default_rag_method** (str): RAG method used if the RetrievalRequest does not specify one. Can be set to any [RetrievalMethodId](src/eri_components/specification.json).
`Default: "GARAG#783493"`

- **default_depth** (int): Default depth used if the RetrievalRequest does not specify one and the RAG method requires a depth parameter. `Default: 1`

### security
- **ssl_cert_path** (path): The path to the certification file for https encryption. When using http, leave this value empty. `Default: not set`
  
- **ssl_key_path** (path): The path to the key file for https encryption. When using http, leave this value empty. `Default: not set`

### arangodb

General settings to access the Arango database
- **username**  (str): The name of the user being used to manage the database. This user has to have read, write and collection and graph create access. `Default: not set`
  
- **password** (str): If set, this password will be used to register as the user on the ArangoDB. If `None`, the user will be asked to enter a password at the start of the program execution (Only works during initialization without docker). `Default: not set`
  
- **url** (url): The url that will be used to access the ArangoDB. `Default: not set`

### database

General settings to access the Postgres database

- **username** (str): Username for the database login. `Default: postgres`
- **password** (str): Username for the database login. `Default: root`
- **host** (hostname): Domain used for accessing the database. `Default: not set`
- **port** (int): Port used for accessing the database. `Default: not set`
- **database_name** (str): Name of the database. `Default: postgres`

### elastic

- **url** (url): The url used to store the index data at. `Default: not set`

### LLM (index/query)

Settings controlling the large language model used Settings controlling the large language model used by the program..

- **base_url** (str): The url used to communicate with the llm.
- **model_name** (str): The name of the model used when communicating with an Ollama server.
- **api_key** (str): When provided, this api key will be used for all Ollama llm requests.
- **options** (dict): llm configuration

## Valid file types

This is a list of al file types, recognised by [KG_1_LoadData.py](src/KG_1_LoadData.py):

  - pdf
  - docx
  - txt
  - md

Files not included during reading:

- Files starting with ~$...: These files are usually temporary files used, while the file is open and thus don't provide any information and are ignored.

All other file types raise a warning, which may be examined by the user afterwards in the created log file.

# Dive Deeper

- For more details about configuring the pipeline, see the [configuration documentation](config/overview.md).
- To learn more about Initialization, refer to the [Initialization documentation](config/index.md).
- Check out our [visualization guide](config/visualization_guide.md) for a more interactive experience in debugging and exploring the knowledge graph.