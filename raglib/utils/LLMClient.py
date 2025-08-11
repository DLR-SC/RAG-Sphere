from os import system
from langchain_ollama import OllamaLLM
from requests import post, exceptions
from pathlib import Path
import json
from typing import (
    Any,
    Literal,
    Optional,
    Union,
)

class LLMClient:

    def __init__(self, type: str = "ollama",url : str = "http://localhost:11434", model_name = "llama3.2:latest", *, debug_name : str = None, api_key : str = None, \
        system_prompt : str = None, answer_format : dict = None):
        """
        Initializes a LLM model.
        
        Parameters:
        - url (str) : The base url to the LLM api (defualt: "http://localhost:11434")
        Keyword Arguments:
        - model_name (str) : The name of the model in use (default: "llama3.2:latest")
        - debug_name (str) : A name printed in addition to the debug messages (default: None)
        - api_key (str) : The api key to be used for this llm instance. Can also be specified during request (default: None)
        - system_prompt (str) : The system prompt to be used for generation (default: None)
        - answer_format (dict) : The required format of the generated answer (default: None)
        """

        # Check provided values
        if not model_name: raise ValueError("model_name is required when communicating with an Ollama server")

        # The url to request Llama.CPP data from
        self.url = (url if url else "http://localhost:11434") + "/api/generate" 
        
        # The system prompt
        self.system_prompt = system_prompt
        # The answer format
        self.answer_format = answer_format
        # The name of the LLM
        self.debug_name = debug_name
        self.model_name = model_name
        # The api key
        self.api_key = api_key if api_key else None

    def send_prompt(self, user_prompt : str, *, system_prompt : str = None, answer_format : dict = None, api_key : str = None, debug : bool = False) -> str:
        """
        Sends a prompt to the Ollama server and returns the answer.

        Parameters:
        - user_prompt (str) : The user prompt to be used for generation
        - system_prompt (str) : The system prompt to be used for generation. If empty, uses preset prompt (default: None)
        - answer_format (dict) : The required format of the generated answer (default: None)
        - api_key (str) : The api_key to be used during the request. If empty, uses stored api key (default: None)
        - debug (bool) : If enabled, any request and response will be printed to console (default: False)

        Returns:
        The answer given by the LLM
        """
        # Get values
        system_prompt = system_prompt or self.system_prompt
        answer_format = answer_format or self.answer_format
        api_key = api_key or self.api_key

        # Configure request headers
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        
        # Data payload to be sent in the request
        data = {
            "prompt": user_prompt,
            "model": self.model_name,
            "stream": False,
            "options": {
                "num_ctx": 8096,
                "temperature": 0.1
            }
        }
        if system_prompt:
            data["system"] = system_prompt
        if answer_format:
            data["format"] = answer_format
        
        # Debug print
        if debug:
            if system_prompt:
                print(f"SYSTEM: {system_prompt}\n-------")
            if answer_format:
                print(f"FORMAT: {str(answer_format)}\n-------")
            print(f"USER: {user_prompt}")
        
        # Request the response from the Ollama server
        response = post(self.url, json=data, headers=headers)
        
        # Check response
        if not response.ok:
            raise ValueError(f"Can't connect to Ollama-API on the url: {self.complete_url}\nReason: {response.reason} - Text: {response.text}")

        # Convert the content of the response into a dict and read the value
        try:
            response_content = json.loads(response.content)["response"].strip()
        except KeyError:
            if debug: print(f"{self.debug_name} raised error on completion:\n{data}\nResponse: {response.content}")
            return self.send_ollama_prompt(user_prompt, api_key = api_key, debug = debug, image_data = image_data)
        except json.decoder.JSONDecodeError:
            print(f"{self.debug_name} raised error on completion:\n{data}\nResponse: {response.content}")
            return self.send_ollama_prompt(user_prompt, api_key = api_key, debug = debug, image_data = image_data)
        
        # Debug print
        if debug: 
            print(f"-------\n{self.debug_name or 'OLLAMA'}: {response_content}")

        # Return the content of the provided response
        return response_content
