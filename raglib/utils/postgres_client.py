from typing import (
    Optional,
    List
)

from urllib.parse import urlparse
from psycopg2 import connect
from datetime import datetime, timedelta
from uuid import uuid4
from configparser import ConfigParser

class PostgresDBClient:
    """
    Class for connecting to a Postgres Database
    """

    def __init__(self, 
        config : Optional[ConfigParser] = None,
        username : Optional[str] = None,
        password : Optional[str] = None,
        url : Optional[str] = None,
        database_name : Optional[str] = None
    ):
        username = username if username is not None else config.get("postgres", "username").strip()
        password = password if password is not None else config.get("postgres", "password").strip()
        url = urlparse(url if url is not None else config.get("postgres", "url").strip())
        database_name = database_name if database_name is not None else config.get("postgres", "database_name").strip()
        host = url.hostname or url.scheme or url.path or None
        port = url.port or (int(url.path) if url.path.isdecimal() else None)

        # open connection to postgres db
        self.connection = connect(
            user = username, 
            password = password, 
            host = host, 
            port = port, 
            database = database_name
        )
        self.cursor = self.connection.cursor()
    
    def close(self):
        self.cursor.close()
        self.connection.close()
