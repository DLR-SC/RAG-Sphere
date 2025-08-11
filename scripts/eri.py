from fastapi import FastAPI, Header, Request
from configparser import ConfigParser
from typing import Annotated, List
from uuid import uuid4
from re import search

from raglib.eri_components.components import AuthorizationMethods, AllowedTypes, AuthHeader, AuthResponse, RetrievalRequest, RetrievalAnswer
from raglib.graphrag.query.generation_api import GenerationAPI

from raglib.utils.DatabaseConnection import DatabaseConnection

# Initialisation:

config = ConfigParser()
config.read("resources/config.ini")

api = GenerationAPI(config)
db = DatabaseConnection(config)

db.init_tables()

# check for a ssl certificate:
if (cert := config.get("security", "ssl_cert_path").strip()) and (key := config.get("security", "ssl_key_path").strip()):
    app = FastAPI(ssl_keyfile = key, ssl_certfile = cert)
else:
    app = FastAPI()

retrieval_process_methods = {
  "GRAPH_RAG#892743": lambda prompt, depth, max_matches: api.generate_graph_rag_answer(prompt, max_matches, community_degree = depth),
  "NAIVE_GRAPH_RAG#912378": lambda prompt, depth, max_matches: api.generate_graph_rag_rag_answer(prompt, max_matches),
  "RAG#162478": lambda prompt, depth, max_matches: api.generate_rag_answer(prompt, max_matches),
  "GARAG#783493": lambda prompt, depth, max_matches: api.generate_garag_answer(prompt, max_matches)
}

# load the ERI specification for the get responses:
with open("src/eri_components/specification.json", "r") as spec_file:
    responses = eval(spec_file.read())

global counter
counter = 0

def check_if_valid():
    """
    Checks the expiration date of all tokens every 50th call.
    """
    global counter
    counter += 1
    if(counter == 50):
        counter = 0
        db.remove_expired_tokens()

@app.get("/auth/methods", status_code = 200)
def get_auth_methods():
    """
    [Called by FastAPI]
    Returns the /auth/methods part of the ERI specification (eri_components/specification.json).
    """
    # respond with the requested part of the specification:
    return responses["auth/methods"]

@app.get("/dataSource", status_code = 200)
def get_data_source(token_header: Annotated[AuthHeader, Header()], request: Request):
    """
    [Called by FastAPI]
    Returns the /dataSource part of the ERI specification (eri_components/specification.json)
    if a valid token is supplied (in the header token).
    """
    # check if the token is valid and then return the requested part of the specification:
    check_if_valid()
    if(not db.check_token(token_header.token)): return {"Error": "Invalid Token"}
    return responses["dataSource"]

@app.get("/embedding/info", status_code = 200)
def get_embedding_info(token_header: Annotated[AuthHeader, Header()]):
    """
    [Called by FastAPI]
    Returns the /embedding/info part of the ERI specification (eri_components/specification.json)
    if a valid token is supplied (in the header token).
    """
    # check if the token is valid and then return the requested part of the specification:
    check_if_valid()
    if(not db.check_token(token_header.token)): return {"Error": "Invalid Token"}
    return responses["embedding/info"]

@app.get("/retrieval/info", status_code = 200)
def get_retrieval_info(token_header: Annotated[AuthHeader, Header()]):
    """
    [Called by FastAPI]
    Returns the /retrieval/info part of the ERI specification (eri_components/specification.json)
    if a valid token is supplied (in the header token).
    """
    # check if the token is valid and then return the requested part of the specification:
    check_if_valid()
    if(not db.check_token(token_header.token)): return {"Error": "Invalid Token"}
    return responses["retrieval/info"]

@app.get("/security/requirements", status_code = 200)
def get_security_requirements(token_header: Annotated[AuthHeader, Header()]):
    """
    [Called by FastAPI]
    Returns the /security/requirements part of the ERI specification (eri_components/specification.json)
    if a valid token is supplied (in the header token).
    """
    # check if the token is valid and then return the requested part of the specification:
    check_if_valid()
    if(not db.check_token(token_header.token)): return {"Error": "Invalid Token"}
    return responses["security/requirements"]

@app.post("/auth")
def authenticate(authMethod: AuthorizationMethods, request : Request) -> AuthResponse:
    """
    [Called by FastAPI]
    Authenticates the client by validating the selected authentication method and returning
    a token that can be used for all other API calls.
    Returns an AuthResponse (eri_components/components.py)
    """
    headers = request.headers
    # create response after ERI format:
    response = {"success": False, "token": "", "message": ""}
    match(authMethod):

        case AuthorizationMethods.NONE:
            # create token and add it to the db:
            session_token = str(uuid4())
            if not db.add_none_token(session_token):
                response["message"] = "Could not add token!"
                return AuthResponse(**response)
            # respond with the token:
            response["success"] = True
            response["token"] = session_token
            return AuthResponse(**response)

        case AuthorizationMethods.TOKEN:
            # extract token from header and checks the format (Bearer token):
            token = search(r'(?<= )[^ ]*', headers.get("authorization")).group()
            auth_header = headers.get("authorization")
            if(not auth_header or not auth_header.startswith("Bearer")):
                response["message"] = "Invalid authentication!"
                return AuthResponse(**response)
            if(token):
                # create token and add it to the db:
                session_token = str(uuid4())
                if(db.add_api_key_token(session_token, token)):
                    response["success"] = True
                    response["token"] = session_token
                else:
                    response["message"] = "Invalid token!"
            else:
                response["message"] = "Invalid token!"
            return AuthResponse(**response)

@app.post("/retrieval")
def retrieve(retrieval_request: RetrievalRequest, auth_header: Annotated[AuthHeader, Header()]) -> List[RetrievalAnswer]:
    """
    [Called by FastAPI]
    Retrieves data requested by the RetrievalRequest after authenticating the token.
    Returns a RetrievalAnswer (eri_components/components.py)
    """
    token = auth_header.token
    # create answer after the ERI format
    answer = {
        "name": "Knowledge Graph",
        "category": "extracted data from multiple different files (sources)",
        "path": "",
        "type": AllowedTypes.NONE,
        "matchedContent":  "",
        "surroundingContent": [],
        "links": []
    }

    try:          
        # check if the type of given content is allowed:
        if(retrieval_request.latestUserPromptType != AllowedTypes.TEXT):
            answer["matchedContent"] = "Invalid Prompt Type!"
            return [RetrievalAnswer(**answer)]

        # check if methods needs parameters (and if they are found):
        index = sum([index for (index, information) in enumerate(responses["retrieval/info"]) if information["id"] == retrieval_request.retrievalProcessId])
        if responses["retrieval/info"][index].get("parametersDescription"):
            if(not retrieval_request.parameters and retrieval_request.parameters["depth"] not in range(1,8)):
                answer["matchedContent"] = "Invalid depth!"
                return [RetrievalAnswer(**answer)]

        # check date:
        db.remove_expired_tokens()

        # check authorized methods (if not authorized, return):
        allowed_methods = db.get_allowed_methods(token)
        if(not allowed_methods):
            answer["matchedContent"] = "Unauthorized Access!"
            return [RetrievalAnswer(**answer)]
        
        # extract used RAG method per retrievalProcessId:
        rag_method = retrieval_process_methods[retrieval_request.retrievalProcessId] if retrieval_request.retrievalProcessId else retrieval_process_methods[config.get("general", "default_rag_method")]
        # extract method arguments:
        prompt = retrieval_request.latestUserPrompt
        depth = retrieval_request.parameters["depth"] if retrieval_request.parameters else config.get("general", "default_depth")
        # call method and save results:
        results = rag_method(prompt, depth, retrieval_request.maxMatches)

        # convert results into a list of RetrievalAnswers (ERI format):
        answer["type"] = AllowedTypes.TEXT
        answers = []
        for result in results:
            answer["matchedContent"] = result["content"]
            answer["name"] = str(result["source"])
            answer["path"] = result["document"]
            answers.append(RetrievalAnswer(**answer))
        if(len(answers) == 0):
            return [RetrievalAnswer(**answer)]
        return answers

    except Exception as error:
        answer["matchedContent"] = str(error)
        return [RetrievalAnswer(**answer)]
