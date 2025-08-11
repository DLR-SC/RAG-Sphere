if [ "$1" == "db" ]; then
    docker compose -f "docker/docker-compose_db.yml" up
fi