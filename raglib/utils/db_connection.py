from psycopg2 import connect
from datetime import datetime, timedelta
from uuid import uuid4
from configparser import ConfigParser

class DatabaseConnection():
    """
    Class for connecting to a Postres-Database and handling the queries for ERI authentication.
    """
    def __init__(self, config):
        """
        Initialises the connection to the database.
        Parameters:
        config (ConfigParser): The config containing information about the database
        """
        # get information about db:
        user = config.get("database", "username").strip()
        password = config.get("database", "password").strip()
        host = config.get("database", "host").strip()
        port = int(config.get("database", "port").strip())
        database_name = config.get("database", "database_name").strip()

        # open connection to postgres db:
        self.connection = connect(user = user, password = password, host = host, port = port, database = database_name)
        self.cursor = self.connection.cursor()

    def close(self):
        """
        Closes the connection to the database.
        """
        self.cursor.close()
        self.connection.close()

    def get_allowed_methods(self, token):
        """
        Returns all supported RAG methods for the given token.
        Parameters:
        token (UUID): The token that will be checked
        """
        try:
            self.cursor.execute("SELECT auth_methods FROM AuthToken WHERE auth_token = %s", (token, ))
            selector = self.cursor.fetchone()
            if(not selector[0]):
                return False
            self.cursor.execute("SELECT method_name FROM AuthMethods WHERE selector = %s;", selector)
            allowed_methods = self.cursor.fetchall()
            return [method[0] for method in allowed_methods]
        except Exception as e:
            return False

    def add_none_token(self, token):
        """
        Adds the given token to the database.
        This token supports all RAG methods except GraphRag.
        The token can now be used to query the remaining API.
        Parameters:
        token (UUID): The token inserted into the database
        """
        gen_id = str(uuid4())
        try:
            self.cursor.execute("INSERT INTO AuthToken VALUES (%s, %s, %s, %s)", (gen_id, token, str(datetime.now() + timedelta(hours=24)), "LIMITED"))
            return True
        except Exception as e:
            print(e)
            return False

    def check_token(self, token):
        """
        Checks if the given token is valid.
        Parameters:
        token (UUID): The token that will be checked
        """
        try:
            self.cursor.execute("SELECT COUNT(datetime) FROM AuthToken WHERE auth_token = %s;", (token, ))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(e)
            return False

    def add_api_key_token(self, token, api_key):
        """
        Adds the given token to the database for the given API-Key.
        If a token already exists it will be overwritten.
        This token supports all RAG methods.
        The token can now be used to query the remaining API.
        Parameters:
        token (UUID): The token that is going to be saved
        api_key (String): The API-Key to check if the user is allowed to issue a token
        """
        self.cursor.execute("SELECT id FROM Token WHERE name = %s;", (api_key, ))
        gen_id = self.cursor.fetchone()
        if(gen_id):
            try:
                self.cursor.execute("SELECT COUNT(datetime) FROM AuthToken WHERE id = %s;", gen_id)
                if(self.cursor.fetchone()[0]):
                    self.cursor.execute("UPDATE AuthToken SET auth_token = %s, datetime = %s WHERE id = %s;", (token, str((datetime.now() + timedelta(hours=24))), gen_id[0]))
                else:
                    self.cursor.execute("INSERT INTO AuthToken VALUES (%s, %s, %s, %s)", (gen_id[0], token, str(datetime.now() + timedelta(hours=24)), "ALL"))
            except Exception as e:
                print(e)
                return False
            return True
        else:
            print("Invalid API-Key")
            return False

    def remove_expired_tokens(self):
        """
        Checks the expiration date on the saved tokens and removes every expired token.
        """
        try:
            self.cursor.execute("DELETE FROM AuthToken WHERE datetime >= %s;", str(datetime.now()))
            return True
        except:
            return False

    def insert_api_key(self, api_key):
        """
        Inserts the given API-Key into the database.
        Now a user is able to issue a token with this API-Key.
        Parameters:
        api_key (String): The API-Key that is going to be added to the database
        """
        try:
            self.cursor.execute("INSERT INTO Token VALUES (%s, %s);", (str(uuid4()), api_key))
            return True
        except Exception as e:
            print(e)
            return False

    def init_tables(self):
        """
        Initialises the database and adds a test token.
        """
        # TODO: check if tables exists and add commits to db!!
        

        self.cursor.execute("CREATE TABLE AuthMethods (selector varchar, method_name varchar);")
        self.cursor.execute("CREATE TABLE AuthToken (id varchar PRIMARY KEY, auth_token varchar, datetime varchar, auth_methods varchar);")
        self.cursor.execute("CREATE TABLE Token (id varchar PRIMARY KEY, name varchar);")

        # adds AuthMethods:
        self.cursor.execute("INSERT INTO AuthMethods VALUES (%s, %s);", ("ALL", "GRAPH_RAG#892743"))
        self.cursor.execute("INSERT INTO AuthMethods VALUES (%s, %s);", ("ALL", "NAIVE_GRAPH_RAG#912378"))
        self.cursor.execute("INSERT INTO AuthMethods VALUES (%s, %s);", ("ALL", "RAG#162478"))
        self.cursor.execute("INSERT INTO AuthMethods VALUES (%s, %s);", ("ALL", "GARAG#783493"))
        self.cursor.execute("INSERT INTO AuthMethods VALUES (%s, %s);", ("LIMITED", "GARAG#783493"))
        self.cursor.execute("INSERT INTO AuthMethods VALUES (%s, %s);", ("LIMITED", "NAIVE_GRAPH_RAG#912378"))
        self.cursor.execute("INSERT INTO AuthMethods VALUES (%s, %s);", ("LIMITED", "RAG#162478"))

        # AuthTokens should be empty

        # Remove expired tokens on startup:
        self.remove_expired_tokens()

        # Add API-Keys into Token:
        return self.insert_api_key("TEST_API_TOKEN")

