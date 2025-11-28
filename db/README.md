## DB Subfolder

This folder will be used, when running the [docker compose setup](../docker-compose.yml). 3 Folders will be created in here:

### db/arango_data

This folder is used by ArangoDB to store the generated KnowledgeGraph and CommunityGraph. It will further be used on user query.

### db/elastic_data

This folder is used by ElasticSearch to store the generated Embeddings of document contents and community summaries. It will further be used on user query.

### db/postgres_data

This folder is used by PostgresDB to store valid ERI-Interface authentications and session tokens.
