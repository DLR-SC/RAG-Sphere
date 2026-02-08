from fastapi import FastAPI, Header, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from configparser import ConfigParser
from typing import Annotated, List
from pathlib import Path
from uuid import uuid4
from re import search
import json

from eri_components.components import (
    AuthorizationMethods, 
    AllowedTypes, 
    AuthHeader,
    AuthResponse, 
    RetrievalRequest, 
    RetrievalAnswer, 
    ProviderType
)
from graphrag import (
    GARAGRetriever,
    GraphRAGRetriever,
    NaiveGraphRAGRetriever,
    NaiveRAGRetriever,
    VectorGRRetriever,
    HybridGRRetriever,
    Text2CypherRetriever
)
from models.retriever import (
    GARAGRetrieverConfig,
    GraphRAGRetrieverConfig,
    NaiveRAGRetrieverConfig,
    NaiveRAGRetrieverConfig,
    VectorGRRetrieverConfig,
    HybridGRRetrieverConfig,
    Text2CypherRetrieverConfig
)

from sentence_transformers import SentenceTransformer
from utils.arango_client import ArangoDBClient
from utils.postgres_client import PostgresDBClient
from elasticsearch import Elasticsearch
from utils.llm_client import LLMClient


# Read eri general config
config = ConfigParser()
config.read(Path(__file__).parent.parent / "resources" / "eri.ini")

# Get postgres connection entry, if present
postgres_connection = config.get("ERI_SETTINGS", "postgres_connection", fallback="NONE")
# Read authorization methods and check format
authorization_methods = json.loads(config.get("ERI_SETTINGS", "authorization_methods"))
if isinstance(authorization_methods, str):
    authorization_methods = [authorization_methods]
elif not (
        isinstance(authorization_methods, list) and 
        all(isinstance(method, str) for method in authorization_methods)
    ):
    raise ValueError("Expected a json string or a json array of strings in [ERI_SETTINGS] authorization_methods")
# Read allowed provider types
allowed_provider_type = config.get("ERI_SETTINGS", "allowed_provider_type").strip()
# Read the data source name and description
data_source_name = config.get("ERI_SETTINGS", "data_source_name").strip()
data_source_description = config.get("ERI_SETTINGS", "data_source_description").strip()
# Read TLS certificate and key file paths for https
cert = config.get("ERI_SETTINGS", "ssl_cert_path", fallback="").strip()
key = config.get("ERI_SETTINGS", "ssl_key_path", fallback="").strip()

# Information about retrieval information
## EXTEND SUPPORTED METHODS HERE
__RETRIEVAL_METHODS_INFO = {
    "GARAG": {
        "id": "GARAG",
        "name": "GARAG",
        "description": "An implementation reducing the halucination of the filtered information. Important communities are first found, using the Graph Rag Rag approach. Then the original document contents are ranked by influence on these summaries and the top results are returned to the user. Therefor this approach can be seen as Graph-Assisted RAG (or GARAG).",
        "link": "https://gitlab.dlr.de/sc/ivs-intern/vfchatbot",
        "parametersDescription": {
            "confidence_cutoff": "The confidence level, at which to stop returning hits. (float, 0 < confidence_cutoff < 1)"
        },
        "embeddings": []
    },
    "GraphRAG": {
        "id": "GraphRAG",
        "name": "Graph RAG",
        "description": "An implementation inspired by Graph RAG by Microsoft. The data is read and transformed into a knowledge graph, stored in ArangoDB. The resulting nodes are then grouped by their topic and summarized. These summarizations will then by used during query time to find relevant information, using a llm to judge the importance of the information.",
        "link": "https://gitlab.dlr.de/sc/ivs-intern/vfchatbot",
        "parametersDescription": {
            "confidence_cutoff": "The confidence level, at which to stop returning hits. (int, 0 < confidence_cutoff < 100)",
            "community_degree": "The number of layers the graph is searched through. (int, 0 < community_degree)"
        },
        "embeddings": []
    },
    "NaiveGraphRAG": {
        "id": "NaiveGraphRAG",
        "name": "Naive Graph RAG",
        "description": "An implementation, reducing the query time of the Graph RAG implementation. After the generation of topic summaries, those are than converted into vecors and stored into an ElasticSearch server. During query time, this server is then used to seach of appropiate information for specific queries.",
        "link": "https://gitlab.dlr.de/sc/ivs-intern/vfchatbot",
        "parametersDescription": {
            "confidence_cutoff": "The confidence level, at which to stop returning hits. (float, 0 < confidence_cutoff < 1)"
        },
        "embeddings": []
    },
    "NaiveRAG": {
        "id": "NaiveRAG",
        "name": "Naive RAG",
        "description": "The standard RAG implementation: All files are read and their content is split into chunks. These chunks are transformed into vectors and stored into an ElasticSearch database. This database is then used to search for helpful information.",
        "link": "https://gitlab.dlr.de/sc/ivs-intern/vfchatbot",
        "parametersDescription": {
            "confidence_cutoff": "The confidence level, at which to stop returning hits. (float, 0 < confidence_cutoff < 1)"
        },
        "embeddings": []
    },
    "VectorGR": {
        "id": "VectorGR",
        "name": "Vector GraphRAG",
        "description": "",
        "link": "",
        "parametersDescription": {
            "filters": "Filters for metadata pre-filtering. (Dictionary: str->Any)"
        },
        "embeddings": []
    },
    "HybridGR": {
        "id": "HybridGR",
        "name": "Hybrid GraphRAG",
        "description": "",
        "link": "",
        "parametersDescription": {},
        "embeddings": []
    },
    "Text2Cypher": {
        "id": "Text2Cypher",
        "name": "Text2Cypher",
        "description": "",
        "link": "",
        "parametersDescription": {},
        "embeddings": []
    }
}

# Other internal Constants
__SESSION_TOKENS_EXIRE_DURATION = timedelta(minutes=30)
__IMPLEMENTED_AUTHORITZATION_METHODS = {
    AuthorizationMethods.NONE,
    AuthorizationMethods.TOKEN
}
__AUTHORIZATION_METHODS_RESPONSES = {
    AuthorizationMethods.NONE: {
        "authMethod": "NONE",
        "authFieldMappings": []
    },
    AuthorizationMethods.TOKEN: {
        "authMethod": "TOKEN",
        "authFieldMappings": [
            {
                "authField": "TOKEN",
                "fieldName": "token"
            }
        ]
    }
}

# Convert config values into enum values
authorization_methods = [
    AuthorizationMethods(method) for method in authorization_methods
]
allowed_provider_type = ProviderType(allowed_provider_type)

# Check for valid authorization method
if any(method not in __IMPLEMENTED_AUTHORITZATION_METHODS for method in authorization_methods):
    raise ValueError(f"Unsupported authorization method detected! Please only use the following: {list(__IMPLEMENTED_AUTHORITZATION_METHODS).__repr__()}.")

# Build responses dict
responses = {
    "auth/methods": [
        __AUTHORIZATION_METHODS_RESPONSES[auth_method] for auth_method in authorization_methods
    ],
    "dataSource" : {
        "name": data_source_name,
        "description": data_source_description
    },
    "embedding/info": [],
    "retrieval/info": [
        __RETRIEVAL_METHODS_INFO[retrieval_id]
        for retrieval_id in config.sections()
        if retrieval_id in __RETRIEVAL_METHODS_INFO
    ],
    "security/requirements": {
        "allowedProviderType": allowed_provider_type
    }
}

# Create retrievers for all specified methods
## EXTEND SUPPORTED METHODS HERE
retrieval_methods = {}
if config.has_section("GARAG"):
    ret_config = json.loads(config.get("GARAG", "config", fallback="{}")) or {}
    emb_model = config.get("GARAG", "emb_model")
    elastic_db_url = config.get("GARAG", "elastic_db_url")
    arango_db = json.loads(config.get("GARAG", "arango_db")) or {}

    retrieval_methods["GARAG"] = GARAGRetriever(
        config=GARAGRetrieverConfig(
            top_k=ret_config.get("top_k", 1024),
            confidence_cutoff=ret_config.get("confidence_cutoff", 0.4),
            vector_db_index_name=ret_config["vector_db_index_name"]
        ),
        emb_model=SentenceTransformer(emb_model),
        vector_db=Elasticsearch(elastic_db_url),
        graph_db=ArangoDBClient(
            config=None,
            url=arango_db["url"],
            username=arango_db["username"],
            password=arango_db["password"],
            db_name=arango_db["db_name"],
            graph_name=arango_db["graph_name"]
        )
    )
if config.has_section("GraphRAG"):
    ret_config = json.loads(config.get("GraphRAG", "config", fallback="{}")) or {}
    llm = json.loads(config.get("GraphRAG", "llm")) or {}
    arango_db = json.loads(config.get("GraphRAG", "arango_db")) or {}

    retrieval_methods["GraphRAG"] = GraphRAGRetriever(
        config=GraphRAGRetrieverConfig(
            top_k=ret_config.get("top_k", 1024),
            community_degree=ret_config.get("community_degree", 1),
            confidence_cutoff=ret_config.get("confidence_cutoff", 40)
        ),
        llm=LLMClient(
            provider=llm["provider"],
            base_url=llm["base_url"],
            api_key=llm["api_key"],
            model_name=llm["model_name"],
            options=llm["options"]
        ),
        graph_db=ArangoDBClient(
            config=None,
            url=arango_db["url"],
            username=arango_db["username"],
            password=arango_db["password"],
            db_name=arango_db["db_name"],
            graph_name=arango_db["graph_name"]
        )
    )
if config.has_section("NaiveGraphRAG"):
    ret_config = json.loads(config.get("NaiveGraphRAG", "config", fallback="{}")) or {}
    emb_model = config.get("NaiveGraphRAG", "emb_model")
    elastic_db_url = config.get("NaiveGraphRAG", "elastic_db_url")

    retrieval_methods["NaiveGraphRAG"] = NaiveGraphRAGRetriever(
        config=NaiveRAGRetrieverConfig(
            top_k=ret_config.get("top_k", 1024),
            confidence_cutoff=ret_config.get("confidence_cutoff", 0.4),
            vector_db_index_name=ret_config["vector_db_index_name"]
        ),
        emb_model=SentenceTransformer(emb_model),
        vector_db=Elasticsearch(elastic_db_url)
    )
if config.has_section("NaiveRAG"):
    ret_config = json.loads(config.get("NaiveRAG", "config", fallback="{}")) or {}
    emb_model = config.get("NaiveRAG", "emb_model")
    elastic_db_url = config.get("NaiveRAG", "elastic_db_url")

    retrieval_methods["NaiveRAG"] = NaiveRAGRetriever(
        config=NaiveRAGRetrieverConfig(
            top_k=ret_config.get("top_k", 1024),
            confidence_cutoff=ret_config.get("confidence_cutoff", 0.4),
            vector_db_index_name=ret_config["vector_db_index_name"]
        ),
        emb_model=SentenceTransformer(emb_model),
        vector_db=Elasticsearch(elastic_db_url)
    )
if config.has_section("VectorGR"):
    ret_config = json.loads(config.get("VectorGR", "config", fallback="{}")) or {}
    emb_model = config.get("VectorGR", "emb_model")
    llm = json.loads(config.get("VectorGR", "llm")) or {}
    neo4j_db = json.loads(config.get("VectorGR", "neo4j_db")) or {}

    ret_config_parser = ConfigParser()
    ret_config_parser.read_dict({
        "neo4j": {
            "url": neo4j_db["url"],
            "db_name": neo4j_db["db_name"],
            "password": neo4j_db["password"]
        },
        "llm_query" : {
            "provider": llm["provider"],
            "base_url": llm["base_url"],
            "api_key": llm["api_key"],
            "model_name": llm["model_name"],
            "options": llm["options"]
        },
        "general" : {
            "default_embedding_model": emb_model
        }
    })

    retrieval_methods["VectorGR"] = VectorGRRetriever(
        config=VectorGRRetrieverConfig(
            top_k=ret_config.get("top_k", 5),
            v_index_name=ret_config["v_index_name"],
            return_properties=ret_config.get("return_properties") or None,
            filters=ret_config.get("filters") or None
        ),
        config_parser=ret_config_parser
    )
if config.has_section("HybridGR"):
    ret_config = json.loads(config.get("HybridGR", "config", fallback="{}")) or {}
    emb_model = config.get("HybridGR", "emb_model")
    llm = json.loads(config.get("HybridGR", "llm")) or {}
    neo4j_db = json.loads(config.get("HybridGR", "neo4j_db")) or {}

    ret_config_parser = ConfigParser()
    ret_config_parser.read_dict({
        "neo4j": {
            "url": neo4j_db["url"],
            "db_name": neo4j_db["db_name"],
            "password": neo4j_db["password"]
        },
        "llm_query" : {
            "provider": llm["provider"],
            "base_url": llm["base_url"],
            "api_key": llm["api_key"],
            "model_name": llm["model_name"],
            "options": llm["options"]
        },
        "general" : {
            "default_embedding_model": emb_model
        }
    })

    retrieval_methods["HybridGR"] = HybridGRRetriever(
        config=HybridGRRetrieverConfig(
            top_k=ret_config.get("top_k", 5),
            v_index_name=ret_config["v_index_name"],
            f_index_name=ret_config["f_index_name"],
            return_properties=ret_config.get("return_properties") or None
        ),
        config_parser=ret_config_parser
    )
if config.has_section("Text2Cypher"):
    ret_config = json.loads(config.get("Text2Cypher", "config", fallback="{}")) or {}
    llm = json.loads(config.get("Text2Cypher", "llm")) or {}
    neo4j_db = json.loads(config.get("Text2Cypher", "neo4j_db")) or {}

    ret_config_parser = ConfigParser()
    ret_config_parser.read_dict({
        "neo4j": {
            "url": neo4j_db["url"],
            "db_name": neo4j_db["db_name"],
            "password": neo4j_db["password"]
        },
        "llm_query" : {
            "provider": llm["provider"],
            "base_url": llm["base_url"],
            "api_key": llm["api_key"],
            "model_name": llm["model_name"],
            "options": llm["options"]
        }
    })

    retrieval_methods["Text2Cypher"] = Text2CypherRetriever(
        config=Text2CypherRetrieverConfig(
            examples=ret_config.get("examples") or None
        ),
        config_parser=ret_config_parser
    )

# Storage for session tokens
_session_tokens = []
# Database connection for token authentication
if AuthorizationMethods.TOKEN in authorization_methods:
    postgres_connection = json.loads(postgres_connection)
    _postgres_db = PostgresDBClient(
        config=None,
        username=postgres_connection["username"],
        password=postgres_connection["password"],
        url=postgres_connection["url"],
        database_name=postgres_connection["database_name"]
    )

    # Create used table, if not already present
    _postgres_db.cursor.execute("CREATE TABLE IF NOT EXISTS API_Key (key varchar PRIMARY KEY, user varchar);")
else:
    _postgres_db = None

# Check for a ssl certificate and create FastAPI app
if cert and key:
    app = FastAPI(ssl_keyfile = key, ssl_certfile = cert)
else:
    app = FastAPI()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://orbait.intra.dlr.de",  # your frontend domain
        "http://localhost:3000",       # (optional) local dev frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],               # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],               # allow all headers
)

## HTTP Methods
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers or {}
    )
    
@app.get("/auth/methods", status_code = 200)
def get_auth_methods():
    """
    [Called by FastAPI]
    Returns the /auth/methods part of the ERI specification (eri_components/specification.json).
    """
    # returns the requested part of the specification:
    return responses["auth/methods"]

@app.get("/dataSource", status_code = 200)
def get_data_source(token_header: Annotated[AuthHeader, Header()]):
    """
    [Called by FastAPI]
    Returns the /dataSource part of the ERI specification (eri_components/specification.json).
    """
    if not any(token == token_header.token for token, _ in _session_tokens):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW_Authenticate": "Bearer"}
        )

    # returns the requested part of the specification:
    return responses["dataSource"]

@app.get("/embedding/info", status_code = 200)
def get_embedding_info(token_header: Annotated[AuthHeader, Header()]):
    """
    [Called by FastAPI]
    Returns the /embedding/info part of the ERI specification (eri_components/specification.json).
    """
    if not any(token == token_header.token for token, _ in _session_tokens):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW_Authenticate": "Bearer"}
        )

    # returns the requested part of the specification:
    return responses["embedding/info"]

@app.get("/retrieval/info", status_code = 200)
def get_retrieval_info(token_header: Annotated[AuthHeader, Header()]):
    """
    [Called by FastAPI]
    Returns the /retrieval/info part of the ERI specification (eri_components/specification.json).
    """
    if not any(token == token_header.token for token, _ in _session_tokens):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW_Authenticate": "Bearer"}
        )

    # returns the requested part of the specification:
    return responses["retrieval/info"]

@app.get("/security/requirements", status_code = 200)
def get_security_requirements(token_header: Annotated[AuthHeader, Header()]):
    """
    [Called by FastAPI]
    Returns the /security/requirements part of the ERI specification (eri_components/specification.json).
    """
    if not any(token == token_header.token for token, _ in _session_tokens):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW_Authenticate": "Bearer"}
        )

    # returns the requested part of the specification:
    return responses["security/requirements"]

@app.post("/auth")
def authenticate(authMethod: AuthorizationMethods, request: Request) -> AuthResponse:
    """
    [Called by FastAPI]
    Authenticates the client by validating the selected authorization method and returning
    a token that can be used for all other API calls.
    Returns an AuthResponse (eri_components/components.py)
    """
    # Remove all expired tokens
    global _session_tokens
    _session_tokens = [
        (session_token, expiration_date) 
        for (session_token, expiration_date) in _session_tokens
        if datetime.now() > expiration_date
    ]

    # Create new session token
    match(authMethod):
        case AuthorizationMethods.NONE:
            session_token = str(uuid4())
            _session_tokens.append((session_token, datetime.now() + __SESSION_TOKENS_EXIRE_DURATION))

            return AuthResponse(
                success=True,
                token=session_token,
                message=""
            )
        case AuthorizationMethods.TOKEN:
            # Extract Bearer token
            if not (request.headers.get("authorization") or "").startswith("Bearer "):
                return AuthResponse(
                    success=False,
                    token="",
                    message="Bearer Token Authentication failed, invalid format!"
                )
            bearer_token = request.headers.get("authorization").removeprefix("Bearer ")
            
            # Check for token in db
            try:
                _postgres_db.cursor.execute(f"SELECT user FROM API_Key WHERE key = {bearer_token};")
                user = _postgres_db.cursor.fetchone()
                if user:
                    session_token = str(uuid4())
                    _session_tokens.append((session_token, datetime.now() + __SESSION_TOKENS_EXIRE_DURATION))
                    # Success
                    return AuthResponse(
                        success=True,
                        token=session_token,
                        message=""
                    )
                else:
                    # Invalid Token
                    return AuthResponse(
                        success=False,
                        token="",
                        message="Bearer Token Authentication failed, invalid token!"
                    )
            except Exception as error:
                # Error during Token check
                return AuthResponse(
                    success=False,
                    token="",
                    message=str(error)
                )

    return AuthResponse(success=False, token="", message="Unknown method of authorization!")

@app.post("/retrieval")
def retrieve(retrieval_request: RetrievalRequest, token_header: Annotated[AuthHeader, Header()]) -> List[RetrievalAnswer]:
    """
    [Called by FastAPI]
    Retrieves data requested by the RetrievalRequest after authenticating the token.
    Returns a RetrievalAnswer (eri_components/components.py)
    """
    # Check session token
    if not any(token == token_header.token for token, _ in _session_tokens):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW_Authenticate": "Bearer"}
        )
    
    # Check for valid prompt type
    if(retrieval_request.latestUserPromptType != AllowedTypes.TEXT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Prompt Type"
        )
    
    # Check retrieval process
    if retrieval_request.retrievalProcessId not in retrieval_methods:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown or unsupported retrieval process"
        )
    
    # Copy max matches to parameter dict
    if retrieval_request.parameters is None:
        retrieval_request.parameters = {"top_k": str(retrieval_request.maxMatches)}
    else:
        retrieval_request.parameters["top_k"] = str(retrieval_request.maxMatches)
    # Filter parameter dict for valid entries
    parameters = {
        key: json.loads(value)
        for key, value in retrieval_request.parameters.items()
        if key == "top_k" or key in __RETRIEVAL_METHODS_INFO[retrieval_request.retrievalProcessId]["parametersDescription"]
    }

    try:
        # Fetch retrieval result
        result = retrieval_methods[retrieval_request.retrievalProcessId].retrieve(
            prompt=str(retrieval_request.latestUserPrompt),
            **parameters
        )


        # If result is not in form List[RetrievalAnswer], the format has to be modified manually
        ## EXTEND SUPPORTED METHODS HERE
        if retrieval_request.retrievalProcessId in {"VectorGR", "HybridGR", "Text2Cypher"}:
            result = [
                RetrievalAnswer(
                    name="Knowledge Graph Retrieval",
                    category="Extracted data from multiple different sources",
                    path="",
                    type=AllowedTypes.TEXT,
                    matchedContent=match.content,   #match.__repr__(), match.content
                    surroundingContent=[],
                    links=[]
                ) for match in result["retriever_result"]
            ]

    except Exception as error:
        # Internal error
        print(str(error))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )

    print(result)
    return result
    
