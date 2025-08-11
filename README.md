# RAGlib Library of RAG algorithms

RAGlib provides a high-level implementation of most common RAG algorithms independently from the database backend.

![overview](docs/illustrations/rag_lib.png)


## 🔧 Getting Started

To preview the documentation locally:

1. **Install the required dependencies listed in 'requirements.txt' .**

```py
pip install -r requirements.txt
```

You can install the minimal requirements for the documentation page using:

```py
pip install mkdocs mkdocs-material mkdocs-jupyter
```

2. **Start the development server:**

```py
mkdocs serve
```

3. **Open your browser and navigate to:** [http://127.0.0.1:8000](http://127.0.0.1:8000)

   The documentation will automatically reload as you edit the files

## 🔧 Build the Documentation (Optional)

To build the static site for deployment:

```py
mkdocs build
```

The site will be generated in the `site/` directory.

---

## 🚀 Quickstart Guide
+ Check out the [Notebook](/raglib/pipeline-test.ipynb)
+ See the slides for more information (RAGLIB.pptx)
  

## Provided retrieval implementations

### RAG

A naive rag implementation. All files are read and their content is split into chunks, preserving chapters where possible. Their embeddings are then stored into an Elasticsearch database, which will be queried for every user prompt.

### GRAPH RAG

An implementation inspired by [Graph RAG by Microsoft](https://arxiv.org/abs/2404.16130). The data is read and transformed into a knowledge graph, stored in ArangoDB. The resulting nodes are then grouped by their topic and summarized. These summarizations will then by used during query time to find relevant information, using a llm to judge the importance of the information.

This kind of initialization takes very long, but might be worth it, as following querys are not matched by text similiarity but by the topic they reside in. The generated knowledge graph is shared between Graph Rag, Graph Rag Rag and Garag. When using this implementation, keep in mind that a longer retrieval time is expected.

### NAIVE GRAPH RAG

An implementation reducing the query time of the Graph Rag implementation. Instead of an llm judging the importance of the information, vector similiarity is used to search for important communities. The information summaries of the communities is then returned to the user. Therefor this approach can be seen as a naive rag approach on community summaries. While this implementation reduces retrieval time compared to Graph RAG, precision on non global questions is reduced.

### GARAG

An implementation reducing the halucination of the filtered information. Important communities are first found, using the Graph Rag Rag approach. Then the original document contents are ranked by influence on these summaries and the top results are returned to the user. Therefor this approach can be seen as Graph-Assisted RAG (or GARAG). It is recommended to use this method, as it combines a very fast retrieval time with good precision. 


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
