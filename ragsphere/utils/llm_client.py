from typing import (
  Any,
  Callable,
  Dict,
  List,
  Literal,
  Mapping,
  Optional,
  Sequence,
  Type,
  TypeVar,
  Union,
  overload,
)

from ollama import Client
from openai import OpenAI

import logging
logger = logging.getLogger(__name__)

import requests
import json
from hashlib import sha256
from os import PathLike
from pathlib import Path
from pydantic.json_schema import JsonSchemaValue

T = TypeVar('T')

class LLMClient:
    provider: str
    api_key: str
    base_url: str
    model_name: str
    project: str
    options: Dict[str, Any]
    chat_history: List[Dict[str, str]]

    def __init__(
        self, 
        provider: Optional[str] = 'ollama', 
        base_url: Optional[str] = None, 
        api_key: Optional[str] = None,  
        model_name: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:    
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.options = options

        match provider:
            case 'openai':
                self.client = OpenAI(
                    base_url=base_url,
                    api_key=api_key
                )
            case 'ollama':
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                self.client = Client(
                    host=base_url,
                    headers=headers
                )
            case _:
                raise ValueError(
                    f"Unsupported API provider '{provider}'. Only 'openai'-compatible and 'ollama'-compatible APIs are supported."
                )
           
    def prepare_chat_history(
          self, 
          prompt: str, 
          messages: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]] | None:
        """
        Appends a system message and a new user prompt to the chat history.

        Args:
            - prompt (str): The new message from the user to append.
            - messages (List[Dict[str, str]]): The chat history

        Returns:
            - List[Dict[str, str]]: The updated chat history.
        """
        if messages:
           messages.append({'role': 'user', 'content': prompt})
           return messages
        
        if self.chat_history:
            self.chat_history.append({'role': 'user', 'content': prompt})
        else:
            self.chat_history = self.create_chat(user_prompt=prompt)

    @staticmethod
    def create_chat(
        system_prompt: Optional[str], 
        user_prompt: Optional[str]
    ) -> List[Dict[str, str]]:
        """
        Convenience method for forming a simple list with chat dicts

        Args:
            - system_prompt (str): Input describing the system's role
            - user_prompt (str): Input describing the user's request

        Returns:
            List[Dict[str, str]]: List with two entries formed using the system input and the user input
        """
        if not system_prompt:
            chat = [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        else:
            chat = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        return chat
    
    def generate(
        self,
        new_model: Optional[str] = None,
        prompt: Optional[str] = None,
        suffix: Optional[str] = None,
        *,
        system: Optional[str] = None,
        template: Optional[str] = None,
        stream: bool = False,
        think: Optional[bool] = None,
        raw: Optional[bool] = None,
        format: Optional[Union[dict, str]] = None, #ToDo see here: https://github.com/openai/openai-python/blob/main/src/openai/resources/chat/completions/completions.py#L1045
        images: Optional[Sequence[str | bytes | Path]] = None,
        new_options: Optional[dict] = None,
        keep_alive: Optional[float | str] = None,
        **kwargs
    ) -> str:
        """
        Args:
            options:
                - see here for openai https://github.com/openai/openai-python/blob/main/src/openai/resources/chat/completions/completions.py#L1045
                - see here for ollama https://github.com/ollama/ollama-python/blob/main/ollama/_types.py#L104
        
        Create a response using the requested model.

        Raises `RequestError` if a model is not provided.

        Raises `ResponseError` if the request could not be fulfilled.

        Returns `GenerateResponse` if `stream` is `False`, otherwise returns a `GenerateResponse` generator.
        """
        if new_options:
            options = new_options
        else:
            options = self.options

        if new_model:
            model = new_model
        else:
            model = self.model_name

        if self.provider=='ollama':
            if options is None:
                options = {}

            r = self.client.generate(
                model=model,
                prompt=prompt,
                suffix=suffix,
                system=system,
                template=template,
                stream=stream,
                raw=raw,
                format=format,
                options=options,
                keep_alive=keep_alive,
                **kwargs
                )
            return r['response']
        
        elif self.provider=='openai':
            chat = self.create_chat(system_prompt=system, user_prompt=prompt)

            if format is not None:
                logger.warning("JSon Formats are not yet supported for openai providers. This method might return unexpected results!")

            if options is None:
                options = {}

            # format only works for ollama
            r = self.client.chat.completions.create(
                model=model,
				messages=chat,
				stream=stream,
				**options,
				**kwargs
			)
            return r.choices[0].message.content.strip()

    def chat(
        self,
        new_model: Optional[str] = None,
        messages: Optional[Sequence[Mapping[str, Any]]] = None,
        *,
        tools: Optional[Sequence[Mapping[str, Any] | Callable]] = None,
        stream: bool = False,
        think: Optional[bool] = None,
        format: Optional[Literal['', 'json'] | JsonSchemaValue] = None,
        new_options: Optional[dict] = None,
        keep_alive: Optional[Union[float, str]] = None,
        **kwargs
    ) -> str:
        """
        Create a chat response using the requested model.
        
        Args:
            tools:
                A JSON schema as a dict, an Ollama Tool or a Python Function.
                Python functions need to follow Google style docstrings to be converted to an Ollama Tool.
                For more information, see: https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings
            stream: Whether to stream the response.
            format: The format of the response. -> Helmholz API doesn't support format
            
            options: 
                - see here for openai https://github.com/openai/openai-python/blob/main/src/openai/resources/chat/completions/completions.py#L1045
                --> all parameters listed here:  https://platform.openai.com/docs/api-reference/chat/create
                - see here for ollama https://github.com/ollama/ollama-python/blob/main/ollama/_types.py#L104
        
        Raises `RequestError` if a model is not provided.

        Raises `ResponseError` if the request could not be fulfilled.

        Returns `ChatResponse` if `stream` is `False`, otherwise returns a `ChatResponse` generator.
        """
        if new_options:
            options = new_options
        else:
            options = self.options

        if new_model:
            model = new_model
        else:
            model = self.model_name

        if self.provider=='ollama':
            if options is None:
                options = {}

            r = self.client.chat(
                model=model,
                messages=messages,
                tools=tools,
                stream=stream,
                format=format,
                options=options,
                keep_alive=keep_alive
            )
            self.chat_history = [
                *messages,
                {'role': 'assistant', 'content': r['message']['content']},
            ]
            return r['message']['content']
        
        elif self.provider=='openai':
            if options is None:
                options = {}

            # format only works for ollama
            r = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools, #response_format={ "type": "json_schema", "json_schema": format.model_json_schema() , "strict": "True" } if format else None,
                stream=stream,
                **options,
                **kwargs
            )
            resp = r.choices[0].message.content.strip()
            self.chat_history = [
                *messages,
                {'role': 'assistant', 'content': resp},
            ]
            return resp

    def embed(
        self,
        new_model: Optional[str] = None,
        input: str | List[str] = '',
        truncate: Optional[bool] = None,
        dimensions: Optional[int] = None,
        encoding_format: Literal["float", "base64"] = None,
        new_options: Optional[dict] = None,
        keep_alive: Optional[float | str] = None,
    ) -> Sequence[Sequence[float]]:
        """
        Args:
            ollama: see https://github.com/ollama/ollama-python/blob/main/ollama/_client.py#L359
            openai: see https://github.com/openai/openai-python/blob/main/src/openai/resources/embeddings.py#L47

            input: Input text to embed, encoded as a array of tokens. 
                   Ollama and OpenAI allow for computing in batches -> input=[t1,t2,...]

            dimensions: The number of dimensions the resulting output embeddings should have. Only
                supported in `text-embedding-3` and later models.

            encoding_format: The format to return the embeddings in. Can be either `float` or
                [`base64`](https://pypi.org/project/pybase64/).
                   
            truncate: Truncate the input to the maximum token length.

        Returns:
            List[List[float]]
        """
        if new_options:
            options = new_options
        else:
            options = self.options

        if new_model:
            model = new_model
        else:
            model = self.model_name

        if self.provider=='ollama':
            if options is None:
                options = {}

            r = self.client.embed(
                model=model,
                input=input,
                truncate=truncate,
            	options=options,
                keep_alive=keep_alive
            )
            # r['embeddings'][0] non batch
            return r['embeddings']
        
        elif self.provider=='openai':
            if options is None:
                options = {}

            r = self.client.embeddings.create(
                input=input,
                model=model,
                encoding_format=encoding_format,
                **options
            )
            embedding_list = [obj.embedding for obj in r.data]
            return embedding_list

    def list(self, id_only: Optional[bool] = False):
      """
      Args:
            id_only: Only lists model names.
      Returns:
            A list of models, along with their descriptions.
      """
      if self.provider=='ollama':
          return self.client.list()
      
      elif self.provider=='openai':
          if id_only:
              headers = {'accept': 'application/json', 'Authorization': f'Bearer {self.api_key}'}
              response = requests.get(url = self.base_url+"/models", headers = headers)
              response = json.loads(response.text)

              ids = []
              for model in response['data']:
                  ids.append(model["id"])

              return print(*ids, sep="\n")
          
          return print(*self.client.models.list().data, sep="\n\n")

    def pull(
      self,
      model: str,
      *,
      insecure: bool = False,
      stream: bool = False,
    ):
      """ Ollama
      Raises `ResponseError` if the request could not be fulfilled.

      Returns `ProgressResponse` if `stream` is `False`, otherwise returns a `ProgressResponse` generator.
      """
      return self.client.pull(model=model, insecure=insecure, stream=stream)

    def push(
      self,
      model: str,
      *,
      insecure: bool = False,
      stream: bool = False,
    ):
      """ Ollama
      Raises `ResponseError` if the request could not be fulfilled.

      Returns `ProgressResponse` if `stream` is `False`, otherwise returns a `ProgressResponse` generator.
      """
      return self.client.push(model=model, insecure=insecure, stream=stream)

    def create(
      self,
      model: str,
      quantize: Optional[str] = None,
      from_: Optional[str] = None,
      files: Optional[Dict[str, str]] = None,
      adapters: Optional[Dict[str, str]] = None,
      template: Optional[str] = None,
      license: Optional[Union[str, List[str]]] = None,
      system: Optional[str] = None,
      parameters: Optional[Union[Mapping[str, Any]]] = None,
      messages: Optional[Sequence[Union[Mapping[str, Any]]]] = None,
      *,
      stream: bool = False,
    ):
      """ Ollama
      Raises `ResponseError` if the request could not be fulfilled.

      Returns `ProgressResponse` if `stream` is `False`, otherwise returns a `ProgressResponse` generator.
      """
      return self.client.create(
          model=model,
          stream=stream,
          quantize=quantize,
          from_=from_,
          files=files,
          adapters=adapters,
          license=license,
          template=template,
          system=system,
          parameters=parameters,
          messages=messages
        )

    def delete(self, model: str):
      return self.client.delete(model=model)

    def copy(self, source: str, destination: str):
      return self.client.copy(source=source, destination=destination)

    def show(self, model: str):
      return self.client.show(model=model)

    def ps(self):
      return self.client.ps()