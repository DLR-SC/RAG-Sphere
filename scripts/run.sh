SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

if [ "$1" == "init" ]; then
    docker compose -f "$PARENT_DIR/docker/docker-compose_init.yml" up
elif [ "$1" == "down" ]; then
    docker compose -f "$PARENT_DIR/docker/docker-compose_init.yml" down
    docker compose -f "$PARENT_DIR/docker/docker-compose_eri.yml" down
    docker compose -f "$PARENT_DIR/docker/docker-compose_eri_http.yml" down
elif [ "$1" == "http" ]; then
    docker compose -f "$PARENT_DIR/docker/docker-compose_eri_http.yml" up
else
    docker compose -f "$PARENT_DIR/docker/docker-compose_eri.yml" up
fi