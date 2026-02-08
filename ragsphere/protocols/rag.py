from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Union,
    Protocol,
    List,
    Callable,
    ClassVar,
    Optional,
    TypeVar,
)

from pydantic import ConfigDict, Field, model_validator

from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from configparser import ConfigParser

from utils.llm_client import LLMClient
from utils.arango_client import ArangoDBClient

from protocols.indexer import BaseIndexer
from protocols.retriever import BaseRetriever


class BaseRAG(ABC):
    @abstractmethod
    def __init__(
            self, 
            documents: Optional[str],
            graph_db: Optional[Union[str, ArangoDBClient]],
            vector_db: Optional[Union[str, Elasticsearch]],
            indexer: Optional[Union[str, BaseIndexer]],
            retriever: Optional[Union[str, BaseRetriever]],
            llm_index: Optional[LLMClient],
            llm_query: Optional[LLMClient],
            emb_model: Optional[Union[str, SentenceTransformer]]
    ) -> None:
        """Initialize with documents, retriever, and LLM"""
        pass

    @abstractmethod
    def index(self) -> None:
        """Indexing Phase"""
        pass

    @abstractmethod
    def query(
            self, 
            prompt: Optional[str], 
            messages: Optional[List[Dict[str,str]]]
    ) -> str:
        """Query the RAG pipeline using a question or message history"""
        pass

"""
    @abstractmethod
    def get_graph(self) -> Any:
        "Return the internal knowledge graph object (e.g. for visualization)"
        pass
"""