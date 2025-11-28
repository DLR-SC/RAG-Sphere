from typing import (
    Optional
)
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from traceback import format_exc
from threading import Lock
from pathlib import Path
from uuid import uuid4
from tqdm import tqdm

import logging
logger = logging.getLogger(__name__)

from models.enums import (
    IndexerType,
    DatabaseType
)

from protocols.indexer import (
    BaseIndexerConfig
)

from utils.arango_client import ArangoDBClient
from utils.file_parsers.docxParser import parse_docx
from utils.file_parsers.pdfParser import parse_pdf
from utils.file_parsers.txtParser import parse_txt
from utils.file_parsers.RAGSplit import split
from utils.file_parsers.zipExtractor import extracted_zip

_LOCK = Lock() # Locks the data insertion parts to run singlethreaded
_FILE_PARSERS = { # A list of file parsers of specific filetypes
    ".docx": parse_docx,
    ".md": parse_txt,
    ".pdf": parse_pdf,
    ".txt": parse_txt,
}

def _load_file(
        config: BaseIndexerConfig,
        file_path : Path, 
        arango_client : Optional[ArangoDBClient], 
        elastic_tuple : tuple,
        max_chunk_size: int
) -> None:
    """
    Loads a specific file / folder into ArangoDB or ElasticSearch

    Paramterse:
    - file_path (Path): the path to the file / folder
    - arango_client (ArangoDBClient): the ArangoDBClient used to insert the data into
    - elastic ((Elasticsearch, SentenceTransformer, rag_index_name)): The ElasticSearch setup to load data into
    """
    if file_path.name.startswith("~$"):
        return # File is temporary file, ignore it!
    
    if file_path.is_dir():
        # File is folder, load the content recursively
        for path in file_path.iterdir():
            _load_file(path, arango_client, elastic_tuple)

    elif file_path.suffix.lower() == ".zip":
        # File is zip file, extract it in temporary folder
        with extracted_zip(file_path) as folder:
            # Load folder content recursively
            for path in folder.iterdir():
                _load_file(path, arango_client, elastic_tuple)
    
    elif file_path.suffix.lower() in _FILE_PARSERS:
        # File can be read using the _FILE_PARSERS

        # Check for the file already existing in the ArangoDB
        if arango_client:
            if not arango_client.get_aql("FOR v IN File FILTER v.file_path == '{}' LIMIT 1 RETURN v"\
                .format(str(file_path.absolute()).replace("\\", "\\\\"))).empty():
                # Skip file
                logger.info(f"({file_path}) File already present in ArangoDB. Content gets skipped!")
                return

        try:
            # Try to read the data
            data = _FILE_PARSERS[file_path.suffix.lower()](file_path)
            # Try to split the data into segments -> Hier chunk size und chunk overlap als argument
            data = split(data=data, max_chunk_size=max_chunk_size)
        except:
            # Error whilst reading or splitting file content!
            logger.error(f"({file_path}) An error ocurred whilst reading a file: {format_exc()}")

        for text_chunk in data:
            # Load data into ArangoDB
            if arango_client:
                with _LOCK:
                    # Values of the node to be inserted
                    fields = {
                        "content": text_chunk[b'Content'],
                        "document": {
                            file_path.name: 1
                        },
                        "source": {
                            file_path.name + " " + text_chunk[b'PageHint']: 1
                        },
                        "label": file_path.name + " - " + text_chunk[b'h1'].replace("*", "") if text_chunk[b'h1'] else file_path.name,
                        "weight": 1,
                        "file_path": str(file_path.absolute()),
                        "is_graph": False
                    }
                    node = arango_client.add_vertex("File", fields)

                    # Add a reflective source reference
                    fields = {
                        "_key": node["_key"],
                        "source_ref": {
                            node["_key"]: 1,
                            "_total": 1
                        }
                    }
                    arango_client.update_vertex("File", fields)
            
            # Load data into ElasticDB
            if elastic_tuple:
                elastic_client, embedding_model, index_name = elastic_tuple
                # Load embedding for text content
                embedding = embedding_model.encode(text_chunk[b'Content'], show_progress_bar = False)

                with _LOCK:
                    # Values used in the ElasticDB
                    embedded = {
                        "content_vector": embedding,
                        "content": text_chunk[b'Content'],
                        "document": {
                            file_path.name : 1,
                        }.__repr__(),
                        "source": {
                            file_path.name + " " + text_chunk[b'PageHint']: 1
                        }.__repr__()
                    }
                    elastic_client.index(index = index_name, id = uuid4(), document = embedded)

    else:
        # File is of unsupported type
        logger.error(f"({file_path}) {file_path.suffix.lower()} type files are not yet supported!")

def load_data(
        config_parser : ConfigParser, 
        config: BaseIndexerConfig,
        documents: str,
        elastic_tuple : tuple,
        arango_client : Optional[ArangoDBClient]
) -> None:
    """
    Loads the provided data files into ArangoDB (further processing) and in Elasticsearch (naive rag).

    Parameters:
    config_parser (ConfigParser): The config file containing the setting of the loader
    arango_client (ArangoDBClient): The ArangoDBClient to load the data into. Might be None
    elastic ((Elasticsearch, SentenceTransformer, rag_index_name)): The setup used to load data into an Elasticsearch database
    """
    # Read config values
    if config:
        config=config
    if documents:
        data_path = Path(documents)
    else:
        data_path = Path(config_parser.get("general", "data_dir"))
    parallel_limit = int(config_parser.get("general", "parallel_limit").strip()) #in dataclass config

    # Setup arangodb enviromnent
    if arango_client and config.name!=IndexerType.VECTOR:
        arango_client.add_vertex_index("File", {'type': 'persistent', 'fields': ['file_path'], 'unique': False})

    # Setup elastic enviromnent
    if elastic_tuple:
        elastic_client, _, index_name = elastic_tuple

        elastic_mappings = {
            "properties": {
                "content_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": "true",
                    "similarity": "l2_norm"
                },
                "content": {"type": "text"},
                "document": {"type": "text"},
                "source": {"type": "text"}
            }
        }
        elastic_client.options(ignore_status = [400]).indices.create(index = index_name, mappings = elastic_mappings)

    max_chunk_size = config.max_chunk_size
    # Load all files in the path
    paths = list(data_path.iterdir())
    with tqdm(total = len(paths), desc = "Loading data from files") as pbar:
        with ThreadPoolExecutor(max_workers = parallel_limit) as executor:
            for path in paths:
                executor.submit(lambda args: (_load_file(*args), pbar.update()), [config, path, arango_client, elastic_tuple, max_chunk_size])